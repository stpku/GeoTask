"""Frozen inputs for the temporal Sufficiency-Guided Refinement proof.

All task thresholds and refinement rules are fixed before the hourly forecast is
acquired.  The benchmark is a fictional outdoor field-inspection scheduling
task, not a real safety or authorization standard.
"""

from __future__ import annotations


SOURCE_FAMILY = "NOAA/NWS hourly point forecast"
SOURCE_POINT_LATITUDE = 33.35
SOURCE_POINT_LONGITUDE = -112.06
SOURCE_UNITS = "si"
SOURCE_FEATURE_FLAGS = ("forecast_wind_speed_qv",)

# The first 24 future hourly periods returned by the discovered NWS
# ``forecastHourly`` endpoint are pinned as one fine temporal reference.  They
# are split into two independent 12-hour task windows after acquisition.
FINE_PERIOD_HOURS = 1
FINE_PERIOD_COUNT = 24
TASK_WINDOW_HOURS = 12
TASK_WINDOW_COUNT = 2
TEMPORAL_LADDER_HOURS = (12, 6, 3, 1)

# Fictional benchmark thresholds, frozen before reading the forecast values.
# The source contract is requested in SI units and live acquisition must verify
# the returned wind-speed unit before fixture admission.
WIND_THRESHOLDS_KMH = (10.0, 20.0, 30.0, 40.0)
PRECIP_PROBABILITY_THRESHOLDS_PERCENT = (10.0, 30.0, 50.0, 70.0)

# A one-hour slot is usable when BOTH conditions hold at that hour.
TASK_ACTION_AVAILABLE = "STOP_AVAILABLE"
TASK_ACTION_UNAVAILABLE = "STOP_UNAVAILABLE"
TASK_ACTION_REFINE = "REFINE"

# Coarse temporal representation carries min/max for each criterion.  It is
# intentionally conservative: it only declares AVAILABLE when every hour in one
# represented block is usable, and UNAVAILABLE when one criterion proves every
# hour in every represented block unusable.  Otherwise it refines ambiguous
# time blocks.
COARSE_REPRESENTATION_FIELDS = (
    "wind_min_kmh",
    "wind_max_kmh",
    "precip_min_percent",
    "precip_max_percent",
)
