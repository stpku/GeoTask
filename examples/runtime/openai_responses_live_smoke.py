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
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


ACK_ENVIRONMENT_VARIABLE = "GEOTASK_OPENAI_LIVE_SMOKE_ACK"
MODEL_ENVIRONMENT_VARIABLE = "GEOTASK_OPENAI_LIVE_MODEL"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
HARD_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 60.0
HARD_MAX_TIMEOUT_SECONDS = 120.0
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
            report = Path(self.report_path).resolve()
            if report.suffix.lower() != ".json":
                raise LiveSmokePreflightError("report_path must use a .json suffix")
            try:
                report.relative_to(root)
            except ValueError:
                pass
            else:
                raise LiveSmokePreflightError(
                    "report_path must be outside the repository to prevent accidental commit"
                )
            object.__setattr__(self, "report_path", report)

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
                "provider_calls_allowed": 1 if self.execute_live else 0,
                "automatic_retries_allowed": 0,
                "tools_allowed": False,
                "response_storage_allowed": False,
                "live_request_executed": False,
            }
        }


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


def _response_report(
    plan: LiveSmokePlan,
    response: object,
    *,
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

    started = time.monotonic()
    try:
        response = submit_runtime_request(adapter, request_payload)
    except Exception as exc:
        raise LiveSmokeExecutionError(
            "the Runtime submission failed without returning a structured response",
            live_request_executed=None,
        ) from exc
    elapsed_ms = max(0, round((time.monotonic() - started) * 1000))
    return _response_report(
        plan,
        response,
        elapsed_ms=elapsed_ms,
        openai_version=str(getattr(openai, "__version__", "unknown")),
        core_version=str(getattr(geotask_core, "__version__", "unknown")),
        adapter_version=str(
            getattr(geotask_openai_responses_adapter, "__version__", "unknown")
        ),
    )


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
        "--execute-live",
        action="store_true",
        help="Allow one paid provider request after the acknowledgement gate passes.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        plan = LiveSmokePlan(
            repository_root=Path(args.repository_root),
            model=args.model,
            output_budget=args.output_budget,
            timeout_seconds=args.timeout_seconds,
            execute_live=args.execute_live,
            report_path=Path(args.report) if args.report else None,
        )
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
                "error": str(exc),
                "live_request_executed": exc.live_request_executed,
            }
        }
        print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
