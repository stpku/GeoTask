"""Build the fixed GT32 progressive takeoff-authorization bundle.

All records are fictional. Five caller-supplied authorization evidence packets
arrive one by one. The existing GT28 control profile is reevaluated after each
arrival, while the GT31 scoped weather conclusion remains a separate input.
The final control result may mark takeoff-related outputs eligible, but GeoTask
Core never publishes them, sends a command, authorizes reality, or executes a
flight action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import (
    ControlEvaluationResult,
    evaluate_control_profile,
    load_control_evaluation,
)
from geotask_core.v1.result import GeotaskResult


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"

TASK = CORE / "gt28_uav_takeoff_authorization_gate.yaml"
EXECUTION = CORE / "takeoff_preflight_execution_result_gt28.json"
INITIAL_CONTROL = CORE / "takeoff_authorization_control_evaluation_gt28.json"
GT31_EVALUATION = CORE / "assurance_evaluation_human_weather_adjudication_gt31.json"
GT31_SCENARIO = CORE / "gt31_human_weather_adjudication.json"
FINAL_CONTROL = CORE / "takeoff_authorization_control_evaluation_gt32.json"
SCENARIO = CORE / "gt32_progressive_takeoff_authorization.json"


class GT32BuildError(ValueError):
    """Raised when the fixed GT32 bundle violates its declared scope."""


@dataclass(frozen=True)
class AuthorizationSpec:
    field: str
    evidence_id: str
    source_label: str
    issued_at: str
    path: Path


AUTHORIZATION_SPECS = (
    AuthorizationSpec(
        field="airspace_authorized",
        evidence_id="fictional-airspace-authorization-gt32",
        source_label="Fictional Airspace Authorization Record",
        issued_at="2026-08-04T14:09:00+08:00",
        path=CORE / "authorization_evidence_airspace_gt32.json",
    ),
    AuthorizationSpec(
        field="operator_authorized",
        evidence_id="fictional-operator-authorization-gt32",
        source_label="Fictional Operator Authorization Record",
        issued_at="2026-08-04T14:09:20+08:00",
        path=CORE / "authorization_evidence_operator_gt32.json",
    ),
    AuthorizationSpec(
        field="departure_site_authorized",
        evidence_id="fictional-departure-site-authorization-gt32",
        source_label="Fictional Departure-Site Authorization Record",
        issued_at="2026-08-04T14:09:40+08:00",
        path=CORE / "authorization_evidence_departure_site_gt32.json",
    ),
    AuthorizationSpec(
        field="weather_release_authorized",
        evidence_id="fictional-weather-release-authorization-gt32",
        source_label="Fictional Weather Release Authorization Record",
        issued_at="2026-08-04T14:10:00+08:00",
        path=CORE / "authorization_evidence_weather_release_gt32.json",
    ),
    AuthorizationSpec(
        field="mission_authorized",
        evidence_id="fictional-mission-authorization-gt32",
        source_label="Fictional Mission Authorization Record",
        issued_at="2026-08-04T14:10:20+08:00",
        path=CORE / "authorization_evidence_mission_gt32.json",
    ),
)

_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_version",
    "evidence_id",
    "authorization_field",
    "authorization_value",
    "subject",
    "scope",
    "issued_at",
    "valid_from",
    "valid_until",
    "source_type",
    "source_label",
    "caller_asserted",
    "fictional_record",
    "external_truth_verified_by_core",
    "real_authority_contacted",
    "production_output_released",
    "command_sent",
    "action_authorized_by_core",
    "action_executed",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pretty_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write(path: Path, payload: Mapping[str, object]) -> bytes:
    raw = _pretty_bytes(payload)
    path.write_bytes(raw)
    return raw


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _parse_time(value: object, path: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise GT32BuildError(f"{path} must be a non-empty ISO date-time string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise GT32BuildError(f"{path} must be a valid ISO date-time") from exc
    if parsed.tzinfo is None:
        raise GT32BuildError(f"{path} must include a timezone")
    return parsed


def _evidence_payload(spec: AuthorizationSpec) -> dict:
    return {
        "authorization_evidence": {
            "evidence_version": "0.1",
            "evidence_id": spec.evidence_id,
            "authorization_field": spec.field,
            "authorization_value": True,
            "subject": "fictional-uav-alpha-mission-gt32",
            "scope": "fictional-east-departure-operation",
            "issued_at": spec.issued_at,
            "valid_from": "2026-08-04T14:08:00+08:00",
            "valid_until": "2026-08-04T14:35:00+08:00",
            "source_type": "fictional_authorization_record",
            "source_label": spec.source_label,
            "caller_asserted": True,
            "fictional_record": True,
            "external_truth_verified_by_core": False,
            "real_authority_contacted": False,
            "production_output_released": False,
            "command_sent": False,
            "action_authorized_by_core": False,
            "action_executed": False,
        }
    }


def validate_authorization_evidence(
    payload: Mapping[str, object],
    *,
    expected_field: str | None = None,
    expected_evidence_id: str | None = None,
) -> dict[str, object]:
    body = payload.get("authorization_evidence")
    if not isinstance(body, Mapping):
        raise GT32BuildError("authorization_evidence must be an object")
    missing = sorted(_REQUIRED_EVIDENCE_FIELDS - set(body))
    unknown = sorted(set(body) - _REQUIRED_EVIDENCE_FIELDS)
    if missing:
        raise GT32BuildError(
            "authorization_evidence missing required field(s): " + ", ".join(missing)
        )
    if unknown:
        raise GT32BuildError(
            "authorization_evidence contains unknown field(s): " + ", ".join(unknown)
        )
    if body["evidence_version"] != "0.1":
        raise GT32BuildError("authorization_evidence.evidence_version must be 0.1")
    field = body["authorization_field"]
    if not isinstance(field, str) or not field:
        raise GT32BuildError("authorization_evidence.authorization_field must be non-empty")
    if expected_field is not None and field != expected_field:
        raise GT32BuildError(
            f"authorization field {field!r} does not match expected {expected_field!r}"
        )
    evidence_id = body["evidence_id"]
    if not isinstance(evidence_id, str) or not evidence_id:
        raise GT32BuildError("authorization_evidence.evidence_id must be non-empty")
    if expected_evidence_id is not None and evidence_id != expected_evidence_id:
        raise GT32BuildError(
            f"evidence id {evidence_id!r} does not match expected {expected_evidence_id!r}"
        )
    if not isinstance(body["authorization_value"], bool):
        raise GT32BuildError("authorization_evidence.authorization_value must be boolean")
    if body["subject"] != "fictional-uav-alpha-mission-gt32":
        raise GT32BuildError("authorization_evidence.subject is outside GT32 scope")
    if body["scope"] != "fictional-east-departure-operation":
        raise GT32BuildError("authorization_evidence.scope is outside GT32 scope")
    issued_at = _parse_time(body["issued_at"], "authorization_evidence.issued_at")
    valid_from = _parse_time(body["valid_from"], "authorization_evidence.valid_from")
    valid_until = _parse_time(body["valid_until"], "authorization_evidence.valid_until")
    if valid_from > issued_at or issued_at >= valid_until:
        raise GT32BuildError("authorization evidence validity must contain issued_at")
    if body["source_type"] != "fictional_authorization_record":
        raise GT32BuildError("authorization evidence must remain fictional")
    if not isinstance(body["source_label"], str) or not body["source_label"]:
        raise GT32BuildError("authorization_evidence.source_label must be non-empty")
    for field_name in ("caller_asserted", "fictional_record"):
        if body[field_name] is not True:
            raise GT32BuildError(f"authorization_evidence.{field_name} must be true")
    for field_name in (
        "external_truth_verified_by_core",
        "real_authority_contacted",
        "production_output_released",
        "command_sent",
        "action_authorized_by_core",
        "action_executed",
    ):
        if body[field_name] is not False:
            raise GT32BuildError(f"authorization_evidence.{field_name} must be false")
    return dict(body)


def _load_document_and_execution() -> tuple[object, GeotaskResult]:
    raw_document = load_geotask(TASK)
    errors = [
        item
        for item in validate_document(raw_document)
        if item.get("severity", "error") == "error"
    ]
    if errors:
        raise GT32BuildError(f"GT28 task validation failed: {errors}")
    document = canonicalize(raw_document)
    execution = GeotaskResult.from_dict(_json(EXECUTION))
    if execution.task_id != document.metadata.id:
        raise GT32BuildError("GT28 task and execution result do not bind")
    return document, execution


def _validate_upstream_weather() -> tuple[int, int]:
    evaluation = _json(GT31_EVALUATION)["assurance_evaluation"]
    scenario = _json(GT31_SCENARIO)["scenario"]
    if evaluation["state"] != "verified":
        raise GT32BuildError("GT31 weather Assurance must be verified")
    if evaluation["eligible_outputs"] != ["weather_condition_verified"]:
        raise GT32BuildError("GT31 weather output must be eligible")
    for field in ("production_output_released", "action_authorized", "action_executed"):
        if evaluation[field] is not False:
            raise GT32BuildError(f"GT31 Assurance must keep {field}=false")
    facts = scenario["facts"]
    wind = facts["human_selected_wind_speed_mps"]
    limit = facts["mission_wind_limit_mps"]
    if not isinstance(wind, int) or not isinstance(limit, int) or wind > limit:
        raise GT32BuildError("GT31 weather result must remain within the mission limit")
    return wind, limit


def evaluate_authorization_sequence(
    evidence_payloads: Sequence[Mapping[str, object]],
) -> tuple[ControlEvaluationResult, ...]:
    document, execution = _load_document_and_execution()
    wind, limit = _validate_upstream_weather()
    domain_state: dict[str, object] = {
        "wind_speed_mps": wind,
        "max_wind_mps": limit,
    }
    seen: set[str] = set()
    evaluations: list[ControlEvaluationResult] = []
    allowed_fields = {spec.field for spec in AUTHORIZATION_SPECS}
    for payload in evidence_payloads:
        body = validate_authorization_evidence(payload)
        field = str(body["authorization_field"])
        if field not in allowed_fields:
            raise GT32BuildError(f"unexpected authorization field: {field}")
        if field in seen:
            raise GT32BuildError(f"duplicate authorization field: {field}")
        seen.add(field)
        domain_state[field] = body["authorization_value"]
        control = load_control_evaluation(
            evaluate_control_profile(document, execution, domain_state).to_dict()
        )
        if control.action_executed is not False:
            raise GT32BuildError("public control evaluation must not execute action")
        evaluations.append(control)
    return tuple(evaluations)


def build() -> dict[str, object]:
    initial_control = load_control_evaluation(_json(INITIAL_CONTROL))
    if initial_control.state != "unknown" or len(initial_control.unknown_identifiers) != 5:
        raise GT32BuildError("GT28 must begin with five unknown authorizations")
    if initial_control.blocked_outputs != (
        "automatic_takeoff_authorization",
        "takeoff_command",
    ):
        raise GT32BuildError("GT28 must begin with both takeoff outputs blocked")

    evidence_payloads: list[dict] = []
    evidence_bytes: dict[str, bytes] = {}
    for spec in AUTHORIZATION_SPECS:
        payload = _evidence_payload(spec)
        body = validate_authorization_evidence(
            payload,
            expected_field=spec.field,
            expected_evidence_id=spec.evidence_id,
        )
        if body["authorization_value"] is not True:
            raise GT32BuildError("fixed GT32 evidence must explicitly authorize")
        evidence_payloads.append(payload)
        evidence_bytes[spec.field] = _write(spec.path, payload)

    evaluations = evaluate_authorization_sequence(evidence_payloads)
    if len(evaluations) != 5:
        raise GT32BuildError("GT32 must contain five cumulative evaluations")

    fields = [spec.field for spec in AUTHORIZATION_SPECS]
    steps: list[dict[str, object]] = []
    for index, (spec, control) in enumerate(zip(AUTHORIZATION_SPECS, evaluations), start=1):
        remaining = fields[index:]
        if list(control.unknown_identifiers) != sorted(remaining):
            raise GT32BuildError(f"step {index} unknown authorization scope mismatch")
        is_final = index == len(AUTHORIZATION_SPECS)
        expected_state = "satisfied" if is_final else "unknown"
        if control.state != expected_state:
            raise GT32BuildError(f"step {index} control state must be {expected_state}")
        if is_final:
            if control.blocked_outputs:
                raise GT32BuildError("final control must have no blocked outputs")
            if control.eligible_outputs != (
                "automatic_takeoff_authorization",
                "takeoff_command",
            ):
                raise GT32BuildError("final control must make both outputs eligible")
        else:
            if control.blocked_outputs != (
                "automatic_takeoff_authorization",
                "takeoff_command",
            ):
                raise GT32BuildError(f"step {index} must keep takeoff outputs blocked")
            if control.eligible_outputs:
                raise GT32BuildError(f"step {index} must not release eligible outputs")
        steps.append(
            {
                "sequence": index,
                "evidence_id": spec.evidence_id,
                "authorization_field": spec.field,
                "authorization_value": True,
                "received_authorizations": fields[:index],
                "remaining_authorizations": remaining,
                "control_state": control.state,
                "gate_satisfied": control.gate_satisfied,
                "unknown_identifiers": list(control.unknown_identifiers),
                "blocked_outputs": list(control.blocked_outputs),
                "eligible_outputs": list(control.eligible_outputs),
                "action_executed": control.action_executed,
            }
        )

    final_control = evaluations[-1]
    final_control_bytes = _write(FINAL_CONTROL, final_control.to_dict())
    input_paths = {
        "task": TASK,
        "execution_result": EXECUTION,
        "initial_control_evaluation": INITIAL_CONTROL,
        "gt31_assurance_evaluation": GT31_EVALUATION,
        "gt31_scenario": GT31_SCENARIO,
    }
    scenario = {
        "scenario": {
            "id": "gt32-progressive-takeoff-authorization",
            "title_zh": "五项授权陆续到达后，什么时候才算可起飞？",
            "title_en": "When five authorization records arrive one by one, when does takeoff become eligible?",
            "upstream": {
                "route_weather_precheck": "eligible",
                "weather_condition_verified": "eligible",
                "wind_speed_mps": 8,
                "mission_wind_limit_mps": 12,
                "initial_unknown_authorization_count": 5,
            },
            "authorization_order": fields,
            "steps": steps,
            "final_gate": {
                "control_state": final_control.state,
                "gate_satisfied": final_control.gate_satisfied,
                "automatic_takeoff_authorization": "eligible",
                "takeoff_command": "eligible",
                "production_output_released": False,
                "command_sent": False,
                "action_authorized_by_core": False,
                "action_executed": False,
            },
            "incorrect_actions": [
                "infer_missing_authorization_from_other_records",
                "release_takeoff_output_before_all_five_records_arrive",
                "treat_output_eligibility_as_command_delivery",
                "treat_command_eligibility_as_action_execution",
            ],
            "required_action": "handoff_eligible_outputs_to_external_authorization_and_execution_runtime",
            "sha256": {
                **{name: _sha256(path.read_bytes()) for name, path in input_paths.items()},
                **{
                    f"authorization_evidence_{field}": _sha256(raw)
                    for field, raw in evidence_bytes.items()
                },
                "final_control_evaluation": _sha256(final_control_bytes),
            },
            "boundaries": {
                "all_authorization_values_caller_asserted": True,
                "external_truth_verified_by_core": False,
                "real_authority_contacted": False,
                "authorization_inferred": False,
                "production_output_released": False,
                "command_sent": False,
                "action_authorized_by_core": False,
                "action_executed": False,
            },
        }
    }
    _write(SCENARIO, scenario)
    return {
        "evidence": evidence_payloads,
        "evaluations": evaluations,
        "final_control": final_control.to_dict(),
        "scenario": scenario,
    }


if __name__ == "__main__":
    build()
    print("GT32 progressive takeoff authorization bundle generated")
