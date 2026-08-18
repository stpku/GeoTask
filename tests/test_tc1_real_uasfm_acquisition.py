from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest


_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.uasfm_acquisition import (
        DEFAULT_OUT_FIELDS,
        build_uasfm_query_url,
    )
finally:
    sys.path.remove(_ROOT)


def _query(url: str):
    return parse_qs(urlparse(url).query)


def test_uasfm_query_is_bounded_envelope_geojson():
    url = build_uasfm_query_url(
        bbox=(-112.10, 33.40, -112.00, 33.50),
    )
    query = _query(url)

    assert url.startswith("https://")
    assert url.endswith("f=geojson")
    assert query["geometry"] == ["-112.1,33.4,-112,33.5"]
    assert query["geometryType"] == ["esriGeometryEnvelope"]
    assert query["inSR"] == ["4326"]
    assert query["outSR"] == ["4326"]
    assert query["spatialRel"] == ["esriSpatialRelIntersects"]
    assert query["returnGeometry"] == ["true"]
    assert set(query["outFields"][0].split(",")) == set(DEFAULT_OUT_FIELDS)


def test_uasfm_query_can_omit_geometry_but_keeps_bounded_spatial_filter():
    url = build_uasfm_query_url(
        bbox=(-112.10, 33.40, -112.00, 33.50),
        return_geometry=False,
    )
    query = _query(url)

    assert query["returnGeometry"] == ["false"]
    assert "geometry" in query


def test_invalid_bbox_fails_before_network_request():
    with pytest.raises(ValueError, match="minimums"):
        build_uasfm_query_url(bbox=(-112.0, 33.5, -112.1, 33.4))

    with pytest.raises(ValueError, match="longitude"):
        build_uasfm_query_url(bbox=(-200.0, 33.4, -112.0, 33.5))


def test_non_https_endpoint_is_rejected():
    with pytest.raises(ValueError, match="https"):
        build_uasfm_query_url(
            bbox=(-112.10, 33.40, -112.00, 33.50),
            endpoint="http://example.invalid/FeatureServer/0",
        )
