from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from benchmarks.tc1_real.spatial_planning.arcgis_acquisition import (
    build_numeric_in_where,
    build_object_ids_query_url,
    build_spatial_ids_query_url,
    build_spatial_query_url,
    build_table_ids_query_url,
    build_table_query_url,
    chunk_object_ids,
    extract_object_ids,
    normalize_bbox,
)
from benchmarks.tc1_real.spatial_planning.source_profiles import (
    PHX_LAND_USE_ZONES,
    PHX_LIBRARIES,
)


def test_spatial_query_is_bounded_and_explicit() -> None:
    url = build_spatial_query_url(
        layer_endpoint="https://example.test/FeatureServer/2",
        bbox=(-112.1, 33.4, -112.0, 33.5),
        out_fields=("objectid", "newluau"),
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.path.endswith("/FeatureServer/2/query")
    assert params["geometry"] == ["-112.1,33.4,-112.0,33.5"]
    assert params["geometryType"] == ["esriGeometryEnvelope"]
    assert params["inSR"] == ["4326"]
    assert params["outSR"] == ["4326"]
    assert params["outFields"] == ["objectid,newluau"]
    assert params["f"] == ["geojson"]


def test_json_only_provider_can_use_same_bounded_scope_contract() -> None:
    url = build_spatial_query_url(
        layer_endpoint="https://example.test/FeatureServer/14",
        bbox=(-112.075, 33.425, -112.050, 33.450),
        out_fields=("*",),
        output_format="json",
    )
    params = parse_qs(urlparse(url).query)
    assert params["geometry"] == ["-112.075,33.425,-112.05,33.45"]
    assert params["f"] == ["json"]
    assert PHX_LAND_USE_ZONES.query_formats == ("json",)
    assert "geojson" in PHX_LIBRARIES.query_formats


def test_ids_first_spatial_query_preserves_same_scope() -> None:
    url = build_spatial_ids_query_url(
        layer_endpoint="https://example.test/FeatureServer/2",
        bbox=(-112.1, 33.4, -112.0, 33.5),
    )
    params = parse_qs(urlparse(url).query)
    assert params["geometry"] == ["-112.1,33.4,-112.0,33.5"]
    assert params["returnIdsOnly"] == ["true"]
    assert params["f"] == ["json"]
    assert "outFields" not in params


def test_ids_first_table_query_preserves_where() -> None:
    url = build_table_ids_query_url(
        table_endpoint="https://example.test/FeatureServer/13",
        where="newluau IN (3,7)",
    )
    params = parse_qs(urlparse(url).query)
    assert params["where"] == ["newluau IN (3,7)"]
    assert params["returnIdsOnly"] == ["true"]


def test_object_ids_are_sorted_deduplicated_and_chunked() -> None:
    chunks = chunk_object_ids((5, 3, 5, 2, 9), chunk_size=2)
    assert chunks == ((2, 3), (5, 9))

    url = build_object_ids_query_url(
        layer_endpoint="https://example.test/FeatureServer/2",
        object_ids=(9, 2, 5),
        out_fields=("objectid", "newluau"),
        return_geometry=True,
        output_format="geojson",
    )
    params = parse_qs(urlparse(url).query)
    assert params["objectIds"] == ["2,5,9"]
    assert params["returnGeometry"] == ["true"]
    assert params["outSR"] == ["4326"]


def test_extract_object_ids_fails_closed_and_deduplicates() -> None:
    assert extract_object_ids(json.dumps({"objectIds": [3, 1, 3]}).encode()) == (1, 3)
    with pytest.raises(ValueError, match="no objectIds"):
        extract_object_ids(b'{"features": []}')
    with pytest.raises(ValueError, match="successful"):
        extract_object_ids(b'{"error": {"code": 400}}')
    with pytest.raises(ValueError, match="at least one"):
        extract_object_ids(b'{"objectIds": []}')


def test_numeric_in_where_is_sorted_deduplicated_and_injection_safe() -> None:
    assert build_numeric_in_where("newluau", (7, 3, 7)) == "newluau IN (3,7)"
    with pytest.raises(ValueError, match="unsafe ArcGIS field"):
        build_numeric_in_where("newluau);DROP", (1,))
    with pytest.raises(ValueError, match="at least one"):
        build_numeric_in_where("newluau", ())


def test_table_query_has_no_geometry_and_preserves_where() -> None:
    url = build_table_query_url(
        table_endpoint="https://example.test/FeatureServer/13",
        out_fields=("newluau", "year", "popcount"),
        where="newluau IN (3,7)",
    )
    params = parse_qs(urlparse(url).query)
    assert params["where"] == ["newluau IN (3,7)"]
    assert params["outFields"] == ["newluau,year,popcount"]
    assert params["returnGeometry"] == ["false"]
    assert params["f"] == ["json"]


def test_bbox_and_field_validation_fail_closed() -> None:
    with pytest.raises(ValueError, match="minimums"):
        normalize_bbox((-112.0, 33.5, -112.1, 33.4))
    with pytest.raises(ValueError, match="unsafe ArcGIS field"):
        build_spatial_query_url(
            layer_endpoint="https://example.test/FeatureServer/2",
            bbox=(-112.1, 33.4, -112.0, 33.5),
            out_fields=("objectid&f=pjson",),
        )
    with pytest.raises(ValueError, match="https"):
        build_spatial_query_url(
            layer_endpoint="http://example.test/FeatureServer/2",
            bbox=(-112.1, 33.4, -112.0, 33.5),
            out_fields=("objectid",),
        )
    with pytest.raises(ValueError, match="geometry-free"):
        build_object_ids_query_url(
            layer_endpoint="https://example.test/FeatureServer/13",
            object_ids=(1,),
            out_fields=("objectid",),
            return_geometry=False,
            output_format="geojson",
        )
