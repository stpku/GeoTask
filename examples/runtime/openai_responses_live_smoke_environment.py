"""Read-only environment inspection for the private OpenAI live smoke.

The inspector distinguishes repository source loading, editable installs, and
formal non-editable package installs. It reads module discovery data, package
metadata, repository version declarations, and presence-only environment gates.
It never imports provider modules, reads credential values into output, validates
an authorization ticket, creates files, or sends a network request. This file
remains outside the public export and normal CI.
"""

from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

try:  # Package import when loaded through examples.runtime.
    from .openai_responses_live_smoke import (
        ACK_ENVIRONMENT_VARIABLE,
        _acknowledgement,
        _credential_environment_variable,
    )
except ImportError:  # Direct script execution from examples/runtime.
    from openai_responses_live_smoke import (  # type: ignore[no-redef]
        ACK_ENVIRONMENT_VARIABLE,
        _acknowledgement,
        _credential_environment_variable,
    )


_VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:(?P<pre>a|b|rc)(?P<pre_number>0|[1-9]\d*))?"
    r"(?:\.post(?P<post>0|[1-9]\d*))?"
    r"(?:\.dev(?P<dev>0|[1-9]\d*))?"
    r"(?:\+[A-Za-z0-9.-]+)?$"
)


@dataclass(frozen=True)
class ComponentSpec:
    key: str
    module: str
    distribution: str
    minimum: str
    maximum_exclusive: str
    source_root: str | None = None
    source_version_file: str | None = None
    source_version_name: str | None = None


@dataclass(frozen=True)
class DistributionRecord:
    present: bool
    version: str | None
    editable: bool
    location: Path | None = None


_COMPONENTS = (
    ComponentSpec(
        key="openai_sdk",
        module="openai",
        distribution="openai",
        minimum="2.46.0",
        maximum_exclusive="3.0.0",
    ),
    ComponentSpec(
        key="geotask_core",
        module="geotask_core",
        distribution="geotask-core",
        minimum="0.4.0",
        maximum_exclusive="0.5.0",
        source_root="src/geotask_core",
        source_version_file="src/geotask_core/_version.py",
        source_version_name="__version__",
    ),
    ComponentSpec(
        key="provider_neutral_adapter",
        module="geotask_model_adapter_reference",
        distribution="geotask-provider-neutral-model-adapter",
        minimum="0.1.0",
        maximum_exclusive="0.2.0",
        source_root=(
            "examples/model_adapters/provider_neutral/src/"
            "geotask_model_adapter_reference"
        ),
        source_version_file=(
            "examples/model_adapters/provider_neutral/src/"
            "geotask_model_adapter_reference/contracts.py"
        ),
        source_version_name="MODEL_ADAPTER_PACKAGE_VERSION",
    ),
    ComponentSpec(
        key="openai_responses_adapter",
        module="geotask_openai_responses_adapter",
        distribution="geotask-openai-responses-adapter",
        minimum="0.1.0",
        maximum_exclusive="0.2.0",
        source_root=(
            "examples/model_adapters/openai_responses/src/"
            "geotask_openai_responses_adapter"
        ),
        source_version_file=(
            "examples/model_adapters/openai_responses/src/"
            "geotask_openai_responses_adapter/config.py"
        ),
        source_version_name="OPENAI_RESPONSES_ADAPTER_VERSION",
    ),
)


def _check(code: str, passed: bool, detail: str) -> dict[str, object]:
    return {"code": code, "passed": passed, "detail": detail}


def _append_once(values: list[str], code: str) -> None:
    if code not in values:
        values.append(code)


def _parse_version(value: str) -> tuple[int, int, int, int, int, int, int] | None:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    pre = match.group("pre")
    dev = match.group("dev")
    post = match.group("post")
    if dev is not None:
        stage = -4
        stage_number = int(dev)
    elif pre == "a":
        stage = -3
        stage_number = int(match.group("pre_number"))
    elif pre == "b":
        stage = -2
        stage_number = int(match.group("pre_number"))
    elif pre == "rc":
        stage = -1
        stage_number = int(match.group("pre_number"))
    elif post is not None:
        stage = 1
        stage_number = int(post)
    else:
        stage = 0
        stage_number = 0
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        stage,
        stage_number,
        0,
        0,
    )


def _version_in_range(value: str | None, minimum: str, maximum_exclusive: str) -> bool:
    if value is None:
        return False
    parsed = _parse_version(value)
    lower = _parse_version(minimum)
    upper = _parse_version(maximum_exclusive)
    if parsed is None or lower is None or upper is None:
        return False
    if parsed[3] < 0:
        return False
    if parsed[:3] >= upper[:3]:
        return False
    return lower <= parsed


def _safe_module_origin(name: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, AttributeError, ValueError):
        return None
    if spec is None or spec.origin in {None, "built-in", "frozen"}:
        return None
    try:
        return Path(spec.origin).resolve()
    except OSError:
        return None


def _safe_distribution_record(name: str) -> DistributionRecord:
    try:
        distribution = importlib.metadata.distribution(name)
        version = distribution.version
        location = Path(distribution.locate_file("")).resolve()
    except (importlib.metadata.PackageNotFoundError, OSError, ValueError):
        return DistributionRecord(False, None, False)
    editable = False
    try:
        direct_url = distribution.read_text("direct_url.json")
        if direct_url:
            payload = json.loads(direct_url)
            editable = bool(
                isinstance(payload, dict)
                and isinstance(payload.get("dir_info"), dict)
                and payload["dir_info"].get("editable") is True
            )
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        editable = False
    return DistributionRecord(True, version, editable, location)


def _source_declared_version(path: Path, variable_name: str) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        if any(isinstance(target, ast.Name) and target.id == variable_name for target in targets):
            return value.value
    return None


def _inside(path: Path | None, root: Path) -> bool:
    if path is None:
        return False
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _python_supported(version: Sequence[int]) -> bool:
    return tuple(version[:2]) >= (3, 10)


def inspect_environment(
    repository_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    python_version: Sequence[int] | None = None,
    module_probe: Callable[[str], Path | None] | None = None,
    distribution_probe: Callable[[str], DistributionRecord] | None = None,
    source_version_reader: Callable[[Path, str], str | None] | None = None,
) -> dict[str, object]:
    """Inspect source and installed compatibility without importing providers."""

    root = repository_root.resolve()
    environment = os.environ if environ is None else environ
    interpreter = sys.version_info if python_version is None else python_version
    find_origin = _safe_module_origin if module_probe is None else module_probe
    find_distribution = (
        _safe_distribution_record if distribution_probe is None else distribution_probe
    )
    read_source_version = (
        _source_declared_version
        if source_version_reader is None
        else source_version_reader
    )

    checks: list[dict[str, object]] = []
    source_checkout_blockers: list[str] = []
    formal_release_blockers: list[str] = []
    supported_python = _python_supported(interpreter)
    checks.append(
        _check(
            "python_supported",
            supported_python,
            "Python version satisfies the repository minimum"
            if supported_python
            else "Python 3.10 or newer is required",
        )
    )

    alternate_endpoint_present = bool(environment.get("OPENAI_BASE_URL", "").strip())
    sdk_logging_present = bool(environment.get("OPENAI_LOG", "").strip())
    endpoint_safe = not alternate_endpoint_present
    logging_safe = not sdk_logging_present
    checks.append(
        _check(
            "official_endpoint",
            endpoint_safe,
            "alternate endpoint is not configured"
            if endpoint_safe
            else "alternate endpoint configuration is forbidden",
        )
    )
    checks.append(
        _check(
            "sdk_logging_disabled",
            logging_safe,
            "SDK logging override is absent"
            if logging_safe
            else "SDK logging override must be removed",
        )
    )
    if not supported_python:
        _append_once(source_checkout_blockers, "python_unsupported")
        _append_once(formal_release_blockers, "python_unsupported")
    if not endpoint_safe:
        _append_once(source_checkout_blockers, "alternate_endpoint_configured")
        _append_once(formal_release_blockers, "alternate_endpoint_configured")
    if not logging_safe:
        _append_once(source_checkout_blockers, "sdk_logging_enabled")
        _append_once(formal_release_blockers, "sdk_logging_enabled")

    components: dict[str, dict[str, object]] = {}
    source_component_ready: list[bool] = []
    installed_component_present: list[bool] = []
    formal_component_compatible: list[bool] = []

    for spec in _COMPONENTS:
        origin = find_origin(spec.module)
        distribution = find_distribution(spec.distribution)
        source_root = root / spec.source_root if spec.source_root else None
        source_origin = source_root is not None and _inside(origin, source_root)
        distribution_owns_origin = (
            distribution.location is not None
            and _inside(origin, distribution.location)
        )
        source_version = None
        source_tree_present = False
        if spec.source_version_file and spec.source_version_name:
            version_path = root / spec.source_version_file
            source_tree_present = version_path.is_file()
            source_version = read_source_version(version_path, spec.source_version_name)

        if origin is None:
            loading_mode = "unavailable"
        elif distribution.present and distribution.editable:
            loading_mode = "editable_install"
        elif source_origin:
            loading_mode = "source_checkout"
        elif distribution.present and distribution_owns_origin:
            loading_mode = "installed_package"
        elif distribution.present:
            loading_mode = "distribution_shadowed"
        else:
            loading_mode = "external_unmanaged"

        effective_version = (
            source_version
            if source_origin and source_version is not None
            else distribution.version
        )
        contract_satisfied = _version_in_range(
            effective_version,
            spec.minimum,
            spec.maximum_exclusive,
        )
        if spec.key == "openai_sdk":
            source_version_contract_satisfied = contract_satisfied
        elif spec.key == "geotask_core":
            source_version_contract_satisfied = _version_in_range(
                source_version,
                "0.3.0",
                "0.5.0",
            )
        else:
            source_version_contract_satisfied = _version_in_range(
                source_version,
                spec.minimum,
                spec.maximum_exclusive,
            )
        module_available = origin is not None
        installed_noneditable = (
            module_available
            and distribution.present
            and distribution_owns_origin
            and not distribution.editable
            and loading_mode == "installed_package"
        )

        if spec.key == "openai_sdk":
            source_ready = module_available and contract_satisfied
        else:
            source_ready = (
                module_available
                and source_origin
                and source_tree_present
                and source_version is not None
                and loading_mode in {"source_checkout", "editable_install"}
                and source_version_contract_satisfied
            )
        if not module_available:
            _append_once(source_checkout_blockers, f"{spec.key}_module_unavailable")
            _append_once(formal_release_blockers, f"{spec.key}_module_unavailable")
        if spec.key == "openai_sdk":
            if not contract_satisfied:
                _append_once(source_checkout_blockers, "openai_sdk_version_incompatible")
        else:
            if not source_origin:
                _append_once(
                    source_checkout_blockers,
                    f"{spec.key}_not_loaded_from_repository_source",
                )
            if not source_tree_present:
                _append_once(source_checkout_blockers, f"{spec.key}_source_tree_missing")
            if source_version is None:
                _append_once(
                    source_checkout_blockers,
                    f"{spec.key}_source_version_unreadable",
                )
            if not source_version_contract_satisfied:
                _append_once(
                    source_checkout_blockers,
                    f"{spec.key}_source_version_incompatible",
                )
        if distribution.present and module_available and not distribution_owns_origin:
            _append_once(
                formal_release_blockers,
                f"{spec.key}_distribution_does_not_own_module",
            )
        if not installed_noneditable:
            _append_once(
                formal_release_blockers,
                f"{spec.key}_not_noneditable_install",
            )
        if not contract_satisfied:
            _append_once(
                formal_release_blockers,
                f"{spec.key}_version_incompatible",
            )

        source_component_ready.append(source_ready)
        installed_component_present.append(installed_noneditable)
        formal_component_compatible.append(installed_noneditable and contract_satisfied)

        components[spec.key] = {
            "module": spec.module,
            "distribution": spec.distribution,
            "module_available": module_available,
            "origin_scope": (
                "repository_source"
                if source_origin
                else "external_environment"
                if module_available
                else "unavailable"
            ),
            "loading_mode": loading_mode,
            "distribution_present": distribution.present,
            "distribution_version": distribution.version,
            "distribution_editable": distribution.editable,
            "distribution_owns_module": distribution_owns_origin,
            "source_tree_present": source_tree_present,
            "source_declared_version": source_version,
            "source_required_range": (
                ">=0.3.0,<0.5.0"
                if spec.key == "geotask_core"
                else f">={spec.minimum},<{spec.maximum_exclusive}"
            ),
            "source_version_contract_satisfied": source_version_contract_satisfied,
            "effective_version": effective_version,
            "required_range": f">={spec.minimum},<{spec.maximum_exclusive}",
            "formal_version_contract_satisfied": contract_satisfied,
        }
        checks.append(
            _check(
                f"component:{spec.key}",
                module_available,
                f"{spec.module} is discoverable without import"
                if module_available
                else f"{spec.module} is unavailable",
            )
        )

    safe_configuration = supported_python and endpoint_safe and logging_safe
    source_checkout_ready = safe_configuration and all(source_component_ready)
    installed_package_ready = safe_configuration and all(installed_component_present)
    formal_release_compatible = safe_configuration and all(formal_component_compatible)

    credential_name = _credential_environment_variable()
    credential_value = environment.get(credential_name)
    credential_present = isinstance(credential_value, str) and bool(credential_value.strip())
    acknowledgement_present = (
        environment.get(ACK_ENVIRONMENT_VARIABLE) == _acknowledgement()
    )
    live_execution_environment_ready = (
        (source_checkout_ready or formal_release_compatible)
        and credential_present
        and acknowledgement_present
    )
    live_execution_blockers: list[str] = []
    if not (source_checkout_ready or formal_release_compatible):
        _append_once(live_execution_blockers, "environment_not_ready")
    if not credential_present:
        _append_once(live_execution_blockers, "server_credential_absent")
    if not acknowledgement_present:
        _append_once(live_execution_blockers, "explicit_acknowledgement_absent")
    _append_once(live_execution_blockers, "authorization_ticket_not_checked")

    if formal_release_compatible:
        gate_state = "formal_release_compatible"
    elif source_checkout_ready:
        gate_state = "source_checkout_ready"
    elif installed_package_ready:
        gate_state = "installed_package_version_blocked"
    else:
        gate_state = "environment_blocked"

    environment_valid = source_checkout_ready or formal_release_compatible
    return {
        "openai_live_smoke_environment": {
            "valid": environment_valid,
            "release_gate_state": gate_state,
            "python": {
                "major": int(interpreter[0]),
                "minor": int(interpreter[1]),
                "micro": int(interpreter[2]) if len(interpreter) > 2 else 0,
                "supported": supported_python,
            },
            "source_checkout_ready": source_checkout_ready,
            "source_checkout_blockers": source_checkout_blockers,
            "installed_package_ready": installed_package_ready,
            "formal_release_compatible": formal_release_compatible,
            "formal_release_blockers": formal_release_blockers,
            "live_execution_environment_ready": live_execution_environment_ready,
            "live_execution_blockers": live_execution_blockers,
            "live_execution_ready": False,
            "authorization_ticket_checked": False,
            "authorization_claim_created": False,
            "credential_presence_checked": True,
            "credential_present": credential_present,
            "credential_value_exposed": False,
            "acknowledgement_presence_checked": True,
            "acknowledgement_present": acknowledgement_present,
            "provider_modules_imported": False,
            "network_called": False,
            "components": components,
            "checks": checks,
        }
    }


__all__ = [
    "ComponentSpec",
    "DistributionRecord",
    "inspect_environment",
]
