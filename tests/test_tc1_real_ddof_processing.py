from io import BytesIO
from pathlib import Path
import sys
import zipfile

import pytest


_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.ddof_processing import (
        extract_single_csv_from_zip,
        inspect_csv_fields,
        select_ddof_csv_context,
    )
    from benchmarks.tc1_real.source_profiles import FAA_DDOF
finally:
    sys.path.remove(_ROOT)


CSV_PAYLOAD = (
    "ID,LAT,LON,VERIFY,AGL\n"
    "a,33.4500,-112.0500,O,120\n"
    "b,33.4600,-112.0600,U,80\n"
    "c,34.0000,-113.0000,O,300\n"
).encode("cp1252")


def _zip_with_csv(name="DOF.CSV", payload=CSV_PAYLOAD):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return buffer.getvalue()


def test_ddof_profile_explicitly_records_broad_provider_and_limitations():
    assert FAA_DDOF.spatial_reference == "WGS84"
    assert FAA_DDOF.query_formats == ("zip-csv",)
    assert "broad file download" in FAA_DDOF.notes
    assert "does not purport to contain every obstruction" in FAA_DDOF.notes
    assert "unverified" in FAA_DDOF.notes.lower()


def test_extract_single_csv_from_zip_preserves_exact_member_bytes():
    member, payload = extract_single_csv_from_zip(_zip_with_csv())

    assert member == "DOF.CSV"
    assert payload == CSV_PAYLOAD


def test_zip_with_multiple_csv_members_fails_closed():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("one.csv", CSV_PAYLOAD)
        archive.writestr("two.csv", CSV_PAYLOAD)

    with pytest.raises(ValueError, match="exactly one CSV"):
        extract_single_csv_from_zip(buffer.getvalue())


def test_header_inspection_returns_exact_fields_without_semantic_guessing():
    assert inspect_csv_fields(CSV_PAYLOAD) == (
        "ID",
        "LAT",
        "LON",
        "VERIFY",
        "AGL",
    )


def test_bbox_selection_reduces_local_context_but_not_acquisition_claim():
    result = select_ddof_csv_context(
        CSV_PAYLOAD,
        bbox=(-112.10, 33.40, -112.00, 33.50),
        latitude_field="LAT",
        longitude_field="LON",
    )

    assert result.measurement.input_row_count == 3
    assert result.measurement.selected_row_count == 2
    assert result.measurement.row_reduction_ratio == pytest.approx(1 / 3)
    assert result.measurement.selected_serialized_bytes < len(CSV_PAYLOAD)
    assert result.measurement.byte_reduction_ratio > 0
    assert {row["ID"] for row in result.selected_rows} == {"a", "b"}


def test_verification_filter_can_keep_only_caller_declared_statuses():
    result = select_ddof_csv_context(
        CSV_PAYLOAD,
        bbox=(-112.10, 33.40, -112.00, 33.50),
        latitude_field="LAT",
        longitude_field="LON",
        verification_field="VERIFY",
        accepted_verification_values=("O",),
    )

    assert result.measurement.selected_row_count == 1
    assert result.selected_rows[0]["ID"] == "a"
    assert result.measurement.accepted_verification_values == ("O",)


def test_verification_values_require_explicit_field():
    with pytest.raises(ValueError, match="verification_field"):
        select_ddof_csv_context(
            CSV_PAYLOAD,
            bbox=(-112.10, 33.40, -112.00, 33.50),
            latitude_field="LAT",
            longitude_field="LON",
            accepted_verification_values=("O",),
        )


def test_missing_declared_field_fails_closed():
    with pytest.raises(ValueError, match="missing required fields"):
        select_ddof_csv_context(
            CSV_PAYLOAD,
            bbox=(-112.10, 33.40, -112.00, 33.50),
            latitude_field="LATDEC",
            longitude_field="LONDEC",
        )


def test_invalid_coordinate_fails_closed_instead_of_skipping_row():
    payload = (
        "ID,LAT,LON\n"
        "a,not-a-number,-112.05\n"
    ).encode("cp1252")

    with pytest.raises(ValueError, match="invalid decimal coordinates"):
        select_ddof_csv_context(
            payload,
            bbox=(-112.10, 33.40, -112.00, 33.50),
            latitude_field="LAT",
            longitude_field="LON",
        )
