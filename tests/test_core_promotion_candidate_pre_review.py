"""Tests for the fail-closed Core Promotion Candidate pre-review."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "evaluate_core_promotion_candidate.py"
TEMPLATE = ROOT / "docs" / "reference" / "core-promotion-candidate-template.yaml"


def _module():
    spec = importlib.util.spec_from_file_location("promotion_pre_review", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate(**overrides):
    candidate = {
        "schema_version": "0.1",
        "candidate_id": "dependency-relation-state-v0.1",
        "source_line": "Lowa-GT Integration",
        "target_line": "GeoTask Core",
        "problem_statement": "Derived results need replayable dependency change detection.",
        "proposed_generic_name": "dependency relation state",
        "first_system_evidence": {
            "system_id": "lowa-product",
            "evidence_refs": ["integration-evidence://lowa/dependency-relation/1"],
        },
        "second_system_evidence": {
            "system_id": "independent-system-b",
            "independent_owner": True,
            "real_system_evidence": True,
            "evidence_refs": ["evidence://system-b/dependency-relation/1"],
            "matched_case_refs": ["case://system-b/matched"],
            "nonmatching_or_unverifiable_case_refs": ["case://system-b/changed"],
            "replay_instructions_ref": "runbook://system-b/dependency-replay",
            "authoritative_state_unchanged": True,
        },
        "core_gate_conditions": {
            "industry_neutral_semantics": True,
            "deterministic_fail_closed_replayable": True,
            "no_system_of_record_capture": True,
            "no_hidden_side_effect_expansion": True,
            "core_native_public_safe_verification": True,
            "compatibility_migration_reviewed": True,
        },
        "proposed_public_surface": "A neutral dependency-relation artifact or verifier contract.",
        "compatibility_notes": "New versioned surface only; no silent reinterpretation of existing artifacts.",
        "excluded_source_logic": ["Lowa AssessmentRecord business semantics", "report publication workflow"],
        "review_notes": "Prepared for architecture review only.",
        "explicit_gate_decision": "UNDECIDED",
    }
    candidate.update(overrides)
    return candidate


def _write(tmp_path: Path, candidate: dict) -> Path:
    path = tmp_path / "candidate.yaml"
    path.write_text(yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8")
    return path


def test_unfilled_template_is_invalid_not_deferred_evidence() -> None:
    module = _module()
    with pytest.raises(module.CandidateError, match="template placeholder"):
        module.load_candidate(TEMPLATE)


def test_complete_record_is_only_eligible_for_review_never_promoted(tmp_path: Path) -> None:
    module = _module()
    result = module.evaluate(module.load_candidate(_write(tmp_path, _candidate())))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "eligible_for_gate_review"
    assert result["machine_can_promote"] is False
    assert result["explicit_gate_decision"] == "UNDECIDED"
    assert result["missing_or_failed_checks"] == []


def test_missing_second_system_real_evidence_defers(tmp_path: Path) -> None:
    module = _module()
    candidate = _candidate()
    candidate["second_system_evidence"]["real_system_evidence"] = False
    result = module.evaluate(module.load_candidate(_write(tmp_path, candidate)))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "defer"
    assert "second_system_real_evidence" in result["missing_or_failed_checks"]


def test_same_system_cannot_satisfy_independent_reuse(tmp_path: Path) -> None:
    module = _module()
    candidate = _candidate()
    candidate["second_system_evidence"]["system_id"] = "LOWA-PRODUCT"
    result = module.evaluate(module.load_candidate(_write(tmp_path, candidate)))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "defer"
    assert result["checks"]["second_system_is_distinct"] is False


def test_missing_matched_or_nonmatching_case_defers(tmp_path: Path) -> None:
    module = _module()
    candidate = _candidate()
    candidate["second_system_evidence"]["matched_case_refs"] = []
    candidate["second_system_evidence"]["nonmatching_or_unverifiable_case_refs"] = []
    result = module.evaluate(module.load_candidate(_write(tmp_path, candidate)))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "defer"
    assert "second_system_matched_case_recorded" in result["missing_or_failed_checks"]
    assert "second_system_nonmatching_or_unverifiable_case_recorded" in result[
        "missing_or_failed_checks"
    ]


def test_any_failed_core_gate_condition_defers(tmp_path: Path) -> None:
    module = _module()
    candidate = _candidate()
    candidate["core_gate_conditions"]["no_hidden_side_effect_expansion"] = False
    result = module.evaluate(module.load_candidate(_write(tmp_path, candidate)))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "defer"
    assert "core_gate_no_hidden_side_effect_expansion" in result[
        "missing_or_failed_checks"
    ]


def test_explicit_human_decision_is_reported_but_machine_still_does_not_promote(
    tmp_path: Path,
) -> None:
    module = _module()
    candidate = _candidate(explicit_gate_decision="PROMOTE")
    result = module.evaluate(module.load_candidate(_write(tmp_path, candidate)))[
        "core_promotion_pre_review"
    ]
    assert result["machine_outcome"] == "eligible_for_gate_review"
    assert result["explicit_gate_decision"] == "PROMOTE"
    assert result["machine_can_promote"] is False


def test_excluded_source_logic_must_be_recorded(tmp_path: Path) -> None:
    module = _module()
    candidate = _candidate(excluded_source_logic=[])
    with pytest.raises(module.CandidateError, match="excluded_source_logic"):
        module.load_candidate(_write(tmp_path, candidate))
