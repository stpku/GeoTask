"""Write-once closure retention tests for the private OpenAI live smoke."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import timedelta

import pytest


def test_verified_evidence_can_be_recorded_as_write_once_closure(live_smoke) -> None:
    ticket_path, claim_path, report_path, authorization_id = (
        live_smoke.write_verified_bundle()
    )
    output_path = (
        live_smoke.tmp_path.parent
        / f"{live_smoke.tmp_path.name}-live-smoke-closure.json"
    )
    output_path.unlink(missing_ok=True)

    original = {
        name: sys.modules.pop(name, None) for name in live_smoke.provider_modules
    }
    try:
        result = live_smoke.audit.write_closure_manifest(
            ticket_path,
            claim_path,
            report_path,
            output_path,
            repository_root=live_smoke.tmp_path,
            now=live_smoke.fixed + timedelta(minutes=3),
        )
        assert all(name not in sys.modules for name in live_smoke.provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value

    body = result["openai_live_smoke_closure_write"]
    assert body["valid"] is True
    assert body["release_gate_state"] == "live_smoke_closure_recorded"
    assert body["authorization_id"] == authorization_id
    assert body["model"] == live_smoke.model
    assert body["audit_ref"] == live_smoke.audit_ref
    assert body["verified_at"] == "2026-07-31T08:03:00Z"
    assert body["live_request_executed"] is True
    assert body["provider_modules_imported"] is False
    assert body["credential_presence_checked"] is False
    assert body["credential_value_exposed"] is False
    assert body["output_created"] is True
    assert all(item["passed"] for item in body["checks"])

    raw = output_path.read_bytes()
    closure = json.loads(raw.decode("utf-8"))["openai_live_smoke_closure"]
    assert set(closure) == {
        "format_version",
        "verifier_version",
        "release_gate_state",
        "verified_at",
        "authorization_id",
        "model",
        "audit_ref",
        "file_hashes",
        "evidence_bundle_sha256",
        "live_request_executed",
        "credential_data_retained",
    }
    assert closure["format_version"] == "1.0"
    assert closure["verifier_version"] == "1.0"
    assert closure["release_gate_state"] == "live_smoke_verified"
    assert closure["authorization_id"] == authorization_id
    assert closure["model"] == live_smoke.model
    assert closure["audit_ref"] == live_smoke.audit_ref
    assert closure["credential_data_retained"] is False
    verified = live_smoke.audit.verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=live_smoke.tmp_path,
    )["openai_live_smoke_evidence"]
    assert closure["file_hashes"] == verified["file_hashes"]
    assert closure["evidence_bundle_sha256"] == verified["evidence_bundle_sha256"]
    assert body["closure_manifest_sha256"] == hashlib.sha256(raw).hexdigest()
    assert str(ticket_path) not in raw.decode("utf-8")
    assert "REDACTED_SECRET" not in raw.decode("utf-8")
    if os.name != "nt":
        assert stat.S_IMODE(output_path.stat().st_mode) == 0o600

    before = raw
    replay = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        output_path,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_write"]
    assert replay["valid"] is False
    assert replay["release_gate_state"] == "closure_not_recorded"
    assert replay["output_created"] is False
    assert any(
        item["code"] == "closure_already_exists" and not item["passed"]
        for item in replay["checks"]
    )
    assert output_path.read_bytes() == before
    assert list(output_path.parent.glob(f"{output_path.name}.*.tmp")) == []


def test_invalid_evidence_or_unsafe_output_cannot_record_closure(live_smoke) -> None:
    ticket_path, claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    output_path = (
        live_smoke.tmp_path.parent
        / f"{live_smoke.tmp_path.name}-invalid-closure.json"
    )
    output_path.unlink(missing_ok=True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["openai_live_smoke"]["audit_ref"] = (
        "openai://responses/client-local/unknown-response"
    )
    live_smoke.smoke._write_report(report_path, report)
    invalid = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        output_path,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=3),
    )["openai_live_smoke_closure_write"]
    assert invalid["valid"] is False
    assert invalid["output_created"] is False
    assert output_path.exists() is False
    assert any(item["code"] == "evidence_not_verified" for item in invalid["checks"])

    ticket_path, claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    inside_repository = live_smoke.tmp_path / "closure.json"
    inside = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        inside_repository,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=3),
    )["openai_live_smoke_closure_write"]
    assert inside["valid"] is False
    assert inside_repository.exists() is False
    assert any(
        item["code"] == "evidence_inside_repository" for item in inside["checks"]
    )

    invalid_suffix = (
        live_smoke.tmp_path.parent / f"{live_smoke.tmp_path.name}-closure.txt"
    )
    invalid_suffix.unlink(missing_ok=True)
    suffix_result = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        invalid_suffix,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=3),
    )["openai_live_smoke_closure_write"]
    assert suffix_result["valid"] is False
    assert invalid_suffix.exists() is False
    assert any(
        item["code"] == "invalid_closure_output"
        for item in suffix_result["checks"]
    )

    report_before = report_path.read_bytes()
    collision = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        report_path,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=3),
    )["openai_live_smoke_closure_write"]
    assert collision["valid"] is False
    assert any(
        item["code"] == "evidence_path_collision" for item in collision["checks"]
    )
    assert report_path.read_bytes() == report_before


def test_post_publish_permission_failure_rolls_back_new_closure(
    live_smoke,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticket_path, claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    output_path = (
        live_smoke.tmp_path.parent
        / f"{live_smoke.tmp_path.name}-rollback-closure.json"
    )
    output_path.unlink(missing_ok=True)
    monkeypatch.setattr(live_smoke.closure, "_is_private_file", lambda _path: False)

    result = live_smoke.audit.write_closure_manifest(
        ticket_path,
        claim_path,
        report_path,
        output_path,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=3),
    )["openai_live_smoke_closure_write"]

    assert result["valid"] is False
    assert result["output_created"] is False
    assert any(
        item["code"] == "insecure_closure_permissions"
        for item in result["checks"]
    )
    assert output_path.exists() is False
    assert list(output_path.parent.glob(f"{output_path.name}.*.tmp")) == []


def test_cli_write_closure_records_once_without_exposing_paths(
    live_smoke,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ticket_path, _claim_path, report_path, _authorization_id = (
        live_smoke.write_verified_bundle()
    )
    output_path = (
        live_smoke.tmp_path.parent / f"{live_smoke.tmp_path.name}-cli-closure.json"
    )
    output_path.unlink(missing_ok=True)
    arguments = [
        "write-closure",
        "--repository-root",
        str(live_smoke.tmp_path),
        "--authorization-ticket",
        str(ticket_path),
        "--report",
        str(report_path),
        "--output",
        str(output_path),
    ]

    assert live_smoke.audit.main(arguments) == 0
    output = capsys.readouterr().out
    body = json.loads(output)["openai_live_smoke_closure_write"]
    assert body["release_gate_state"] == "live_smoke_closure_recorded"
    assert body["output_created"] is True
    assert str(output_path) not in output
    assert output_path.is_file()

    assert live_smoke.audit.main(arguments) == 2
    replay = json.loads(capsys.readouterr().out)["openai_live_smoke_closure_write"]
    assert replay["release_gate_state"] == "closure_not_recorded"
    assert replay["output_created"] is False
