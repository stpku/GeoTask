from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from benchmarks.tc1_real.spatial_planning.arcgis_acquisition import (
    build_numeric_in_where,
    build_spatial_query_url,
    build_table_query_url,
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
