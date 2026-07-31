"""Retained evidence verification tests for the private OpenAI live smoke."""

from __future__ import annotations

import json

import pytest


def test_verified_evidence_bundle_closes_gate_and_emits_hashes(live_smoke) -> None:
    ticket_path, claim_path, report_path, authorization_id = (
        live_smoke.write_verified_bundle()
    )
    result = live_smoke.audit.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=live_smoke.tmp_path,
    )
    body = result["openai_live_smoke_evidence"]
    assert body["valid"] is True
    assert body["release_gate_state"] == "live_smoke_verified"
    assert body["authorization_id"] == authorization_id
    assert body["audit_ref"] == live_smoke.audit_ref
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


def test_evidence_mismatch_or_unknown_audit_cannot_close_gate(live_smoke) -> None:
    ticket_path, claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["openai_live_smoke"]["audit_ref"] = (
        "openai://responses/client-local/unknown-response"
    )
    live_smoke.smoke._write_report(report_path, report)

    result = live_smoke.audit.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    assert result["valid"] is False
    assert result["release_gate_state"] == "evidence_invalid"
    assert any(not item["passed"] for item in result["checks"])


def test_evidence_rechecks_pinned_model_and_hard_limits(live_smoke) -> None:
    ticket_path, claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    body = ticket["geotask_openai_live_smoke_authorization"]
    body["model"] = "gpt-alias"
    live_smoke.smoke._write_report(ticket_path, ticket)
    result = live_smoke.audit.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    failed_codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "invalid_ticket_model" in failed_codes

    body["model"] = live_smoke.model
    body["output_budget"] = live_smoke.smoke.HARD_MAX_OUTPUT_TOKENS + 1
    live_smoke.smoke._write_report(ticket_path, ticket)
    result = live_smoke.audit.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    failed_codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "invalid_ticket_budget" in failed_codes


def test_evidence_inside_repository_or_path_collision_is_rejected(live_smoke) -> None:
    inside = live_smoke.tmp_path / "inside.json"
    inside.write_text("{}\n", encoding="utf-8")
    result = live_smoke.audit.verify_evidence_bundle(
        inside,
        inside,
        inside,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    assert result["valid"] is False
    codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "evidence_path_collision" in codes

    claim = live_smoke.tmp_path / "claim.json"
    report = live_smoke.tmp_path / "report.json"
    claim.write_text("{}\n", encoding="utf-8")
    report.write_text("{}\n", encoding="utf-8")
    result = live_smoke.audit.verify_evidence_bundle(
        inside,
        claim,
        report,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "evidence_inside_repository" in codes


def test_cli_evidence_verification_is_read_only(
    live_smoke,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ticket_path, _claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    before = {
        ticket_path: ticket_path.read_bytes(),
        report_path: report_path.read_bytes(),
    }
    assert live_smoke.audit.main(
        [
            "verify-evidence",
            "--repository-root",
            str(live_smoke.tmp_path),
            "--authorization-ticket",
            str(ticket_path),
            "--report",
            str(report_path),
        ]
    ) == 0
    evidence = json.loads(capsys.readouterr().out)["openai_live_smoke_evidence"]
    assert evidence["release_gate_state"] == "live_smoke_verified"
    assert all(path.read_bytes() == raw for path, raw in before.items())
