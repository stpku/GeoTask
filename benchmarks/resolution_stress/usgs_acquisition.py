"""Reproducible USGS 3DEP fine-reference acquisition helpers.

The helper only constructs a pinned benchmark request. Network access remains a
one-shot acquisition concern and is excluded from normal CI.
"""

from __future__ import annotations

from math import log, pi, radians, tan
from urllib.parse import urlencode

from benchmarks.resolution_stress.experiment_spec import (
    ANALYSIS_CRS_WKID,
    FINE_GRID_HEIGHT,
    FINE_GRID_WIDTH,
    ROI_SIZE_METERS,
    SOURCE_CENTER_WGS84,
    SOURCE_EXPORT_FORMAT,
    SOURCE_EXPORT_INTERPOLATION,
    SOURCE_EXPORT_PIXEL_TYPE,
    SOURCE_SERVICE,
)


WEB_MERCATOR_RADIUS = 6378137.0
MAX_WEB_MERCATOR_LATITUDE = 85.0511287798066


def lonlat_to_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Project WGS84 longitude/latitude to spherical Web Mercator meters."""

    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be within [-180, 180]")
    if not -MAX_WEB_MERCATOR_LATITUDE <= lat <= MAX_WEB_MERCATOR_LATITUDE:
        raise ValueError("latitude is outside Web Mercator domain")
    x = WEB_MERCATOR_RADIUS * radians(lon)
    y = WEB_MERCATOR_RADIUS * log(tan(pi / 4.0 + radians(lat) / 2.0))
    return x, y


def frozen_roi_bbox_3857() -> tuple[float, float, float, float]:
    center_x, center_y = lonlat_to_web_mercator(*SOURCE_CENTER_WGS84)
    half = ROI_SIZE_METERS / 2.0
    return (
        center_x - half,
        center_y - half,
        center_x + half,
        center_y + half,
    )


def build_export_image_metadata_url() -> str:
    """Build the exact ArcGIS exportImage metadata request for the fine fixture."""

    bbox = frozen_roi_bbox_3857()
    params = {
        "bbox": ",".join(f"{value:.6f}" for value in bbox),
        "bboxSR": str(ANALYSIS_CRS_WKID),
        "size": f"{FINE_GRID_WIDTH},{FINE_GRID_HEIGHT}",
        "imageSR": str(ANALYSIS_CRS_WKID),
        "format": SOURCE_EXPORT_FORMAT,
        "pixelType": SOURCE_EXPORT_PIXEL_TYPE,
        "interpolation": SOURCE_EXPORT_INTERPOLATION,
        "f": "json",
    }
    return SOURCE_SERVICE.rstrip("/") + "/exportImage?" + urlencode(params)
