"""Read-only readiness tests for the private OpenAI live smoke."""

from __future__ import annotations

import json
import sys
from datetime import timedelta

import pytest


def test_readiness_is_read_only_and_can_reach_ready_state(live_smoke) -> None:
    plan, ticket_path = live_smoke.issue_ticket()
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    before = ticket_path.read_bytes()
    credential_name = live_smoke.smoke._credential_environment_variable()
    secret_value = "[REDACTED_SECRET]"

    original = {
        name: sys.modules.pop(name, None) for name in live_smoke.provider_modules
    }
    try:
        result = live_smoke.audit.audit_readiness(
            plan,
            environ={
                live_smoke.smoke.ACK_ENVIRONMENT_VARIABLE: (
                    live_smoke.smoke._acknowledgement()
                ),
                credential_name: secret_value,
            },
            now=live_smoke.fixed + timedelta(minutes=1),
            package_probe=lambda _name: True,
        )
        assert all(name not in sys.modules for name in live_smoke.provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value

    body = result["openai_live_smoke_readiness"]
    assert body["valid"] is True
    assert body["release_gate_state"] == "live_execution_ready"
    assert body["authorization_id"] is not None
    assert body["provider_calls_allowed"] == 0
    assert body["live_request_executed"] is False
    assert body["credential_presence_checked"] is True
    assert body["credential_value_exposed"] is False
    assert body["provider_modules_imported"] is False
    assert body["authorization_claim_created"] is False
    assert all(item["passed"] for item in body["checks"])
    assert ticket_path.read_bytes() == before
    assert claim_path.exists() is False
    serialized = json.dumps(result)
    assert secret_value not in serialized
    assert credential_name not in serialized


def test_readiness_reports_all_blockers_without_claiming_ticket(live_smoke) -> None:
    plan, ticket_path = live_smoke.issue_ticket()
    result = live_smoke.audit.audit_readiness(
        plan,
        environ={
            "OPENAI_BASE_URL": "https://example.invalid/v1",
            "OPENAI_LOG": "info",
        },
        now=live_smoke.fixed + timedelta(minutes=1),
        package_probe=lambda _name: False,
    )
    body = result["openai_live_smoke_readiness"]
    failed_codes = {item["code"] for item in body["checks"] if not item["passed"]}
    assert body["valid"] is False
    assert body["release_gate_state"] == "readiness_blocked"
    assert "explicit_acknowledgement" in failed_codes
    assert "server_credential" in failed_codes
    assert "official_endpoint" in failed_codes
    assert "sdk_logging_disabled" in failed_codes
    assert "package:openai" in failed_codes
    assert "package:geotask_model_adapter_reference" in failed_codes
    assert ticket_path.with_suffix(ticket_path.suffix + ".claimed").exists() is False


def test_readiness_rejects_expired_or_claimed_ticket(live_smoke) -> None:
    plan, _ticket_path = live_smoke.issue_ticket(valid_minutes=1)
    environment = {
        live_smoke.smoke.ACK_ENVIRONMENT_VARIABLE: (
            live_smoke.smoke._acknowledgement()
        ),
        live_smoke.smoke._credential_environment_variable(): "[REDACTED_SECRET]",
    }
    expired = live_smoke.audit.audit_readiness(
        plan,
        environ=environment,
        now=live_smoke.fixed + timedelta(minutes=2),
        package_probe=lambda _name: True,
    )["openai_live_smoke_readiness"]
    assert expired["valid"] is False
    assert any(
        item["code"] == "authorization_ticket" and not item["passed"]
        for item in expired["checks"]
    )

    plan, _ticket_path = live_smoke.issue_ticket()
    live_smoke.smoke._claim_authorization_ticket(
        plan,
        now=live_smoke.fixed + timedelta(minutes=1),
    )
    claimed = live_smoke.audit.audit_readiness(
        plan,
        environ=environment,
        now=live_smoke.fixed + timedelta(minutes=2),
        package_probe=lambda _name: True,
    )["openai_live_smoke_readiness"]
    assert claimed["valid"] is False
    assert any("already been claimed" in item["detail"] for item in claimed["checks"])


def test_cli_readiness_is_read_only(
    live_smoke,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    now = live_smoke.smoke._utc_now()
    plan, ticket_path = live_smoke.issue_ticket(now=now)
    monkeypatch.setenv(
        live_smoke.smoke.ACK_ENVIRONMENT_VARIABLE,
        live_smoke.smoke._acknowledgement(),
    )
    monkeypatch.setenv(
        live_smoke.smoke._credential_environment_variable(),
        "[REDACTED_SECRET]",
    )
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_LOG", raising=False)
    monkeypatch.setattr(live_smoke.audit, "_safe_package_probe", lambda _name: True)

    original = {
        name: sys.modules.pop(name, None) for name in live_smoke.provider_modules
    }
    try:
        assert live_smoke.audit.main(
            [
                "readiness",
                "--repository-root",
                str(plan.repository_root),
                "--model",
                live_smoke.model,
                "--authorization-ticket",
                str(ticket_path),
            ]
        ) == 0
        assert all(name not in sys.modules for name in live_smoke.provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value

    readiness = json.loads(capsys.readouterr().out)["openai_live_smoke_readiness"]
    assert readiness["release_gate_state"] == "live_execution_ready"
    assert ticket_path.with_suffix(ticket_path.suffix + ".claimed").exists() is False
