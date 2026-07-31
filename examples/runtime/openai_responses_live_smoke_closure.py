"""Write-once retention of verified, redacted OpenAI live-smoke closure evidence.

This module never imports provider packages, reads credentials, creates an
authorization claim, or sends a network request. It first invokes the strict
retained-evidence verifier, then atomically publishes one minimal JSON manifest
outside the repository. The file remains outside the public export and normal CI.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Mapping

try:  # Package import when loaded through examples.runtime.
    from .openai_responses_live_smoke import (
        _PINNED_MODEL_PATTERN,
        _timestamp,
        _utc_now,
    )
    from .openai_responses_live_smoke_evidence import verify_evidence_bundle
except ImportError:  # Direct loading from examples/runtime.
    from openai_responses_live_smoke import (  # type: ignore[no-redef]
        _PINNED_MODEL_PATTERN,
        _timestamp,
        _utc_now,
    )
    from openai_responses_live_smoke_evidence import (  # type: ignore[no-redef]
        verify_evidence_bundle,
    )


_CLOSURE_TOP_LEVEL_KEY = "openai_live_smoke_closure"
_CLOSURE_FORMAT_VERSION = "1.0"
_CLOSURE_VERIFIER_VERSION = "1.0"
_HASH_KEYS = {
    "ticket_sha256",
    "claim_sha256",
    "report_sha256",
}


class ClosureWriteError(ValueError):
    """Raised when verified evidence cannot be retained as a closure manifest."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _check(code: str, passed: bool, detail: str) -> dict[str, object]:
    return {"code": code, "passed": passed, "detail": detail}


def _failure(
    code: str,
    detail: str,
    *,
    checks: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    closure_checks = list(checks or [])
    closure_checks.append(_check(code, False, detail))
    return {
        "openai_live_smoke_closure_write": {
            "valid": False,
            "release_gate_state": "closure_not_recorded",
            "authorization_id": None,
            "live_request_executed": None,
            "provider_modules_imported": False,
            "credential_presence_checked": False,
            "credential_value_exposed": False,
            "output_created": False,
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
    output_path: Path,
) -> tuple[Path, Path, Path, Path]:
    root = repository_root.resolve()
    resolved = tuple(
        path.resolve()
        for path in (ticket_path, claim_path, report_path, output_path)
    )
    if len(set(resolved)) != len(resolved):
        raise ClosureWriteError(
            "evidence_path_collision",
            "live-smoke evidence and closure paths must be distinct files",
        )
    output = resolved[-1]
    if output.suffix.lower() != ".json":
        raise ClosureWriteError(
            "invalid_closure_output",
            "closure output must use a .json suffix",
        )
    for path in resolved:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        raise ClosureWriteError(
            "evidence_inside_repository",
            "live-smoke evidence and closure must remain outside the repository",
        )
    ticket, claim, report, output = resolved
    return ticket, claim, report, output


def _canonical_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ClosureWriteError(
            "invalid_authorization_id", "closure authorization ID is missing"
        )
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ClosureWriteError(
            "invalid_authorization_id", "closure authorization ID must be a UUID"
        ) from exc
    if str(parsed) != value:
        raise ClosureWriteError(
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


def _closure_payload(
    evidence_body: Mapping[str, object],
    *,
    verified_at: datetime,
) -> dict[str, object]:
    if (
        evidence_body.get("valid") is not True
        or evidence_body.get("release_gate_state") != "live_smoke_verified"
        or evidence_body.get("live_request_executed") is not True
    ):
        raise ClosureWriteError(
            "evidence_not_verified",
            "closure cannot be recorded until retained evidence is verified",
        )

    file_hashes = evidence_body.get("file_hashes")
    if not isinstance(file_hashes, dict) or set(file_hashes) != _HASH_KEYS:
        raise ClosureWriteError(
            "invalid_evidence_hashes", "verified evidence file hashes are incomplete"
        )
    if not all(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        for value in file_hashes.values()
    ):
        raise ClosureWriteError(
            "invalid_evidence_hashes", "verified evidence file hashes are malformed"
        )
    bundle_material = "\n".join(file_hashes[key] for key in sorted(file_hashes))
    bundle_sha256 = hashlib.sha256(bundle_material.encode("ascii")).hexdigest()
    if evidence_body.get("evidence_bundle_sha256") != bundle_sha256:
        raise ClosureWriteError(
            "evidence_bundle_digest_mismatch",
            "verified evidence bundle digest does not match its file hashes",
        )

    authorization_id = _canonical_uuid(evidence_body.get("authorization_id"))
    model = evidence_body.get("model")
    if not isinstance(model, str) or not _PINNED_MODEL_PATTERN.fullmatch(model):
        raise ClosureWriteError(
            "invalid_closure_model", "closure model is not a pinned snapshot"
        )
    audit_ref = evidence_body.get("audit_ref")
    if not _server_audit_reference(audit_ref):
        raise ClosureWriteError(
            "invalid_server_audit", "closure lacks server request and response identifiers"
        )

    return {
        _CLOSURE_TOP_LEVEL_KEY: {
            "format_version": _CLOSURE_FORMAT_VERSION,
            "verifier_version": _CLOSURE_VERIFIER_VERSION,
            "release_gate_state": "live_smoke_verified",
            "verified_at": _timestamp(verified_at),
            "authorization_id": authorization_id,
            "model": model,
            "audit_ref": audit_ref,
            "file_hashes": dict(file_hashes),
            "evidence_bundle_sha256": bundle_sha256,
            "live_request_executed": True,
            "credential_data_retained": False,
        }
    }


def _write_private_json_once(path: Path, payload: dict[str, object]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    published = False
    try:
        try:
            os.fchmod(descriptor, 0o600)
        except (AttributeError, OSError):
            pass
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            published = True
        except FileExistsError as exc:
            raise ClosureWriteError(
                "closure_already_exists",
                "closure output already exists and will not be overwritten",
            ) from exc
        except OSError as exc:
            raise ClosureWriteError(
                "closure_publish_failed",
                "closure output could not be atomically published",
            ) from exc
        try:
            path.chmod(0o600)
        except OSError:
            pass
        if not _is_private_file(path):
            raise ClosureWriteError(
                "insecure_closure_permissions",
                "closure output permissions are not private",
            )
        return serialized
    except Exception:
        if published:
            path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def write_closure_manifest(
    ticket_path: Path,
    claim_path: Path,
    report_path: Path,
    output_path: Path,
    *,
    repository_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    """Verify retained evidence and atomically record one redacted manifest."""

    evidence = verify_evidence_bundle(
        ticket_path,
        claim_path,
        report_path,
        repository_root=repository_root,
    )["openai_live_smoke_evidence"]
    evidence_checks = evidence.get("checks")
    checks = list(evidence_checks) if isinstance(evidence_checks, list) else []
    if evidence.get("valid") is not True:
        return _failure(
            "evidence_not_verified",
            "closure cannot be recorded until retained evidence is verified",
            checks=checks,
        )

    try:
        _ticket, _claim, _report, output = _validate_paths(
            repository_root,
            ticket_path,
            claim_path,
            report_path,
            output_path,
        )
        checks.append(
            _check(
                "private_closure_boundary",
                True,
                "closure output is distinct and outside the repository",
            )
        )
        payload = _closure_payload(
            evidence,
            verified_at=_utc_now() if now is None else now,
        )
        serialized = _write_private_json_once(output, payload)
        checks.append(
            _check(
                "closure_manifest_recorded",
                True,
                "closure manifest was atomically recorded without overwrite",
            )
        )
    except ClosureWriteError as exc:
        return _failure(exc.code, str(exc), checks=checks)
    except OSError:
        return _failure(
            "closure_output_unavailable",
            "closure output could not be created",
            checks=checks,
        )

    closure = payload[_CLOSURE_TOP_LEVEL_KEY]
    return {
        "openai_live_smoke_closure_write": {
            "valid": True,
            "release_gate_state": "live_smoke_closure_recorded",
            "authorization_id": closure["authorization_id"],
            "model": closure["model"],
            "audit_ref": closure["audit_ref"],
            "verified_at": closure["verified_at"],
            "evidence_bundle_sha256": closure["evidence_bundle_sha256"],
            "closure_manifest_sha256": hashlib.sha256(serialized).hexdigest(),
            "live_request_executed": True,
            "provider_modules_imported": False,
            "credential_presence_checked": False,
            "credential_value_exposed": False,
            "output_created": True,
            "checks": checks,
        }
    }
