from __future__ import annotations

import json
from pathlib import Path

import pytest

from geotask_core import cli
from geotask_core.reference_agent_activation import (
    REFERENCE_AGENT_BUNDLE_MANIFEST,
    ReferenceAgentActivationError,
    compute_reference_agent_bundle_manifest,
    materialize_reference_agent,
    replay_materialized_reference_agent,
    verify_reference_agent_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "reference_agent" / "facility_assessment_update"


def test_reference_agent_source_bundle_is_deterministic_and_complete() -> None:
    manifest = verify_reference_agent_bundle(SOURCE)
    body = manifest["reference_agent_bundle"]
    paths = {entry["path"] for entry in body["files"]}

    assert body["bundle_version"] == "0.1"
    assert body["file_count"] >= 10
    assert len(body["content_sha256"]) == 64
    assert {
        "README.md",
        "replay.py",
        "quality_benchmark.py",
        "quality_benchmark_v0_2.py",
        "request.txt",
        "task.yaml",
        "world_state_before.json",
        "scenarios/success.json",
        "scenarios/missing_evidence.json",
        "scenarios/conflicting_evidence.json",
        "scenarios/stale_evidence.json",
        "scenarios/contradicted.json",
    }.issubset(paths)


def test_materialize_reference_agent_writes_verified_self_contained_workspace(
    tmp_path: Path,
) -> None:
    target, source_manifest = materialize_reference_agent(tmp_path / "demo")

    assert target == (tmp_path / "demo").resolve()
    assert (target / "README.md").is_file()
    assert (target / "replay.py").is_file()
    assert (target / REFERENCE_AGENT_BUNDLE_MANIFEST).is_file()
    assert compute_reference_agent_bundle_manifest(target) == source_manifest
    assert json.loads(
        (target / REFERENCE_AGENT_BUNDLE_MANIFEST).read_text(encoding="utf-8")
    ) == source_manifest


def test_materialize_reference_agent_refuses_to_overwrite_existing_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "demo"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")

    with pytest.raises(ReferenceAgentActivationError, match="refusing to overwrite"):
        materialize_reference_agent(target)

    assert sentinel.read_text(encoding="utf-8") == "keep\n"


def test_materialized_success_is_eligible_but_never_authorized_or_executed(
    tmp_path: Path,
) -> None:
    target, _ = materialize_reference_agent(tmp_path / "demo")
    body = replay_materialized_reference_agent(target, scenario="success")["reference_agent"]
    decision = body["decision_assurance"]

    assert body["world_state_update"]["observation_state_revision"] == 2
    assert body["world_state_update"]["successor_revision"] == 3
    assert body["verification"]["state"] == "satisfied"
    assert body["control_evaluation"]["state"] == "satisfied"
    assert decision["report_update_eligible"] is True
    assert decision["production_write_performed"] is False
    assert decision["production_report_refreshed"] is False
    assert decision["action_authorized"] is False
    assert decision["action_executed"] is False


def test_materialized_custom_scenario_file_replays_without_invented_expected_result(
    tmp_path: Path,
) -> None:
    target, _ = materialize_reference_agent(tmp_path / "demo")
    payload = json.loads((target / "scenarios" / "success.json").read_text(encoding="utf-8"))
    scenario = payload["scenario"]
    scenario["id"] = "developer-60m"
    scenario["evidence"][0]["coordinates"] = [60, 0]
    scenario.pop("expected", None)
    custom = tmp_path / "developer-60m.json"
    custom.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    body = replay_materialized_reference_agent(
        target,
        scenario_path=custom,
    )["reference_agent"]
    decision = body["decision_assurance"]

    assert body["scenario"] == "developer-60m"
    assert body["verification"]["distance_m"] == 60.0
    assert body["world_state_update"]["observation_state_revision"] == 2
    assert body["world_state_update"]["successor_revision"] == 3
    assert decision["report_update_eligible"] is True
    assert decision["production_report_refreshed"] is False
    assert decision["action_authorized"] is False
    assert decision["action_executed"] is False

    with pytest.raises(ReferenceAgentActivationError, match="scenario file not found"):
        replay_materialized_reference_agent(
            target,
            scenario_path=tmp_path / "missing.json",
        )


def test_materialized_conflict_remains_fail_closed(tmp_path: Path) -> None:
    target, _ = materialize_reference_agent(tmp_path / "demo")
    body = replay_materialized_reference_agent(
        target,
        scenario="conflicting_evidence",
    )["reference_agent"]

    assert body["evidence"]["state"] == "conflicted"
    assert body["verification"]["state"] == "conflicted"
    assert body["control_evaluation"]["state"] == "unknown"
    assert body["decision_assurance"]["report_update_eligible"] is False
    assert body["decision_assurance"]["action_authorized"] is False
    assert body["decision_assurance"]["action_executed"] is False


def test_materialized_bundle_tamper_blocks_before_replay(tmp_path: Path) -> None:
    target, _ = materialize_reference_agent(tmp_path / "demo")
    task = target / "task.yaml"
    task.write_text(task.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    with pytest.raises(ReferenceAgentActivationError, match="SHA-256 manifest verification"):
        replay_materialized_reference_agent(target, scenario="success")


def test_cli_agent_demo_json_materializes_and_replays(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "cli-demo"
    report = cli.cmd_agent(
        [
            "demo",
            "--output",
            str(target),
            "--scenario",
            "success",
            "--format",
            "json",
        ]
    )
    rendered = json.loads(capsys.readouterr().out)
    body = rendered["reference_agent_activation"]

    assert rendered == report
    assert target.is_dir()
    assert body["replayed"] is True
    assert body["replay"]["report_update_eligible"] is True
    assert body["replay"]["production_write_performed"] is False
    assert body["replay"]["action_authorized"] is False
    assert body["replay"]["action_executed"] is False


def test_cli_agent_demo_existing_target_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "exists"
    target.mkdir()

    with pytest.raises(SystemExit) as exc:
        cli.cmd_agent(["demo", "--output", str(target)])

    assert exc.value.code == 1
    assert "refusing to overwrite" in capsys.readouterr().err


def test_build_hook_reference_agent_bundle_matches_canonical_source(tmp_path: Path) -> None:
    pytest.importorskip("setuptools", reason="build-backend dependency is not a Core runtime dependency")
    import geotask_build_support

    geotask_build_support._copy_reference_agent_bundle(ROOT, tmp_path)
    built = tmp_path / "geotask_core" / "reference_agent_demo"
    installed_manifest = json.loads(
        (built / REFERENCE_AGENT_BUNDLE_MANIFEST).read_text(encoding="utf-8")
    )

    assert installed_manifest == compute_reference_agent_bundle_manifest(SOURCE)
    assert installed_manifest == compute_reference_agent_bundle_manifest(built)
