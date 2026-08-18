from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

import pytest


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.resolution_stress.experiment_spec import (
        ANALYSIS_CRS_WKID,
        FINE_GRID_HEIGHT,
        FINE_GRID_WIDTH,
        ROI_SIZE_METERS,
        SOURCE_CENTER_WGS84,
        SOURCE_EXPORT_INTERPOLATION,
    )
    from benchmarks.resolution_stress.usgs_acquisition import (
        build_export_image_metadata_url,
        frozen_roi_bbox_3857,
        lonlat_to_web_mercator,
    )
finally:
    sys.path.remove(_ROOT)


def test_frozen_roi_is_exactly_512_meters_square_in_analysis_crs() -> None:
    min_x, min_y, max_x, max_y = frozen_roi_bbox_3857()

    assert max_x - min_x == pytest.approx(ROI_SIZE_METERS)
    assert max_y - min_y == pytest.approx(ROI_SIZE_METERS)
    center_x, center_y = lonlat_to_web_mercator(*SOURCE_CENTER_WGS84)
    assert (min_x + max_x) / 2 == pytest.approx(center_x)
    assert (min_y + max_y) / 2 == pytest.approx(center_y)


def test_export_request_freezes_one_meter_grid_contract() -> None:
    url = build_export_image_metadata_url()
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.path.endswith("/3DEPElevation/ImageServer/exportImage")
    assert params["bboxSR"] == [str(ANALYSIS_CRS_WKID)]
    assert params["imageSR"] == [str(ANALYSIS_CRS_WKID)]
    assert params["size"] == [f"{FINE_GRID_WIDTH},{FINE_GRID_HEIGHT}"]
    assert params["format"] == ["tiff"]
    assert params["pixelType"] == ["F32"]
    assert params["interpolation"] == [SOURCE_EXPORT_INTERPOLATION]
    assert params["f"] == ["json"]

    bbox_values = tuple(float(value) for value in params["bbox"][0].split(","))
    assert bbox_values == pytest.approx(frozen_roi_bbox_3857(), abs=1e-6)
