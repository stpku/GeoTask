"""Installed public Capability Registry and CLI discovery tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from geotask_core import capability_registry
from geotask_core.operator_registry import list_operator_metadata
from geotask_core.v1.artifact_registry import list_artifact_descriptors
from geotask_core.v1.schema_bundle import list_bundled_schema_ids

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _by_id(payload: dict) -> dict[str, dict]:
    capabilities = payload["capability_registry"]["capabilities"]
    return {item["id"]: item for item in capabilities}


def test_capability_registry_projects_live_public_sources_without_external_discovery() -> None:
    payload = capability_registry.capability_registry_payload()
    body = payload["capability_registry"]
    capabilities = _by_id(payload)

    assert body["registry_version"] == "0.1"
    assert body["scope"] == "installed_public_core"
    assert body["capability_count"] == 9
    assert set(capabilities) == {
        "geotask.operator-registry",
        "geotask.artifact-registry",
        "geotask.schema-bundle",
        "geotask.runtime-interface",
        "geotask.verification-provider-interface",
        "geotask.reference-agent",
        "geotask.core-benchmark",
        "geotask.verification-quality-benchmark",
        "geotask.self-diagnostic",
    }
    assert capabilities["geotask.operator-registry"]["item_count"] == len(
        list_operator_metadata()
    )
    assert capabilities["geotask.artifact-registry"]["item_count"] == len(
        list_artifact_descriptors()
    )
    assert capabilities["geotask.schema-bundle"]["item_count"] == len(
        list_bundled_schema_ids()
    )
    assert capabilities["geotask.operator-registry"]["deterministic_count"] == len(
        list_operator_metadata()
    )
    assert capabilities["geotask.runtime-interface"]["artifact_ids"] == [
        "geotask.runtime-descriptor",
        "geotask.runtime-request",
        "geotask.runtime-response",
    ]
    assert capabilities["geotask.verification-provider-interface"]["artifact_ids"] == [
        "geotask.verification-provider-descriptor",
        "geotask.verification-request",
        "geotask.verification-response",
        "geotask.assurance-profile",
    ]
    assert capabilities["geotask.reference-agent"]["scenarios"] == [
        "success",
        "missing_evidence",
        "conflicting_evidence",
        "stale_evidence",
        "contradicted",
    ]
    assert body["boundaries"] == {
        "registered_artifact": False,
        "new_schema_introduced": False,
        "new_operator_introduced": False,
        "external_plugins_discovered": False,
        "runtime_instances_discovered": False,
        "provider_instances_discovered": False,
        "domain_packs_discovered": False,
        "network_used": False,
        "external_truth_fetched": False,
        "real_world_validation_claimed": False,
        "authorization_granted": False,
        "action_executed": False,
    }


def test_capability_registry_can_filter_one_surface() -> None:
    payload = capability_registry.capability_registry_payload("geotask.runtime-interface")
    body = payload["capability_registry"]

    assert body["capability_count"] == 1
    assert body["capabilities"][0]["id"] == "geotask.runtime-interface"
    assert body["capabilities"][0]["kind"] == "extension_contract"


def test_capability_registry_unknown_id_is_explicit() -> None:
    with pytest.raises(capability_registry.CapabilityRegistryError) as caught:
        capability_registry.capability_registry_payload("geotask.not-real")

    assert "unknown Core capability" in str(caught.value)
    assert "geotask.not-real" in str(caught.value)


def test_capability_registry_fails_closed_when_required_contract_artifact_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts = tuple(
        item
        for item in list_artifact_descriptors()
        if item.artifact_id != "geotask.runtime-response"
    )
    monkeypatch.setattr(capability_registry, "list_artifact_descriptors", lambda: artifacts)

    with pytest.raises(capability_registry.CapabilityRegistryError) as caught:
        capability_registry.capability_registry_payload()

    assert "geotask.runtime-interface" in str(caught.value)
    assert "geotask.runtime-response" in str(caught.value)


def test_cli_inspect_capabilities_json_filter_help_and_errors() -> None:
    listing = _run_cli("inspect", "capabilities", "--format", "json")
    assert listing.returncode == 0, listing.stderr or listing.stdout
    body = json.loads(listing.stdout)["capability_registry"]
    assert body["capability_count"] == 9
    assert body["boundaries"]["external_plugins_discovered"] is False

    filtered = _run_cli(
        "inspect",
        "capabilities",
        "geotask.verification-provider-interface",
        "--format",
        "json",
    )
    assert filtered.returncode == 0, filtered.stderr or filtered.stdout
    filtered_body = json.loads(filtered.stdout)["capability_registry"]
    assert filtered_body["capability_count"] == 1
    assert filtered_body["capabilities"][0]["id"] == (
        "geotask.verification-provider-interface"
    )

    help_result = _run_cli("inspect", "capabilities", "--help")
    assert help_result.returncode == 0
    assert "Usage: geotask inspect capabilities" in help_result.stdout

    bad_id = _run_cli("inspect", "capabilities", "geotask.not-real")
    assert bad_id.returncode != 0
    assert "inspect_capabilities_failed" in bad_id.stderr
    assert "Traceback" not in bad_id.stderr

    bad_format = _run_cli("inspect", "capabilities", "--format", "xml")
    assert bad_format.returncode != 0
    assert "unsupported_inspect_capabilities_format" in bad_format.stderr
    assert "Traceback" not in bad_format.stderr
