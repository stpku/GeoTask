"""Public installed-capability discovery for GeoTask Core.

The Capability Registry is a product/developer discovery projection over existing
Core sources of truth. It does not create a new Artifact, Schema, Operator,
Provider, Runtime implementation, GT capability, or external plugin contract.
It intentionally discovers only the public capabilities shipped by the installed
``geotask-core`` package and never probes network, production, or third-party
systems.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from geotask_core._version import __version__
from geotask_core.operator_registry import list_operator_metadata
from geotask_core.reference_agent_activation import REFERENCE_AGENT_SCENARIOS
from geotask_core.v1.artifact_registry import list_artifact_descriptors
from geotask_core.v1.schema_bundle import list_bundled_schema_ids

CAPABILITY_REGISTRY_VERSION = "0.1"

_RUNTIME_ARTIFACT_IDS = (
    "geotask.runtime-descriptor",
    "geotask.runtime-request",
    "geotask.runtime-response",
)
_VERIFICATION_PROVIDER_ARTIFACT_IDS = (
    "geotask.verification-provider-descriptor",
    "geotask.verification-request",
    "geotask.verification-response",
    "geotask.assurance-profile",
)


class CapabilityRegistryError(ValueError):
    """Raised when the installed public capability registry is inconsistent."""


def _artifact_contract_capability(
    *,
    capability_id: str,
    title: str,
    artifact_ids: tuple[str, ...],
    artifact_by_id: Mapping[str, object],
    inspect_command: str,
    description: str,
) -> dict[str, Any]:
    missing = [artifact_id for artifact_id in artifact_ids if artifact_id not in artifact_by_id]
    if missing:
        raise CapabilityRegistryError(
            f"{capability_id} requires registered artifacts that are missing: "
            + ", ".join(missing)
        )
    return {
        "id": capability_id,
        "title": title,
        "kind": "extension_contract",
        "status": "available",
        "source_of_truth": "artifact_registry",
        "item_count": len(artifact_ids),
        "artifact_ids": list(artifact_ids),
        "inspect_command": inspect_command,
        "description": description,
    }


def _capabilities() -> list[dict[str, Any]]:
    operators = list_operator_metadata()
    artifacts = list_artifact_descriptors()
    schema_ids = list(list_bundled_schema_ids())
    artifact_by_id = {item.artifact_id: item for item in artifacts}

    operator_names = [item.get("name") for item in operators]
    if not operators or not all(isinstance(name, str) and name for name in operator_names):
        raise CapabilityRegistryError("Operator Registry returned invalid public metadata")
    if len(set(operator_names)) != len(operator_names):
        raise CapabilityRegistryError("Operator Registry contains duplicate public operator IDs")
    if not artifacts or len(artifact_by_id) != len(artifacts):
        raise CapabilityRegistryError("Artifact Registry contains duplicate or missing artifact IDs")
    if not schema_ids or len(set(schema_ids)) != len(schema_ids):
        raise CapabilityRegistryError("Schema Bundle contains duplicate or missing schema IDs")

    families = sorted(
        {
            str(item.get("family"))
            for item in operators
            if isinstance(item.get("family"), str) and item.get("family")
        }
    )

    capabilities: list[dict[str, Any]] = [
        {
            "id": "geotask.operator-registry",
            "title": "Deterministic Operator Registry",
            "kind": "registry",
            "status": "available",
            "source_of_truth": "operator_contract_registry",
            "item_count": len(operators),
            "operator_families": families,
            "deterministic_count": sum(
                1 for item in operators if item.get("deterministic") is True
            ),
            "inspect_command": "geotask inspect operators --format json",
            "description": (
                "Public-safe metadata projected from the installed Core OperatorContract "
                "registry."
            ),
        },
        {
            "id": "geotask.artifact-registry",
            "title": "Artifact Registry",
            "kind": "registry",
            "status": "available",
            "source_of_truth": "artifact_registry",
            "item_count": len(artifacts),
            "inspect_command": "geotask inspect schemas --format json",
            "description": (
                "Versioned public Artifact descriptors, their schemas, validation commands, "
                "and execution boundaries."
            ),
        },
        {
            "id": "geotask.schema-bundle",
            "title": "Bundled Schema Set",
            "kind": "schema_bundle",
            "status": "available",
            "source_of_truth": "schema_bundle",
            "item_count": len(schema_ids),
            "inspect_command": "geotask inspect schemas --verify --format json",
            "description": "Installed public JSON Schema bundle with local verification support.",
        },
        _artifact_contract_capability(
            capability_id="geotask.runtime-interface",
            title="Runtime Interface",
            artifact_ids=_RUNTIME_ARTIFACT_IDS,
            artifact_by_id=artifact_by_id,
            inspect_command="geotask runtime inspect --profile --format json",
            description=(
                "Versioned Runtime descriptor/request/response contract. Discovery here does "
                "not discover or attest any external Runtime instance."
            ),
        ),
        _artifact_contract_capability(
            capability_id="geotask.verification-provider-interface",
            title="Verification Provider Interface",
            artifact_ids=_VERIFICATION_PROVIDER_ARTIFACT_IDS,
            artifact_by_id=artifact_by_id,
            inspect_command="geotask provider inspect --profile --format json",
            description=(
                "Versioned Verification Provider descriptor/request/response and assurance "
                "profile contracts. Discovery here does not discover or attest any external "
                "Provider instance."
            ),
        ),
        {
            "id": "geotask.reference-agent",
            "title": "Reference Agent",
            "kind": "reference_implementation",
            "status": "available",
            "source_of_truth": "packaged_reference_agent_bundle",
            "item_count": len(REFERENCE_AGENT_SCENARIOS),
            "scenarios": list(REFERENCE_AGENT_SCENARIOS),
            "inspect_command": "geotask agent demo --help",
            "description": (
                "Packaged deterministic teaching workflow for the public five-scenario "
                "facility-assessment example."
            ),
        },
        {
            "id": "geotask.core-benchmark",
            "title": "Core Conformance Benchmark",
            "kind": "benchmark",
            "status": "available",
            "source_of_truth": "core_benchmark",
            "item_count": 1,
            "inspect_command": "geotask benchmark core --help",
            "description": (
                "Deterministic Core conformance and optional local performance benchmark."
            ),
        },
        {
            "id": "geotask.verification-quality-benchmark",
            "title": "Verification Quality Benchmark",
            "kind": "benchmark",
            "status": "available",
            "source_of_truth": "verification_quality_benchmark",
            "item_count": 2,
            "suites": ["fixed", "perturbation"],
            "inspect_command": "geotask benchmark quality --help",
            "description": (
                "Fixed fictional and deterministic synthetic-perturbation verification "
                "quality suites."
            ),
        },
        {
            "id": "geotask.self-diagnostic",
            "title": "Installed Core Self-Diagnostic",
            "kind": "diagnostic",
            "status": "available",
            "source_of_truth": "geotask_core.doctor",
            "item_count": 1,
            "inspect_command": "geotask inspect health --format json --compact",
            "description": (
                "Offline read-only installed-package health aggregation. A pass is not a "
                "real-world correctness or authorization claim."
            ),
        },
    ]
    return capabilities


def capability_registry_payload(capability_id: str | None = None) -> dict[str, Any]:
    """Return deterministic installed public Core capability discovery metadata."""

    capabilities = _capabilities()
    if capability_id is not None:
        selected = [item for item in capabilities if item["id"] == capability_id]
        if not selected:
            supported = ", ".join(item["id"] for item in capabilities)
            raise CapabilityRegistryError(
                f"unknown Core capability {capability_id!r}. Supported capabilities: {supported}"
            )
        capabilities = selected

    return {
        "capability_registry": {
            "registry_version": CAPABILITY_REGISTRY_VERSION,
            "geotask_core_version": __version__,
            "scope": "installed_public_core",
            "capability_count": len(capabilities),
            "capabilities": capabilities,
            "boundaries": {
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
            },
        }
    }


__all__ = [
    "CAPABILITY_REGISTRY_VERSION",
    "CapabilityRegistryError",
    "capability_registry_payload",
]
