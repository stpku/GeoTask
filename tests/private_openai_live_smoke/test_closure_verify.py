"""Read-only retained closure verification tests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import timedelta

import pytest


def test_closure_verification_reanchors_digest_and_source_evidence(live_smoke) -> None:
    (
        ticket_path,
        claim_path,
        report_path,
        closure_path,
        authorization_id,
        closure_sha256,
    ) = live_smoke.write_verified_closure()
    before = {
        path: path.read_bytes()
        for path in (ticket_path, claim_path, report_path, closure_path)
    }

    original = {
        name: sys.modules.pop(name, None) for name in live_smoke.provider_modules
    }
    try:
        result = live_smoke.audit.verify_closure_manifest(
            ticket_path,
            claim_path,
            report_path,
            closure_path,
            expected_closure_sha256=closure_sha256,
            repository_root=live_smoke.tmp_path,
            now=live_smoke.fixed + timedelta(minutes=4),
        )
        assert all(name not in sys.modules for name in live_smoke.provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value

    body = result["openai_live_smoke_closure_verification"]
    assert body["valid"] is True
    assert body["release_gate_state"] == "live_smoke_closure_verified"
    assert body["authorization_id"] == authorization_id
    assert body["model"] == live_smoke.model
    assert body["audit_ref"] == live_smoke.audit_ref
    assert body["verified_at"] == "2026-07-31T08:03:00Z"
    assert body["closure_manifest_sha256"] == closure_sha256
    assert body["closure_digest_anchored"] is True
    assert body["live_request_executed"] is True
    assert body["provider_modules_imported"] is False
    assert body["credential_presence_checked"] is False
    assert body["credential_value_exposed"] is False
    assert body["evidence_mutated"] is False
    assert all(item["passed"] for item in body["checks"])
    assert all(path.read_bytes() == raw for path, raw in before.items())


def test_closure_verification_rejects_wrong_or_malformed_digest(live_smoke) -> None:
    ticket, claim, report, closure, _authorization_id, _digest = (
        live_smoke.write_verified_closure()
    )
    before = closure.read_bytes()

    mismatch = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256="0" * 64,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert mismatch["valid"] is False
    assert mismatch["release_gate_state"] == "closure_invalid"
    assert mismatch["closure_manifest_sha256"] == hashlib.sha256(before).hexdigest()
    assert mismatch["closure_digest_anchored"] is False
    assert any(
        item["code"] == "closure_digest_mismatch"
        for item in mismatch["checks"]
    )

    malformed = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256="not-a-sha256",
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert malformed["valid"] is False
    assert any(item["code"] == "invalid_sha256" for item in malformed["checks"])
    assert closure.read_bytes() == before


def test_rehashed_closure_tampering_still_fails_evidence_and_time_binding(
    live_smoke,
) -> None:
    ticket, claim, report, closure, _authorization_id, _digest = (
        live_smoke.write_verified_closure()
    )
    payload = json.loads(closure.read_text(encoding="utf-8"))
    payload["openai_live_smoke_closure"]["model"] = "gpt-other-2026-07-31"
    live_smoke.smoke._write_report(closure, payload)
    changed_digest = hashlib.sha256(closure.read_bytes()).hexdigest()
    changed = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=changed_digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert changed["valid"] is False
    assert changed["closure_digest_anchored"] is True
    assert any(
        item["code"] == "closure_evidence_mismatch"
        for item in changed["checks"]
    )

    ticket, claim, report, closure, _authorization_id, _digest = (
        live_smoke.write_verified_closure()
    )
    payload = json.loads(closure.read_text(encoding="utf-8"))
    payload["openai_live_smoke_closure"]["verified_at"] = "2026-07-31T08:01:00Z"
    live_smoke.smoke._write_report(closure, payload)
    changed_digest = hashlib.sha256(closure.read_bytes()).hexdigest()
    time_invalid = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=changed_digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert time_invalid["valid"] is False
    assert any(
        item["code"] == "invalid_closure_time"
        for item in time_invalid["checks"]
    )

    ticket, claim, report, closure, _authorization_id, _digest = (
        live_smoke.write_verified_closure()
    )
    payload = json.loads(closure.read_text(encoding="utf-8"))
    payload["openai_live_smoke_closure"]["unexpected"] = True
    live_smoke.smoke._write_report(closure, payload)
    changed_digest = hashlib.sha256(closure.read_bytes()).hexdigest()
    contract_invalid = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=changed_digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert contract_invalid["valid"] is False
    assert any(
        item["code"] == "invalid_closure_contract"
        for item in contract_invalid["checks"]
    )


def test_closure_verification_rejects_non_strict_json(live_smoke) -> None:
    ticket, claim, report, closure, _authorization_id, _digest = (
        live_smoke.write_verified_closure()
    )
    raw = closure.read_text(encoding="utf-8")
    model_line = f'    "model": "{live_smoke.model}",\n'
    duplicate = raw.replace(model_line, model_line + model_line, 1)
    assert duplicate != raw
    closure.write_text(duplicate, encoding="utf-8", newline="\n")
    if os.name != "nt":
        closure.chmod(0o600)
    changed_digest = hashlib.sha256(closure.read_bytes()).hexdigest()

    result = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=changed_digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]

    assert result["valid"] is False
    assert result["closure_digest_anchored"] is False
    assert any(
        item["code"] == "invalid_closure_json" for item in result["checks"]
    )


def test_closure_verification_detects_changed_source_evidence(live_smoke) -> None:
    ticket, claim, report, closure, _authorization_id, digest = (
        live_smoke.write_verified_closure()
    )
    report_payload = json.loads(report.read_text(encoding="utf-8"))
    report_payload["openai_live_smoke"]["elapsed_ms"] = 126
    live_smoke.smoke._write_report(report, report_payload)

    result = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert result["valid"] is False
    assert result["closure_digest_anchored"] is True
    assert any(
        item["code"] == "closure_evidence_mismatch"
        for item in result["checks"]
    )


def test_closure_verification_detects_midflight_source_evidence_change(
    live_smoke,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticket, claim, report, closure, _authorization_id, digest = (
        live_smoke.write_verified_closure()
    )
    original_verify = live_smoke.closure_verifier.verify_evidence_bundle
    call_count = 0

    def unstable_verify(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        result = original_verify(*args, **kwargs)
        if call_count == 2:
            result = json.loads(json.dumps(result))
            body = result["openai_live_smoke_evidence"]
            body["file_hashes"]["report_sha256"] = "f" * 64
            body["evidence_bundle_sha256"] = "e" * 64
        return result

    monkeypatch.setattr(
        live_smoke.closure_verifier,
        "verify_evidence_bundle",
        unstable_verify,
    )
    result = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        closure,
        expected_closure_sha256=digest,
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]

    assert call_count == 2
    assert result["valid"] is False
    assert result["closure_digest_anchored"] is True
    assert any(
        item["code"] == "source_evidence_changed_during_verification"
        for item in result["checks"]
    )


def test_closure_verification_rejects_repository_path_or_open_permissions(
    live_smoke,
) -> None:
    ticket, claim, report, closure, _authorization_id, digest = (
        live_smoke.write_verified_closure()
    )
    inside = live_smoke.tmp_path / "retained-closure.json"
    inside.write_bytes(closure.read_bytes())
    if os.name != "nt":
        inside.chmod(0o600)
    inside_result = live_smoke.audit.verify_closure_manifest(
        ticket,
        claim,
        report,
        inside,
        expected_closure_sha256=hashlib.sha256(inside.read_bytes()).hexdigest(),
        repository_root=live_smoke.tmp_path,
        now=live_smoke.fixed + timedelta(minutes=4),
    )["openai_live_smoke_closure_verification"]
    assert inside_result["valid"] is False
    assert any(
        item["code"] == "evidence_inside_repository"
        for item in inside_result["checks"]
    )

    if os.name != "nt":
        closure.chmod(0o644)
        permission_result = live_smoke.audit.verify_closure_manifest(
            ticket,
            claim,
            report,
            closure,
            expected_closure_sha256=digest,
            repository_root=live_smoke.tmp_path,
            now=live_smoke.fixed + timedelta(minutes=4),
        )["openai_live_smoke_closure_verification"]
        assert permission_result["valid"] is False
        assert any(
            item["code"] == "insecure_closure_permissions"
            for item in permission_result["checks"]
        )


def test_cli_verify_closure_is_read_only_and_path_redacted(
    live_smoke,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ticket, _claim, report, closure, _authorization_id, digest = (
        live_smoke.write_verified_closure()
    )
    before = closure.read_bytes()
    arguments = [
        "verify-closure",
        "--repository-root",
        str(live_smoke.tmp_path),
        "--authorization-ticket",
        str(ticket),
        "--report",
        str(report),
        "--closure",
        str(closure),
        "--expected-closure-sha256",
        digest,
    ]

    assert live_smoke.audit.main(arguments) == 0
    output = capsys.readouterr().out
    body = json.loads(output)["openai_live_smoke_closure_verification"]
    assert body["release_gate_state"] == "live_smoke_closure_verified"
    assert body["closure_digest_anchored"] is True
    assert str(ticket) not in output
    assert str(report) not in output
    assert str(closure) not in output
    assert closure.read_bytes() == before

    arguments[-1] = "0" * 64
    assert live_smoke.audit.main(arguments) == 2
    failed = json.loads(capsys.readouterr().out)[
        "openai_live_smoke_closure_verification"
    ]
    assert failed["release_gate_state"] == "closure_invalid"
    assert failed["closure_digest_anchored"] is False
