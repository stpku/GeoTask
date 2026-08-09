#!/usr/bin/env python3
"""Fail-closed pre-review for GeoTask Core Promotion Candidates.

The machine can determine whether a candidate record is complete enough for an
explicit Promotion Gate review. It cannot decide PROMOTE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml


SCHEMA_VERSION = "0.1"
TARGET_LINE = "GeoTask Core"
GATE_FIELDS = (
    "industry_neutral_semantics",
    "deterministic_fail_closed_replayable",
    "no_system_of_record_capture",
    "no_hidden_side_effect_expansion",
    "core_native_public_safe_verification",
    "compatibility_migration_reviewed",
)
DECISIONS = {"UNDECIDED", "PROMOTE", "KEEP_LOCAL", "DEFER", "REJECT"}


class CandidateError(ValueError):
    pass


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CandidateError(f"{field} must be a mapping")
    return dict(value)


def _nonempty_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateError(f"{field} must be a non-empty string")
    text = value.strip()
    if text.startswith("<") and text.endswith(">"):
        raise CandidateError(f"{field} still contains a template placeholder")
    return text


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise CandidateError(f"{field} must be a list")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CandidateError(f"{field}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def load_candidate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CandidateError(f"{path}: candidate file does not exist")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CandidateError(f"{path}: invalid YAML: {exc}") from exc
    candidate = _mapping(raw, field="candidate")
    if candidate.get("schema_version") != SCHEMA_VERSION:
        raise CandidateError(f"schema_version must be {SCHEMA_VERSION!r}")

    for field in (
        "candidate_id",
        "source_line",
        "problem_statement",
        "proposed_generic_name",
        "proposed_public_surface",
        "compatibility_notes",
    ):
        candidate[field] = _nonempty_text(candidate.get(field), field=field)
    if candidate.get("target_line") != TARGET_LINE:
        raise CandidateError(f"target_line must be {TARGET_LINE!r}")

    first = _mapping(candidate.get("first_system_evidence"), field="first_system_evidence")
    second = _mapping(candidate.get("second_system_evidence"), field="second_system_evidence")
    gates = _mapping(candidate.get("core_gate_conditions"), field="core_gate_conditions")

    first["system_id"] = _nonempty_text(first.get("system_id"), field="first_system_evidence.system_id")
    first["evidence_refs"] = _string_list(first.get("evidence_refs"), field="first_system_evidence.evidence_refs")
    second["system_id"] = _nonempty_text(second.get("system_id"), field="second_system_evidence.system_id")
    for field in ("independent_owner", "real_system_evidence", "authoritative_state_unchanged"):
        if type(second.get(field)) is not bool:
            raise CandidateError(f"second_system_evidence.{field} must be true or false")
    for field in ("evidence_refs", "matched_case_refs", "nonmatching_or_unverifiable_case_refs"):
        second[field] = _string_list(second.get(field), field=f"second_system_evidence.{field}")
    second["replay_instructions_ref"] = _nonempty_text(
        second.get("replay_instructions_ref"), field="second_system_evidence.replay_instructions_ref"
    )

    for field in GATE_FIELDS:
        if type(gates.get(field)) is not bool:
            raise CandidateError(f"core_gate_conditions.{field} must be true or false")

    candidate["excluded_source_logic"] = _string_list(
        candidate.get("excluded_source_logic"), field="excluded_source_logic"
    )
    if not candidate["excluded_source_logic"]:
        raise CandidateError("excluded_source_logic must name at least one source/domain behavior not promoted")

    decision = candidate.get("explicit_gate_decision")
    if decision not in DECISIONS:
        raise CandidateError(
            "explicit_gate_decision must be one of UNDECIDED, PROMOTE, KEEP_LOCAL, DEFER, REJECT"
        )

    candidate["first_system_evidence"] = first
    candidate["second_system_evidence"] = second
    candidate["core_gate_conditions"] = gates
    return candidate


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    first = candidate["first_system_evidence"]
    second = candidate["second_system_evidence"]
    gates = candidate["core_gate_conditions"]

    checks = {
        "first_system_evidence_recorded": bool(first["evidence_refs"]),
        "second_system_is_distinct": first["system_id"].casefold() != second["system_id"].casefold(),
        "second_system_independent_owner": second["independent_owner"],
        "second_system_real_evidence": second["real_system_evidence"],
        "second_system_evidence_refs_recorded": bool(second["evidence_refs"]),
        "second_system_matched_case_recorded": bool(second["matched_case_refs"]),
        "second_system_nonmatching_or_unverifiable_case_recorded": bool(
            second["nonmatching_or_unverifiable_case_refs"]
        ),
        "second_system_replay_recorded": bool(second["replay_instructions_ref"]),
        "second_system_authoritative_state_unchanged": second["authoritative_state_unchanged"],
        **{f"core_gate_{field}": gates[field] for field in GATE_FIELDS},
        "excluded_source_logic_recorded": bool(candidate["excluded_source_logic"]),
    }
    eligible = all(checks.values())
    machine_outcome = "eligible_for_gate_review" if eligible else "defer"
    missing = [name for name, passed in checks.items() if not passed]

    return {
        "core_promotion_pre_review": {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": candidate["candidate_id"],
            "proposed_generic_name": candidate["proposed_generic_name"],
            "machine_outcome": machine_outcome,
            "machine_can_promote": False,
            "explicit_gate_decision": candidate["explicit_gate_decision"],
            "checks": checks,
            "missing_or_failed_checks": missing,
            "invariant": "eligible_for_gate_review is not PROMOTE; ownership changes only after an explicit Promotion Gate decision",
        }
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pre-review a GeoTask Core Promotion Candidate.")
    parser.add_argument("candidate", help="Candidate YAML file")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("--output", help="Write JSON output to a file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        candidate = load_candidate(Path(args.candidate))
        result = evaluate(candidate)
    except CandidateError as exc:
        print(f"core_promotion_candidate_invalid: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["core_promotion_pre_review"]["machine_outcome"] == "eligible_for_gate_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
