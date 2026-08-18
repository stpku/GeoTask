from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(ROOT)
sys.path.insert(0, _ROOT)
try:
    from benchmarks.resolution_stress.experiment_spec import (
        CORRIDORS,
        ELEVATION_THRESHOLDS_METERS,
        FINE_GRID_HEIGHT,
        FINE_GRID_WIDTH,
        FINE_PIXEL_SIZE_METERS,
        RESOLUTION_LADDER_METERS,
        ROI_SIZE_METERS,
        SOURCE_CANDIDATE_ID,
        SOURCE_CENTER_WGS84,
        SOURCE_DISCOVERY_BBOX_WGS84,
    )
finally:
    sys.path.remove(_ROOT)


def test_source_selection_was_frozen_before_elevation_scoring() -> None:
    assert SOURCE_CANDIDATE_ID == "phoenix_south_mountain"
    assert SOURCE_DISCOVERY_BBOX_WGS84 == (-112.10, 33.32, -112.02, 33.38)
    assert SOURCE_CENTER_WGS84 == (-112.06, 33.35)


def test_resolution_ladder_is_nested_and_ends_at_fine_reference() -> None:
    assert RESOLUTION_LADDER_METERS == (32, 16, 8, 4, 1)
    assert RESOLUTION_LADDER_METERS[-1] == FINE_PIXEL_SIZE_METERS
    assert FINE_GRID_WIDTH == FINE_GRID_HEIGHT == ROI_SIZE_METERS == 512
    assert all(ROI_SIZE_METERS % resolution == 0 for resolution in RESOLUTION_LADDER_METERS)


def test_every_frozen_corridor_is_valid_and_inside_roi() -> None:
    assert len(CORRIDORS) == 6
    assert len({corridor.corridor_id for corridor in CORRIDORS}) == len(CORRIDORS)
    for corridor in CORRIDORS:
        assert 0 <= corridor.min_x < corridor.max_x <= ROI_SIZE_METERS
        assert 0 <= corridor.min_y < corridor.max_y <= ROI_SIZE_METERS
        assert corridor.width == 4 or corridor.height == 4


def test_threshold_matrix_is_predeclared_and_complete() -> None:
    assert ELEVATION_THRESHOLDS_METERS == (300, 350, 400, 450, 500, 550, 600, 650)
    assert tuple(sorted(set(ELEVATION_THRESHOLDS_METERS))) == ELEVATION_THRESHOLDS_METERS
