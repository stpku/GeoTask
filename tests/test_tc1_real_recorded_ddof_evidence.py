from pathlib import Path
import json

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "benchmarks" / "tc1_real" / "fixtures" / "ddof_phx_20260818"
ACQUISITION_PATH = FIXTURE_DIR / "acquisition.record.json"
HEADER_PATH = FIXTURE_DIR / "header.json"
SUMMARY_PATH = FIXTURE_DIR / "summary.json"
PIN_PATH = FIXTURE_DIR / "source-pin.json"
SELECTION_PATH = FIXTURE_DIR / "selection.json"
SELECTION_SUMMARY_PATH = FIXTURE_DIR / "selection-summary.json"

ZIP_SHA256 = "5cb2d97cd07553f51ce09b88829ea397041fdcb2e9f4b1963079592eaf7bf57d"
CSV_SHA256 = "a01c47f57202305a39faf0b3c6bd44bb30428c2397312b2085006c012aba6f16"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_recorded_ddof_acquisition_is_broad_and_pinned():
    acquisition = _load(ACQUISITION_PATH)
    summary = _load(SUMMARY_PATH)
    pin = _load(PIN_PATH)

    assert acquisition["provenance"]["source_id"] == "faa-ddof"
    assert acquisition["provenance"]["source_crs"] == "WGS84"
    assert acquisition["provenance"]["content_sha256"] == ZIP_SHA256
    assert acquisition["measurement"]["request_count"] == 1
    assert acquisition["measurement"]["bytes_transferred"] == 20_518_681
    assert acquisition["measurement"]["monetary_cost"] is None
    assert "Broad DDOF ZIP acquisition" in acquisition["notes"]

    assert summary["zip_bytes"] == 20_518_681
    assert summary["zip_sha256"] == ZIP_SHA256
    assert summary["csv_bytes"] == 98_840_705
    assert summary["csv_row_count"] == 653_466
    assert summary["csv_sha256"] == CSV_SHA256
    assert summary["monetary_cost"] is None

    assert pin == {
        "csv_member": "DOF.CSV",
        "csv_sha256": CSV_SHA256,
        "zip_sha256": ZIP_SHA256,
    }


def test_recorded_header_uses_observed_fields_not_guessed_aliases():
    header = _load(HEADER_PATH)

    assert header["csv_member"] == "DOF.CSV"
    assert header["encoding"] == "cp1252"
    assert "LATDEC" in header["fields"]
    assert "LONDEC" in header["fields"]
    assert "VERIFIED STATUS" in header["fields"]
    assert "AGL" in header["fields"]
    assert "TYPE" in header["fields"]


def test_task_bounded_selection_is_bound_to_exact_pinned_csv():
    selection = _load(SELECTION_PATH)
    summary = _load(SELECTION_SUMMARY_PATH)

    assert selection["source_csv_sha256"] == CSV_SHA256
    assert summary["source_csv_sha256"] == CSV_SHA256
    assert summary["bbox"] == [-112.1, 33.4, -112.0, 33.5]
    assert summary["latitude_field"] == "LATDEC"
    assert summary["longitude_field"] == "LONDEC"
    assert summary["verification_field"] == "VERIFIED STATUS"
    assert summary["accepted_verification_values"] is None


def test_task_bounded_ddof_selection_reduces_downstream_context_not_network_acquisition():
    acquisition = _load(ACQUISITION_PATH)
    summary = _load(SELECTION_SUMMARY_PATH)

    assert acquisition["measurement"]["bytes_transferred"] == 20_518_681
    assert summary["input_csv_bytes"] == 98_840_705
    assert summary["input_row_count"] == 653_466
    assert summary["selected_row_count"] == 313
    assert summary["selected_serialized_bytes"] == 47_401
    assert summary["row_reduction_ratio"] == pytest.approx(0.9995210156304996)
    assert summary["byte_reduction_ratio"] == pytest.approx(0.9995204303732961)
    assert summary["processing_wall_clock_seconds"] > 0

    # The local selection ratio must never be reinterpreted as download savings.
    assert summary["selected_serialized_bytes"] < acquisition["measurement"]["bytes_transferred"]
    assert acquisition["measurement"]["bytes_transferred"] > 0


def test_recorded_selection_preserves_verified_and_unverified_source_rows():
    selection = _load(SELECTION_PATH)
    summary = _load(SELECTION_SUMMARY_PATH)
    rows = selection["selected_rows"]

    assert len(rows) == 313
    assert summary["verification_status_counts"] == {"O": 139, "U": 174}
    assert sum(summary["verification_status_counts"].values()) == 313
    assert {row["VERIFIED STATUS"] for row in rows} == {"O", "U"}

    # GeoTask has not silently decided that unverified source rows are false or
    # disposable. Their downstream handling remains an explicit task/domain rule.
    assert sum(row["VERIFIED STATUS"] == "U" for row in rows) == 174


def test_selected_rows_are_inside_declared_task_bbox():
    selection = _load(SELECTION_PATH)

    for row in selection["selected_rows"]:
        lat = float(row["LATDEC"])
        lon = float(row["LONDEC"])
        assert 33.4 <= lat <= 33.5
        assert -112.1 <= lon <= -112.0
