from pathlib import Path
import sys

import pytest


# TC1-Real is repository-local benchmark infrastructure, not geotask-core.
_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.measurement import (
        AcquisitionMeasurement,
        SourceProvenance,
        build_offline_record,
        sha256_bytes,
    )
    from benchmarks.tc1_real.source_profiles import (
        FAA_DDOF,
        FAA_UASFM,
        NOAA_HRRR,
        get_source_profile,
    )
finally:
    sys.path.remove(_ROOT)


def test_public_source_profiles_preserve_authorization_boundary():
    assert FAA_UASFM.can_authorize_real_action is False
    assert FAA_DDOF.can_authorize_real_action is False
    assert NOAA_HRRR.can_authorize_real_action is False
    assert "authorize" in FAA_UASFM.notes.lower()


def test_uasfm_profile_records_bounded_query_capability_without_promoting_endpoint():
    assert FAA_UASFM.spatial_reference == "EPSG:4326"
    assert set(FAA_UASFM.query_formats) >= {"json", "geojson", "pbf"}
    assert FAA_UASFM.observed_machine_endpoint is not None
    assert "FeatureServer/0" in FAA_UASFM.observed_machine_endpoint


def test_hrrr_profile_keeps_space_and_time_resolution_explicit():
    assert NOAA_HRRR.spatial_resolution_meters == 3000.0
    assert NOAA_HRRR.temporal_update_seconds == 3600


def test_ddof_profile_is_broad_download_not_claimed_as_query_service():
    assert FAA_DDOF.query_formats == ("zip-csv",)
    assert FAA_DDOF.observed_machine_endpoint.endswith("DAILY_DOF_CSV.ZIP")


def test_unknown_measurement_dimension_is_not_zero():
    measurement = AcquisitionMeasurement(
        request_count=1,
        bytes_transferred=2048,
        wall_clock_seconds=0.25,
    )

    assert measurement.monetary_cost is None
    assert measurement.human_preparation_seconds is None
    assert "monetary_cost" not in measurement.known_dimensions
    assert "bytes_transferred" in measurement.known_dimensions


def test_known_zero_remains_distinct_from_unknown():
    measurement = AcquisitionMeasurement(
        monetary_cost=0.0,
        request_count=1,
    )

    assert measurement.monetary_cost == 0.0
    assert "monetary_cost" in measurement.known_dimensions
    assert measurement.bytes_transferred is None


def test_negative_measurement_is_rejected():
    with pytest.raises(ValueError, match="bytes_transferred"):
        AcquisitionMeasurement(bytes_transferred=-1)


def test_payload_hash_is_exact_byte_binding():
    assert sha256_bytes(b"abc") != sha256_bytes(b"abc\n")
    assert len(sha256_bytes(b"abc")) == 64


def test_offline_record_binds_exact_payload_and_preserves_measurement():
    payload = b'{"features":[{"ceiling":100}]}'
    measurement = AcquisitionMeasurement(
        request_count=1,
        bytes_transferred=len(payload),
        wall_clock_seconds=0.1,
        monetary_cost=0.0,
    )

    record = build_offline_record(
        source_id=FAA_UASFM.source_id,
        source_family=FAA_UASFM.source_family,
        retrieval_timestamp="2026-08-18T10:00:00Z",
        source_url=FAA_UASFM.observed_machine_endpoint or "missing",
        payload=payload,
        measurement=measurement,
        fixture_path="fixtures/uasfm.json",
        request_parameters={"geometry": "bounded-test-geometry"},
        source_crs="EPSG:4326",
        source_units={"CEILING": "foot_agl"},
    )

    assert record.provenance.content_sha256 == sha256_bytes(payload)
    assert record.measurement.bytes_transferred == len(payload)
    assert record.provenance.request_parameters["geometry"] == "bounded-test-geometry"
    assert "content_sha256" in record.canonical_json()


def test_invalid_provenance_digest_is_rejected():
    with pytest.raises(ValueError, match="64-character"):
        SourceProvenance(
            source_id="source",
            source_family="family",
            retrieval_timestamp="2026-08-18T10:00:00Z",
            source_url="https://example.invalid/source",
            content_sha256="abc",
        )


def test_source_lookup_fails_closed_for_unknown_profile():
    assert get_source_profile("faa-uasfm") is FAA_UASFM
    with pytest.raises(KeyError, match="unknown TC1-Real source profile"):
        get_source_profile("unknown-source")
