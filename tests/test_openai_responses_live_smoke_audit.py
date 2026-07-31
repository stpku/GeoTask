"""Offline tests for private live-smoke readiness and evidence auditing."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "examples" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

SMOKE = importlib.import_module("openai_responses_live_smoke")
AUDIT = importlib.import_module("openai_responses_live_smoke_audit")


FIXED = datetime(2026, 7, 31, 8, 0, tzinfo=timezone.utc)
MODEL = "gpt-test-2026-07-31"
AUDIT_REF = "openai://responses/req_server/resp_server"


def _repository(tmp_path: Path) -> Path:
    request = (
        tmp_path
        / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
    )
    request.parent.mkdir(parents=True, exist_ok=True)
    source = (
        ROOT
        / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
    )
    request.write_bytes(source.read_bytes())
    return tmp_path


def _plan(
    tmp_path: Path,
    *,
    ticket_path: Path | None = None,
    output_budget: int = 2048,
    timeout_seconds: float = 60.0,
):
    return SMOKE.LiveSmokePlan(
        repository_root=_repository(tmp_path),
        model=MODEL,
        output_budget=output_budget,
        timeout_seconds=timeout_seconds,
        execute_live=True,
        authorization_ticket_path=ticket_path,
    )


def _issue_ticket(
    tmp_path: Path,
    *,
    now: datetime = FIXED,
    valid_minutes: int = 15,
    output_budget: int = 2048,
    timeout_seconds: float = 60.0,
) -> tuple[object, Path]:
    ticket_path = tmp_path.parent / f"{tmp_path.name}-authorization.json"
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    ticket_path.unlink(missing_ok=True)
    claim_path.unlink(missing_ok=True)
    plan = _plan(
        tmp_path,
        output_budget=output_budget,
        timeout_seconds=timeout_seconds,
    )
    SMOKE.issue_authorization_ticket(
        plan,
        ticket_path,
        valid_minutes=valid_minutes,
        environ={
            SMOKE.ACK_ENVIRONMENT_VARIABLE: SMOKE._acknowledgement(),
        },
        now=now,
    )
    return (
        _plan(
            tmp_path,
            ticket_path=ticket_path,
            output_budget=output_budget,
            timeout_seconds=timeout_seconds,
        ),
        ticket_path,
    )


def _write_verified_bundle(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    plan, ticket_path = _issue_ticket(tmp_path)
    authorization_id = SMOKE._claim_authorization_ticket(
        plan,
        now=FIXED + timedelta(minutes=1),
    )
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    claim = json.loads(claim_path.read_text(encoding="utf-8"))["authorization_claim"]
    finalized_claim = {
        "authorization_claim": {
            "authorization_id": authorization_id,
            "claimed_at": claim["claimed_at"],
            "finalized_at": "2026-07-31T08:02:00Z",
            "ticket_sha256": claim["ticket_sha256"],
            "state": "live_smoke_verified",
            "live_request_executed": True,
            "runtime_state": "completed",
            "audit_ref": AUDIT_REF,
            "valid": True,
        }
    }
    SMOKE._write_report(claim_path, finalized_claim)

    report_path = tmp_path.parent / f"{tmp_path.name}-live-smoke-report.json"
    report_path.unlink(missing_ok=True)
    report = {
        "openai_live_smoke": {
            "valid": True,
            "release_gate_state": "live_smoke_verified",
            "authorization_id": authorization_id,
            "model": MODEL,
            "runtime_state": "completed",
            "retryable": False,
            "side_effects_executed": True,
            "audit_ref": AUDIT_REF,
            "diagnostic_codes": [],
            "output_artifact_ids": ["geotask.execution-result"],
            "elapsed_ms": 125,
            "output_budget": 2048,
            "timeout_seconds": 60.0,
            "provider_calls_allowed": 1,
            "automatic_retries_allowed": 0,
            "tools_allowed": False,
            "response_storage_allowed": False,
            "live_request_executed": True,
            "versions": {
                "openai": "2.test",
                "geotask_core": "0.3.test",
                "openai_adapter": "0.1.test",
            },
        }
    }
    SMOKE._write_report(report_path, report)
    return ticket_path, claim_path, report_path, authorization_id


def test_readiness_is_read_only_and_can_reach_ready_state(tmp_path: Path) -> None:
    plan, ticket_path = _issue_ticket(tmp_path)
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    before = ticket_path.read_bytes()
    credential_name = SMOKE._credential_environment_variable()
    secret_value = "[REDACTED_SECRET]"

    provider_modules = (
        "openai",
        "geotask_core",
        "geotask_openai_responses_adapter",
    )
    original = {name: sys.modules.pop(name, None) for name in provider_modules}
    try:
        result = AUDIT.audit_readiness(
            plan,
            environ={
                SMOKE.ACK_ENVIRONMENT_VARIABLE: SMOKE._acknowledgement(),
                credential_name: secret_value,
            },
            now=FIXED + timedelta(minutes=1),
            package_probe=lambda _name: True,
        )
        assert all(name not in sys.modules for name in provider_modules)
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


def test_readiness_reports_all_blockers_without_claiming_ticket(tmp_path: Path) -> None:
    plan, ticket_path = _issue_ticket(tmp_path)
    result = AUDIT.audit_readiness(
        plan,
        environ={
            "OPENAI_BASE_URL": "https://example.invalid/v1",
            "OPENAI_LOG": "info",
        },
        now=FIXED + timedelta(minutes=1),
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


def test_readiness_rejects_expired_or_claimed_ticket(tmp_path: Path) -> None:
    plan, ticket_path = _issue_ticket(tmp_path, valid_minutes=1)
    environment = {
        SMOKE.ACK_ENVIRONMENT_VARIABLE: SMOKE._acknowledgement(),
        SMOKE._credential_environment_variable(): "[REDACTED_SECRET]",
    }
    expired = AUDIT.audit_readiness(
        plan,
        environ=environment,
        now=FIXED + timedelta(minutes=2),
        package_probe=lambda _name: True,
    )["openai_live_smoke_readiness"]
    assert expired["valid"] is False
    assert any(
        item["code"] == "authorization_ticket" and not item["passed"]
        for item in expired["checks"]
    )

    plan, ticket_path = _issue_ticket(tmp_path)
    SMOKE._claim_authorization_ticket(plan, now=FIXED + timedelta(minutes=1))
    claimed = AUDIT.audit_readiness(
        plan,
        environ=environment,
        now=FIXED + timedelta(minutes=2),
        package_probe=lambda _name: True,
    )["openai_live_smoke_readiness"]
    assert claimed["valid"] is False
    assert any("already been claimed" in item["detail"] for item in claimed["checks"])


def test_verified_evidence_bundle_closes_gate_and_emits_hashes(tmp_path: Path) -> None:
    ticket_path, claim_path, report_path, authorization_id = _write_verified_bundle(
        tmp_path
    )
    result = AUDIT.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=tmp_path,
    )
    body = result["openai_live_smoke_evidence"]
    assert body["valid"] is True
    assert body["release_gate_state"] == "live_smoke_verified"
    assert body["authorization_id"] == authorization_id
    assert body["audit_ref"] == AUDIT_REF
    assert body["live_request_executed"] is True
    assert body["provider_modules_imported"] is False
    assert body["credential_presence_checked"] is False
    assert body["credential_value_exposed"] is False
    assert set(body["file_hashes"]) == {
        "ticket_sha256",
        "claim_sha256",
        "report_sha256",
    }
    assert len(body["evidence_bundle_sha256"]) == 64
    assert all(item["passed"] for item in body["checks"])


def test_evidence_mismatch_or_unknown_audit_cannot_close_gate(tmp_path: Path) -> None:
    ticket_path, claim_path, report_path, _authorization_id = _write_verified_bundle(
        tmp_path
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["openai_live_smoke"]["audit_ref"] = (
        "openai://responses/client-local/unknown-response"
    )
    SMOKE._write_report(report_path, report)

    result = AUDIT.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=tmp_path,
    )["openai_live_smoke_evidence"]
    assert result["valid"] is False
    assert result["release_gate_state"] == "evidence_invalid"
    assert any(not item["passed"] for item in result["checks"])


def test_evidence_rechecks_pinned_model_and_hard_limits(tmp_path: Path) -> None:
    ticket_path, claim_path, report_path, _authorization_id = _write_verified_bundle(
        tmp_path
    )
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    body = ticket["geotask_openai_live_smoke_authorization"]
    body["model"] = "gpt-alias"
    SMOKE._write_report(ticket_path, ticket)
    result = AUDIT.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=tmp_path,
    )["openai_live_smoke_evidence"]
    failed_codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "invalid_ticket_model" in failed_codes

    body["model"] = MODEL
    body["output_budget"] = SMOKE.HARD_MAX_OUTPUT_TOKENS + 1
    SMOKE._write_report(ticket_path, ticket)
    result = AUDIT.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=tmp_path,
    )["openai_live_smoke_evidence"]
    failed_codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "invalid_ticket_budget" in failed_codes


def test_evidence_inside_repository_or_path_collision_is_rejected(
    tmp_path: Path,
) -> None:
    inside = tmp_path / "inside.json"
    inside.write_text("{}\n", encoding="utf-8")
    result = AUDIT.verify_evidence_bundle(
        inside,
        inside,
        inside,
        repository_root=tmp_path,
    )["openai_live_smoke_evidence"]
    assert result["valid"] is False
    codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "evidence_path_collision" in codes

    claim = tmp_path / "claim.json"
    report = tmp_path / "report.json"
    claim.write_text("{}\n", encoding="utf-8")
    report.write_text("{}\n", encoding="utf-8")
    result = AUDIT.verify_evidence_bundle(
        inside,
        claim,
        report,
        repository_root=tmp_path,
    )["openai_live_smoke_evidence"]
    codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "evidence_inside_repository" in codes


def test_cli_readiness_and_evidence_are_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    now = SMOKE._utc_now()
    plan, ticket_path = _issue_ticket(tmp_path, now=now)
    monkeypatch.setenv(SMOKE.ACK_ENVIRONMENT_VARIABLE, SMOKE._acknowledgement())
    monkeypatch.setenv(
        SMOKE._credential_environment_variable(),
        "[REDACTED_SECRET]",
    )
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_LOG", raising=False)
    monkeypatch.setattr(AUDIT, "_safe_package_probe", lambda _name: True)

    provider_modules = (
        "openai",
        "geotask_core",
        "geotask_openai_responses_adapter",
    )
    original = {name: sys.modules.pop(name, None) for name in provider_modules}
    try:
        assert AUDIT.main(
            [
                "readiness",
                "--repository-root",
                str(plan.repository_root),
                "--model",
                MODEL,
                "--authorization-ticket",
                str(ticket_path),
            ]
        ) == 0
        assert all(name not in sys.modules for name in provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value
    readiness = json.loads(capsys.readouterr().out)["openai_live_smoke_readiness"]
    assert readiness["release_gate_state"] == "live_execution_ready"
    assert ticket_path.with_suffix(ticket_path.suffix + ".claimed").exists() is False

    ticket_path, claim_path, report_path, _authorization_id = _write_verified_bundle(
        tmp_path
    )
    assert AUDIT.main(
        [
            "verify-evidence",
            "--repository-root",
            str(tmp_path),
            "--authorization-ticket",
            str(ticket_path),
            "--report",
            str(report_path),
        ]
    ) == 0
    evidence = json.loads(capsys.readouterr().out)["openai_live_smoke_evidence"]
    assert evidence["release_gate_state"] == "live_smoke_verified"


def test_official_sdk_mock_transport_serializes_one_strict_response_call() -> None:
    openai = pytest.importorskip("openai", minversion="2.46.0")
    httpx = pytest.importorskip("httpx")

    neutral_src = ROOT / "examples/model_adapters/provider_neutral/src"
    openai_src = ROOT / "examples/model_adapters/openai_responses/src"
    for package_src in (neutral_src, openai_src):
        if str(package_src) not in sys.path:
            sys.path.insert(0, str(package_src))

    from geotask_core import submit_runtime_request
    from geotask_openai_responses_adapter import (
        OPENAI_AUTHORIZATION_REF,
        OpenAIResponsesConfig,
        StaticOpenAIClientResolver,
        build_openai_responses_runtime_adapter,
    )

    request_payload = json.loads(
        (
            ROOT
            / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
        ).read_text(encoding="utf-8")
    )
    output_payload = json.loads(
        (
            ROOT
            / "examples/model_adapters/provider_neutral/examples/mock_model_execution_result.json"
        ).read_text(encoding="utf-8")
    )
    envelope = json.dumps(
        {
            "artifact_json": json.dumps(
                output_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        },
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    captured: dict[str, object] = {}

    def handler(request: object):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"x-request-id": "req_sdk_mock_001"},
            json={
                "id": "resp_sdk_mock_001",
                "object": "response",
                "created_at": 1785488400,
                "status": "completed",
                "model": "gpt-4.1-mini-2025-04-14",
                "output": [
                    {
                        "id": "msg_sdk_mock_001",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": envelope,
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = openai.OpenAI(
        api_key="[REDACTED_SECRET]",
        max_retries=0,
        timeout=60.0,
        http_client=http_client,
    )
    try:
        adapter = build_openai_responses_runtime_adapter(
            OpenAIResponsesConfig(
                model="gpt-4.1-mini-2025-04-14",
                max_output_tokens=2048,
            ),
            StaticOpenAIClientResolver(OPENAI_AUTHORIZATION_REF, client),
        )
        response = submit_runtime_request(adapter, request_payload)
    finally:
        client.close()

    assert response.state == "completed"
    assert response.side_effects_executed is True
    assert response.audit_ref == (
        "openai://responses/req_sdk_mock_001/resp_sdk_mock_001"
    )
    assert [item.artifact_id for item in response.output_artifacts] == [
        "geotask.execution-result"
    ]
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    body = captured["body"]
    assert body["model"] == "gpt-4.1-mini-2025-04-14"
    assert body["store"] is False
    assert body["truncation"] == "disabled"
    assert body["max_output_tokens"] == 2048
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "tools" not in body
    assert client.max_retries == 0


def test_private_auditor_and_tests_are_excluded_from_public_export() -> None:
    import yaml

    release_dir = ROOT / ".release"
    if str(release_dir) not in sys.path:
        sys.path.insert(0, str(release_dir))
    import export_public

    manifest = yaml.safe_load(
        (release_dir / "public-manifest.yaml").read_text(encoding="utf-8")
    )
    exported = {
        path.relative_to(ROOT).as_posix()
        for path in export_public.collect_files(manifest)
    }
    assert "examples/runtime/openai_responses_live_smoke_audit.py" not in exported
    assert "examples/runtime/openai_responses_live_smoke_evidence.py" not in exported
    assert "tests/test_openai_responses_live_smoke_audit.py" not in exported
