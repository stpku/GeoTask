"""Private readiness, evidence auditing, and closure retention or verification.

The readiness, evidence, and closure verification commands are read-only. The
explicit ``write-closure`` command can atomically retain one redacted closure
manifest after evidence passes. This module never imports the OpenAI SDK, emits
credential values, creates an authorization claim, or sends a network request.
It remains outside the public export and normal public CI.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

try:  # Package import when loaded through examples.runtime.
    from .openai_responses_live_smoke import (
        ACK_ENVIRONMENT_VARIABLE,
        LiveSmokePlan,
        LiveSmokePreflightError,
        _acknowledgement,
        _credential_environment_variable,
        _load_request,
        _validate_authorization_ticket,
    )
    from .openai_responses_live_smoke_closure import write_closure_manifest
    from .openai_responses_live_smoke_closure_verifier import (
        verify_closure_manifest,
    )
    from .openai_responses_live_smoke_evidence import verify_evidence_bundle
except ImportError:  # Direct script execution from examples/runtime.
    from openai_responses_live_smoke import (  # type: ignore[no-redef]
        ACK_ENVIRONMENT_VARIABLE,
        LiveSmokePlan,
        LiveSmokePreflightError,
        _acknowledgement,
        _credential_environment_variable,
        _load_request,
        _validate_authorization_ticket,
    )
    from openai_responses_live_smoke_closure import (  # type: ignore[no-redef]
        write_closure_manifest,
    )
    from openai_responses_live_smoke_closure_verifier import (  # type: ignore[no-redef]
        verify_closure_manifest,
    )
    from openai_responses_live_smoke_evidence import (  # type: ignore[no-redef]
        verify_evidence_bundle,
    )


_REQUIRED_PACKAGES = (
    "openai",
    "geotask_core",
    "geotask_model_adapter_reference",
    "geotask_openai_responses_adapter",
)


def _check(code: str, passed: bool, detail: str) -> dict[str, object]:
    return {"code": code, "passed": passed, "detail": detail}


def _safe_package_probe(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def audit_readiness(
    plan: LiveSmokePlan,
    *,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
    package_probe: Callable[[str], bool] | None = None,
) -> dict[str, object]:
    """Read all preconditions without importing providers or mutating evidence."""

    environment = os.environ if environ is None else environ
    probe = _safe_package_probe if package_probe is None else package_probe
    checks: list[dict[str, object]] = []
    authorization_id: str | None = None

    try:
        _load_request(plan)
    except LiveSmokePreflightError:
        checks.append(_check("reviewed_request", False, "fixed request validation failed"))
    else:
        checks.append(_check("reviewed_request", True, "fixed request digest matches"))

    acknowledgement_ready = (
        environment.get(ACK_ENVIRONMENT_VARIABLE) == _acknowledgement()
    )
    checks.append(
        _check(
            "explicit_acknowledgement",
            acknowledgement_ready,
            "explicit one-request acknowledgement is present"
            if acknowledgement_ready
            else "explicit one-request acknowledgement is absent",
        )
    )

    credential_name = _credential_environment_variable()
    credential_value = environment.get(credential_name)
    credential_ready = isinstance(credential_value, str) and bool(credential_value.strip())
    checks.append(
        _check(
            "server_credential",
            credential_ready,
            "server credential is present but not emitted"
            if credential_ready
            else "server credential is unavailable",
        )
    )

    base_url_clear = not (
        isinstance(environment.get("OPENAI_BASE_URL"), str)
        and environment["OPENAI_BASE_URL"].strip()
    )
    checks.append(
        _check(
            "official_endpoint",
            base_url_clear,
            "alternate endpoint is not configured"
            if base_url_clear
            else "alternate endpoint configuration is forbidden",
        )
    )

    logging_clear = not environment.get("OPENAI_LOG", "").strip()
    checks.append(
        _check(
            "sdk_logging_disabled",
            logging_clear,
            "SDK logging override is absent"
            if logging_clear
            else "SDK logging override must be removed",
        )
    )

    for package_name in _REQUIRED_PACKAGES:
        available = bool(probe(package_name))
        checks.append(
            _check(
                f"package:{package_name}",
                available,
                "package metadata is discoverable"
                if available
                else "package metadata is unavailable",
            )
        )

    ticket_ready = False
    if plan.authorization_ticket_path is None:
        checks.append(
            _check(
                "authorization_ticket",
                False,
                "an external authorization ticket is required",
            )
        )
    elif not plan.authorization_ticket_path.is_file():
        checks.append(
            _check(
                "authorization_ticket",
                False,
                "authorization ticket file is unavailable",
            )
        )
    else:
        claim_path = plan.authorization_ticket_path.with_suffix(
            plan.authorization_ticket_path.suffix + ".claimed"
        )
        if claim_path.exists():
            checks.append(
                _check(
                    "authorization_ticket",
                    False,
                    "authorization ticket has already been claimed",
                )
            )
        else:
            try:
                authorization_id, _raw, _current = _validate_authorization_ticket(
                    plan,
                    now=now,
                )
            except LiveSmokePreflightError as exc:
                checks.append(
                    _check(
                        "authorization_ticket",
                        False,
                        f"authorization ticket failed strict validation: {exc}",
                    )
                )
            else:
                ticket_ready = True
                checks.append(
                    _check(
                        "authorization_ticket",
                        True,
                        "authorization ticket is active, bound, and unclaimed",
                    )
                )

    ready = bool(checks) and all(bool(item["passed"]) for item in checks)
    return {
        "openai_live_smoke_readiness": {
            "valid": ready,
            "release_gate_state": (
                "live_execution_ready" if ready else "readiness_blocked"
            ),
            "authorization_id": authorization_id if ticket_ready else None,
            "model": plan.model,
            "output_budget": plan.output_budget,
            "timeout_seconds": float(plan.timeout_seconds),
            "provider_calls_allowed": 0,
            "live_request_executed": False,
            "credential_presence_checked": True,
            "credential_value_exposed": False,
            "provider_modules_imported": False,
            "authorization_claim_created": False,
            "checks": checks,
        }
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit private OpenAI live-smoke readiness, retained evidence, or closure."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    readiness = subparsers.add_parser(
        "readiness", help="Check live execution prerequisites without side effects."
    )
    readiness.add_argument("--repository-root", default=".")
    readiness.add_argument("--model", required=True)
    readiness.add_argument(
        "--max-output-tokens",
        dest="output_budget",
        type=int,
        default=2048,
    )
    readiness.add_argument("--timeout-seconds", type=float, default=60.0)
    readiness.add_argument("--authorization-ticket", required=True)

    evidence = subparsers.add_parser(
        "verify-evidence", help="Verify ticket, claim, and report consistency."
    )
    evidence.add_argument("--repository-root", default=".")
    evidence.add_argument("--authorization-ticket", required=True)
    evidence.add_argument("--authorization-claim")
    evidence.add_argument("--report", required=True)

    closure = subparsers.add_parser(
        "write-closure",
        help="Verify retained evidence and record one redacted closure manifest.",
    )
    closure.add_argument("--repository-root", default=".")
    closure.add_argument("--authorization-ticket", required=True)
    closure.add_argument("--authorization-claim")
    closure.add_argument("--report", required=True)
    closure.add_argument("--output", required=True)

    closure_verification = subparsers.add_parser(
        "verify-closure",
        help="Verify exact closure identity and current source evidence binding.",
    )
    closure_verification.add_argument("--repository-root", default=".")
    closure_verification.add_argument("--authorization-ticket", required=True)
    closure_verification.add_argument("--authorization-claim")
    closure_verification.add_argument("--report", required=True)
    closure_verification.add_argument("--closure", required=True)
    closure_verification.add_argument("--expected-closure-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "readiness":
            ticket_path = Path(args.authorization_ticket)
            plan = LiveSmokePlan(
                repository_root=Path(args.repository_root),
                model=args.model,
                output_budget=args.output_budget,
                timeout_seconds=args.timeout_seconds,
                execute_live=True,
                authorization_ticket_path=ticket_path,
            )
            payload = audit_readiness(plan)
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0 if payload["openai_live_smoke_readiness"]["valid"] else 2

        ticket_path = Path(args.authorization_ticket).resolve()
        claim_path = (
            Path(args.authorization_claim).resolve()
            if args.authorization_claim
            else ticket_path.with_suffix(ticket_path.suffix + ".claimed")
        )
        report_path = Path(args.report).resolve()
        if args.command == "write-closure":
            payload = write_closure_manifest(
                ticket_path,
                claim_path,
                report_path,
                Path(args.output).resolve(),
                repository_root=Path(args.repository_root),
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return (
                0
                if payload["openai_live_smoke_closure_write"]["valid"]
                else 2
            )

        if args.command == "verify-closure":
            payload = verify_closure_manifest(
                ticket_path,
                claim_path,
                report_path,
                Path(args.closure).resolve(),
                expected_closure_sha256=args.expected_closure_sha256,
                repository_root=Path(args.repository_root),
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return (
                0
                if payload["openai_live_smoke_closure_verification"]["valid"]
                else 2
            )

        payload = verify_evidence_bundle(
            ticket_path,
            claim_path,
            report_path,
            repository_root=Path(args.repository_root),
        )
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if payload["openai_live_smoke_evidence"]["valid"] else 2
    except (LiveSmokePreflightError, OSError, ValueError) as exc:
        error = (
            "audit input file is unavailable"
            if isinstance(exc, OSError)
            else str(exc)
        )
        payload = {
            "openai_live_smoke_audit": {
                "valid": False,
                "release_gate_state": "audit_input_invalid",
                "error": error,
                "live_request_executed": False,
                "provider_modules_imported": False,
                "credential_presence_checked": False,
                "credential_value_exposed": False,
            }
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
