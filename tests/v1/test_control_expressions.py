"""Finite control-expression parser and evaluator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.control_expressions import (
    BinaryExpression,
    ExpressionEvaluationError,
    ExpressionSyntaxError,
    evaluate_control_expression,
    parse_control_expression,
    referenced_identifiers,
)
from geotask_core.v1.enums import INVALID_EXPRESSION


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "geotask-v1.0.schema.json"
PROFILED_EXAMPLES = (
    ROOT / "examples" / "core" / "unverifiable_constraint.yaml",
    ROOT / "examples" / "core" / "evidence_request_plan.yaml",
    ROOT / "examples" / "core" / "evidence_conflict_review.yaml",
    ROOT / "examples" / "core" / "city_event_report_deduplication.yaml",
    ROOT / "examples" / "core" / "rescue_robot_shortest_route_hazard.yaml",
    ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml",
    ROOT / "examples" / "core" / "vehicle_green_light_downstream_blockage.yaml",
)


def _base_document() -> dict:
    return {
        "geotask": {
            "id": "expression-test",
            "name": "Expression test",
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


def test_parser_applies_boolean_precedence_and_parentheses() -> None:
    expression = parse_control_expression("a OR b AND NOT c")
    grouped = parse_control_expression("(a OR b) AND NOT c")

    assert isinstance(expression, BinaryExpression)
    assert expression.operator == "OR"
    assert evaluate_control_expression(expression, {"a": False, "b": True, "c": False}) is True
    assert evaluate_control_expression(grouped, {"a": True, "b": False, "c": True}) is False


@pytest.mark.parametrize(
    ("expression", "context", "expected"),
    (
        ("available >= required", {"available": 6.8, "required": 6.8}, True),
        ("temperature < 80", {"temperature": 81}, False),
        ("status == 'verified'", {"status": "verified"}, True),
        ("enabled != false", {"enabled": True}, True),
        ("vehicle.clearance >= 3", {"vehicle": {"clearance": 4}}, True),
        ("missing_value == true", {}, None),
    ),
)
def test_scalar_comparisons_and_dotted_identifier_resolution(
    expression: str,
    context: dict,
    expected: bool | None,
) -> None:
    assert evaluate_control_expression(expression, context) is expected


@pytest.mark.parametrize(
    ("expression", "context", "expected"),
    (
        ("unknown AND false", {}, False),
        ("unknown AND true", {}, None),
        ("unknown OR true", {}, True),
        ("unknown OR false", {}, None),
        ("NOT unknown", {}, None),
        ("verified AND missing", {"verified": True}, None),
        ("blocked OR missing", {"blocked": False}, None),
    ),
)
def test_boolean_operators_use_three_valued_logic(
    expression: str,
    context: dict,
    expected: bool | None,
) -> None:
    assert evaluate_control_expression(expression, context) is expected


def test_identifier_collection_is_deterministic() -> None:
    identifiers = referenced_identifiers(
        "route.valid AND (clearance >= vehicle.required OR override == true)"
    )

    assert identifiers == frozenset(
        {"route.valid", "clearance", "vehicle.required", "override"}
    )


@pytest.mark.parametrize(
    "expression",
    (
        "__import__('os')",
        "dangerous.call()",
        "values[0] == 1",
        "a + b",
        "a == b == c",
        "a = true",
        "a AND",
        "(a OR b",
        "08:36",
        "",
    ),
)
def test_parser_rejects_code_execution_and_unsupported_syntax(expression: str) -> None:
    with pytest.raises(ExpressionSyntaxError):
        parse_control_expression(expression)


def test_parser_enforces_resource_limits() -> None:
    with pytest.raises(ExpressionSyntaxError, match="length exceeds"):
        parse_control_expression("a" * 4097)
    with pytest.raises(ExpressionSyntaxError, match="token count exceeds"):
        parse_control_expression(" ".join("a" for _ in range(1025)))
    with pytest.raises(ExpressionSyntaxError, match="nesting exceeds"):
        parse_control_expression("(" * 65 + "true" + ")" * 65)
    with pytest.raises(ExpressionSyntaxError, match="Unary nesting exceeds"):
        parse_control_expression("NOT " * 65 + "true")


def test_json_schema_enforces_expression_shape_and_length_only() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    contract = schema["$defs"]["controlExpression"]

    assert contract["type"] == "string"
    assert contract["minLength"] == 1
    assert contract["maxLength"] == 4096
    assert "Full grammar validation" in contract["description"]

    document = _base_document()
    document["extensions"] = {
        "extension_profile": {"id": "geotask.control", "version": "1.0"},
        "task_gate": {
            "status": "blocked",
            "selected_action": "hold",
            "blocked_outputs": ["movement_command"],
            "required_controls": ["retain_evidence"],
            "resume_when": "a" * 4097,
            "next_action": "request_review",
        },
    }
    errors = list(Draft202012Validator(schema).iter_errors(document))

    assert any("too long" in error.message for error in errors)


@pytest.mark.parametrize(
    ("expression", "context"),
    (
        ("count AND true", {"count": 1}),
        ("'a' < 'b'", {}),
        ("true == 1", {}),
        ("value >= 0", {"value": float("nan")}),
        ("value >= 0", {"value": float("inf")}),
        ("5", {}),
        ("'verified'", {}),
    ),
)
def test_evaluator_rejects_ambiguous_operand_types(
    expression: str,
    context: dict,
) -> None:
    with pytest.raises(ExpressionEvaluationError):
        evaluate_control_expression(expression, context)


def test_profile_validation_reports_expression_path_and_position() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": {"id": "geotask.control", "version": "1.0"},
        "task_gate": {
            "status": "blocked",
            "selected_action": "hold",
            "blocked_outputs": ["movement_command"],
            "required_controls": ["retain_evidence"],
            "resume_when": "review_complete() == true",
            "next_action": "request_review",
        },
    }

    diagnostics = validate_document(document)
    errors = [item for item in diagnostics if item["code"] == INVALID_EXPRESSION]

    assert len(errors) == 1
    assert errors[0]["path"] == "extensions.task_gate.resume_when"
    assert "position" in errors[0]["message"]


@pytest.mark.parametrize("path", PROFILED_EXAMPLES)
def test_all_profiled_example_expressions_parse(path: Path) -> None:
    document = load_geotask(path)
    extensions = document["extensions"]

    expressions: list[str] = []
    if "decision_rule" in extensions:
        expressions.append(extensions["decision_rule"]["expression"])
    for block_name in ("evidence_request", "evidence_conflict", "task_gate"):
        if block_name in extensions:
            expressions.append(extensions[block_name]["resume_when"])

    assert expressions
    for expression in expressions:
        parse_control_expression(expression)


@pytest.mark.parametrize(
    ("example_name", "block_name", "field", "context", "expected"),
    (
        (
            "unverifiable_constraint.yaml",
            "decision_rule",
            "expression",
            {
                "route_intersects_zone": True,
                "altitude_conflict": True,
                "temporal_conflict": None,
            },
            None,
        ),
        (
            "city_event_report_deduplication.yaml",
            "task_gate",
            "resume_when",
            {"verified_event_cluster_active": True, "dispatch_task_count": 1},
            True,
        ),
        (
            "rescue_robot_shortest_route_hazard.yaml",
            "task_gate",
            "resume_when",
            {"safe_route_executable": True, "monitored_temperature_c": 60},
            True,
        ),
        (
            "uav_arrival_ground_clearance_release.yaml",
            "task_gate",
            "resume_when",
            {"ground_zone_clear": False, "clearance_evidence_age_seconds": 8},
            False,
        ),
        (
            "vehicle_green_light_downstream_blockage.yaml",
            "task_gate",
            "resume_when",
            {
                "signal_permission_valid": True,
                "downstream_exit_clear": False,
                "available_storage_m": 4.0,
                "downstream_evidence_age_seconds": 2,
            },
            False,
        ),
    ),
)
def test_profiled_case_expressions_have_expected_three_valued_results(
    example_name: str,
    block_name: str,
    field: str,
    context: dict,
    expected: bool | None,
) -> None:
    document = load_geotask(ROOT / "examples" / "core" / example_name)
    expression = document["extensions"][block_name][field]

    assert evaluate_control_expression(expression, context) is expected


def test_expression_module_contains_no_dynamic_eval() -> None:
    source = (
        ROOT / "src" / "geotask_core" / "v1" / "control_expressions.py"
    ).read_text(encoding="utf-8")

    assert "eval(" not in source
    assert "exec(" not in source
