"""Frozen inputs for the first real Task Context Resolution Stress Test.

Source discovery inspected only USGS product metadata, not elevation values.
These inputs are therefore fixed before the fine-resolution terrain is read.
The experiment is a fictional terrain-context screening benchmark, not a flight
safety or authorization decision.
"""

from __future__ import annotations

from dataclasses import dataclass


SOURCE_FAMILY = "USGS 3DEP Bare Earth Elevation"
SOURCE_SERVICE = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer"
)
SOURCE_DISCOVERY_DATASET = "Digital Elevation Model (DEM) 1 meter"
SOURCE_EXPORT_FORMAT = "tiff"
SOURCE_EXPORT_PIXEL_TYPE = "F32"
SOURCE_EXPORT_INTERPOLATION = "RSP_NearestNeighbor"

# First Phoenix candidate in the predeclared rugged-area discovery list with
# non-empty 1-meter product coverage. Selection occurred without inspecting
# elevation pixels or any coarse/fine benchmark result.
SOURCE_CANDIDATE_ID = "phoenix_south_mountain"
SOURCE_DISCOVERY_BBOX_WGS84 = (-112.10, 33.32, -112.02, 33.38)
SOURCE_CENTER_WGS84 = (
    (SOURCE_DISCOVERY_BBOX_WGS84[0] + SOURCE_DISCOVERY_BBOX_WGS84[2]) / 2,
    (SOURCE_DISCOVERY_BBOX_WGS84[1] + SOURCE_DISCOVERY_BBOX_WGS84[3]) / 2,
)

# A 512 m square around the mechanically derived discovery-bbox center. The
# export is requested in EPSG:3857 at 512x512 pixels, giving a nominal 1 m
# benchmark reference grid when the service honors the requested image size.
# Live acquisition must verify returned raster dimensions/transform before the
# fixture is admitted.
ANALYSIS_CRS = "EPSG:3857"
ANALYSIS_CRS_WKID = 3857
ROI_SIZE_METERS = 512
FINE_PIXEL_SIZE_METERS = 1
FINE_GRID_WIDTH = 512
FINE_GRID_HEIGHT = 512

# Powers-of-two make local deterministic aggregation exact and avoid partial
# source blocks at the fixed ROI boundary. This is an experiment design choice,
# not a GeoTask product recommendation.
RESOLUTION_LADDER_METERS = (32, 16, 8, 4, 1)

# Absolute bare-earth elevation thresholds are experiment inputs. Every
# threshold/corridor combination is reported; the benchmark must not select only
# combinations that happen to exhibit an attractive resolution flip.
ELEVATION_THRESHOLDS_METERS = (300, 350, 400, 450, 500, 550, 600, 650)


@dataclass(frozen=True)
class CorridorRect:
    corridor_id: str
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    @property
    def width(self) -> int:
        return self.max_x - self.min_x

    @property
    def height(self) -> int:
        return self.max_y - self.min_y


# Local coordinates are meters/pixels from the southwest/lower-left benchmark
# ROI origin after the acquired raster is normalized into benchmark row/column
# orientation. Corridors are narrow (4 m) so coarse cells may legitimately
# include off-corridor terrain, creating a conservative ambiguity without using
# a deliberately lossy mean statistic.
CORRIDORS = (
    CorridorRect("horizontal_center", 32, 254, 480, 258),
    CorridorRect("vertical_center", 254, 32, 258, 480),
    CorridorRect("horizontal_north", 32, 382, 480, 386),
    CorridorRect("horizontal_south", 32, 126, 480, 130),
    CorridorRect("vertical_west", 126, 32, 130, 480),
    CorridorRect("vertical_east", 382, 32, 386, 480),
)

NEXT_ACTIONS = ("STOP_CLEAR", "STOP_BLOCKED", "REFINE")
