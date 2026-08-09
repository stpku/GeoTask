"""Tests for the P1 real external developer activation reporting gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "summarize_developer_activation.py"
TEMPLATE = ROOT / "docs" / "reference" / "developer-activation-result-template.yaml"


def _module():
    spec = importlib.util.spec_from_file_location("developer_activation_reporting", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(alias: str, **overrides):
    record = {
        "schema_version": "0.1",
        "protocol_version": "0.1",
        "participant_alias": alias,
        "started_at": "2026-08-09T09:00:00+08:00",
        "completed_at": "2026-08-09T09:20:00+08:00",
        "completed_within_30_minutes": True,
        "entrypoint_found_without_help": True,
        "first_replay_succeeded": True,
        "custom_scenario_succeeded": True,
        "understood_rev1_rev2_rev3": True,
        "understood_unknown_not_false": True,
        "understood_bounded_impact": True,
        "understood_eligible_not_executed": True,
        "first_replay_failure_repository_defect": False,
        "repository_defects": [],
        "help_events": [],
        "confusion_points": [],
        "documentation_gaps": [],
        "participant_summary": "Completed independently.",
        "observer_notes": "",
    }
    record.update(overrides)
    return record


def _write(tmp_path: Path, alias: str, **overrides) -> Path:
    path = tmp_path / f"{alias}.yaml"
    path.write_text(
        yaml.safe_dump(_record(alias, **overrides), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_template_is_safe_unfilled_evidence_not_a_passing_result() -> None:
    data = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1"
    assert data["protocol_version"] == "0.1"
    assert data["completed_within_30_minutes"] is False
    assert data["first_replay_succeeded"] is False
    assert data["custom_scenario_succeeded"] is False
    assert data["understood_eligible_not_executed"] is False
    assert data["repository_defects"] == []

    module = _module()
    with pytest.raises(module.ActivationRecordError, match="ISO-8601 timestamp"):
        module._load_record(TEMPLATE)


def test_three_clean_real_records_satisfy_initial_gate(tmp_path: Path) -> None:
    module = _module()
    records = [module._load_record(_write(tmp_path, f"tester-0{i}")) for i in range(1, 4)]
    report = module.summarize(records)["developer_activation_report"]

    assert report["decision"] == "validated"
    assert report["metrics"]["participants_attempted"] == 3
    assert all(check["passed"] for check in report["gate_checks"].values())
    assert report["automated_tests_count_as_external_participants"] is False
    assert report["followups_required"] is False


def test_fewer_than_three_records_fail_closed(tmp_path: Path) -> None:
    module = _module()
    records = [module._load_record(_write(tmp_path, f"tester-0{i}")) for i in range(1, 3)]
    report = module.summarize(records)["developer_activation_report"]

    assert report["decision"] == "not_yet_validated"
    gate = report["gate_checks"]["minimum_three_unfamiliar_participants"]
    assert gate == {"passed": False, "actual": 2, "required": 3}


def test_two_thirds_threshold_is_applied_to_same_participant_lifecycle_and_boundary(
    tmp_path: Path,
) -> None:
    module = _module()
    paths = [
        _write(tmp_path, "tester-01"),
        _write(tmp_path, "tester-02"),
        _write(
            tmp_path,
            "tester-03",
            custom_scenario_succeeded=False,
            understood_rev1_rev2_rev3=False,
            understood_eligible_not_executed=False,
        ),
    ]
    report = module.summarize([module._load_record(path) for path in paths])[
        "developer_activation_report"
    ]

    assert report["decision"] == "validated"
    assert report["gate_checks"]["at_least_two_thirds_custom_scenario"] == {
        "passed": True,
        "actual": 2,
        "required": 2,
    }
    assert report["gate_checks"][
        "at_least_two_thirds_lifecycle_and_action_boundary"
    ] == {"passed": True, "actual": 2, "required": 2}


def test_repeated_confusion_preserves_metrics_but_requires_followup(tmp_path: Path) -> None:
    module = _module()
    paths = [
        _write(tmp_path, "tester-01", confusion_points=["Could not find the custom input command"]),
        _write(tmp_path, "tester-02", confusion_points=["Could not find the custom input command"]),
        _write(tmp_path, "tester-03"),
    ]
    report = module.summarize([module._load_record(path) for path in paths])[
        "developer_activation_report"
    ]

    assert report["decision"] == "validated_with_followups"
    assert report["followups_required"] is True
    assert report["repeated_confusion_points"] == [
        {
            "point": "Could not find the custom input command",
            "participant_count": 2,
        }
    ]


def test_documented_repository_defect_can_satisfy_fixed_replay_gate_only_with_evidence(
    tmp_path: Path,
) -> None:
    module = _module()
    paths = [
        _write(
            tmp_path,
            "tester-01",
            first_replay_succeeded=False,
            first_replay_failure_repository_defect=True,
            repository_defects=["Quickstart command references a missing fixture."],
        ),
        _write(tmp_path, "tester-02"),
        _write(tmp_path, "tester-03"),
    ]
    report = module.summarize([module._load_record(path) for path in paths])[
        "developer_activation_report"
    ]

    assert report["gate_checks"][
        "fixed_reference_agent_runnable_or_repository_defect_documented"
    ]["passed"] is True
    assert report["decision"] == "validated_with_followups"
    assert report["repository_defects"][0]["participant_alias"] == "tester-01"


def test_timebox_flag_is_derived_and_cannot_disagree_with_timestamps(tmp_path: Path) -> None:
    module = _module()
    path = _write(
        tmp_path,
        "tester-01",
        completed_at="2026-08-09T09:45:00+08:00",
        completed_within_30_minutes=True,
    )

    with pytest.raises(module.ActivationRecordError, match="disagrees with timestamps"):
        module._load_record(path)


def test_duplicate_aliases_are_rejected(tmp_path: Path) -> None:
    module = _module()
    first = module._load_record(_write(tmp_path, "tester-01"))
    second_path = tmp_path / "other.yaml"
    second_path.write_text(
        yaml.safe_dump(_record("tester-01"), sort_keys=False), encoding="utf-8"
    )
    second = module._load_record(second_path)

    with pytest.raises(module.ActivationRecordError, match="must be unique"):
        module.summarize([first, second])


def test_markdown_keeps_pending_status_when_gate_not_closed(tmp_path: Path) -> None:
    module = _module()
    record = module._load_record(_write(tmp_path, "tester-01"))
    report = module.summarize([record])
    markdown = module.render_markdown(report)

    assert "**Decision:** `not_yet_validated`" in markdown
    assert "external developer activation validation pending" in markdown
