"""Deterministic Task -> ContextRequirement derivation for GeoTask GT-C1.

The Core owns only the derivation method. Domain/task-specific profiles remain
external inputs. The method does not resolve world truth, discover providers, or
infer sufficiency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Mapping, Sequence

from geotask_core.v1.task_context import ContextRequirement, JSONValue, TaskFrame, TaskContextContractError

REQUIREMENT_DERIVATION_CONTRACT_VERSION = "0.1"
REQUIREMENT_DERIVATION_RESULT_CONTRACT_ID = "geotask.requirement-derivation-result"


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TaskContextContractError(f"{name} must be a non-empty string")


def _freeze(value: object, name: str) -> JSONValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TaskContextContractError(f"{name} must not contain non-finite numbers")
        return value
    if isinstance(value, Mapping):
        out: dict[str, JSONValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TaskContextContractError(f"{name} keys must be strings")
            out[key] = _freeze(item, f"{name}.{key}")
        return MappingProxyType(out)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(item, f"{name}[]") for item in value)
    raise TaskContextContractError(f"{name} must be JSON-compatible")


def _freeze_map(value: Mapping[str, object], name: str) -> Mapping[str, JSONValue]:
    frozen = _freeze(value, name)
    assert isinstance(frozen, Mapping)
    return frozen


def _plain(value: JSONValue) -> object:
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class RequirementTemplate:
    template_id: str
    kind: str
    description: str
    critical: bool
    constraints: Mapping[str, JSONValue] = field(default_factory=dict)
    additional_scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.template_id, "template_id")
        _require_text(self.kind, "kind")
        _require_text(self.description, "description")
        if not isinstance(self.critical, bool):
            raise TaskContextContractError("critical must be boolean")
        object.__setattr__(self, "constraints", _freeze_map(self.constraints, "constraints"))
        refs = tuple(self.additional_scope_refs)
        if len(refs) != len(set(refs)) or any(not str(ref).strip() for ref in refs):
            raise TaskContextContractError("additional_scope_refs must be unique non-empty strings")
        object.__setattr__(self, "additional_scope_refs", refs)


@dataclass(frozen=True, slots=True)
class RequirementDerivationRule:
    rule_id: str
    task_types: tuple[str, ...]
    templates: tuple[RequirementTemplate, ...]
    metadata_equals: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.rule_id, "rule_id")
        task_types = tuple(self.task_types)
        if not task_types or len(task_types) != len(set(task_types)) or any(not str(x).strip() for x in task_types):
            raise TaskContextContractError("task_types must contain unique non-empty values")
        template_ids = [t.template_id for t in self.templates]
        if not template_ids or len(template_ids) != len(set(template_ids)):
            raise TaskContextContractError("templates must have unique template_id values")
        object.__setattr__(self, "task_types", task_types)
        object.__setattr__(self, "templates", tuple(self.templates))
        object.__setattr__(self, "metadata_equals", _freeze_map(self.metadata_equals, "metadata_equals"))


@dataclass(frozen=True, slots=True)
class RequirementDerivationResult:
    result_ref: str
    task_id: str
    matched_rule_ids: tuple[str, ...]
    requirements: tuple[ContextRequirement, ...]
    method: str = "deterministic-profile-rules"
    contract_version: str = REQUIREMENT_DERIVATION_CONTRACT_VERSION


def _matches(task: TaskFrame, rule: RequirementDerivationRule) -> bool:
    if task.task_type not in rule.task_types and "*" not in rule.task_types:
        return False
    return all(task.metadata.get(key) == value for key, value in rule.metadata_equals.items())


def _stable_requirement_id(task: TaskFrame, rule_id: str, template_id: str) -> str:
    payload = json.dumps({"task_id": task.task_id, "rule_id": rule_id, "template_id": template_id}, sort_keys=True, separators=(",", ":"))
    return "geotask://requirement/" + hashlib.sha256(payload.encode()).hexdigest()


def derive_context_requirements(task: TaskFrame, rules: Sequence[RequirementDerivationRule]) -> RequirementDerivationResult:
    """Derive requirements from externally supplied domain-neutral profiles.

    Rule order does not affect the output. No matching rule means an explicit empty
    derivation result, not an invented default requirement set.
    """
    rule_ids = [r.rule_id for r in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise TaskContextContractError("rules must have unique rule_id values")

    matched = [rule for rule in sorted(rules, key=lambda item: item.rule_id) if _matches(task, rule)]
    requirements: list[ContextRequirement] = []
    for rule in matched:
        for template in sorted(rule.templates, key=lambda item: item.template_id):
            scope_refs = tuple(dict.fromkeys((*task.scope_refs, *template.additional_scope_refs)))
            requirements.append(ContextRequirement(
                requirement_id=_stable_requirement_id(task, rule.rule_id, template.template_id),
                kind=template.kind,
                description=template.description,
                critical=template.critical,
                constraints=template.constraints,
                scope_refs=scope_refs,
            ))

    identity = {
        "task_id": task.task_id,
        "matched_rule_ids": [r.rule_id for r in matched],
        "requirement_ids": [r.requirement_id for r in requirements],
        "contract_version": REQUIREMENT_DERIVATION_CONTRACT_VERSION,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return RequirementDerivationResult(
        result_ref="geotask://requirement-derivation/" + hashlib.sha256(encoded.encode()).hexdigest(),
        task_id=task.task_id,
        matched_rule_ids=tuple(r.rule_id for r in matched),
        requirements=tuple(requirements),
    )


def requirement_derivation_result_payload(result: RequirementDerivationResult) -> dict[str, object]:
    return {
        "contract": REQUIREMENT_DERIVATION_RESULT_CONTRACT_ID,
        "contract_version": result.contract_version,
        "result_ref": result.result_ref,
        "task_id": result.task_id,
        "matched_rule_ids": list(result.matched_rule_ids),
        "method": result.method,
        "requirements": [
            {
                "requirement_id": item.requirement_id,
                "kind": item.kind,
                "description": item.description,
                "critical": item.critical,
                "constraints": _plain(item.constraints),
                "scope_refs": list(item.scope_refs),
            }
            for item in result.requirements
        ],
    }
