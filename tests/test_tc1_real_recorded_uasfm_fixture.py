from pathlib import Path
import hashlib
import json


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "benchmarks" / "tc1_real" / "fixtures" / "uasfm_phx_20260818"
PAYLOAD_PATH = FIXTURE_DIR / "uasfm-phx.geojson"
RECORD_PATH = FIXTURE_DIR / "uasfm-phx.record.json"
SUMMARY_PATH = FIXTURE_DIR / "summary.json"
EXPECTED_SHA256 = "e9cf9402fb7c2fd583d04de5700e0bf7ac67bdda4a8d17a486105ea02470df05"
EXPECTED_BYTES = 67529
EXPECTED_FEATURES = 124


def test_recorded_uasfm_fixture_has_exact_acquisition_hash_and_size():
    payload = PAYLOAD_PATH.read_bytes()

    assert len(payload) == EXPECTED_BYTES
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA256


def test_record_and_summary_bind_the_same_exact_payload():
    payload = PAYLOAD_PATH.read_bytes()
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    assert record["provenance"]["content_sha256"] == EXPECTED_SHA256
    assert record["measurement"]["bytes_transferred"] == EXPECTED_BYTES
    assert record["measurement"]["request_count"] == 1
    assert record["measurement"]["monetary_cost"] == 0.0
    assert record["notes"].endswith("does not represent FAA flight authorization.")

    assert summary["sha256"] == EXPECTED_SHA256
    assert summary["payload_bytes"] == EXPECTED_BYTES
    assert summary["feature_count"] == EXPECTED_FEATURES
    assert summary["bbox"] == [-112.1, 33.4, -112.0, 33.5]
    assert hashlib.sha256(payload).hexdigest() == summary["sha256"]


def test_m1_activation_condition_is_satisfied_by_recorded_fixture():
    document = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    features = document["features"]

    assert document["type"] == "FeatureCollection"
    assert document["crs"]["properties"]["name"] == "EPSG:4326"
    assert len(features) == EXPECTED_FEATURES
    assert all(feature["geometry"]["type"] == "Polygon" for feature in features)
    assert any(feature["properties"].get("APT1_ICAO") == "KPHX" for feature in features)
    assert any(feature["properties"].get("AIRSPACE_1") == "B" for feature in features)
    assert {feature["properties"].get("UNIT") for feature in features} == {"Feet"}


def test_recorded_uasfm_ceiling_values_remain_source_data_not_authorization():
    document = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    ceilings = {
        feature["properties"].get("CEILING")
        for feature in document["features"]
    }

    # This asserts only that the recorded source contains multiple grid values.
    # It intentionally does not translate any CEILING into operational approval.
    assert len(ceilings) > 1
    assert 0 in ceilings
