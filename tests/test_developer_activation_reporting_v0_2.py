"""Tests for the P1 developer activation v0.2 gate and v0.1 separation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "summarize_developer_activation.py"
TEMPLATE_V02 = ROOT / "docs" / "reference" / "developer-activation-result-template-v0.2.yaml"


def _module():
    spec = importlib.util.spec_from_file_location("developer_activation_reporting_v02", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record_v02(alias: str, **overrides):
    record = {
        "schema_version": "0.2",
        "protocol_version": "0.2",
        "participant_alias": alias,
        "started_at": "2026-08-13T09:00:00+08:00",
        "product_activation_completed_at": "2026-08-13T09:12:00+08:00",
        "completed_at": "2026-08-13T09:25:00+08:00",
        "product_activation_completed_within_15_minutes": True,
        "completed_within_30_minutes": True,
        "entrypoint_found_without_help": True,
        "first_replay_succeeded": True,
        "custom_scenario_succeeded": True,
        "understood_bounded_impact": True,
        "understood_eligible_not_executed": True,
        "understood_rev1_rev2_rev3": False,
        "understood_unknown_not_false": True,
        "first_replay_failure_repository_defect": False,
        "repository_defects": [],
        "help_events": [],
        "confusion_points": [],
        "documentation_gaps": [],
        "participant_summary": "Completed Product Activation independently.",
        "observer_notes": "",
    }
    record.update(overrides)
    return record


def _write_v02(tmp_path: Path, alias: str, **overrides) -> Path:
    path = tmp_path / f"{alias}.yaml"
    path.write_text(
        yaml.safe_dump(_record_v02(alias, **overrides), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_v02_template_is_safe_unfilled_evidence() -> None:
    data = yaml.safe_load(TEMPLATE_V02.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.2"
    assert data["protocol_version"] == "0.2"
    assert data["product_activation_completed_within_15_minutes"] is False
    assert data["first_replay_succeeded"] is False
    assert data["custom_scenario_succeeded"] is False
    assert data["understood_bounded_impact"] is False
    assert data["understood_eligible_not_executed"] is False

    module = _module()
    with pytest.raises(module.ActivationRecordError, match="ISO-8601 timestamp"):
        module._load_record(TEMPLATE_V02)


def test_v02_three_clean_records_validate_without_lifecycle_exam(tmp_path: Path) -> None:
    module = _module()
    records = [module._load_record(_write_v02(tmp_path, f"tester-0{i}")) for i in range(1, 4)]
    report = module.summarize(records)["developer_activation_report"]

    assert report["protocol_version"] == "0.2"
    assert report["decision"] == "validated"
    assert report["metrics"]["understood_rev1_rev2_rev3"] == 0
    assert report["metrics"]["advanced_lifecycle_comprehension"] == 0
    assert "at_least_two_thirds_lifecycle_and_action_boundary" not in report["gate_checks"]
    assert report["gate_checks"]["at_least_two_thirds_bounded_impact_and_action_boundary"]["passed"] is True


def test_v02_two_thirds_requires_bounded_impact_and_boundary_on_same_participants(tmp_path: Path) -> None:
    module = _module()
    paths = [
        _write_v02(tmp_path, "tester-01", understood_eligible_not_executed=False),
        _write_v02(tmp_path, "tester-02", understood_bounded_impact=False),
        _write_v02(tmp_path, "tester-03"),
    ]
    report = module.summarize([module._load_record(path) for path in paths])[
        "developer_activation_report"
    ]

    assert report["decision"] == "not_yet_validated"
    assert report["gate_checks"]["at_least_two_thirds_bounded_impact_and_action_boundary"] == {
        "passed": False,
        "actual": 1,
        "required": 2,
    }


def test_v02_two_of_three_same_participant_pairs_pass(tmp_path: Path) -> None:
    module = _module()
    paths = [
        _write_v02(tmp_path, "tester-01"),
        _write_v02(tmp_path, "tester-02"),
        _write_v02(
            tmp_path,
            "tester-03",
            custom_scenario_succeeded=False,
            understood_bounded_impact=False,
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
    assert report["gate_checks"]["at_least_two_thirds_bounded_impact_and_action_boundary"] == {
        "passed": True,
        "actual": 2,
        "required": 2,
    }


def test_v02_fifteen_minute_target_is_metric_not_independent_gate(tmp_path: Path) -> None:
    module = _module()
    records = [
        module._load_record(
            _write_v02(
                tmp_path,
                f"tester-0{i}",
                product_activation_completed_at="2026-08-13T09:18:00+08:00",
                product_activation_completed_within_15_minutes=False,
            )
        )
        for i in range(1, 4)
    ]
    report = module.summarize(records)["developer_activation_report"]

    assert report["decision"] == "validated"
    assert report["metrics"]["product_activation_completed_within_15_minutes"] == 0
    assert all("15" not in key for key in report["gate_checks"])


def test_v02_product_activation_time_flag_is_derived(tmp_path: Path) -> None:
    module = _module()
    path = _write_v02(
        tmp_path,
        "tester-01",
        product_activation_completed_at="2026-08-13T09:18:00+08:00",
        product_activation_completed_within_15_minutes=True,
    )
    with pytest.raises(module.ActivationRecordError, match="product_activation_completed_within_15_minutes disagrees"):
        module._load_record(path)


def test_v02_product_activation_timestamp_must_be_inside_session(tmp_path: Path) -> None:
    module = _module()
    path = _write_v02(
        tmp_path,
        "tester-01",
        product_activation_completed_at="2026-08-13T09:27:00+08:00",
        product_activation_completed_within_15_minutes=False,
    )
    with pytest.raises(module.ActivationRecordError, match="must not follow completed_at"):
        module._load_record(path)


def test_mixed_v01_v02_records_fail_closed(tmp_path: Path) -> None:
    module = _module()
    v02 = module._load_record(_write_v02(tmp_path, "tester-02"))
    v01_path = tmp_path / "tester-01.yaml"
    v01_record = {
        "schema_version": "0.1",
        "protocol_version": "0.1",
        "participant_alias": "tester-01",
        "started_at": "2026-08-13T09:00:00+08:00",
        "completed_at": "2026-08-13T09:20:00+08:00",
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
        "participant_summary": "v0.1 historical record",
        "observer_notes": "",
    }
    v01_path.write_text(yaml.safe_dump(v01_record, sort_keys=False), encoding="utf-8")
    v01 = module._load_record(v01_path)

    with pytest.raises(module.ActivationRecordError, match="must not be mixed"):
        module.summarize([v01, v02])


def test_v02_markdown_exposes_product_and_advanced_metrics(tmp_path: Path) -> None:
    module = _module()
    records = [module._load_record(_write_v02(tmp_path, f"tester-0{i}")) for i in range(1, 4)]
    markdown = module.render_markdown(module.summarize(records))

    assert "**Protocol:** v0.2" in markdown
    assert "Product min" in markdown
    assert "Bounded impact" in markdown
    assert "rev lifecycle (advanced)" in markdown
