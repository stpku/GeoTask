#!/usr/bin/env python3
"""Validate and aggregate real GeoTask P1 external developer activation records.

The tool never fabricates participant evidence. It supports the historical v0.1
activation contract and the simplified v0.2 Product Activation contract. A
single report may contain exactly one protocol version; mixed versions fail
closed rather than being silently reinterpreted.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from typing import Any

import yaml


# Kept for backward compatibility with the original v0.1 module surface.
SCHEMA_VERSION = "0.1"
PROTOCOL_VERSION = "0.1"
SUPPORTED_VERSION_PAIRS = {("0.1", "0.1"), ("0.2", "0.2")}

BASE_BOOL_FIELDS = (
    "completed_within_30_minutes",
    "entrypoint_found_without_help",
    "first_replay_succeeded",
    "custom_scenario_succeeded",
    "understood_rev1_rev2_rev3",
    "understood_unknown_not_false",
    "understood_bounded_impact",
    "understood_eligible_not_executed",
    "first_replay_failure_repository_defect",
)
V02_BOOL_FIELDS = BASE_BOOL_FIELDS + ("product_activation_completed_within_15_minutes",)
LIST_FIELDS = (
    "repository_defects",
    "help_events",
    "confusion_points",
    "documentation_gaps",
)
BASE_TEXT_FIELDS = (
    "participant_alias",
    "started_at",
    "completed_at",
    "participant_summary",
    "observer_notes",
)
V02_TEXT_FIELDS = BASE_TEXT_FIELDS + ("product_activation_completed_at",)


class ActivationRecordError(ValueError):
    """Raised when a participant record is not auditable."""


def _parse_timestamp(value: str, *, field: str, path: Path) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ActivationRecordError(
            f"{path}: {field} must be an ISO-8601 timestamp with timezone"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ActivationRecordError(
            f"{path}: {field} must include an explicit timezone offset"
        )
    return parsed


def _require_mapping(value: Any, *, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ActivationRecordError(f"{path}: record root must be a mapping")
    return dict(value)


def _record_version(record: dict[str, Any], *, path: Path) -> str:
    pair = (record.get("schema_version"), record.get("protocol_version"))
    if pair not in SUPPORTED_VERSION_PAIRS:
        supported = ", ".join(f"schema={s}/protocol={p}" for s, p in sorted(SUPPORTED_VERSION_PAIRS))
        raise ActivationRecordError(
            f"{path}: unsupported developer activation version pair {pair!r}; supported: {supported}"
        )
    return str(pair[1])


def _validate_help_events(record: dict[str, Any], *, path: Path) -> None:
    for index, event in enumerate(record["help_events"]):
        if not isinstance(event, dict):
            raise ActivationRecordError(f"{path}: help_events[{index}] must be a mapping")
        minute = event.get("minute")
        issue = event.get("issue")
        intervention = event.get("intervention")
        if isinstance(minute, bool) or not isinstance(minute, (int, float)) or minute < 0:
            raise ActivationRecordError(
                f"{path}: help_events[{index}].minute must be a non-negative number"
            )
        if not isinstance(issue, str) or not issue.strip():
            raise ActivationRecordError(
                f"{path}: help_events[{index}].issue must be a non-empty string"
            )
        if not isinstance(intervention, str) or not intervention.strip():
            raise ActivationRecordError(
                f"{path}: help_events[{index}].intervention must be a non-empty string"
            )


def _load_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ActivationRecordError(f"{path}: result file does not exist")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ActivationRecordError(f"{path}: invalid YAML: {exc}") from exc
    record = _require_mapping(raw, path=path)
    version = _record_version(record, path=path)

    text_fields = V02_TEXT_FIELDS if version == "0.2" else BASE_TEXT_FIELDS
    bool_fields = V02_BOOL_FIELDS if version == "0.2" else BASE_BOOL_FIELDS

    for field in text_fields:
        if not isinstance(record.get(field), str):
            raise ActivationRecordError(f"{path}: {field} must be a string")
    alias = record["participant_alias"].strip()
    if not alias:
        raise ActivationRecordError(f"{path}: participant_alias must not be empty")

    for field in bool_fields:
        if type(record.get(field)) is not bool:  # bool only; reject 0/1
            raise ActivationRecordError(f"{path}: {field} must be true or false")
    for field in LIST_FIELDS:
        if not isinstance(record.get(field), list):
            raise ActivationRecordError(f"{path}: {field} must be a list")

    for field in ("repository_defects", "confusion_points", "documentation_gaps"):
        if not all(isinstance(item, str) and item.strip() for item in record[field]):
            raise ActivationRecordError(
                f"{path}: every {field} entry must be a non-empty string"
            )
    _validate_help_events(record, path=path)

    started_at = _parse_timestamp(record["started_at"], field="started_at", path=path)
    completed_at = _parse_timestamp(record["completed_at"], field="completed_at", path=path)
    duration_seconds = (completed_at - started_at).total_seconds()
    if duration_seconds < 0:
        raise ActivationRecordError(f"{path}: completed_at must not precede started_at")
    computed_within_30 = duration_seconds <= 30 * 60
    if record["completed_within_30_minutes"] is not computed_within_30:
        raise ActivationRecordError(
            f"{path}: completed_within_30_minutes disagrees with timestamps "
            f"({duration_seconds / 60:.1f} minutes)"
        )

    product_activation_minutes: float | None = None
    if version == "0.2":
        product_at = _parse_timestamp(
            record["product_activation_completed_at"],
            field="product_activation_completed_at",
            path=path,
        )
        product_seconds = (product_at - started_at).total_seconds()
        if product_seconds < 0:
            raise ActivationRecordError(
                f"{path}: product_activation_completed_at must not precede started_at"
            )
        if product_at > completed_at:
            raise ActivationRecordError(
                f"{path}: product_activation_completed_at must not follow completed_at"
            )
        computed_within_15 = product_seconds <= 15 * 60
        if record["product_activation_completed_within_15_minutes"] is not computed_within_15:
            raise ActivationRecordError(
                f"{path}: product_activation_completed_within_15_minutes disagrees with timestamps "
                f"({product_seconds / 60:.1f} minutes)"
            )
        product_activation_minutes = round(product_seconds / 60, 2)

    replay_succeeded = record["first_replay_succeeded"]
    defect_override = record["first_replay_failure_repository_defect"]
    defects = record["repository_defects"]
    if replay_succeeded and defect_override:
        raise ActivationRecordError(
            f"{path}: first_replay_failure_repository_defect must be false when "
            "first_replay_succeeded=true"
        )
    if defect_override and not defects:
        raise ActivationRecordError(
            f"{path}: repository_defects must describe the documented defect when "
            "first_replay_failure_repository_defect=true"
        )

    normalized = dict(record)
    normalized["participant_alias"] = alias
    normalized["duration_minutes"] = round(duration_seconds / 60, 2)
    if product_activation_minutes is not None:
        normalized["product_activation_minutes"] = product_activation_minutes
    normalized["source_file"] = path.name
    return normalized


def _normalized_confusion(text: str) -> str:
    return " ".join(text.casefold().split())


def _require_single_version(records: list[dict[str, Any]]) -> str:
    versions = {record["protocol_version"] for record in records}
    if len(versions) > 1:
        raise ActivationRecordError(
            "developer activation records from different protocol versions must not be mixed"
        )
    return next(iter(versions), PROTOCOL_VERSION)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    version = _require_single_version(records)
    aliases = [record["participant_alias"] for record in records]
    duplicates = sorted(alias for alias, count in Counter(aliases).items() if count > 1)
    if duplicates:
        raise ActivationRecordError(
            "participant_alias values must be unique; duplicates: " + ", ".join(duplicates)
        )

    attempted = len(records)
    two_thirds_threshold = math.ceil((2 * attempted) / 3) if attempted else 0
    fixed_replay_acceptable_count = sum(
        1
        for record in records
        if record["first_replay_succeeded"]
        or (
            record["first_replay_failure_repository_defect"]
            and bool(record["repository_defects"])
        )
    )
    custom_succeeded_count = sum(
        1 for record in records if record["custom_scenario_succeeded"]
    )
    lifecycle_and_boundary_count = sum(
        1
        for record in records
        if record["understood_rev1_rev2_rev3"]
        and record["understood_eligible_not_executed"]
    )
    bounded_and_boundary_count = sum(
        1
        for record in records
        if record["understood_bounded_impact"]
        and record["understood_eligible_not_executed"]
    )

    confusion_lookup: dict[str, str] = {}
    confusion_counter: Counter[str] = Counter()
    for record in records:
        seen_for_participant: set[str] = set()
        for point in record["confusion_points"]:
            normalized = _normalized_confusion(point)
            confusion_lookup.setdefault(normalized, point.strip())
            seen_for_participant.add(normalized)
        confusion_counter.update(seen_for_participant)
    repeated_confusions = [
        {"point": confusion_lookup[key], "participant_count": count}
        for key, count in sorted(confusion_counter.items())
        if count >= 2
    ]

    repository_defects = [
        {"participant_alias": record["participant_alias"], "defect": defect}
        for record in records
        for defect in record["repository_defects"]
    ]
    documentation_gaps = [
        {"participant_alias": record["participant_alias"], "gap": gap}
        for record in records
        for gap in record["documentation_gaps"]
    ]

    gate_checks = {
        "minimum_three_unfamiliar_participants": {
            "passed": attempted >= 3,
            "actual": attempted,
            "required": 3,
        },
        "fixed_reference_agent_runnable_or_repository_defect_documented": {
            "passed": attempted > 0 and fixed_replay_acceptable_count == attempted,
            "actual": fixed_replay_acceptable_count,
            "required": attempted,
        },
        "at_least_two_thirds_custom_scenario": {
            "passed": attempted > 0 and custom_succeeded_count >= two_thirds_threshold,
            "actual": custom_succeeded_count,
            "required": two_thirds_threshold,
        },
    }
    if version == "0.1":
        gate_checks["at_least_two_thirds_lifecycle_and_action_boundary"] = {
            "passed": attempted > 0 and lifecycle_and_boundary_count >= two_thirds_threshold,
            "actual": lifecycle_and_boundary_count,
            "required": two_thirds_threshold,
        }
    elif version == "0.2":
        gate_checks["at_least_two_thirds_bounded_impact_and_action_boundary"] = {
            "passed": attempted > 0 and bounded_and_boundary_count >= two_thirds_threshold,
            "actual": bounded_and_boundary_count,
            "required": two_thirds_threshold,
        }
    else:  # defensive; _load_record already rejects unsupported versions
        raise ActivationRecordError(f"unsupported protocol_version {version!r}")

    core_gate_passed = all(check["passed"] for check in gate_checks.values())
    followups_required = bool(repeated_confusions or repository_defects or documentation_gaps)
    if not core_gate_passed:
        decision = "not_yet_validated"
    elif followups_required:
        decision = "validated_with_followups"
    else:
        decision = "validated"

    metrics: dict[str, Any] = {
        "participants_attempted": attempted,
        "completed_within_30_minutes": sum(
            1 for record in records if record["completed_within_30_minutes"]
        ),
        "entrypoint_found_without_help": sum(
            1 for record in records if record["entrypoint_found_without_help"]
        ),
        "first_replay_succeeded": sum(
            1 for record in records if record["first_replay_succeeded"]
        ),
        "custom_scenario_succeeded": custom_succeeded_count,
        "understood_rev1_rev2_rev3": sum(
            1 for record in records if record["understood_rev1_rev2_rev3"]
        ),
        "understood_unknown_not_false": sum(
            1 for record in records if record["understood_unknown_not_false"]
        ),
        "understood_bounded_impact": sum(
            1 for record in records if record["understood_bounded_impact"]
        ),
        "understood_eligible_not_executed": sum(
            1 for record in records if record["understood_eligible_not_executed"]
        ),
    }
    if version == "0.1":
        metrics["lifecycle_and_action_boundary"] = lifecycle_and_boundary_count
    else:
        metrics["product_activation_completed_within_15_minutes"] = sum(
            1
            for record in records
            if record["product_activation_completed_within_15_minutes"]
        )
        metrics["bounded_impact_and_action_boundary"] = bounded_and_boundary_count
        metrics["advanced_lifecycle_comprehension"] = sum(
            1 for record in records if record["understood_rev1_rev2_rev3"]
        )

    participant_summaries: list[dict[str, Any]] = []
    for record in records:
        item = {
            "participant_alias": record["participant_alias"],
            "duration_minutes": record["duration_minutes"],
            "completed_within_30_minutes": record["completed_within_30_minutes"],
            "entrypoint_found_without_help": record["entrypoint_found_without_help"],
            "first_replay_succeeded": record["first_replay_succeeded"],
            "custom_scenario_succeeded": record["custom_scenario_succeeded"],
            "understood_rev1_rev2_rev3": record["understood_rev1_rev2_rev3"],
            "understood_unknown_not_false": record["understood_unknown_not_false"],
            "understood_bounded_impact": record["understood_bounded_impact"],
            "understood_eligible_not_executed": record["understood_eligible_not_executed"],
            "help_event_count": len(record["help_events"]),
            "confusion_points": list(record["confusion_points"]),
            "documentation_gaps": list(record["documentation_gaps"]),
            "repository_defects": list(record["repository_defects"]),
            "participant_summary": record["participant_summary"],
            "observer_notes": record["observer_notes"],
        }
        if version == "0.2":
            item["product_activation_minutes"] = record["product_activation_minutes"]
            item["product_activation_completed_within_15_minutes"] = record[
                "product_activation_completed_within_15_minutes"
            ]
        participant_summaries.append(item)

    return {
        "developer_activation_report": {
            "schema_version": version,
            "protocol_version": version,
            "decision": decision,
            "automated_tests_count_as_external_participants": False,
            "participant_data_anonymized_by_alias": True,
            "gate_checks": gate_checks,
            "metrics": metrics,
            "repeated_confusion_points": repeated_confusions,
            "repository_defects": repository_defects,
            "documentation_gaps": documentation_gaps,
            "followups_required": followups_required,
            "participants": participant_summaries,
        }
    }


def render_markdown(report: dict[str, Any]) -> str:
    payload = report["developer_activation_report"]
    metrics = payload["metrics"]
    version = payload["protocol_version"]
    lines = [
        "# GeoTask P1 External Developer Activation Report",
        "",
        f"**Protocol:** v{version}",
        f"**Decision:** `{payload['decision']}`",
        "",
        "> This report aggregates anonymized real participant records. Automated tests, scripted demos, and implementation agents do not count as external participants.",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Gate checks", "", "| Gate | Passed | Actual | Required |", "|---|---|---:|---:|"])
    for key, check in payload["gate_checks"].items():
        lines.append(
            f"| `{key}` | {'yes' if check['passed'] else 'no'} | {check['actual']} | {check['required']} |"
        )

    if version == "0.1":
        lines.extend(
            [
                "",
                "## Participant results",
                "",
                "| Alias | Minutes | Fixed replay | Custom input | rev1→rev2→rev3 | eligible≠executed |",
                "|---|---:|---|---|---|---|",
            ]
        )
        for participant in payload["participants"]:
            lines.append(
                "| {alias} | {minutes:.2f} | {fixed} | {custom} | {lifecycle} | {boundary} |".format(
                    alias=participant["participant_alias"],
                    minutes=participant["duration_minutes"],
                    fixed="yes" if participant["first_replay_succeeded"] else "no",
                    custom="yes" if participant["custom_scenario_succeeded"] else "no",
                    lifecycle="yes" if participant["understood_rev1_rev2_rev3"] else "no",
                    boundary="yes" if participant["understood_eligible_not_executed"] else "no",
                )
            )
    else:
        lines.extend(
            [
                "",
                "## Participant results",
                "",
                "| Alias | Product min | ≤15m | Fixed replay | Custom input | Bounded impact | eligible≠executed | rev lifecycle (advanced) |",
                "|---|---:|---|---|---|---|---|---|",
            ]
        )
        for participant in payload["participants"]:
            lines.append(
                "| {alias} | {minutes:.2f} | {within15} | {fixed} | {custom} | {bounded} | {boundary} | {lifecycle} |".format(
                    alias=participant["participant_alias"],
                    minutes=participant["product_activation_minutes"],
                    within15="yes" if participant["product_activation_completed_within_15_minutes"] else "no",
                    fixed="yes" if participant["first_replay_succeeded"] else "no",
                    custom="yes" if participant["custom_scenario_succeeded"] else "no",
                    bounded="yes" if participant["understood_bounded_impact"] else "no",
                    boundary="yes" if participant["understood_eligible_not_executed"] else "no",
                    lifecycle="yes" if participant["understood_rev1_rev2_rev3"] else "no",
                )
            )

    lines.extend(["", "## Repeated friction points", ""])
    if payload["repeated_confusion_points"]:
        for item in payload["repeated_confusion_points"]:
            lines.append(f"- {item['point']} ({item['participant_count']} participants)")
    else:
        lines.append("- None recorded across two or more participants.")

    lines.extend(["", "## Repository defects", ""])
    if payload["repository_defects"]:
        for item in payload["repository_defects"]:
            lines.append(f"- `{item['participant_alias']}`: {item['defect']}")
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Documentation gaps", ""])
    if payload["documentation_gaps"]:
        for item in payload["documentation_gaps"]:
            lines.append(f"- `{item['participant_alias']}`: {item['gap']}")
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Interpretation", ""])
    if payload["decision"] == "validated":
        lines.append(
            "The external activation gate for this declared protocol version is satisfied with no recorded repository defect, repeated confusion point, or documentation gap requiring follow-up."
        )
    elif payload["decision"] == "validated_with_followups":
        lines.append(
            "The quantitative activation gate is satisfied, but repository defects, repeated confusion points, or documentation gaps remain and must be tracked as product follow-ups."
        )
    else:
        lines.append(
            "P1 external activation is not yet validated. The repository status must remain: **P1 implementation and developer materials complete; external developer activation validation pending.**"
        )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate real GeoTask P1 external developer activation records."
    )
    parser.add_argument("results", nargs="+", help="Participant YAML result files")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--output", help="Write output to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        records = [_load_record(Path(value)) for value in args.results]
        report = summarize(records)
    except ActivationRecordError as exc:
        print(f"developer_activation_invalid: {exc}", file=sys.stderr)
        return 1

    if args.format == "markdown":
        rendered = render_markdown(report)
    else:
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    decision = report["developer_activation_report"]["decision"]
    return 2 if decision == "not_yet_validated" else 0


if __name__ == "__main__":
    raise SystemExit(main())
