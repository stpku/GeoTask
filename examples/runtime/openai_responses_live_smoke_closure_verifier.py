"""Read-only verification of a retained OpenAI live-smoke closure manifest.

A closure manifest is not self-authenticating: its exact SHA-256 must be retained
outside the file and supplied to this verifier. The verifier also reruns the
strict ticket, claim, and report checks so a matching closure cannot outlive
changed or corrupted source evidence. It never imports provider packages,
reads credentials, mutates evidence, creates files, or sends a network request.
This file remains outside the public export and normal CI.
"""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

try:  # Package import when loaded through examples.runtime.
    from .openai_responses_live_smoke import (
        LiveSmokePreflightError,
        _PINNED_MODEL_PATTERN,
        _parse_timestamp,
        _strict_json_object,
        _utc_now,
    )
    from .openai_responses_live_smoke_closure import (
        _CLOSURE_FIELDS,
        _CLOSURE_FORMAT_VERSION,
        _CLOSURE_TOP_LEVEL_KEY,
        _CLOSURE_VERIFIER_VERSION,
        _HASH_KEYS,
    )
    from .openai_responses_live_smoke_evidence import verify_evidence_bundle
except ImportError:  # Direct loading from examples/runtime.
    from openai_responses_live_smoke import (  # type: ignore[no-redef]
        LiveSmokePreflightError,
        _PINNED_MODEL_PATTERN,
        _parse_timestamp,
        _strict_json_object,
        _utc_now,
    )
    from openai_responses_live_smoke_closure import (  # type: ignore[no-redef]
        _CLOSURE_FIELDS,
        _CLOSURE_FORMAT_VERSION,
        _CLOSURE_TOP_LEVEL_KEY,
        _CLOSURE_VERIFIER_VERSION,
        _HASH_KEYS,
    )
    from openai_responses_live_smoke_evidence import (  # type: ignore[no-redef]
        verify_evidence_bundle,
    )


_MAX_FUTURE_CLOCK_SKEW = timedelta(minutes=5)


class ClosureVerificationError(ValueError):
    """Raised when a retained closure cannot be verified fail-closed."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        closure_sha256: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.closure_sha256 = closure_sha256


def _check(code: str, passed: bool, detail: str) -> dict[str, object]:
    return {"code": code, "passed": passed, "detail": detail}


def _failure(
    code: str,
    detail: str,
    *,
    checks: list[dict[str, object]] | None = None,
    closure_sha256: str | None = None,
    digest_anchored: bool = False,
) -> dict[str, object]:
    closure_checks = list(checks or [])
    closure_checks.append(_check(code, False, detail))
    return {
        "openai_live_smoke_closure_verification": {
            "valid": False,
            "release_gate_state": "closure_invalid",
            "authorization_id": None,
            "closure_manifest_sha256": closure_sha256,
            "closure_digest_anchored": digest_anchored,
            "live_request_executed": None,
            "provider_modules_imported": False,
            "credential_presence_checked": False,
            "credential_value_exposed": False,
            "evidence_mutated": False,
            "checks": closure_checks,
        }
    }


def _is_private_file(path: Path) -> bool:
    if os.name == "nt":
        return True
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def _validate_paths(
    repository_root: Path,
    ticket_path: Path,
    claim_path: Path,
    report_path: Path,
    closure_path: Path,
) -> tuple[Path, Path, Path, Path]:
    root = repository_root.resolve()
    resolved = tuple(
        path.resolve()
        for path in (ticket_path, claim_path, report_path, closure_path)
    )
    if len(set(resolved)) != len(resolved):
        raise ClosureVerificationError(
            "closure_path_collision",
            "ticket, claim, report, and closure must be distinct files",
        )
    if resolved[-1].suffix.lower() != ".json":
        raise ClosureVerificationError(
            "invalid_closure_path",
            "closure manifest must use a .json suffix",
        )
    for path in resolved:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        raise ClosureVerificationError(
            "evidence_inside_repository",
            "live-smoke evidence and closure must remain outside the repository",
        )
    ticket, claim, report, closure = resolved
    return ticket, claim, report, closure


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ClosureVerificationError(
            "invalid_sha256",
            f"{label} must be a lowercase 64-character SHA-256",
        )
    return value


def _canonical_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ClosureVerificationError(
            "invalid_authorization_id", "closure authorization ID is missing"
        )
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ClosureVerificationError(
            "invalid_authorization_id", "closure authorization ID must be a UUID"
        ) from exc
    if str(parsed) != value:
        raise ClosureVerificationError(
            "invalid_authorization_id",
            "closure authorization ID must use canonical UUID form",
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


def _current_time(now: datetime | None) -> datetime:
    value = _utc_now() if now is None else now
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClosureVerificationError(
            "invalid_verification_time", "verification time must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


def _read_anchored_closure(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[dict[str, object], bytes, str]:
    try:
        payload, raw = _strict_json_object(path, "live smoke closure")
    except LiveSmokePreflightError as exc:
        raise ClosureVerificationError("invalid_closure_json", str(exc)) from exc
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        expected = _sha256(expected_sha256, "expected closure digest")
    except ClosureVerificationError as exc:
        raise ClosureVerificationError(
            exc.code,
            str(exc),
            closure_sha256=actual_sha256,
        ) from exc
    if actual_sha256 != expected:
        raise ClosureVerificationError(
            "closure_digest_mismatch",
            "closure manifest no longer matches its externally retained SHA-256",
            closure_sha256=actual_sha256,
        )
    return payload, raw, actual_sha256


def _strict_closure(
    path: Path,
    payload: Mapping[str, object],
    raw: bytes,
    actual_sha256: str,
    *,
    claim_path: Path,
    now: datetime | None,
) -> tuple[dict[str, object], bytes, str, datetime]:
    if set(payload) != {_CLOSURE_TOP_LEVEL_KEY}:
        raise ClosureVerificationError(
            "invalid_closure_contract",
            "closure manifest must contain exactly one body",
        )
    if not _is_private_file(path):
        raise ClosureVerificationError(
            "insecure_closure_permissions",
            "closure manifest permissions are not private",
        )
    body = payload.get(_CLOSURE_TOP_LEVEL_KEY)
    if not isinstance(body, dict) or set(body) != _CLOSURE_FIELDS:
        raise ClosureVerificationError(
            "invalid_closure_contract",
            "closure manifest fields are not exact",
        )
    if (
        body.get("format_version") != _CLOSURE_FORMAT_VERSION
        or body.get("verifier_version") != _CLOSURE_VERIFIER_VERSION
    ):
        raise ClosureVerificationError(
            "unsupported_closure_version",
            "closure format or verifier version is unsupported",
        )
    if body.get("release_gate_state") != "live_smoke_verified":
        raise ClosureVerificationError(
            "closure_not_verified",
            "closure release gate state is not live_smoke_verified",
        )
    if body.get("live_request_executed") is not True:
        raise ClosureVerificationError(
            "closure_not_verified",
            "closure does not retain a successful live request state",
        )
    if body.get("credential_data_retained") is not False:
        raise ClosureVerificationError(
            "closure_retains_credentials",
            "closure must explicitly record that credential data was not retained",
        )

    authorization_id = _canonical_uuid(body.get("authorization_id"))
    model = body.get("model")
    if not isinstance(model, str) or not _PINNED_MODEL_PATTERN.fullmatch(model):
        raise ClosureVerificationError(
            "invalid_closure_model", "closure model is not a pinned snapshot"
        )
    if not _server_audit_reference(body.get("audit_ref")):
        raise ClosureVerificationError(
            "invalid_server_audit", "closure lacks server request and response identifiers"
        )

    file_hashes = body.get("file_hashes")
    if not isinstance(file_hashes, dict) or set(file_hashes) != _HASH_KEYS:
        raise ClosureVerificationError(
            "invalid_evidence_hashes", "closure evidence hashes are incomplete"
        )
    normalized_hashes = {
        key: _sha256(value, f"closure {key}") for key, value in file_hashes.items()
    }
    bundle_material = "\n".join(
        normalized_hashes[key] for key in sorted(normalized_hashes)
    )
    bundle_sha256 = hashlib.sha256(bundle_material.encode("ascii")).hexdigest()
    if body.get("evidence_bundle_sha256") != bundle_sha256:
        raise ClosureVerificationError(
            "evidence_bundle_digest_mismatch",
            "closure evidence bundle digest does not match its file hashes",
        )

    try:
        verified_at = _parse_timestamp(body.get("verified_at"), "closure verified_at")
        claim_payload, _claim_raw = _strict_json_object(
            claim_path, "authorization claim"
        )
        claim_body = claim_payload.get("authorization_claim")
        if not isinstance(claim_body, dict):
            raise ClosureVerificationError(
                "invalid_claim_contract", "authorization claim body is missing"
            )
        finalized_at = _parse_timestamp(
            claim_body.get("finalized_at"), "claim finalized_at"
        )
    except LiveSmokePreflightError as exc:
        raise ClosureVerificationError("invalid_closure_time", str(exc)) from exc
    current = _current_time(now)
    if verified_at < finalized_at:
        raise ClosureVerificationError(
            "invalid_closure_time",
            "closure verification time precedes claim finalization",
        )
    if verified_at > current + _MAX_FUTURE_CLOCK_SKEW:
        raise ClosureVerificationError(
            "invalid_closure_time",
            "closure verification time is unreasonably far in the future",
        )

    normalized_body = dict(body)
    normalized_body["authorization_id"] = authorization_id
    normalized_body["file_hashes"] = normalized_hashes
    return normalized_body, raw, actual_sha256, verified_at


def _evidence_binding(evidence_body: Mapping[str, object]) -> dict[str, object]:
    return {
        "authorization_id": evidence_body.get("authorization_id"),
        "model": evidence_body.get("model"),
        "audit_ref": evidence_body.get("audit_ref"),
        "file_hashes": evidence_body.get("file_hashes"),
        "evidence_bundle_sha256": evidence_body.get("evidence_bundle_sha256"),
    }


def _compare_to_evidence(
    closure_body: Mapping[str, object],
    evidence_body: Mapping[str, object],
) -> None:
    for key, expected in _evidence_binding(evidence_body).items():
        if closure_body.get(key) != expected:
            raise ClosureVerificationError(
                "closure_evidence_mismatch",
                f"closure {key} no longer matches verified source evidence",
            )


def verify_closure_manifest(
    ticket_path: Path,
    claim_path: Path,
    report_path: Path,
    closure_path: Path,
    *,
    expected_closure_sha256: str,
    repository_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify exact closure identity and rerun all retained-evidence checks."""

    checks: list[dict[str, object]] = []
    actual_sha256: str | None = None
    digest_anchored = False
    try:
        ticket, claim, report, closure = _validate_paths(
            repository_root,
            ticket_path,
            claim_path,
            report_path,
            closure_path,
        )
        checks.append(
            _check(
                "private_closure_boundary",
                True,
                "ticket, claim, report, and closure are distinct and outside the repository",
            )
        )

        evidence = verify_evidence_bundle(
            ticket,
            claim,
            report,
            repository_root=repository_root,
        )["openai_live_smoke_evidence"]
        evidence_checks = evidence.get("checks")
        if isinstance(evidence_checks, list):
            checks.extend(evidence_checks)
        if evidence.get("valid") is not True:
            raise ClosureVerificationError(
                "evidence_not_verified",
                "closure cannot be verified because source evidence is invalid",
            )
        checks.append(
            _check(
                "source_evidence_reverified",
                True,
                "ticket, claim, and report were reverified without mutation",
            )
        )

        closure_payload, closure_raw, actual_sha256 = _read_anchored_closure(
            closure,
            expected_sha256=expected_closure_sha256,
        )
        digest_anchored = True
        checks.append(
            _check(
                "closure_digest_anchor",
                True,
                "closure matches its externally retained SHA-256",
            )
        )
        closure_body, _raw, actual_sha256, _verified_at = _strict_closure(
            closure,
            closure_payload,
            closure_raw,
            actual_sha256,
            claim_path=claim,
            now=now,
        )
        checks.append(
            _check(
                "closure_contract",
                True,
                "closure contract, permissions, and timeline are valid",
            )
        )

        _compare_to_evidence(closure_body, evidence)
        checks.append(
            _check(
                "closure_evidence_binding",
                True,
                "closure identity, audit reference, and hashes match current source evidence",
            )
        )

        final_evidence = verify_evidence_bundle(
            ticket,
            claim,
            report,
            repository_root=repository_root,
        )["openai_live_smoke_evidence"]
        if (
            final_evidence.get("valid") is not True
            or _evidence_binding(final_evidence) != _evidence_binding(evidence)
        ):
            raise ClosureVerificationError(
                "source_evidence_changed_during_verification",
                "source evidence changed while closure verification was in progress",
            )
        checks.append(
            _check(
                "source_evidence_stable",
                True,
                "source evidence remained byte-bound across the verification window",
            )
        )
    except ClosureVerificationError as exc:
        return _failure(
            exc.code,
            str(exc),
            checks=checks,
            closure_sha256=exc.closure_sha256 or actual_sha256,
            digest_anchored=digest_anchored,
        )
    except (LiveSmokePreflightError, OSError):
        return _failure(
            "closure_file_unavailable",
            "closure or source evidence could not be read safely",
            checks=checks,
            closure_sha256=actual_sha256,
            digest_anchored=digest_anchored,
        )

    return {
        "openai_live_smoke_closure_verification": {
            "valid": True,
            "release_gate_state": "live_smoke_closure_verified",
            "authorization_id": closure_body["authorization_id"],
            "model": closure_body["model"],
            "audit_ref": closure_body["audit_ref"],
            "verified_at": closure_body["verified_at"],
            "evidence_bundle_sha256": closure_body["evidence_bundle_sha256"],
            "closure_manifest_sha256": actual_sha256,
            "closure_digest_anchored": True,
            "live_request_executed": True,
            "provider_modules_imported": False,
            "credential_presence_checked": False,
            "credential_value_exposed": False,
            "evidence_mutated": False,
            "checks": checks,
        }
    }
