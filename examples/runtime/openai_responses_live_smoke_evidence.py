"""Strict verification of retained OpenAI live-smoke evidence.

The verifier reads only redacted ticket, claim, and report files. It never
imports provider modules, checks credential presence, creates claims, or sends
network requests. This file remains outside the public export and normal CI.
"""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping

try:  # Package import when loaded through examples.runtime.
    from .openai_responses_live_smoke import (
        HARD_MAX_AUTHORIZATION_VALID_MINUTES,
        HARD_MAX_OUTPUT_TOKENS,
        HARD_MAX_TIMEOUT_SECONDS,
        LiveSmokePreflightError,
        _EXPECTED_REQUEST_SHA256,
        _PINNED_MODEL_PATTERN,
        _parse_timestamp,
        _strict_json_object,
    )
except ImportError:  # Direct loading from examples/runtime.
    from openai_responses_live_smoke import (  # type: ignore[no-redef]
        HARD_MAX_AUTHORIZATION_VALID_MINUTES,
        HARD_MAX_OUTPUT_TOKENS,
        HARD_MAX_TIMEOUT_SECONDS,
        LiveSmokePreflightError,
        _EXPECTED_REQUEST_SHA256,
        _PINNED_MODEL_PATTERN,
        _parse_timestamp,
        _strict_json_object,
    )


_TICKET_TOP_LEVEL_KEY = "geotask_openai_live_smoke_authorization"
_CLAIM_TOP_LEVEL_KEY = "authorization_claim"
_REPORT_TOP_LEVEL_KEY = "openai_live_smoke"


class EvidenceVerificationError(ValueError):
    """Raised when a retained evidence bundle cannot close the live gate."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _check(code: str, passed: bool, detail: str) -> dict[str, object]:
    return {"code": code, "passed": passed, "detail": detail}


def _is_private_file(path: Path) -> bool:
    if os.name == "nt":
        return True
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def _validate_external_evidence_paths(
    repository_root: Path,
    *paths: Path,
) -> tuple[Path, ...]:
    root = repository_root.resolve()
    resolved = tuple(path.resolve() for path in paths)
    if len(set(resolved)) != len(resolved):
        raise EvidenceVerificationError(
            "evidence_path_collision", "ticket, claim, and report must be distinct files"
        )
    for path in resolved:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        raise EvidenceVerificationError(
            "evidence_inside_repository",
            "live-smoke evidence must remain outside the repository",
        )
    return resolved


def _canonical_uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise EvidenceVerificationError("invalid_authorization_id", f"{label} is missing")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise EvidenceVerificationError(
            "invalid_authorization_id", f"{label} must be a UUID"
        ) from exc
    if str(parsed) != value:
        raise EvidenceVerificationError(
            "invalid_authorization_id", f"{label} must use canonical UUID form"
        )
    return value


def _server_audit_reference(value: object) -> bool:
    prefix = "openai://responses/"
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    parts = value[len(prefix) :].split("/")
    return (
        len(parts) == 2
        and all(parts)
        and not parts[0].startswith("client-")
        and parts[1] != "unknown-response"
    )


def _strict_ticket(path: Path) -> tuple[dict[str, object], bytes, datetime, datetime]:
    payload, raw = _strict_json_object(path, "authorization ticket")
    if set(payload) != {_TICKET_TOP_LEVEL_KEY}:
        raise EvidenceVerificationError(
            "invalid_ticket_contract",
            "authorization ticket must contain exactly one body",
        )
    if not _is_private_file(path):
        raise EvidenceVerificationError(
            "insecure_ticket_permissions",
            "authorization ticket permissions are not private",
        )
    body = payload.get(_TICKET_TOP_LEVEL_KEY)
    if not isinstance(body, dict):
        raise EvidenceVerificationError(
            "invalid_ticket_contract", "authorization ticket body is missing"
        )
    required = {
        "format_version",
        "authorization_id",
        "state",
        "issued_at",
        "expires_at",
        "model",
        "output_budget",
        "timeout_seconds",
        "request_sha256",
        "max_provider_calls",
        "automatic_retries_allowed",
        "tools_allowed",
        "response_storage_allowed",
    }
    if set(body) != required:
        raise EvidenceVerificationError(
            "invalid_ticket_contract", "authorization ticket fields are not exact"
        )
    _canonical_uuid(body.get("authorization_id"), "ticket authorization_id")
    if body.get("format_version") != "1.0" or body.get("state") != "issued":
        raise EvidenceVerificationError(
            "invalid_ticket_contract", "authorization ticket version or state is invalid"
        )
    if body.get("request_sha256") != _EXPECTED_REQUEST_SHA256:
        raise EvidenceVerificationError(
            "request_digest_mismatch", "ticket request digest is not the reviewed digest"
        )
    expected_controls = {
        "max_provider_calls": 1,
        "automatic_retries_allowed": 0,
        "tools_allowed": False,
        "response_storage_allowed": False,
    }
    for key, expected in expected_controls.items():
        if body.get(key) != expected:
            raise EvidenceVerificationError(
                "invalid_ticket_controls", f"ticket {key} is not fail-closed"
            )
    model = body.get("model")
    if (
        not isinstance(model, str)
        or not model.strip()
        or not _PINNED_MODEL_PATTERN.fullmatch(model)
    ):
        raise EvidenceVerificationError(
            "invalid_ticket_model",
            "ticket model must be a pinned snapshot ending in YYYY-MM-DD",
        )
    budget = body.get("output_budget")
    timeout = body.get("timeout_seconds")
    if (
        isinstance(budget, bool)
        or not isinstance(budget, int)
        or budget <= 0
        or budget > HARD_MAX_OUTPUT_TOKENS
    ):
        raise EvidenceVerificationError(
            "invalid_ticket_budget", "ticket budget exceeds the reviewed limits"
        )
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
        or timeout > HARD_MAX_TIMEOUT_SECONDS
    ):
        raise EvidenceVerificationError(
            "invalid_ticket_timeout", "ticket timeout exceeds the reviewed limits"
        )
    try:
        issued_at = _parse_timestamp(body.get("issued_at"), "ticket issued_at")
        expires_at = _parse_timestamp(body.get("expires_at"), "ticket expires_at")
    except LiveSmokePreflightError as exc:
        raise EvidenceVerificationError("invalid_ticket_time", str(exc)) from exc
    if expires_at <= issued_at:
        raise EvidenceVerificationError(
            "invalid_ticket_time", "ticket expiry is not after issuance"
        )
    if expires_at - issued_at > timedelta(
        minutes=HARD_MAX_AUTHORIZATION_VALID_MINUTES
    ):
        raise EvidenceVerificationError(
            "invalid_ticket_time", "ticket validity exceeds the hard maximum"
        )
    return body, raw, issued_at, expires_at


def _strict_claim(
    path: Path,
    *,
    ticket_body: Mapping[str, object],
    ticket_raw: bytes,
    issued_at: datetime,
    expires_at: datetime,
) -> tuple[dict[str, object], bytes, datetime, datetime]:
    payload, raw = _strict_json_object(path, "authorization claim")
    if set(payload) != {_CLAIM_TOP_LEVEL_KEY}:
        raise EvidenceVerificationError(
            "invalid_claim_contract", "authorization claim must contain exactly one body"
        )
    if not _is_private_file(path):
        raise EvidenceVerificationError(
            "insecure_claim_permissions", "authorization claim permissions are not private"
        )
    body = payload.get(_CLAIM_TOP_LEVEL_KEY)
    if not isinstance(body, dict):
        raise EvidenceVerificationError(
            "invalid_claim_contract", "authorization claim body is missing"
        )
    required = {
        "authorization_id",
        "claimed_at",
        "finalized_at",
        "ticket_sha256",
        "state",
        "live_request_executed",
        "runtime_state",
        "audit_ref",
        "valid",
    }
    if set(body) != required:
        raise EvidenceVerificationError(
            "invalid_claim_contract", "authorization claim fields are not exact"
        )
    if body.get("authorization_id") != ticket_body.get("authorization_id"):
        raise EvidenceVerificationError(
            "authorization_mismatch", "claim authorization ID does not match ticket"
        )
    if body.get("ticket_sha256") != hashlib.sha256(ticket_raw).hexdigest():
        raise EvidenceVerificationError(
            "ticket_digest_mismatch", "claim no longer matches the retained ticket"
        )
    if body.get("state") != "live_smoke_verified":
        raise EvidenceVerificationError(
            "claim_not_verified", "claim state is not live_smoke_verified"
        )
    if body.get("valid") is not True or body.get("live_request_executed") is not True:
        raise EvidenceVerificationError(
            "claim_not_verified", "claim does not record a successful live request"
        )
    if body.get("runtime_state") != "completed":
        raise EvidenceVerificationError(
            "claim_not_verified", "claim Runtime state is not completed"
        )
    if not _server_audit_reference(body.get("audit_ref")):
        raise EvidenceVerificationError(
            "invalid_server_audit", "claim lacks server request and response identifiers"
        )
    try:
        claimed_at = _parse_timestamp(body.get("claimed_at"), "claim claimed_at")
        finalized_at = _parse_timestamp(body.get("finalized_at"), "claim finalized_at")
    except LiveSmokePreflightError as exc:
        raise EvidenceVerificationError("invalid_claim_time", str(exc)) from exc
    if claimed_at < issued_at - timedelta(seconds=5) or claimed_at >= expires_at:
        raise EvidenceVerificationError(
            "invalid_claim_time", "claim time is outside the ticket validity window"
        )
    if finalized_at < claimed_at:
        raise EvidenceVerificationError(
            "invalid_claim_time", "claim finalization precedes claim creation"
        )
    return body, raw, claimed_at, finalized_at


def _strict_report(
    path: Path,
    *,
    ticket_body: Mapping[str, object],
    claim_body: Mapping[str, object],
) -> tuple[dict[str, object], bytes]:
    payload, raw = _strict_json_object(path, "live smoke report")
    if set(payload) != {_REPORT_TOP_LEVEL_KEY}:
        raise EvidenceVerificationError(
            "invalid_report_contract", "report must contain exactly one live-smoke body"
        )
    if not _is_private_file(path):
        raise EvidenceVerificationError(
            "insecure_report_permissions", "live-smoke report permissions are not private"
        )
    body = payload.get(_REPORT_TOP_LEVEL_KEY)
    if not isinstance(body, dict):
        raise EvidenceVerificationError(
            "invalid_report_contract", "live-smoke report body is missing"
        )
    required = {
        "valid",
        "release_gate_state",
        "authorization_id",
        "model",
        "runtime_state",
        "retryable",
        "side_effects_executed",
        "audit_ref",
        "diagnostic_codes",
        "output_artifact_ids",
        "elapsed_ms",
        "output_budget",
        "timeout_seconds",
        "provider_calls_allowed",
        "automatic_retries_allowed",
        "tools_allowed",
        "response_storage_allowed",
        "live_request_executed",
        "versions",
    }
    if set(body) != required:
        raise EvidenceVerificationError(
            "invalid_report_contract", "live-smoke report fields are not exact"
        )
    success_values = {
        "valid": True,
        "release_gate_state": "live_smoke_verified",
        "authorization_id": ticket_body.get("authorization_id"),
        "model": ticket_body.get("model"),
        "runtime_state": "completed",
        "retryable": False,
        "side_effects_executed": True,
        "audit_ref": claim_body.get("audit_ref"),
        "diagnostic_codes": [],
        "output_artifact_ids": ["geotask.execution-result"],
        "output_budget": ticket_body.get("output_budget"),
        "timeout_seconds": ticket_body.get("timeout_seconds"),
        "provider_calls_allowed": 1,
        "automatic_retries_allowed": 0,
        "tools_allowed": False,
        "response_storage_allowed": False,
        "live_request_executed": True,
    }
    for key, expected in success_values.items():
        if body.get(key) != expected:
            raise EvidenceVerificationError(
                "report_not_verified", f"report {key} does not satisfy the live gate"
            )
    if not _server_audit_reference(body.get("audit_ref")):
        raise EvidenceVerificationError(
            "invalid_server_audit", "report lacks server request and response identifiers"
        )
    elapsed_ms = body.get("elapsed_ms")
    if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int) or elapsed_ms < 0:
        raise EvidenceVerificationError(
            "invalid_report_timing", "report elapsed_ms is invalid"
        )
    versions = body.get("versions")
    if not isinstance(versions, dict) or set(versions) != {
        "openai",
        "geotask_core",
        "openai_adapter",
    }:
        raise EvidenceVerificationError(
            "invalid_report_versions", "report versions are incomplete"
        )
    if not all(isinstance(value, str) and value.strip() for value in versions.values()):
        raise EvidenceVerificationError(
            "invalid_report_versions", "report versions must be non-empty strings"
        )
    return body, raw


def verify_evidence_bundle(
    ticket_path: Path,
    claim_path: Path,
    report_path: Path,
    *,
    repository_root: Path,
) -> dict[str, object]:
    """Verify a retained, redacted evidence bundle without provider access."""

    checks: list[dict[str, object]] = []
    try:
        ticket_path, claim_path, report_path = _validate_external_evidence_paths(
            repository_root,
            ticket_path,
            claim_path,
            report_path,
        )
        checks.append(
            _check(
                "private_evidence_boundary",
                True,
                "ticket, claim, and report are distinct and outside the repository",
            )
        )
        ticket_body, ticket_raw, issued_at, expires_at = _strict_ticket(ticket_path)
        checks.append(_check("ticket_contract", True, "ticket contract is valid"))
        claim_body, claim_raw, _claimed_at, _finalized_at = _strict_claim(
            claim_path,
            ticket_body=ticket_body,
            ticket_raw=ticket_raw,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        checks.append(_check("claim_contract", True, "claim is finalized and bound"))
        report_body, report_raw = _strict_report(
            report_path,
            ticket_body=ticket_body,
            claim_body=claim_body,
        )
        checks.append(_check("report_contract", True, "report closes the live gate"))
        if report_body.get("authorization_id") != claim_body.get("authorization_id"):
            raise EvidenceVerificationError(
                "authorization_mismatch", "report authorization ID does not match claim"
            )
        checks.append(
            _check(
                "cross_artifact_binding",
                True,
                "ticket, claim, and report share one authorization and audit reference",
            )
        )
    except (EvidenceVerificationError, LiveSmokePreflightError, OSError) as exc:
        if isinstance(exc, EvidenceVerificationError):
            code = exc.code
            detail = str(exc)
        elif isinstance(exc, OSError):
            code = "evidence_file_unavailable"
            detail = "one or more evidence files are unavailable"
        else:
            code = "invalid_json"
            detail = str(exc)
        checks.append(_check(code, False, detail))
        return {
            "openai_live_smoke_evidence": {
                "valid": False,
                "release_gate_state": "evidence_invalid",
                "authorization_id": None,
                "live_request_executed": None,
                "provider_modules_imported": False,
                "credential_presence_checked": False,
                "credential_value_exposed": False,
                "checks": checks,
            }
        }

    file_hashes = {
        "ticket_sha256": hashlib.sha256(ticket_raw).hexdigest(),
        "claim_sha256": hashlib.sha256(claim_raw).hexdigest(),
        "report_sha256": hashlib.sha256(report_raw).hexdigest(),
    }
    bundle_material = "\n".join(file_hashes[key] for key in sorted(file_hashes))
    return {
        "openai_live_smoke_evidence": {
            "valid": True,
            "release_gate_state": "live_smoke_verified",
            "authorization_id": ticket_body["authorization_id"],
            "model": ticket_body["model"],
            "audit_ref": claim_body["audit_ref"],
            "live_request_executed": True,
            "provider_modules_imported": False,
            "credential_presence_checked": False,
            "credential_value_exposed": False,
            "file_hashes": file_hashes,
            "evidence_bundle_sha256": hashlib.sha256(
                bundle_material.encode("ascii")
            ).hexdigest(),
            "checks": checks,
        }
    }
