from pathlib import Path
import hashlib
import json
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "benchmarks" / "tc1_real" / "fixtures" / "hrrr_phx_20260818"
TASK_GRIB = FIXTURE_DIR / "hrrr-task.grib2"
R0_GRIB = FIXTURE_DIR / "hrrr-r0-regional.grib2"
TASK_RECORD = FIXTURE_DIR / "hrrr-task.record.json"
R0_RECORD = FIXTURE_DIR / "hrrr-r0-regional.record.json"
SUMMARY = FIXTURE_DIR / "summary.json"
DIAGNOSTIC = FIXTURE_DIR / "diagnostic.json"

TASK_SHA256 = "bc0a27b7194b4079d3ed0b0c4afc4287f79c379ec86ffe2c766ef099d112f357"
R0_SHA256 = "5780d52a6ab74f10a5a46e983bb78f61d96e5a482028e4c547d6045528e1f7f3"

_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.hrrr_real_comparison import compare_recorded_hrrr
finally:
    sys.path.remove(_ROOT)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_recorded_hrrr_payloads_are_exact_grib2_bytes():
    task = TASK_GRIB.read_bytes()
    r0 = R0_GRIB.read_bytes()

    assert len(task) == 594
    assert len(r0) == 912
    assert task[:4] == b"GRIB" and task[7] == 2
    assert r0[:4] == b"GRIB" and r0[7] == 2
    assert hashlib.sha256(task).hexdigest() == TASK_SHA256
    assert hashlib.sha256(r0).hexdigest() == R0_SHA256


def test_task_and_r0_records_bind_same_run_valid_time_variables_and_levels():
    task = _load(TASK_RECORD)
    r0 = _load(R0_RECORD)

    for record, digest, size in (
        (task, TASK_SHA256, 594),
        (r0, R0_SHA256, 912),
    ):
        assert record["provenance"]["content_sha256"] == digest
        assert record["measurement"]["bytes_transferred"] == size
        assert record["measurement"]["request_count"] == 1
        assert record["measurement"]["monetary_cost"] is None
        assert record["provenance"]["source_effective_at"] == "2026-08-18T06:00:00Z"
        assert record["provenance"]["valid_from"] == "2026-08-18T10:00:00Z"
        assert record["provenance"]["valid_until"] == "2026-08-18T10:00:00Z"
        assert record["provenance"]["request_parameters"]["variables"] == [
            "UGRD",
            "VGRD",
            "VIS",
        ]
        assert record["provenance"]["request_parameters"]["levels"] == [
            "10_m_above_ground",
            "surface",
        ]


def test_recorded_hrrr_comparison_reduces_bytes_but_not_observed_latency():
    comparison = compare_recorded_hrrr(
        task_record=_load(TASK_RECORD),
        r0_record=_load(R0_RECORD),
    )

    assert comparison.task_bytes == 594
    assert comparison.r0_bytes == 912
    assert comparison.byte_reduction_ratio == pytest.approx(0.3486842105263158)
    assert comparison.run_time == "2026-08-18T06:00:00Z"
    assert comparison.valid_time == "2026-08-18T10:00:00Z"
    assert comparison.task_bbox == (-112.1, 33.4, -112.0, 33.5)
    assert comparison.r0_bbox == (-112.2, 33.3, -111.9, 33.6)

    # Negative result is intentionally preserved: the smaller payload was
    # slower in this single uncontrolled request pair.
    assert comparison.task_wall_clock_seconds == pytest.approx(0.7786113619999995)
    assert comparison.r0_wall_clock_seconds == pytest.approx(0.6329548490000008)
    assert comparison.observed_wall_clock_reduction_ratio < 0


def test_recorded_summary_and_diagnostic_agree_on_success():
    summary = _load(SUMMARY)
    diagnostic = _load(DIAGNOSTIC)

    assert diagnostic["status"] == "success"
    assert diagnostic["summary"] == summary
    assert summary["task_bytes"] == 594
    assert summary["r0_bytes"] == 912
    assert summary["byte_reduction_ratio"] == pytest.approx(0.3486842105263158)
    assert summary["task_sha256"] == TASK_SHA256
    assert summary["r0_sha256"] == R0_SHA256


def test_hrrr_comparison_fails_if_run_or_variables_change():
    task = _load(TASK_RECORD)
    r0 = _load(R0_RECORD)

    changed_run = json.loads(json.dumps(r0))
    changed_run["provenance"]["source_effective_at"] = "2026-08-18T07:00:00Z"
    with pytest.raises(ValueError, match="source_effective_at"):
        compare_recorded_hrrr(task_record=task, r0_record=changed_run)

    changed_vars = json.loads(json.dumps(r0))
    changed_vars["provenance"]["request_parameters"]["variables"] = ["UGRD"]
    with pytest.raises(ValueError, match="variables"):
        compare_recorded_hrrr(task_record=task, r0_record=changed_vars)
