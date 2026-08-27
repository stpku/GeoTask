from pathlib import Path
import json
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "benchmarks" / "tc1_real" / "fixtures" / "uasfm_phx_20260818"
R0_DIR = ROOT / "benchmarks" / "tc1_real" / "fixtures" / "uasfm_phx_r0_regional_20260818"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.uasfm_real_comparison import compare_recorded_uasfm
finally:
    sys.path.remove(_ROOT)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _comparison():
    return compare_recorded_uasfm(
        task_summary=_load(TASK_DIR / "summary.json"),
        task_record=_load(TASK_DIR / "uasfm-phx.record.json"),
        r0_summary=_load(R0_DIR / "summary.json"),
        r0_record=_load(R0_DIR / "uasfm-phx-regional.record.json"),
    )


def test_recorded_uasfm_task_and_r0_are_comparable():
    result = _comparison()

    assert result.task_bbox == (-112.1, 33.4, -112.0, 33.5)
    assert result.r0_bbox == (-112.2, 33.3, -111.9, 33.6)
    assert result.task_feature_count == 124
    assert result.r0_feature_count == 516
    assert result.task_payload_bytes == 67529
    assert result.r0_payload_bytes == 280585


def test_task_bounded_uasfm_reduces_recorded_feature_and_payload_burden():
    result = _comparison()

    assert result.feature_reduction_ratio == pytest.approx(0.7596899224806202)
    assert result.byte_reduction_ratio == pytest.approx(0.7593278329205053)
    # This is only a single observed pair and is not a stable latency claim.
    assert result.observed_wall_clock_reduction_ratio == pytest.approx(
        0.5756559971798573
    )


def test_comparison_fails_if_requested_fields_change():
    task_summary = _load(TASK_DIR / "summary.json")
    task_record = _load(TASK_DIR / "uasfm-phx.record.json")
    r0_summary = _load(R0_DIR / "summary.json")
    r0_record = _load(R0_DIR / "uasfm-phx-regional.record.json")
    r0_record["provenance"]["request_parameters"]["out_fields"] = ["OBJECTID"]

    with pytest.raises(ValueError, match="out_fields"):
        compare_recorded_uasfm(
            task_summary=task_summary,
            task_record=task_record,
            r0_summary=r0_summary,
            r0_record=r0_record,
        )


def test_comparison_fails_if_r0_does_not_contain_task_bbox():
    task_summary = _load(TASK_DIR / "summary.json")
    task_record = _load(TASK_DIR / "uasfm-phx.record.json")
    r0_summary = _load(R0_DIR / "summary.json")
    r0_record = _load(R0_DIR / "uasfm-phx-regional.record.json")
    r0_summary["bbox"] = [-111.0, 34.0, -110.9, 34.1]

    with pytest.raises(ValueError, match="contain"):
        compare_recorded_uasfm(
            task_summary=task_summary,
            task_record=task_record,
            r0_summary=r0_summary,
            r0_record=r0_record,
        )
