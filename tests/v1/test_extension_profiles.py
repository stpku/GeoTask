"""Versioned extension-profile validation tests."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.enums import (
    EXTENSION_PROFILE_VIOLATION,
    INVALID_REFERENCE,
    MISSING_FIELD,
    UNKNOWN_FIELD,
    UNSUPPORTED_EXTENSION_PROFILE,
)


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
PROFILED_PAGES = tuple(
    ROOT / "site" / f"gt{number:02d}" / "index.html"
    for number in (7, 8, 9, 17, 18, 19, 20)
)


def _base_document() -> dict:
    return {
        "geotask": {
            "id": "extension-profile-test",
            "name": "Extension profile test",
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
                    },
                    {
                        "id": "backup_check",
                        "operator": "distance_2d",
                        "object_refs": ["point_a", "point_b"],
                        "expected_type": "number",
                    },
                ],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "run",
                    "executor": "local",
                    "assertion_refs": ["distance_check", "backup_check"],
                }
            ],
        },
        "output_contract": {"format": "structured", "required_fields": []},
    }


def _profile() -> dict:
    return {"id": "geotask.control", "version": "1.0"}


def _errors(document: dict) -> list[dict]:
    return [
        diagnostic
        for diagnostic in validate_document(document)
        if diagnostic.get("severity", "error") == "error"
    ]


def test_profile_api_is_exported_from_public_namespaces() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for module in (geotask_core, v1):
        assert module.CONTROL_PROFILE_ID == "geotask.control"
        assert module.CONTROL_PROFILE_VERSION == "1.0"
        assert callable(module.validate_extension_profiles)
        assert module.CONTROL_EXPRESSION_LANGUAGE_ID == "geotask.control-expression"
        assert module.CONTROL_EXPRESSION_LANGUAGE_VERSION == "1.0"
        assert callable(module.parse_control_expression)
        assert callable(module.evaluate_control_expression)
        assert callable(module.referenced_identifiers)
        assert issubclass(module.ExpressionSyntaxError, ValueError)
        assert issubclass(module.ExpressionEvaluationError, ValueError)


def test_unprofiled_extensions_remain_open_for_backward_compatibility() -> None:
    document = _base_document()
    document["extensions"] = {
        "task_gate": "legacy-free-form-value",
        "domain_state": {"anything": True},
    }

    diagnostics = validate_document(document)

    assert not any(
        diagnostic["path"].startswith("extensions") for diagnostic in diagnostics
    )


def test_supported_profile_accepts_a_valid_decision_rule() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "decision_rule": {
            "id": "distance-policy",
            "logic": "three_valued_and",
            "expression": "distance_check AND backup_check",
            "unknown_policy": "propagate",
            "expected_status": "verified",
        },
        "domain_state": {"custom": "still-open"},
    }

    assert _errors(document) == []


def test_profile_rejects_unsupported_id_or_version() -> None:
    for profile in (
        {"id": "geotask.control", "version": "2.0"},
        {"id": "vendor.private", "version": "1.0"},
    ):
        document = _base_document()
        document["extensions"] = {
            "extension_profile": profile,
            "decision_rule": {
                "id": "distance-policy",
                "logic": "and",
                "expression": "distance_check",
            },
        }

        errors = _errors(document)
        assert any(item["code"] == UNSUPPORTED_EXTENSION_PROFILE for item in errors)


def test_profile_requires_at_least_one_control_block() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "domain_state": {"custom": True},
    }

    errors = _errors(document)

    assert any(item["code"] == EXTENSION_PROFILE_VIOLATION for item in errors)
    assert any(item["path"] == "extensions" for item in errors)


def test_evidence_request_checks_required_fields_and_assertion_reference() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "evidence_request": {
            "id": "request-weather",
            "trigger": "missing_assertion",
            "reason": "weather_not_verified",
            "required_fields": ["source_reference", "source_reference"],
            "blocked_outputs": ["automatic_approval"],
            "resume_when": "weather_verified == true",
            # next_action intentionally missing
        },
    }

    errors = _errors(document)
    codes = {item["code"] for item in errors}

    assert MISSING_FIELD in codes
    assert INVALID_REFERENCE in codes
    assert EXTENSION_PROFILE_VIOLATION in codes
    assert any(item["path"] == "extensions.evidence_request.next_action" for item in errors)
    assert any(item["path"] == "extensions.evidence_request.trigger" for item in errors)


def test_evidence_conflict_requires_two_valid_assertion_references() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "evidence_conflict": {
            "id": "resolve-distance-conflict",
            "subject": "distance",
            "conflict_type": "incompatible_verified_sources",
            "conflicting_assertions": ["distance_check", "missing_assertion"],
            "source_refs": ["source_a", "source_b"],
            "blocked_outputs": ["automatic_approval"],
            "resolution_required_fields": ["authoritative_source"],
            "resume_when": "evidence_conflict_resolved == true",
            "next_action": "request_conflict_review",
        },
    }

    errors = _errors(document)

    assert any(item["code"] == INVALID_REFERENCE for item in errors)
    assert any(
        item["path"] == "extensions.evidence_conflict.conflicting_assertions[1]"
        for item in errors
    )


def test_task_gate_is_strict_inside_declared_profile() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "task_gate": {
            "status": "blocked_pending_review",
            "selected_action": "hold_position",
            "blocked_outputs": ["movement_command"],
            "required_controls": ["retain_evidence"],
            "resume_when": "review_complete == true",
            "next_action": "request_review",
            "unexpected_field": True,
        },
    }

    errors = _errors(document)

    assert any(item["code"] == UNKNOWN_FIELD for item in errors)
    assert any(item["path"] == "extensions.task_gate.unexpected_field" for item in errors)


@pytest.mark.parametrize("path", PROFILED_EXAMPLES)
def test_public_control_profile_examples_validate(path: Path) -> None:
    document = load_geotask(path)
    profile = document["extensions"]["extension_profile"]

    assert profile == _profile()
    assert _errors(deepcopy(document)) == []


def test_json_schema_rejects_an_incomplete_profiled_task_gate() -> None:
    document = _base_document()
    document["extensions"] = {
        "extension_profile": _profile(),
        "task_gate": {
            "status": "blocked_pending_review",
            "selected_action": "hold_position",
        },
    }
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(document))

    assert errors
    assert any("blocked_outputs" in error.message for error in errors)
    assert any("required_controls" in error.message for error in errors)
    assert any("resume_when" in error.message for error in errors)


@pytest.mark.parametrize("path", PROFILED_PAGES)
def test_profiled_case_pages_disclose_the_public_profile(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert "extension_profile:" in text
    assert 'id: "geotask.control"' in text
    assert 'version: "1.0"' in text
