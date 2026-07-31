"""Offline tests for private OpenAI live-smoke environment inspection."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "examples" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

SMOKE = importlib.import_module("openai_responses_live_smoke")
ENVIRONMENT = importlib.import_module("openai_responses_live_smoke_environment")
AUDIT = importlib.import_module("openai_responses_live_smoke_audit")


def _repository(tmp_path: Path) -> Path:
    files = {
        "src/geotask_core/_version.py": '__version__ = "0.3.0"\n',
        (
            "examples/model_adapters/provider_neutral/src/"
            "geotask_model_adapter_reference/contracts.py"
        ): 'MODEL_ADAPTER_PACKAGE_VERSION = "0.1.0"\n',
        (
            "examples/model_adapters/openai_responses/src/"
            "geotask_openai_responses_adapter/config.py"
        ): 'OPENAI_RESPONSES_ADAPTER_VERSION = "0.1.0"\n',
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def _source_origins(root: Path) -> dict[str, Path]:
    return {
        "openai": Path("/opt/python/site-packages/openai/__init__.py"),
        "geotask_core": root / "src/geotask_core/__init__.py",
        "geotask_model_adapter_reference": (
            root
            / "examples/model_adapters/provider_neutral/src/"
            "geotask_model_adapter_reference/__init__.py"
        ),
        "geotask_openai_responses_adapter": (
            root
            / "examples/model_adapters/openai_responses/src/"
            "geotask_openai_responses_adapter/__init__.py"
        ),
    }


def _installed_origins() -> dict[str, Path]:
    return {
        "openai": Path("/opt/venv/site-packages/openai/__init__.py"),
        "geotask_core": Path("/opt/venv/site-packages/geotask_core/__init__.py"),
        "geotask_model_adapter_reference": Path(
            "/opt/venv/site-packages/geotask_model_adapter_reference/__init__.py"
        ),
        "geotask_openai_responses_adapter": Path(
            "/opt/venv/site-packages/geotask_openai_responses_adapter/__init__.py"
        ),
    }


def _distribution_probe(
    versions: dict[str, str],
    *,
    editable: set[str] | None = None,
):
    editable_names = set() if editable is None else editable

    def probe(name: str):
        version = versions.get(name)
        return ENVIRONMENT.DistributionRecord(
            present=version is not None,
            version=version,
            editable=name in editable_names,
            location=(
                Path("/opt/venv/site-packages")
                if version is not None
                else None
            ),
        )

    return probe


def _inspect(
    root: Path,
    *,
    origins: dict[str, Path | None],
    versions: dict[str, str],
    environ: dict[str, str] | None = None,
    editable: set[str] | None = None,
):
    return ENVIRONMENT.inspect_environment(
        root,
        environ={} if environ is None else environ,
        python_version=(3, 12, 3),
        module_probe=lambda name: origins.get(name),
        distribution_probe=_distribution_probe(versions, editable=editable),
    )["openai_live_smoke_environment"]


def test_version_ranges_fail_closed_for_prereleases_and_next_series() -> None:
    assert ENVIRONMENT._version_in_range("2.46.0", "2.46.0", "3.0.0") is True
    assert ENVIRONMENT._version_in_range("2.99.9", "2.46.0", "3.0.0") is True
    assert ENVIRONMENT._version_in_range("2.46.0rc1", "2.46.0", "3.0.0") is False
    assert ENVIRONMENT._version_in_range("2.47.0rc1", "2.46.0", "3.0.0") is False
    assert ENVIRONMENT._version_in_range("3.0.0rc1", "2.46.0", "3.0.0") is False
    assert ENVIRONMENT._version_in_range("3.0.0", "2.46.0", "3.0.0") is False
    assert ENVIRONMENT._version_in_range("invalid", "2.46.0", "3.0.0") is False


def test_source_checkout_is_ready_without_claiming_formal_release(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    provider_modules = (
        "openai",
        "geotask_core",
        "geotask_model_adapter_reference",
        "geotask_openai_responses_adapter",
    )
    original = {name: sys.modules.pop(name, None) for name in provider_modules}
    try:
        body = _inspect(
            root,
            origins=_source_origins(root),
            versions={"openai": "2.46.0"},
        )
        assert all(name not in sys.modules for name in provider_modules)
    finally:
        for name, value in original.items():
            if value is not None:
                sys.modules[name] = value

    assert body["valid"] is True
    assert body["release_gate_state"] == "source_checkout_ready"
    assert body["source_checkout_ready"] is True
    assert body["source_checkout_blockers"] == []
    assert body["installed_package_ready"] is False
    assert body["formal_release_compatible"] is False
    assert "geotask_core_version_incompatible" in body["formal_release_blockers"]
    assert body["live_execution_environment_ready"] is False
    assert body["live_execution_ready"] is False
    assert body["live_execution_blockers"] == [
        "server_credential_absent",
        "explicit_acknowledgement_absent",
        "authorization_ticket_not_checked",
    ]
    assert body["authorization_ticket_checked"] is False
    assert body["provider_modules_imported"] is False
    assert body["network_called"] is False
    assert body["credential_present"] is False
    assert body["credential_value_exposed"] is False

    core = body["components"]["geotask_core"]
    assert core["loading_mode"] == "source_checkout"
    assert core["source_declared_version"] == "0.3.0"
    assert core["source_required_range"] == ">=0.3.0,<0.5.0"
    assert core["source_version_contract_satisfied"] is True
    assert core["effective_version"] == "0.3.0"
    assert core["formal_version_contract_satisfied"] is False
    assert core["origin_scope"] == "repository_source"
    serialized = json.dumps(body)
    assert str(root) not in serialized


def test_source_checkout_live_environment_needs_ack_and_credential(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    credential_name = SMOKE._credential_environment_variable()
    secret = "[REDACTED_SECRET]"
    body = _inspect(
        root,
        origins=_source_origins(root),
        versions={"openai": "2.46.0"},
        environ={
            credential_name: secret,
            SMOKE.ACK_ENVIRONMENT_VARIABLE: SMOKE._acknowledgement(),
        },
    )

    assert body["source_checkout_ready"] is True
    assert body["credential_present"] is True
    assert body["acknowledgement_present"] is True
    assert body["live_execution_environment_ready"] is True
    assert body["live_execution_ready"] is False
    assert body["live_execution_blockers"] == ["authorization_ticket_not_checked"]
    serialized = json.dumps(body)
    assert secret not in serialized
    assert credential_name not in serialized
    assert SMOKE._acknowledgement() not in serialized


def test_editable_source_is_explicitly_not_formal_install(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    editable = {
        "geotask-core",
        "geotask-provider-neutral-model-adapter",
        "geotask-openai-responses-adapter",
    }
    body = _inspect(
        root,
        origins=_source_origins(root),
        versions={
            "openai": "2.46.0",
            "geotask-core": "0.3.0",
            "geotask-provider-neutral-model-adapter": "0.1.0",
            "geotask-openai-responses-adapter": "0.1.0",
        },
        editable=editable,
    )

    assert body["source_checkout_ready"] is True
    assert body["source_checkout_blockers"] == []
    assert body["installed_package_ready"] is False
    assert body["formal_release_compatible"] is False
    assert body["components"]["geotask_core"]["loading_mode"] == "editable_install"


def test_formal_noneditable_install_requires_all_version_contracts(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    compatible = {
        "openai": "2.46.0",
        "geotask-core": "0.4.0",
        "geotask-provider-neutral-model-adapter": "0.1.0",
        "geotask-openai-responses-adapter": "0.1.0",
    }
    body = _inspect(root, origins=_installed_origins(), versions=compatible)

    assert body["valid"] is True
    assert body["release_gate_state"] == "formal_release_compatible"
    assert body["source_checkout_ready"] is False
    assert body["installed_package_ready"] is True
    assert body["formal_release_compatible"] is True
    assert body["formal_release_blockers"] == []
    assert all(
        component["loading_mode"] == "installed_package"
        for component in body["components"].values()
    )

    incompatible = dict(compatible)
    incompatible["geotask-core"] = "0.3.0"
    blocked = _inspect(root, origins=_installed_origins(), versions=incompatible)
    assert blocked["valid"] is False
    assert blocked["release_gate_state"] == "installed_package_version_blocked"
    assert blocked["installed_package_ready"] is True
    assert blocked["formal_release_compatible"] is False
    assert "geotask_core_version_incompatible" in blocked["formal_release_blockers"]
    assert (
        blocked["components"]["geotask_core"][
            "formal_version_contract_satisfied"
        ]
        is False
    )


def test_formal_install_rejects_distribution_shadowing(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    origins = _installed_origins()
    origins["geotask_core"] = Path("/tmp/shadow/geotask_core/__init__.py")
    body = _inspect(
        root,
        origins=origins,
        versions={
            "openai": "2.46.0",
            "geotask-core": "0.4.0",
            "geotask-provider-neutral-model-adapter": "0.1.0",
            "geotask-openai-responses-adapter": "0.1.0",
        },
    )

    assert body["valid"] is False
    assert body["installed_package_ready"] is False
    assert body["formal_release_compatible"] is False
    core = body["components"]["geotask_core"]
    assert core["loading_mode"] == "distribution_shadowed"
    assert core["distribution_owns_module"] is False
    assert "geotask_core_distribution_does_not_own_module" in body[
        "formal_release_blockers"
    ]


def test_environment_reports_sdk_and_configuration_blockers(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    origins = _source_origins(root)
    origins["geotask_model_adapter_reference"] = None
    body = _inspect(
        root,
        origins=origins,
        versions={"openai": "1.109.1"},
        environ={
            "OPENAI_BASE_URL": "https://example.invalid/v1",
            "OPENAI_LOG": "debug",
        },
    )

    assert body["valid"] is False
    assert body["release_gate_state"] == "environment_blocked"
    assert body["source_checkout_ready"] is False
    assert body["formal_release_compatible"] is False
    assert "openai_sdk_version_incompatible" in body["source_checkout_blockers"]
    assert "alternate_endpoint_configured" in body["source_checkout_blockers"]
    assert "sdk_logging_enabled" in body["source_checkout_blockers"]
    assert (
        "provider_neutral_adapter_module_unavailable"
        in body["source_checkout_blockers"]
    )
    assert body["components"]["openai_sdk"]["effective_version"] == "1.109.1"
    assert (
        body["components"]["openai_sdk"]["formal_version_contract_satisfied"]
        is False
    )
    failed = {item["code"] for item in body["checks"] if not item["passed"]}
    assert "official_endpoint" in failed
    assert "sdk_logging_disabled" in failed
    assert "component:provider_neutral_adapter" in failed


def test_source_adapter_version_drift_blocks_source_checkout(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    def source_version(path: Path, variable: str) -> str | None:
        if variable == "OPENAI_RESPONSES_ADAPTER_VERSION":
            return "0.2.0"
        return ENVIRONMENT._source_declared_version(path, variable)

    body = ENVIRONMENT.inspect_environment(
        root,
        environ={},
        python_version=(3, 12, 3),
        module_probe=lambda name: _source_origins(root).get(name),
        distribution_probe=_distribution_probe({"openai": "2.46.0"}),
        source_version_reader=source_version,
    )["openai_live_smoke_environment"]

    assert body["valid"] is False
    assert body["source_checkout_ready"] is False
    assert (
        "openai_responses_adapter_source_version_incompatible"
        in body["source_checkout_blockers"]
    )
    adapter = body["components"]["openai_responses_adapter"]
    assert adapter["source_declared_version"] == "0.2.0"
    assert adapter["formal_version_contract_satisfied"] is False


@pytest.mark.parametrize("core_version", ["invalid", "0.2.9", "0.5.0rc1"])
def test_core_source_version_must_satisfy_private_source_contract(
    tmp_path: Path,
    core_version: str,
) -> None:
    root = _repository(tmp_path)

    def source_version(path: Path, variable: str) -> str | None:
        if variable == "__version__":
            return core_version
        return ENVIRONMENT._source_declared_version(path, variable)

    body = ENVIRONMENT.inspect_environment(
        root,
        environ={},
        python_version=(3, 12, 3),
        module_probe=lambda name: _source_origins(root).get(name),
        distribution_probe=_distribution_probe({"openai": "2.46.0"}),
        source_version_reader=source_version,
    )["openai_live_smoke_environment"]

    assert body["valid"] is False
    assert body["source_checkout_ready"] is False
    assert "geotask_core_source_version_incompatible" in body[
        "source_checkout_blockers"
    ]
    core = body["components"]["geotask_core"]
    assert core["source_declared_version"] == core_version
    assert core["source_version_contract_satisfied"] is False


def test_python_below_repository_minimum_blocks_all_modes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    body = ENVIRONMENT.inspect_environment(
        root,
        environ={},
        python_version=(3, 9, 18),
        module_probe=lambda name: _source_origins(root).get(name),
        distribution_probe=_distribution_probe({"openai": "2.46.0"}),
    )["openai_live_smoke_environment"]

    assert body["valid"] is False
    assert body["python"]["supported"] is False
    assert body["source_checkout_ready"] is False
    assert body["formal_release_compatible"] is False
    assert "python_unsupported" in body["source_checkout_blockers"]
    assert "python_unsupported" in body["formal_release_blockers"]


def test_cli_inspect_environment_uses_no_ticket_and_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repository(tmp_path)
    payload = {
        "openai_live_smoke_environment": {
            "valid": True,
            "release_gate_state": "source_checkout_ready",
            "source_checkout_ready": True,
            "live_execution_ready": False,
        }
    }
    monkeypatch.setattr(AUDIT, "inspect_environment", lambda _root: payload)
    assert AUDIT.main(["inspect-environment", "--repository-root", str(root)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == payload

    payload["openai_live_smoke_environment"]["valid"] = False
    payload["openai_live_smoke_environment"]["release_gate_state"] = (
        "environment_blocked"
    )
    assert AUDIT.main(["inspect-environment", "--repository-root", str(root)]) == 2
    assert json.loads(capsys.readouterr().out) == payload


def test_environment_inspector_is_excluded_from_public_export() -> None:
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
    assert "examples/runtime/openai_responses_live_smoke_environment.py" not in exported
    assert "tests/test_openai_responses_live_smoke_environment.py" not in exported
