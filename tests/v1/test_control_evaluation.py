"""Read-only control context and structured gate evaluation tests."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import MappingProxyType

import pytest
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_VERSION,
    ControlContextError,
    build_control_context,
    evaluate_control_profile,
)
from geotask_core.v1.result import CheckResult, GeotaskResult


ROOT = Path(__file__).resolve().parents[2]
CONTROL_EVALUATION_SCHEMA = (
    ROOT / "schemas" / "geotask-control-evaluation-v1.0.schema.json"
)


def _check(
    assertion_id: str,
    value: object,
    *,
    status: str = "verified",
    assurance_level: str = "local_deterministic",
    deterministic: bool = True,
    evidence_refs: list[str] | None = None,
) -> CheckResult:
    return CheckResult(
        assertion_id=assertion_id,
        operator="test_operator",
        object_refs=[],
        executor="local",
        value=value,
        status=status,
        assurance_level=assurance_level,
        deterministic=deterministic,
        evidence_refs=evidence_refs or [],
    )


def _result(*checks: CheckResult, task_id: str = "control-test") -> GeotaskResult:
    return GeotaskResult(task_id=task_id, checks=list(checks))


def _document_with_extensions(extensions: dict | None) -> object:
    document = {
        "geotask": {
            "id": "control-evaluation-test",
            "name": "Control evaluation test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "test_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "point_a": {"type": "point", "coordinates": [0, 0]},
            "point_b": {"type": "point", "coordinates": [3, 4]},
        },
        "operator_set": ["distance_2d"],
        "tasks": [
            {
                "id": "measure",
                "assertions": [
                    {
                        "id": "distance_check",
                        "operator": "distance_2d",
                        "object_refs": ["point_a", "point_b"],
                        "expected_type": "number",
                    }
                ],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "run",
                    "executor": "local",
                    "assertion_refs": ["distance_check"],
                }
            ],
        },
        "output_contract": {"format": "structured", "required_fields": []},
    }
    if extensions is not None:
        document["extensions"] = extensions
    return canonicalize(document)


def _task_gate(
    resume_when: str,
    *,
    blocked_outputs: list[str] | None = None,
) -> dict:
    return {
        "extension_profile": {"id": "geotask.control", "version": "1.0"},
        "task_gate": {
            "status": "blocked_pending_review",
            "selected_action": "hold_position",
            "rejected_actions": ["continue_without_review"],
            "blocked_outputs": blocked_outputs or ["movement_command"],
            "required_controls": ["retain_evidence"],
            "resume_when": resume_when,
            "next_action": "request_review",
            "expected_status": "verified_hold",
        },
    }


def test_control_context_is_recursively_read_only_and_tracks_provenance() -> None:
    source_state = {
        "vehicle": {"clearance": 4.0, "ready": True},
        "review_complete": False,
    }
    result = _result(
        _check(
            "route.clear",
            True,
            evidence_refs=["route-map", "live-sensor"],
        )
    )

    context = build_control_context(result, source_state)
    source_state["vehicle"]["clearance"] = 99.0

    assert isinstance(context.values, MappingProxyType)
    assert isinstance(context.values["vehicle"], MappingProxyType)
    assert context.values["route.clear"] is True
    assert context.values["vehicle"]["clearance"] == 4.0
    assert context.entries["route.clear"].source == "assertion_result"
    assert context.entries["route.clear"].assertion_status == "verified"
    assert context.entries["route.clear"].deterministic is True
    assert context.entries["route.clear"].evidence_refs == (
        "route-map",
        "live-sensor",
    )
    assert context.entries["vehicle.clearance"].source == "domain_state"

    with pytest.raises(TypeError):
        context.values["new_value"] = True
    with pytest.raises(TypeError):
        context.values["vehicle"]["clearance"] = 8.0
    with pytest.raises(TypeError):
        context.entries["new_value"] = context.entries["route.clear"]

    serialized = context.to_dict()
    serialized["values"]["vehicle"]["clearance"] = 12.0
    assert context.values["vehicle"]["clearance"] == 4.0


def test_context_rejects_ambiguous_or_non_scalar_domain_state() -> None:
    result = _result(_check("route_clear", True))

    invalid_states = (
        {"route_clear": False},
        {"assertions": {"route_clear": True}},
        {"bad.key": True},
        {"items": [1, 2]},
        {"value": float("nan")},
        {"value": float("inf")},
    )
    for state in invalid_states:
        with pytest.raises(ControlContextError):
            build_control_context(result, state)


def test_context_rejects_duplicate_or_invalid_assertion_ids() -> None:
    duplicate = _result(_check("route_clear", True), _check("route_clear", False))
    with pytest.raises(ControlContextError, match="duplicate assertion id"):
        build_control_context(duplicate)

    invalid = _result(_check("1-invalid", True))
    with pytest.raises(ControlContextError, match="not a valid GeoTask identifier"):
        build_control_context(invalid)


def test_evaluation_rejects_result_from_another_task_or_unknown_checks() -> None:
    doc = _document_with_extensions(_task_gate("ready == true"))

    with pytest.raises(ControlContextError, match="does not match document id"):
        evaluate_control_profile(doc, _result(task_id="another-task"), {"ready": True})

    with pytest.raises(ControlContextError, match="checks not declared"):
        evaluate_control_profile(
            doc,
            _result(_check("fabricated_check", True), task_id=doc.metadata.id),
            {"ready": True},
        )


def test_false_gate_keeps_outputs_blocked_without_executing_action() -> None:
    doc = _document_with_extensions(
        _task_gate("review_complete == true AND evidence_fresh == true")
    )
    execution_result = _result(task_id=doc.metadata.id)
    before = deepcopy(execution_result.to_dict())

    evaluation = evaluate_control_profile(
        doc,
        execution_result,
        {"review_complete": False, "evidence_fresh": True},
    )

    assert evaluation.schema_version == CONTROL_EVALUATION_SCHEMA_VERSION
    assert evaluation.state == "blocked"
    assert evaluation.gate_satisfied is False
    assert evaluation.blocked_outputs == ("movement_command",)
    assert evaluation.eligible_outputs == ()
    assert evaluation.unknown_identifiers == ()
    assert evaluation.action_executed is False

    gate = evaluation.evaluations[0]
    assert gate.state == "blocked"
    assert gate.value is False
    assert gate.selected_action == "hold_position"
    assert gate.next_action == "request_review"
    assert gate.required_controls == ("retain_evidence",)
    assert gate.rejected_actions == ("continue_without_review",)
    assert gate.action_executed is False
    assert execution_result.to_dict() == before


def test_unknown_gate_reports_missing_values_and_continues_blocking() -> None:
    doc = _document_with_extensions(
        _task_gate("review_complete == true AND evidence_fresh == true")
    )

    evaluation = evaluate_control_profile(
        doc,
        _result(task_id=doc.metadata.id),
        {"review_complete": True},
    )

    assert evaluation.state == "unknown"
    assert evaluation.gate_satisfied is None
    assert evaluation.unknown_identifiers == ("evidence_fresh",)
    assert evaluation.blocked_outputs == ("movement_command",)
    assert evaluation.eligible_outputs == ()
    assert evaluation.evaluations[0].unknown_identifiers == ("evidence_fresh",)


def test_true_gate_marks_outputs_eligible_but_does_not_release_them() -> None:
    doc = _document_with_extensions(
        _task_gate(
            "review_complete == true AND evidence_fresh == true",
            blocked_outputs=["movement_command", "automatic_approval"],
        )
    )

    evaluation = evaluate_control_profile(
        doc,
        _result(task_id=doc.metadata.id),
        {"review_complete": True, "evidence_fresh": True},
    )

    assert evaluation.state == "satisfied"
    assert evaluation.gate_satisfied is True
    assert evaluation.blocked_outputs == ()
    assert evaluation.eligible_outputs == (
        "automatic_approval",
        "movement_command",
    )
    assert evaluation.action_executed is False
    assert evaluation.evaluations[0].action_executed is False
    assert evaluation.to_dict()["control_evaluation"]["action_executed"] is False


def test_decision_rule_is_evaluated_without_becoming_a_gate() -> None:
    doc = _document_with_extensions(
        {
            "extension_profile": {"id": "geotask.control", "version": "1.0"},
            "decision_rule": {
                "id": "route-policy",
                "logic": "three_valued_and",
                "expression": "route_clear AND schedule_verified",
                "unknown_policy": "propagate",
                "expected_status": "unverifiable",
            },
        }
    )
    result = _result(task_id=doc.metadata.id)

    evaluation = evaluate_control_profile(doc, result, {"route_clear": True})

    assert evaluation.state == "unknown"
    assert evaluation.gate_satisfied is None
    assert evaluation.unknown_identifiers == ("schedule_verified",)
    assert evaluation.blocked_outputs == ()
    assert evaluation.evaluations[0].block == "decision_rule"
    assert evaluation.evaluations[0].value is None


def test_multiple_controls_union_blocked_outputs_conservatively() -> None:
    doc = _document_with_extensions(
        {
            "extension_profile": {"id": "geotask.control", "version": "1.0"},
            "evidence_request": {
                "id": "request-weather",
                "trigger": "distance_check",
                "reason": "weather_not_verified",
                "required_fields": ["weather_source"],
                "blocked_outputs": ["automatic_approval", "route_command"],
                "resume_when": "weather_verified == true",
                "next_action": "request_evidence",
            },
            "task_gate": {
                "status": "blocked_pending_review",
                "selected_action": "hold_position",
                "blocked_outputs": ["route_command", "movement_command"],
                "required_controls": ["retain_evidence"],
                "resume_when": "review_complete == true",
                "next_action": "request_review",
            },
        }
    )
    result = _result(_check("distance_check", 5.0), task_id=doc.metadata.id)

    evaluation = evaluate_control_profile(
        doc,
        result,
        {"weather_verified": True, "review_complete": False},
    )

    assert evaluation.state == "blocked"
    assert evaluation.gate_satisfied is False
    assert evaluation.blocked_outputs == ("movement_command", "route_command")
    assert evaluation.eligible_outputs == ("automatic_approval",)
    assert [item.state for item in evaluation.evaluations] == [
        "satisfied",
        "blocked",
    ]


def test_evaluation_type_error_is_structured_and_keeps_output_blocked() -> None:
    doc = _document_with_extensions(_task_gate("review_count AND review_complete"))

    evaluation = evaluate_control_profile(
        doc,
        _result(task_id=doc.metadata.id),
        {"review_count": 1, "review_complete": True},
    )

    assert evaluation.state == "error"
    assert evaluation.gate_satisfied is None
    assert evaluation.blocked_outputs == ("movement_command",)
    assert evaluation.eligible_outputs == ()
    assert evaluation.diagnostics[0]["code"] == "control_expression_evaluation_error"
    assert "requires boolean" in evaluation.diagnostics[0]["message"]


def test_missing_or_unsupported_profile_returns_structured_diagnostic() -> None:
    no_profile_doc = _document_with_extensions(None)
    no_profile = evaluate_control_profile(
        no_profile_doc,
        _result(task_id=no_profile_doc.metadata.id),
    )
    assert no_profile.state == "not_applicable"
    assert no_profile.diagnostics[0]["code"] == "control_profile_not_declared"

    unsupported_doc = _document_with_extensions(
        {
            "extension_profile": {"id": "geotask.control", "version": "2.0"},
            "task_gate": _task_gate("ready == true")["task_gate"],
        }
    )
    unsupported = evaluate_control_profile(
        unsupported_doc,
        _result(task_id=unsupported_doc.metadata.id),
    )
    assert unsupported.state == "error"
    assert unsupported.diagnostics[0]["code"] == "unsupported_extension_profile"


def test_serialized_result_contains_context_provenance_and_no_action_claim() -> None:
    doc = _document_with_extensions(_task_gate("ready == true"))
    result = _result(
        _check("distance_check", 5.0, evidence_refs=["measurement-log"]),
        task_id=doc.metadata.id,
    )

    payload = evaluate_control_profile(doc, result, {"ready": True}).to_dict()[
        "control_evaluation"
    ]

    assert payload["schema_version"] == "1.0"
    assert payload["profile"] == {"id": "geotask.control", "version": "1.0"}
    assert payload["gate_satisfied"] is True
    assert payload["action_executed"] is False
    assert payload["control_context"]["values"] == {
        "distance_check": 5.0,
        "ready": True,
    }
    assertion_entry = payload["control_context"]["entries"]["distance_check"]
    assert assertion_entry["source"] == "assertion_result"
    assert assertion_entry["evidence_refs"] == ["measurement-log"]
    assert payload["evaluations"][0]["action_executed"] is False


def test_control_evaluation_serialization_matches_public_json_schema() -> None:
    schema = json.loads(CONTROL_EVALUATION_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    doc = _document_with_extensions(_task_gate("ready == true"))
    payload = evaluate_control_profile(
        doc,
        _result(_check("distance_check", 5.0), task_id=doc.metadata.id),
        {"ready": True, "vehicle": {"clearance": 4.0}},
    ).to_dict()

    assert list(validator.iter_errors(payload)) == []

    unsafe_claim = deepcopy(payload)
    unsafe_claim["control_evaluation"]["action_executed"] = True
    errors = list(validator.iter_errors(unsafe_claim))
    assert errors
    assert any("False was expected" in error.message for error in errors)


def test_gt07_decision_rule_preserves_unknown_temporal_condition() -> None:
    doc = canonicalize(
        load_geotask(ROOT / "examples" / "core" / "unverifiable_constraint.yaml")
    )
    result = _result(
        _check("route_intersects_zone", True),
        _check("altitude_conflict", True),
        _check("temporal_conflict", None, status="unverifiable", deterministic=False),
        task_id=doc.metadata.id,
    )

    evaluation = evaluate_control_profile(doc, result)

    assert evaluation.state == "unknown"
    assert evaluation.gate_satisfied is None
    assert evaluation.unknown_identifiers == ("temporal_conflict",)
    assert evaluation.evaluations[0].value is None


@pytest.mark.parametrize(
    ("example_name", "domain_state", "expected_state", "expected_blocked"),
    (
        (
            "uav_arrival_ground_clearance_release.yaml",
            {"ground_zone_clear": False, "clearance_evidence_age_seconds": 8},
            "blocked",
            ("automatic_drop_authorization", "payload_release_command"),
        ),
        (
            "vehicle_green_light_downstream_blockage.yaml",
            {
                "signal_permission_valid": True,
                "downstream_exit_clear": False,
                "available_storage_m": 4.0,
                "downstream_evidence_age_seconds": 2,
            },
            "blocked",
            ("follow_green_without_exit_check", "intersection_entry_command"),
        ),
    ),
)
def test_real_task_gates_keep_high_risk_outputs_blocked(
    example_name: str,
    domain_state: dict,
    expected_state: str,
    expected_blocked: tuple[str, ...],
) -> None:
    doc = canonicalize(load_geotask(ROOT / "examples" / "core" / example_name))

    evaluation = evaluate_control_profile(
        doc,
        _result(task_id=doc.metadata.id),
        domain_state,
    )

    assert evaluation.state == expected_state
    assert evaluation.gate_satisfied is False
    assert evaluation.blocked_outputs == expected_blocked
    assert evaluation.action_executed is False


def test_public_namespaces_export_control_evaluation_api() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for module in (geotask_core, v1):
        assert module.CONTROL_EVALUATION_SCHEMA_VERSION == "1.0"
        assert module.ControlContextError is ControlContextError
        assert callable(module.build_control_context)
        assert callable(module.evaluate_control_profile)
        assert module.ControlEvaluationResult.__name__ == "ControlEvaluationResult"
