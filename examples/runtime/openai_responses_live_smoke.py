"""Explicitly authorized private live smoke for the OpenAI Responses Adapter.

Running without ``--execute-live`` performs preflight only and never imports the
OpenAI SDK, resolves authentication material, or sends a network request. This
file stays outside the public export and normal public CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Sequence


ACK_ENVIRONMENT_VARIABLE = "GEOTASK_OPENAI_LIVE_SMOKE_ACK"
MODEL_ENVIRONMENT_VARIABLE = "GEOTASK_OPENAI_LIVE_MODEL"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
HARD_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 60.0
HARD_MAX_TIMEOUT_SECONDS = 120.0
DEFAULT_AUTHORIZATION_VALID_MINUTES = 15
HARD_MAX_AUTHORIZATION_VALID_MINUTES = 60
_PINNED_MODEL_PATTERN = re.compile(r"^.+-\d{4}-\d{2}-\d{2}$")
_REQUEST_RELATIVE_PATH = Path(
    "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
)
_EXPECTED_REQUEST_SHA256 = "".join(
    (
        "6c7f2dd98c05e089",
        "857788eb8ca9696f",
        "92d866e59cc6e968",
        "44743baadeaacd06",
    )
)


class LiveSmokePreflightError(ValueError):
    """Raised before a live request when a safety gate is not satisfied."""


class LiveSmokeExecutionError(RuntimeError):
    """Raised with a generic state when execution cannot return a safe report."""

    def __init__(self, message: str, *, live_request_executed: bool | None):
        super().__init__(message)
        self.live_request_executed = live_request_executed


@dataclass(frozen=True)
class LiveSmokePlan:
    """Validated non-secret plan for at most one provider request."""

    repository_root: Path
    model: str
    output_budget: int = DEFAULT_MAX_OUTPUT_TOKENS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    execute_live: bool = False
    report_path: Path | None = None
    authorization_ticket_path: Path | None = None

    def __post_init__(self) -> None:
        root = Path(self.repository_root).resolve()
        object.__setattr__(self, "repository_root", root)
        if not root.is_dir():
            raise LiveSmokePreflightError("repository_root must be an existing directory")
        if not isinstance(self.model, str) or not self.model.strip():
            raise LiveSmokePreflightError("model must be a non-empty pinned snapshot")
        model = self.model.strip()
        object.__setattr__(self, "model", model)
        if not _PINNED_MODEL_PATTERN.fullmatch(model):
            raise LiveSmokePreflightError(
                "model must be a pinned snapshot ending in YYYY-MM-DD"
            )
        if (
            isinstance(self.output_budget, bool)
            or not isinstance(self.output_budget, int)
            or self.output_budget <= 0
            or self.output_budget > HARD_MAX_OUTPUT_TOKENS
        ):
            raise LiveSmokePreflightError(
                f"output_budget must be between 1 and {HARD_MAX_OUTPUT_TOKENS}"
            )
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
            or self.timeout_seconds > HARD_MAX_TIMEOUT_SECONDS
        ):
            raise LiveSmokePreflightError(
                f"timeout_seconds must be greater than 0 and at most {HARD_MAX_TIMEOUT_SECONDS}"
            )
        if not isinstance(self.execute_live, bool):
            raise LiveSmokePreflightError("execute_live must be boolean")

        if not self.request_path.is_file():
            raise LiveSmokePreflightError(
                f"fixed live-smoke request is unavailable: {_REQUEST_RELATIVE_PATH.as_posix()}"
            )
        if self.report_path is not None:
            report = _private_json_path(root, self.report_path, "report_path")
            object.__setattr__(self, "report_path", report)
        if self.authorization_ticket_path is not None:
            ticket = _private_json_path(
                root,
                self.authorization_ticket_path,
                "authorization_ticket_path",
            )
            object.__setattr__(self, "authorization_ticket_path", ticket)
        if (
            self.report_path is not None
            and self.authorization_ticket_path is not None
            and self.report_path == self.authorization_ticket_path
        ):
            raise LiveSmokePreflightError(
                "report_path must not overwrite the authorization ticket"
            )

    @property
    def request_path(self) -> Path:
        return self.repository_root / _REQUEST_RELATIVE_PATH

    def public_plan(self) -> dict[str, object]:
        return {
            "live_smoke_plan": {
                "valid": True,
                "execute_live": self.execute_live,
                "model": self.model,
                "output_budget": self.output_budget,
                "timeout_seconds": float(self.timeout_seconds),
                "request_path": _REQUEST_RELATIVE_PATH.as_posix(),
                "report_path": (
                    str(self.report_path) if self.report_path is not None else None
                ),
                "authorization_ticket_path": (
                    str(self.authorization_ticket_path)
                    if self.authorization_ticket_path is not None
                    else None
                ),
                "provider_calls_allowed": 1 if self.execute_live else 0,
                "automatic_retries_allowed": 0,
                "tools_allowed": False,
                "response_storage_allowed": False,
                "live_request_executed": False,
                "release_gate_state": "authorization_pending",
            }
        }


def _private_json_path(root: Path, value: Path, label: str) -> Path:
    path = Path(value).resolve()
    if path.suffix.lower() != ".json":
        raise LiveSmokePreflightError(f"{label} must use a .json suffix")
    try:
        path.relative_to(root)
    except ValueError:
        return path
    raise LiveSmokePreflightError(
        f"{label} must be outside the repository to prevent accidental commit"
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LiveSmokePreflightError(f"{label} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LiveSmokePreflightError(f"{label} is not a valid timestamp") from exc
    return parsed.astimezone(timezone.utc)


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON object key {key!r} is not allowed")
        payload[key] = value
    return payload


def _strict_json_object(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    try:
        raw = path.read_bytes()
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=_reject_nonfinite,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise LiveSmokePreflightError(f"{label} is not valid strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise LiveSmokePreflightError(f"{label} must have an object root")
    return payload, raw


def _authorization_body(
    plan: LiveSmokePlan,
    *,
    authorization_id: str,
    issued_at: datetime,
    expires_at: datetime,
) -> dict[str, object]:
    return {
        "format_version": "1.0",
        "authorization_id": authorization_id,
        "state": "issued",
        "issued_at": _timestamp(issued_at),
        "expires_at": _timestamp(expires_at),
        "model": plan.model,
        "output_budget": plan.output_budget,
        "timeout_seconds": float(plan.timeout_seconds),
        "request_sha256": _EXPECTED_REQUEST_SHA256,
        "max_provider_calls": 1,
        "automatic_retries_allowed": 0,
        "tools_allowed": False,
        "response_storage_allowed": False,
    }


def issue_authorization_ticket(
    plan: LiveSmokePlan,
    path: Path,
    *,
    valid_minutes: int = DEFAULT_AUTHORIZATION_VALID_MINUTES,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Issue one short-lived non-secret authorization ticket outside the repository."""

    environment = os.environ if environ is None else environ
    if environment.get(ACK_ENVIRONMENT_VARIABLE) != _acknowledgement():
        raise LiveSmokePreflightError(
            f"ticket issuance requires {ACK_ENVIRONMENT_VARIABLE}={_acknowledgement()}"
        )
    if (
        isinstance(valid_minutes, bool)
        or not isinstance(valid_minutes, int)
        or valid_minutes <= 0
        or valid_minutes > HARD_MAX_AUTHORIZATION_VALID_MINUTES
    ):
        raise LiveSmokePreflightError(
            "authorization validity must be between 1 and "
            f"{HARD_MAX_AUTHORIZATION_VALID_MINUTES} minutes"
        )
    _load_request(plan)
    ticket_path = _private_json_path(
        plan.repository_root,
        path,
        "authorization ticket path",
    )
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    if claim_path.exists():
        raise LiveSmokePreflightError(
            "authorization claim history already exists for this ticket path"
        )
    issued_at = (now or _utc_now()).astimezone(timezone.utc)
    expires_at = issued_at + timedelta(minutes=valid_minutes)
    body = _authorization_body(
        plan,
        authorization_id=str(uuid.uuid4()),
        issued_at=issued_at,
        expires_at=expires_at,
    )
    payload = {"geotask_openai_live_smoke_authorization": body}
    _write_report(ticket_path, payload, exclusive=True)
    return {
        "authorization_ticket": {
            "valid": True,
            "authorization_id": body["authorization_id"],
            "state": "issued",
            "issued_at": body["issued_at"],
            "expires_at": body["expires_at"],
            "model": body["model"],
            "output_budget": body["output_budget"],
            "timeout_seconds": body["timeout_seconds"],
            "max_provider_calls": 1,
            "automatic_retries_allowed": 0,
            "live_request_executed": False,
            "release_gate_state": "live_execution_pending",
        }
    }


def _validate_authorization_ticket(
    plan: LiveSmokePlan,
    *,
    now: datetime | None = None,
) -> tuple[str, bytes, datetime]:
    if plan.authorization_ticket_path is None:
        raise LiveSmokePreflightError(
            "live execution requires --authorization-ticket outside the repository"
        )
    ticket_path = plan.authorization_ticket_path
    payload, raw = _strict_json_object(ticket_path, "authorization ticket")
    if set(payload) != {"geotask_openai_live_smoke_authorization"}:
        raise LiveSmokePreflightError(
            "authorization ticket must contain exactly one authorization body"
        )
    if os.name != "nt":
        mode = stat.S_IMODE(ticket_path.stat().st_mode)
        if mode & 0o077:
            raise LiveSmokePreflightError(
                "authorization ticket permissions must not allow group or other access"
            )
    body = payload.get("geotask_openai_live_smoke_authorization")
    if not isinstance(body, dict):
        raise LiveSmokePreflightError("authorization ticket body is missing")
    expected = {
        "format_version": "1.0",
        "state": "issued",
        "model": plan.model,
        "output_budget": plan.output_budget,
        "timeout_seconds": float(plan.timeout_seconds),
        "request_sha256": _EXPECTED_REQUEST_SHA256,
        "max_provider_calls": 1,
        "automatic_retries_allowed": 0,
        "tools_allowed": False,
        "response_storage_allowed": False,
    }
    allowed_keys = set(expected) | {"authorization_id", "issued_at", "expires_at"}
    if set(body) != allowed_keys:
        raise LiveSmokePreflightError(
            "authorization ticket fields do not match the strict ticket contract"
        )
    for key, value in expected.items():
        if body.get(key) != value:
            raise LiveSmokePreflightError(
                f"authorization ticket {key} does not match the reviewed plan"
            )
    authorization_id = body.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id.strip():
        raise LiveSmokePreflightError("authorization ticket ID is missing")
    try:
        parsed_authorization_id = uuid.UUID(authorization_id)
    except ValueError as exc:
        raise LiveSmokePreflightError("authorization ticket ID must be a UUID") from exc
    if str(parsed_authorization_id) != authorization_id:
        raise LiveSmokePreflightError("authorization ticket ID must use canonical UUID form")
    issued_at = _parse_timestamp(body.get("issued_at"), "authorization issued_at")
    expires_at = _parse_timestamp(body.get("expires_at"), "authorization expires_at")
    current = (now or _utc_now()).astimezone(timezone.utc)
    if expires_at <= issued_at:
        raise LiveSmokePreflightError("authorization expiry must be after issuance")
    if expires_at - issued_at > timedelta(
        minutes=HARD_MAX_AUTHORIZATION_VALID_MINUTES
    ):
        raise LiveSmokePreflightError(
            "authorization ticket validity exceeds the hard maximum"
        )
    if current < issued_at - timedelta(seconds=5):
        raise LiveSmokePreflightError("authorization ticket is not active yet")
    if current >= expires_at:
        raise LiveSmokePreflightError("authorization ticket has expired")

    return authorization_id, raw, current


def _claim_authorization_ticket(
    plan: LiveSmokePlan,
    *,
    now: datetime | None = None,
) -> str:
    authorization_id, raw, current = _validate_authorization_ticket(plan, now=now)
    assert plan.authorization_ticket_path is not None
    ticket_path = plan.authorization_ticket_path
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    claim_payload = {
        "authorization_claim": {
            "authorization_id": authorization_id,
            "claimed_at": _timestamp(current),
            "ticket_sha256": hashlib.sha256(raw).hexdigest(),
            "state": "claimed",
            "live_request_executed": None,
        }
    }
    serialized = json.dumps(
        claim_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(str(claim_path), flags, 0o600)
    except FileExistsError as exc:
        raise LiveSmokePreflightError(
            "authorization ticket has already been claimed and cannot be reused"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        claim_path.unlink(missing_ok=True)
        raise
    return authorization_id


def _finalize_authorization_claim(
    plan: LiveSmokePlan,
    authorization_id: str,
    *,
    state: str,
    live_request_executed: bool | None,
    runtime_state: str | None = None,
    audit_ref: str | None = None,
    valid: bool | None = None,
) -> None:
    if plan.authorization_ticket_path is None:
        raise LiveSmokeExecutionError(
            "authorization claim cannot be finalized without its ticket",
            live_request_executed=live_request_executed,
        )
    claim_path = plan.authorization_ticket_path.with_suffix(
        plan.authorization_ticket_path.suffix + ".claimed"
    )
    payload, _raw = _strict_json_object(claim_path, "authorization claim")
    if set(payload) != {"authorization_claim"}:
        raise LiveSmokeExecutionError(
            "authorization claim contains unexpected top-level fields",
            live_request_executed=live_request_executed,
        )
    if os.name != "nt":
        mode = stat.S_IMODE(claim_path.stat().st_mode)
        if mode & 0o077:
            raise LiveSmokeExecutionError(
                "authorization claim permissions are not private",
                live_request_executed=live_request_executed,
            )
    body = payload.get("authorization_claim")
    expected_claim_keys = {
        "authorization_id",
        "claimed_at",
        "ticket_sha256",
        "state",
        "live_request_executed",
    }
    if not isinstance(body, dict) or set(body) != expected_claim_keys:
        raise LiveSmokeExecutionError(
            "authorization claim fields do not match the strict claim contract",
            live_request_executed=live_request_executed,
        )
    if body.get("authorization_id") != authorization_id:
        raise LiveSmokeExecutionError(
            "authorization claim identity does not match the active request",
            live_request_executed=live_request_executed,
        )
    if body.get("state") != "claimed" or body.get("live_request_executed") is not None:
        raise LiveSmokeExecutionError(
            "authorization claim is not in the expected pending state",
            live_request_executed=live_request_executed,
        )
    _parse_timestamp(body.get("claimed_at"), "authorization claimed_at")
    try:
        ticket_raw = plan.authorization_ticket_path.read_bytes()
    except OSError as exc:
        raise LiveSmokeExecutionError(
            "authorization ticket is unavailable during claim finalization",
            live_request_executed=live_request_executed,
        ) from exc
    if body.get("ticket_sha256") != hashlib.sha256(ticket_raw).hexdigest():
        raise LiveSmokeExecutionError(
            "authorization claim no longer matches the issued ticket",
            live_request_executed=live_request_executed,
        )
    finalized = {
        "authorization_claim": {
            "authorization_id": authorization_id,
            "claimed_at": body.get("claimed_at"),
            "finalized_at": _timestamp(_utc_now()),
            "ticket_sha256": body.get("ticket_sha256"),
            "state": state,
            "live_request_executed": live_request_executed,
            "runtime_state": runtime_state,
            "audit_ref": audit_ref,
            "valid": valid,
        }
    }
    _write_report(claim_path, finalized)


def _acknowledgement() -> str:
    return "I_ACCEPT_ONE_" + "PAID_OPENAI_REQUEST"


def _authorization_reference() -> str:
    return "env://OPENAI_API_" + "KEY"


def _credential_environment_variable() -> str:
    return "OPENAI_API_" + "KEY"


def _load_request(plan: LiveSmokePlan) -> dict[str, object]:
    try:
        raw = plan.request_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != _EXPECTED_REQUEST_SHA256:
            raise LiveSmokePreflightError(
                "fixed live-smoke request digest does not match the reviewed request"
            )
        payload = json.loads(raw.decode("utf-8"))
    except LiveSmokePreflightError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveSmokePreflightError(
            "fixed live-smoke request could not be loaded as UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise LiveSmokePreflightError("fixed live-smoke request must have an object root")
    runtime_request = payload.get("runtime_request")
    if not isinstance(runtime_request, dict):
        raise LiveSmokePreflightError("fixed live-smoke request requires runtime_request")
    if runtime_request.get("authorization_ref") != _authorization_reference():
        raise LiveSmokePreflightError(
            "fixed live-smoke request authorization_ref does not match the private harness"
        )
    return payload


def _require_live_authorization(
    plan: LiveSmokePlan,
    environ: Mapping[str, str],
) -> None:
    if not plan.execute_live:
        return
    if environ.get(ACK_ENVIRONMENT_VARIABLE) != _acknowledgement():
        raise LiveSmokePreflightError(
            f"live execution requires {ACK_ENVIRONMENT_VARIABLE}={_acknowledgement()}"
        )
    credential_name = _credential_environment_variable()
    resolved = environ.get(credential_name)
    if not isinstance(resolved, str) or not resolved.strip():
        raise LiveSmokePreflightError("the server-side OpenAI credential is unavailable")
    if isinstance(environ.get("OPENAI_BASE_URL"), str) and environ["OPENAI_BASE_URL"].strip():
        raise LiveSmokePreflightError(
            "OPENAI_BASE_URL must be unset so the smoke cannot target an alternate endpoint"
        )
    if environ.get("OPENAI_LOG", "").strip():
        raise LiveSmokePreflightError(
            "OPENAI_LOG must be unset for the private live smoke"
        )
    if plan.authorization_ticket_path is None:
        raise LiveSmokePreflightError(
            "live execution requires --authorization-ticket outside the repository"
        )
    if not plan.authorization_ticket_path.is_file():
        raise LiveSmokePreflightError("authorization ticket file is unavailable")


def _response_report(
    plan: LiveSmokePlan,
    response: object,
    *,
    authorization_id: str,
    elapsed_ms: int,
    openai_version: str,
    core_version: str,
    adapter_version: str,
) -> dict[str, object]:
    diagnostics = getattr(response, "diagnostics", ())
    output_artifacts = getattr(response, "output_artifacts", ())
    runtime_state = getattr(response, "state", None)
    side_effects_executed = bool(
        getattr(response, "side_effects_executed", False)
    )
    audit_ref = getattr(response, "audit_ref", None)
    output_artifact_ids = [
        getattr(item, "artifact_id", "unknown") for item in output_artifacts
    ]
    audit_prefix = "openai://responses/"
    audit_components = (
        audit_ref[len(audit_prefix) :].split("/")
        if isinstance(audit_ref, str) and audit_ref.startswith(audit_prefix)
        else []
    )
    server_audit_available = (
        len(audit_components) == 2
        and all(audit_components)
        and not audit_components[0].startswith("client-")
        and audit_components[1] != "unknown-response"
    )
    valid = (
        runtime_state == "completed"
        and side_effects_executed
        and server_audit_available
        and output_artifact_ids == ["geotask.execution-result"]
    )
    return {
        "openai_live_smoke": {
            "valid": valid,
            "release_gate_state": (
                "live_smoke_verified" if valid else "live_smoke_failed"
            ),
            "authorization_id": authorization_id,
            "model": plan.model,
            "runtime_state": runtime_state,
            "retryable": bool(getattr(response, "retryable", False)),
            "side_effects_executed": side_effects_executed,
            "audit_ref": audit_ref,
            "diagnostic_codes": [
                getattr(item, "code", "unknown") for item in diagnostics
            ],
            "output_artifact_ids": output_artifact_ids,
            "elapsed_ms": elapsed_ms,
            "output_budget": plan.output_budget,
            "timeout_seconds": float(plan.timeout_seconds),
            "provider_calls_allowed": 1,
            "automatic_retries_allowed": 0,
            "tools_allowed": False,
            "response_storage_allowed": False,
            "live_request_executed": bool(
                getattr(response, "side_effects_executed", False)
            ),
            "versions": {
                "openai": openai_version,
                "geotask_core": core_version,
                "openai_adapter": adapter_version,
            },
        }
    }


def execute_live_smoke(
    plan: LiveSmokePlan,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Execute at most one paid request after all explicit gates pass."""

    environment = os.environ if environ is None else environ
    _require_live_authorization(plan, environment)
    request_payload = _load_request(plan)
    if not plan.execute_live:
        return plan.public_plan()

    try:
        import openai
        from openai import OpenAI
        import geotask_core
        from geotask_core import submit_runtime_request
        import geotask_openai_responses_adapter
        from geotask_openai_responses_adapter import (
            OPENAI_AUTHORIZATION_REF,
            OpenAIResponsesConfig,
            StaticOpenAIClientResolver,
            build_openai_responses_runtime_adapter,
        )
    except ImportError as exc:
        raise LiveSmokePreflightError(
            "live-smoke packages are not installed in the active Python environment"
        ) from exc

    try:
        client = OpenAI(
            max_retries=0,
            timeout=float(plan.timeout_seconds),
        )
        config_values: dict[str, object] = {
            "model": plan.model,
            "timeout_seconds": float(plan.timeout_seconds),
        }
        config_values["max_output_" + "tokens"] = plan.output_budget
        adapter = build_openai_responses_runtime_adapter(
            OpenAIResponsesConfig(**config_values),
            StaticOpenAIClientResolver(OPENAI_AUTHORIZATION_REF, client),
        )
    except Exception as exc:
        raise LiveSmokeExecutionError(
            "the authenticated provider client or Runtime Adapter could not be initialized",
            live_request_executed=False,
        ) from exc

    authorization_id = _claim_authorization_ticket(plan)
    started = time.monotonic()
    try:
        response = submit_runtime_request(adapter, request_payload)
    except Exception as exc:
        try:
            _finalize_authorization_claim(
                plan,
                authorization_id,
                state="submission_unknown",
                live_request_executed=None,
            )
        except Exception:
            pass
        raise LiveSmokeExecutionError(
            "the Runtime submission failed without returning a structured response",
            live_request_executed=None,
        ) from exc
    elapsed_ms = max(0, round((time.monotonic() - started) * 1000))
    report = _response_report(
        plan,
        response,
        authorization_id=authorization_id,
        elapsed_ms=elapsed_ms,
        openai_version=str(getattr(openai, "__version__", "unknown")),
        core_version=str(getattr(geotask_core, "__version__", "unknown")),
        adapter_version=str(
            getattr(geotask_openai_responses_adapter, "__version__", "unknown")
        ),
    )
    body = report["openai_live_smoke"]
    try:
        _finalize_authorization_claim(
            plan,
            authorization_id,
            state=(
                "live_smoke_verified"
                if body["valid"]
                else "structured_response_returned"
            ),
            live_request_executed=body["live_request_executed"],
            runtime_state=body["runtime_state"],
            audit_ref=body["audit_ref"],
            valid=body["valid"],
        )
    except Exception as exc:
        raise LiveSmokeExecutionError(
            "the authorization claim could not be finalized after Runtime submission",
            live_request_executed=body["live_request_executed"],
        ) from exc
    return report


def _write_report(
    path: Path,
    payload: dict[str, object],
    *,
    exclusive: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if exclusive:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(str(path), flags, 0o600)
        except FileExistsError as exc:
            raise LiveSmokePreflightError(
                "authorization ticket path already exists and will not be overwritten"
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        try:
            os.fchmod(descriptor, 0o600)
        except (AttributeError, OSError):
            pass
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or explicitly execute one private OpenAI Responses live smoke."
        )
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--model", default=os.environ.get(MODEL_ENVIRONMENT_VARIABLE))
    parser.add_argument(
        "--max-output-tokens",
        dest="output_budget",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--report")
    parser.add_argument(
        "--issue-authorization",
        metavar="PATH",
        help="Issue one short-lived authorization ticket outside the repository.",
    )
    parser.add_argument(
        "--authorization-valid-minutes",
        type=int,
        default=DEFAULT_AUTHORIZATION_VALID_MINUTES,
    )
    parser.add_argument(
        "--authorization-ticket",
        metavar="PATH",
        help="Use one previously issued, unclaimed authorization ticket.",
    )
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Allow one paid provider request after all authorization gates pass.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.issue_authorization and args.execute_live:
            raise LiveSmokePreflightError(
                "--issue-authorization and --execute-live are mutually exclusive"
            )
        if args.issue_authorization and args.report:
            raise LiveSmokePreflightError(
                "--report cannot be used while issuing an authorization ticket"
            )
        if args.issue_authorization and args.authorization_ticket:
            raise LiveSmokePreflightError(
                "--authorization-ticket cannot be used while issuing a new ticket"
            )
        plan = LiveSmokePlan(
            repository_root=Path(args.repository_root),
            model=args.model,
            output_budget=args.output_budget,
            timeout_seconds=args.timeout_seconds,
            execute_live=args.execute_live,
            report_path=Path(args.report) if args.report else None,
            authorization_ticket_path=(
                Path(args.authorization_ticket) if args.authorization_ticket else None
            ),
        )
        if args.issue_authorization:
            payload = issue_authorization_ticket(
                plan,
                Path(args.issue_authorization),
                valid_minutes=args.authorization_valid_minutes,
            )
        else:
            payload = execute_live_smoke(plan)
        if plan.report_path is not None:
            _write_report(plan.report_path, payload)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        if plan.execute_live and not payload["openai_live_smoke"]["valid"]:
            return 3
        return 0
    except LiveSmokePreflightError as exc:
        error = {
            "openai_live_smoke": {
                "valid": False,
                "phase": "preflight",
                "release_gate_state": "preflight_blocked",
                "error": str(exc),
                "live_request_executed": False,
            }
        }
        print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    except LiveSmokeExecutionError as exc:
        error = {
            "openai_live_smoke": {
                "valid": False,
                "phase": "execution",
                "release_gate_state": (
                    "live_smoke_indeterminate"
                    if exc.live_request_executed is None
                    else (
                        "live_smoke_failed"
                        if exc.live_request_executed
                        else "live_execution_blocked"
                    )
                ),
                "error": str(exc),
                "live_request_executed": exc.live_request_executed,
            }
        }
        print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
