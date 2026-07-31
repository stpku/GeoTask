"""Offline tests for the private OpenAI Responses live-smoke harness."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "examples" / "runtime" / "openai_responses_live_smoke.py"
SPEC = importlib.util.spec_from_file_location("geotask_openai_live_smoke", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _repository(tmp_path: Path) -> Path:
    request = (
        tmp_path
        / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
    )
    request.parent.mkdir(parents=True, exist_ok=True)
    source = (
        ROOT
        / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
    )
    request.write_bytes(source.read_bytes())
    return tmp_path


def _plan(tmp_path: Path, **changes: object):
    values: dict[str, object] = {
        "repository_root": _repository(tmp_path),
        "model": "gpt-test-2026-07-31",
    }
    values.update(changes)
    return MODULE.LiveSmokePlan(**values)


def _live_plan(tmp_path: Path, **changes: object):
    values: dict[str, object] = {
        "output_budget": 2048,
        "timeout_seconds": 60.0,
    }
    values.update(changes)
    issued_plan = _plan(tmp_path, **values)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-authorization.json"
    ticket_path.unlink(missing_ok=True)
    ticket_path.with_suffix(ticket_path.suffix + ".claimed").unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        issued_plan,
        ticket_path,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
    )
    values.update(
        {
            "execute_live": True,
            "authorization_ticket_path": ticket_path,
        }
    )
    return _plan(tmp_path, **values)


def test_preflight_never_imports_provider_or_allows_a_call(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    original = {
        name: sys.modules.pop(name, None)
        for name in (
            "openai",
            "geotask_core",
            "geotask_openai_responses_adapter",
        )
    }
    try:
        report = MODULE.execute_live_smoke(plan, environ={})
        body = report["live_smoke_plan"]
        assert body["valid"] is True
        assert body["execute_live"] is False
        assert body["provider_calls_allowed"] == 0
        assert body["live_request_executed"] is False
        assert all(name not in sys.modules for name in original)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value


def test_model_budget_timeout_and_report_path_are_fail_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    with pytest.raises(MODULE.LiveSmokePreflightError, match="pinned snapshot"):
        MODULE.LiveSmokePlan(repository_root=root, model="gpt-alias")
    with pytest.raises(MODULE.LiveSmokePreflightError, match="between 1"):
        MODULE.LiveSmokePlan(
            repository_root=root,
            model="gpt-test-2026-07-31",
            output_budget=MODULE.HARD_MAX_OUTPUT_TOKENS + 1,
        )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="at most"):
        MODULE.LiveSmokePlan(
            repository_root=root,
            model="gpt-test-2026-07-31",
            timeout_seconds=MODULE.HARD_MAX_TIMEOUT_SECONDS + 1,
        )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="outside the repository"):
        MODULE.LiveSmokePlan(
            repository_root=root,
            model="gpt-test-2026-07-31",
            report_path=root / "report.json",
        )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="outside the repository"):
        MODULE.LiveSmokePlan(
            repository_root=root,
            model="gpt-test-2026-07-31",
            authorization_ticket_path=root / "authorization.json",
        )
    outside = root.parent / f"{root.name}-shared.json"
    with pytest.raises(MODULE.LiveSmokePreflightError, match="must not overwrite"):
        MODULE.LiveSmokePlan(
            repository_root=root,
            model="gpt-test-2026-07-31",
            report_path=outside,
            authorization_ticket_path=outside,
        )


def test_authorization_ticket_requires_ack_is_short_lived_and_exclusive(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-ticket.json"
    ticket_path.unlink(missing_ok=True)
    fixed = MODULE.datetime(2026, 7, 31, 8, 0, tzinfo=MODULE.timezone.utc)

    with pytest.raises(MODULE.LiveSmokePreflightError, match="issuance requires"):
        MODULE.issue_authorization_ticket(plan, ticket_path, environ={}, now=fixed)

    summary = MODULE.issue_authorization_ticket(
        plan,
        ticket_path,
        valid_minutes=15,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )["authorization_ticket"]
    assert summary["valid"] is True
    assert summary["release_gate_state"] == "live_execution_pending"
    assert summary["max_provider_calls"] == 1
    assert summary["automatic_retries_allowed"] == 0
    assert summary["issued_at"] == "2026-07-31T08:00:00Z"
    assert summary["expires_at"] == "2026-07-31T08:15:00Z"

    payload = json.loads(ticket_path.read_text(encoding="utf-8"))[
        "geotask_openai_live_smoke_authorization"
    ]
    assert payload["model"] == plan.model
    assert payload["request_sha256"] == MODULE._EXPECTED_REQUEST_SHA256
    assert payload["max_provider_calls"] == 1
    if os.name != "nt":
        assert stat.S_IMODE(ticket_path.stat().st_mode) == 0o600
    serialized = json.dumps(payload)
    assert MODULE._credential_environment_variable() not in serialized
    assert MODULE._acknowledgement() not in serialized

    with pytest.raises(MODULE.LiveSmokePreflightError, match="already exists"):
        MODULE.issue_authorization_ticket(
            plan,
            ticket_path,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
            },
            now=fixed,
        )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="between 1"):
        MODULE.issue_authorization_ticket(
            plan,
            tmp_path.parent / f"{tmp_path.name}-too-long.json",
            valid_minutes=MODULE.HARD_MAX_AUTHORIZATION_VALID_MINUTES + 1,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
            },
            now=fixed,
        )

    orphan_ticket = tmp_path.parent / f"{tmp_path.name}-orphan.json"
    orphan_ticket.unlink(missing_ok=True)
    orphan_claim = orphan_ticket.with_suffix(orphan_ticket.suffix + ".claimed")
    orphan_claim.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MODULE.LiveSmokePreflightError, match="claim history"):
        MODULE.issue_authorization_ticket(
            plan,
            orphan_ticket,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
            },
            now=fixed,
        )


def test_authorization_ticket_is_bound_expires_and_cannot_be_reused(
    tmp_path: Path,
) -> None:
    fixed = MODULE.datetime(2026, 7, 31, 8, 0, tzinfo=MODULE.timezone.utc)
    plan = _plan(tmp_path, output_budget=1024)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-claim.json"
    ticket_path.unlink(missing_ok=True)
    ticket_path.with_suffix(ticket_path.suffix + ".claimed").unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        plan,
        ticket_path,
        valid_minutes=15,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )
    live_plan = _plan(
        tmp_path,
        output_budget=1024,
        execute_live=True,
        authorization_ticket_path=ticket_path,
    )
    authorization_id = MODULE._claim_authorization_ticket(
        live_plan,
        now=fixed + MODULE.timedelta(minutes=1),
    )
    assert isinstance(authorization_id, str)
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    claim = json.loads(claim_path.read_text(encoding="utf-8"))["authorization_claim"]
    assert claim["authorization_id"] == authorization_id
    assert claim["state"] == "claimed"
    assert claim["live_request_executed"] is None

    with pytest.raises(MODULE.LiveSmokePreflightError, match="already been claimed"):
        MODULE._claim_authorization_ticket(
            live_plan,
            now=fixed + MODULE.timedelta(minutes=2),
        )

    mismatch_path = tmp_path.parent / f"{tmp_path.name}-mismatch.json"
    mismatch_path.unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        plan,
        mismatch_path,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )
    mismatched_plan = _plan(
        tmp_path,
        output_budget=2048,
        execute_live=True,
        authorization_ticket_path=mismatch_path,
    )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="output_budget"):
        MODULE._claim_authorization_ticket(
            mismatched_plan,
            now=fixed + MODULE.timedelta(minutes=1),
        )

    expired_path = tmp_path.parent / f"{tmp_path.name}-expired.json"
    expired_path.unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        plan,
        expired_path,
        valid_minutes=1,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )
    expired_plan = _plan(
        tmp_path,
        output_budget=1024,
        execute_live=True,
        authorization_ticket_path=expired_path,
    )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="expired"):
        MODULE._claim_authorization_ticket(
            expired_plan,
            now=fixed + MODULE.timedelta(minutes=2),
        )


def test_authorization_claim_finalization_rejects_tampering(
    tmp_path: Path,
) -> None:
    fixed = MODULE.datetime(2026, 7, 31, 8, 0, tzinfo=MODULE.timezone.utc)
    plan = _plan(tmp_path)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-finalize.json"
    ticket_path.unlink(missing_ok=True)
    claim_path = ticket_path.with_suffix(ticket_path.suffix + ".claimed")
    claim_path.unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        plan,
        ticket_path,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )
    live_plan = _plan(
        tmp_path,
        execute_live=True,
        authorization_ticket_path=ticket_path,
    )
    authorization_id = MODULE._claim_authorization_ticket(
        live_plan,
        now=fixed + MODULE.timedelta(minutes=1),
    )
    claim_payload = json.loads(claim_path.read_text(encoding="utf-8"))
    claim_payload["authorization_claim"]["ticket_sha256"] = "0" * 64
    claim_path.write_text(json.dumps(claim_payload), encoding="utf-8")
    if os.name != "nt":
        claim_path.chmod(0o600)

    with pytest.raises(MODULE.LiveSmokeExecutionError, match="no longer matches"):
        MODULE._finalize_authorization_claim(
            live_plan,
            authorization_id,
            state="live_smoke_verified",
            live_request_executed=True,
            runtime_state="completed",
            audit_ref="openai://responses/req/resp",
            valid=True,
        )
    remaining = json.loads(claim_path.read_text(encoding="utf-8"))[
        "authorization_claim"
    ]
    assert remaining["state"] == "claimed"
    assert remaining["live_request_executed"] is None


def test_authorization_ticket_rejects_extra_fields_and_invalid_uuid(
    tmp_path: Path,
) -> None:
    fixed = MODULE.datetime(2026, 7, 31, 8, 0, tzinfo=MODULE.timezone.utc)
    plan = _plan(tmp_path)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-strict.json"
    ticket_path.unlink(missing_ok=True)
    MODULE.issue_authorization_ticket(
        plan,
        ticket_path,
        environ={
            MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
        },
        now=fixed,
    )
    payload = json.loads(ticket_path.read_text(encoding="utf-8"))
    body = payload["geotask_openai_live_smoke_authorization"]
    body["unexpected"] = True
    ticket_path.write_text(json.dumps(payload), encoding="utf-8")
    if os.name != "nt":
        ticket_path.chmod(0o600)
    live_plan = _plan(
        tmp_path,
        execute_live=True,
        authorization_ticket_path=ticket_path,
    )
    with pytest.raises(MODULE.LiveSmokePreflightError, match="strict ticket contract"):
        MODULE._claim_authorization_ticket(
            live_plan,
            now=fixed + MODULE.timedelta(minutes=1),
        )

    body.pop("unexpected")
    body["authorization_id"] = "not-a-uuid"
    ticket_path.write_text(json.dumps(payload), encoding="utf-8")
    if os.name != "nt":
        ticket_path.chmod(0o600)
    with pytest.raises(MODULE.LiveSmokePreflightError, match="must be a UUID"):
        MODULE._claim_authorization_ticket(
            live_plan,
            now=fixed + MODULE.timedelta(minutes=1),
        )


def test_reviewed_request_digest_is_required(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan.request_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MODULE.LiveSmokePreflightError, match="digest"):
        MODULE.execute_live_smoke(plan, environ={})


def test_live_requires_two_explicit_gates_before_import(tmp_path: Path) -> None:
    plan = _plan(tmp_path, execute_live=True)
    with pytest.raises(MODULE.LiveSmokePreflightError, match="requires"):
        MODULE.execute_live_smoke(plan, environ={})

    credential_name = MODULE._credential_environment_variable()
    with pytest.raises(MODULE.LiveSmokePreflightError, match="credential"):
        MODULE.execute_live_smoke(
            plan,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
            },
        )

    with pytest.raises(MODULE.LiveSmokePreflightError, match="alternate endpoint"):
        MODULE.execute_live_smoke(
            plan,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
                credential_name: "[REDACTED_SECRET]",
                "OPENAI_BASE_URL": "https://example.invalid/v1",
            },
        )

    with pytest.raises(MODULE.LiveSmokePreflightError, match="must be unset"):
        MODULE.execute_live_smoke(
            plan,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
                credential_name: "[REDACTED_SECRET]",
                "OPENAI_LOG": "info",
            },
        )

    with pytest.raises(MODULE.LiveSmokePreflightError, match="authorization-ticket"):
        MODULE.execute_live_smoke(
            plan,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
                credential_name: "[REDACTED_SECRET]",
            },
        )


def test_live_uses_one_no_retry_call_and_redacted_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_name = MODULE._credential_environment_variable()
    monkeypatch.setenv(MODULE.ACK_ENVIRONMENT_VARIABLE, MODULE._acknowledgement())
    monkeypatch.setenv(credential_name, "[REDACTED_SECRET]")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_LOG", raising=False)

    created_clients: list[object] = []

    class FakeOpenAI:
        def __init__(self, **kwargs: object):
            self.kwargs = dict(kwargs)
            created_clients.append(self)

    openai_module = ModuleType("openai")
    openai_module.OpenAI = FakeOpenAI
    openai_module.__version__ = "2.test"

    class FakeResponse:
        state = "completed"
        retryable = False
        side_effects_executed = True
        audit_ref = "openai://responses/req_live/resp_live"
        diagnostics = ()
        output_artifacts = (SimpleNamespace(artifact_id="geotask.execution-result"),)

    core_module = ModuleType("geotask_core")
    core_module.__version__ = "0.4.test"
    core_calls: list[tuple[object, object]] = []

    def submit_runtime_request(adapter: object, payload: object) -> FakeResponse:
        core_calls.append((adapter, payload))
        return FakeResponse()

    core_module.submit_runtime_request = submit_runtime_request

    adapter_module = ModuleType("geotask_openai_responses_adapter")
    adapter_module.__version__ = "0.1.test"
    adapter_module.OPENAI_AUTHORIZATION_REF = MODULE._authorization_reference()

    class OpenAIResponsesConfig:
        def __init__(self, **kwargs: object):
            self.kwargs = dict(kwargs)

    class StaticOpenAIClientResolver:
        def __init__(self, authorization_ref: str, client: object):
            self.authorization_ref = authorization_ref
            self.client = client

    built: list[tuple[object, object]] = []

    def build_openai_responses_runtime_adapter(config: object, resolver: object) -> object:
        adapter = SimpleNamespace(config=config, resolver=resolver)
        built.append((config, resolver))
        return adapter

    adapter_module.OpenAIResponsesConfig = OpenAIResponsesConfig
    adapter_module.StaticOpenAIClientResolver = StaticOpenAIClientResolver
    adapter_module.build_openai_responses_runtime_adapter = (
        build_openai_responses_runtime_adapter
    )

    monkeypatch.setitem(sys.modules, "openai", openai_module)
    monkeypatch.setitem(sys.modules, "geotask_core", core_module)
    monkeypatch.setitem(
        sys.modules,
        "geotask_openai_responses_adapter",
        adapter_module,
    )

    plan = _live_plan(tmp_path, output_budget=1024)
    report = MODULE.execute_live_smoke(plan)
    body = report["openai_live_smoke"]

    assert len(created_clients) == 1
    assert created_clients[0].kwargs == {"max_retries": 0, "timeout": 60.0}
    assert len(built) == 1
    expected_config = {
        "model": "gpt-test-2026-07-31",
        "timeout_seconds": 60.0,
    }
    expected_config["max_output_" + "tokens"] = 1024
    assert built[0][0].kwargs == expected_config
    assert built[0][1].authorization_ref == MODULE._authorization_reference()
    assert len(core_calls) == 1
    assert body["valid"] is True
    assert body["provider_calls_allowed"] == 1
    assert body["automatic_retries_allowed"] == 0
    assert body["tools_allowed"] is False
    assert body["response_storage_allowed"] is False
    assert body["live_request_executed"] is True
    assert body["release_gate_state"] == "live_smoke_verified"
    assert isinstance(body["authorization_id"], str)
    claim_path = plan.authorization_ticket_path.with_suffix(
        plan.authorization_ticket_path.suffix + ".claimed"
    )
    claim = json.loads(claim_path.read_text(encoding="utf-8"))["authorization_claim"]
    assert claim["authorization_id"] == body["authorization_id"]
    assert claim["state"] == "live_smoke_verified"
    assert claim["valid"] is True
    assert claim["live_request_executed"] is True
    assert claim["runtime_state"] == "completed"
    serialized = json.dumps(report)
    assert "REDACTED_SECRET" not in serialized
    assert credential_name not in serialized


def test_completed_state_alone_is_not_live_smoke_success(tmp_path: Path) -> None:
    plan = _plan(tmp_path, execute_live=True)

    def report_for(**changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "state": "completed",
            "retryable": False,
            "side_effects_executed": True,
            "audit_ref": "openai://responses/req/resp",
            "diagnostics": (),
            "output_artifacts": (
                SimpleNamespace(artifact_id="geotask.execution-result"),
            ),
        }
        values.update(changes)
        return MODULE._response_report(
            plan,
            SimpleNamespace(**values),
            authorization_id="auth-test",
            elapsed_ms=1,
            openai_version="2.test",
            core_version="0.4.test",
            adapter_version="0.1.test",
        )["openai_live_smoke"]

    assert report_for()["valid"] is True
    assert report_for(side_effects_executed=False)["valid"] is False
    assert report_for(audit_ref=None)["valid"] is False
    assert report_for(audit_ref="other://req/resp")["valid"] is False
    assert report_for(
        audit_ref="openai://responses/client-local/unknown-response"
    )["valid"] is False
    assert report_for(
        audit_ref="openai://responses/req-server/unknown-response"
    )["valid"] is False
    assert report_for(output_artifacts=())["valid"] is False
    assert report_for(
        output_artifacts=(SimpleNamespace(artifact_id="geotask.runtime-response"),)
    )["valid"] is False


def test_client_initialization_failure_is_generic_and_pre_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_name = MODULE._credential_environment_variable()

    class BrokenOpenAI:
        def __init__(self, **_kwargs: object):
            raise RuntimeError("[REDACTED_PRIVATE_DATA] client detail")

    openai_module = ModuleType("openai")
    openai_module.OpenAI = BrokenOpenAI
    openai_module.__version__ = "2.test"
    core_module = ModuleType("geotask_core")
    core_module.__version__ = "0.4.test"
    core_module.submit_runtime_request = lambda *_args: None
    adapter_module = ModuleType("geotask_openai_responses_adapter")
    adapter_module.__version__ = "0.1.test"
    adapter_module.OPENAI_AUTHORIZATION_REF = MODULE._authorization_reference()
    adapter_module.OpenAIResponsesConfig = lambda **kwargs: kwargs
    adapter_module.StaticOpenAIClientResolver = lambda *args: args
    adapter_module.build_openai_responses_runtime_adapter = lambda *args: args
    monkeypatch.setitem(sys.modules, "openai", openai_module)
    monkeypatch.setitem(sys.modules, "geotask_core", core_module)
    monkeypatch.setitem(
        sys.modules,
        "geotask_openai_responses_adapter",
        adapter_module,
    )

    with pytest.raises(MODULE.LiveSmokeExecutionError) as caught:
        plan = _live_plan(tmp_path)
        MODULE.execute_live_smoke(
            plan,
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
                credential_name: "[REDACTED_SECRET]",
            },
        )
    assert caught.value.live_request_executed is False
    claim_path = plan.authorization_ticket_path.with_suffix(
        plan.authorization_ticket_path.suffix + ".claimed"
    )
    assert claim_path.exists() is False
    assert str(caught.value) == (
        "the authenticated provider client or Runtime Adapter could not be initialized"
    )
    assert "REDACTED_PRIVATE_DATA" not in str(caught.value)


def test_unstructured_submission_failure_is_generic_and_execution_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_name = MODULE._credential_environment_variable()

    class FakeOpenAI:
        def __init__(self, **_kwargs: object):
            pass

    openai_module = ModuleType("openai")
    openai_module.OpenAI = FakeOpenAI
    openai_module.__version__ = "2.test"
    core_module = ModuleType("geotask_core")
    core_module.__version__ = "0.4.test"

    def submit_runtime_request(*_args: object) -> object:
        raise RuntimeError("[REDACTED_PRIVATE_DATA] submission detail")

    core_module.submit_runtime_request = submit_runtime_request
    adapter_module = ModuleType("geotask_openai_responses_adapter")
    adapter_module.__version__ = "0.1.test"
    adapter_module.OPENAI_AUTHORIZATION_REF = MODULE._authorization_reference()
    adapter_module.OpenAIResponsesConfig = lambda **kwargs: kwargs
    adapter_module.StaticOpenAIClientResolver = lambda *args: args
    adapter_module.build_openai_responses_runtime_adapter = lambda *args: args
    monkeypatch.setitem(sys.modules, "openai", openai_module)
    monkeypatch.setitem(sys.modules, "geotask_core", core_module)
    monkeypatch.setitem(
        sys.modules,
        "geotask_openai_responses_adapter",
        adapter_module,
    )

    with pytest.raises(MODULE.LiveSmokeExecutionError) as caught:
        MODULE.execute_live_smoke(
            _live_plan(tmp_path),
            environ={
                MODULE.ACK_ENVIRONMENT_VARIABLE: MODULE._acknowledgement(),
                credential_name: "[REDACTED_SECRET]",
            },
        )
    assert caught.value.live_request_executed is None
    assert str(caught.value) == (
        "the Runtime submission failed without returning a structured response"
    )
    assert "REDACTED_PRIVATE_DATA" not in str(caught.value)
    claim_paths = list(tmp_path.parent.glob(f"{tmp_path.name}-authorization.json.claimed"))
    assert len(claim_paths) == 1
    claim = json.loads(claim_paths[0].read_text(encoding="utf-8"))[
        "authorization_claim"
    ]
    assert claim["state"] == "submission_unknown"
    assert claim["live_request_executed"] is None
    assert claim["valid"] is None


def test_report_is_atomic_private_and_contains_no_model_output(tmp_path: Path) -> None:
    report_path = tmp_path / "outside" / "live-smoke.json"
    payload = {
        "openai_live_smoke": {
            "valid": True,
            "audit_ref": "openai://responses/req/resp",
        }
    }
    MODULE._write_report(report_path, payload)
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    if os.name != "nt":
        assert stat.S_IMODE(report_path.stat().st_mode) == 0o600
    assert list(report_path.parent.glob("*.tmp")) == []


def test_cli_preflight_is_default_and_missing_model_is_clean(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    monkeypatch.delenv(MODULE.MODEL_ENVIRONMENT_VARIABLE, raising=False)
    assert MODULE.main(["--repository-root", str(root)]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["openai_live_smoke"]["live_request_executed"] is False

    assert MODULE.main(
        [
            "--repository-root",
            str(root),
            "--model",
            "gpt-test-2026-07-31",
        ]
    ) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["live_smoke_plan"]["provider_calls_allowed"] == 0


def test_cli_issues_one_ticket_without_provider_access(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    ticket_path = tmp_path.parent / f"{tmp_path.name}-cli-ticket.json"
    ticket_path.unlink(missing_ok=True)
    monkeypatch.setenv(
        MODULE.ACK_ENVIRONMENT_VARIABLE,
        MODULE._acknowledgement(),
    )
    provider_modules = (
        "openai",
        "geotask_core",
        "geotask_openai_responses_adapter",
    )
    original = {name: sys.modules.pop(name, None) for name in provider_modules}
    try:
        result = MODULE.main(
            [
                "--repository-root",
                str(root),
                "--model",
                "gpt-test-2026-07-31",
                "--authorization-valid-minutes",
                "10",
                "--issue-authorization",
                str(ticket_path),
            ]
        )
        assert all(name not in sys.modules for name in provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value
    assert result == 0
    summary = json.loads(capsys.readouterr().out)["authorization_ticket"]
    assert summary["release_gate_state"] == "live_execution_pending"
    assert summary["live_request_executed"] is False
    assert ticket_path.is_file()

    report_path = tmp_path.parent / f"{tmp_path.name}-issue-report.json"
    assert MODULE.main(
        [
            "--repository-root",
            str(root),
            "--model",
            "gpt-test-2026-07-31",
            "--issue-authorization",
            str(tmp_path.parent / f"{tmp_path.name}-second-ticket.json"),
            "--report",
            str(report_path),
        ]
    ) == 2
    error = json.loads(capsys.readouterr().err)["openai_live_smoke"]
    assert error["release_gate_state"] == "preflight_blocked"
    assert error["live_request_executed"] is False


def test_cli_execution_error_is_generic_and_reports_unknown_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)

    def fail_execution(_plan: object) -> object:
        raise MODULE.LiveSmokeExecutionError(
            "generic execution failure",
            live_request_executed=None,
        )

    monkeypatch.setattr(MODULE, "execute_live_smoke", fail_execution)
    assert MODULE.main(
        [
            "--repository-root",
            str(root),
            "--model",
            "gpt-test-2026-07-31",
            "--execute-live",
        ]
    ) == 4
    error = json.loads(capsys.readouterr().err)["openai_live_smoke"]
    assert error == {
        "valid": False,
        "phase": "execution",
        "release_gate_state": "live_smoke_indeterminate",
        "error": "generic execution failure",
        "live_request_executed": None,
    }


def test_private_harness_and_tests_are_excluded_from_public_export() -> None:
    import yaml

    release_dir = ROOT / ".release"
    if str(release_dir) not in sys.path:
        sys.path.insert(0, str(release_dir))
    import export_public

    manifest = yaml.safe_load(
        (release_dir / "public-manifest.yaml").read_text(encoding="utf-8")
    )
    exported = {
        path.relative_to(ROOT).as_posix()
        for path in export_public.collect_files(manifest)
    }
    assert "examples/runtime/openai_responses_live_smoke.py" not in exported
    assert "tests/test_openai_responses_live_smoke_harness.py" not in exported
