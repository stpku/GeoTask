"""Local fixtures for private OpenAI live-smoke tests.

This directory is intentionally outside the public test whitelist. The factory
creates only fictional, repository-external evidence and never calls a provider.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "examples" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

SMOKE = importlib.import_module("openai_responses_live_smoke")
AUDIT = importlib.import_module("openai_responses_live_smoke_audit")
CLOSURE = importlib.import_module("openai_responses_live_smoke_closure")
CLOSURE_VERIFIER = importlib.import_module(
    "openai_responses_live_smoke_closure_verifier"
)

FIXED = datetime(2026, 7, 31, 8, 0, tzinfo=timezone.utc)
MODEL = "gpt-test-2026-07-31"
AUDIT_REF = "openai://responses/req_server/resp_server"
PROVIDER_MODULES = (
    "openai",
    "geotask_core",
    "geotask_openai_responses_adapter",
)


@dataclass
class LiveSmokeTestFactory:
    """Create consistent fictional ticket, report, and closure evidence."""

    tmp_path: Path

    root = ROOT
    smoke = SMOKE
    audit = AUDIT
    closure = CLOSURE
    closure_verifier = CLOSURE_VERIFIER
    fixed = FIXED
    model = MODEL
    audit_ref = AUDIT_REF
    provider_modules = PROVIDER_MODULES

    def repository(self) -> Path:
        request = (
            self.tmp_path
            / "examples/model_adapters/openai_responses/examples/"
            "openai_runtime_request.json"
        )
        request.parent.mkdir(parents=True, exist_ok=True)
        source = (
            self.root
            / "examples/model_adapters/openai_responses/examples/"
            "openai_runtime_request.json"
        )
        request.write_bytes(source.read_bytes())
        return self.tmp_path

    def plan(
        self,
        *,
        ticket_path: Path | None = None,
        output_budget: int = 2048,
        timeout_seconds: float = 60.0,
    ):
        return self.smoke.LiveSmokePlan(
            repository_root=self.repository(),
            model=self.model,
            output_budget=output_budget,
            timeout_seconds=timeout_seconds,
            execute_live=True,
            authorization_ticket_path=ticket_path,
        )

    def issue_ticket(
        self,
        *,
        now: datetime | None = None,
        valid_minutes: int = 15,
        output_budget: int = 2048,
        timeout_seconds: float = 60.0,
    ) -> tuple[object, Path]:
        ticket_path = self.tmp_path.parent / f"{self.tmp_path.name}-authorization.json"
        claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
        ticket_path.unlink(missing_ok=True)
        claim_path.unlink(missing_ok=True)
        plan = self.plan(
            output_budget=output_budget,
            timeout_seconds=timeout_seconds,
        )
        self.smoke.issue_authorization_ticket(
            plan,
            ticket_path,
            valid_minutes=valid_minutes,
            environ={
                self.smoke.ACK_ENVIRONMENT_VARIABLE: self.smoke._acknowledgement(),
            },
            now=self.fixed if now is None else now,
        )
        return (
            self.plan(
                ticket_path=ticket_path,
                output_budget=output_budget,
                timeout_seconds=timeout_seconds,
            ),
            ticket_path,
        )

    def write_verified_bundle(self) -> tuple[Path, Path, Path, str]:
        plan, ticket_path = self.issue_ticket()
        authorization_id = self.smoke._claim_authorization_ticket(
            plan,
            now=self.fixed + timedelta(minutes=1),
        )
        claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
        claim = json.loads(claim_path.read_text(encoding="utf-8"))[
            "authorization_claim"
        ]
        finalized_claim = {
            "authorization_claim": {
                "authorization_id": authorization_id,
                "claimed_at": claim["claimed_at"],
                "finalized_at": "2026-07-31T08:02:00Z",
                "ticket_sha256": claim["ticket_sha256"],
                "state": "live_smoke_verified",
                "live_request_executed": True,
                "runtime_state": "completed",
                "audit_ref": self.audit_ref,
                "valid": True,
            }
        }
        self.smoke._write_report(claim_path, finalized_claim)

        report_path = (
            self.tmp_path.parent / f"{self.tmp_path.name}-live-smoke-report.json"
        )
        report_path.unlink(missing_ok=True)
        report = {
            "openai_live_smoke": {
                "valid": True,
                "release_gate_state": "live_smoke_verified",
                "authorization_id": authorization_id,
                "model": self.model,
                "runtime_state": "completed",
                "retryable": False,
                "side_effects_executed": True,
                "audit_ref": self.audit_ref,
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
        self.smoke._write_report(report_path, report)
        return ticket_path, claim_path, report_path, authorization_id

    def write_verified_closure(self) -> tuple[Path, Path, Path, Path, str, str]:
        ticket_path, claim_path, report_path, authorization_id = (
            self.write_verified_bundle()
        )
        closure_path = (
            self.tmp_path.parent / f"{self.tmp_path.name}-verified-closure.json"
        )
        closure_path.unlink(missing_ok=True)
        result = self.audit.write_closure_manifest(
            ticket_path,
            claim_path,
            report_path,
            closure_path,
            repository_root=self.tmp_path,
            now=self.fixed + timedelta(minutes=3),
        )["openai_live_smoke_closure_write"]
        assert result["valid"] is True
        return (
            ticket_path,
            claim_path,
            report_path,
            closure_path,
            authorization_id,
            result["closure_manifest_sha256"],
        )


@pytest.fixture
def live_smoke(tmp_path: Path) -> LiveSmokeTestFactory:
    return LiveSmokeTestFactory(tmp_path)
