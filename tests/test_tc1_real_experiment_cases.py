from pathlib import Path
import sys


_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
try:
    from benchmarks.tc1_real.experiment_cases import (
        EXPERIMENT_SPATIAL_SCOPE,
        PHX_EXPERIMENT_BBOX,
        get_tc1_real_case,
        tc1_real_cases,
    )
finally:
    sys.path.remove(_ROOT)


def test_tc1_real_freezes_four_distinct_stress_cases():
    cases = tc1_real_cases()

    assert tuple(case.case_id for case in cases) == (
        "M1-controlled-airspace-context",
        "M2-local-obstacle-selection",
        "M3-weather-temporal-mismatch",
        "M4-unnecessary-weather-breadth",
    )
    assert len({case.expected_stress for case in cases}) == 4


def test_reference_requirements_are_independent_and_same_across_initial_cases():
    cases = tc1_real_cases()
    expected = (
        "airspace_guidance",
        "obstacle_context",
        "weather_wind",
        "weather_visibility",
    )

    for case in cases:
        assert case.headline_requirement_ids == expected
        assert all(
            item.grading_state == "accepted"
            for item in case.reference_requirements
        )
        assert all(item.basis for item in case.reference_requirements)


def test_reference_requirements_preserve_source_limitations():
    case = get_tc1_real_case("M1-controlled-airspace-context")
    obstacle = next(
        item
        for item in case.reference_requirements
        if item.requirement.requirement_id == "obstacle_context"
    )
    airspace = next(
        item
        for item in case.reference_requirements
        if item.requirement.requirement_id == "airspace_guidance"
    )

    assert "not exhaustive" in obstacle.notes
    assert "not authorization" in airspace.requirement.reason


def test_weather_requirements_are_explicitly_spatiotemporal():
    case = get_tc1_real_case("M3-weather-temporal-mismatch")
    weather = [
        item.requirement
        for item in case.reference_requirements
        if item.requirement.requirement_id.startswith("weather_")
    ]

    assert len(weather) == 2
    for requirement in weather:
        assert requirement.spatial_scope == EXPERIMENT_SPATIAL_SCOPE
        assert requirement.temporal_scope == "recorded-experiment-window"
        assert requirement.max_spatial_resolution == 3000.0
        assert requirement.spatial_resolution_unit == "meter"
        assert requirement.max_temporal_resolution_seconds == 3600.0


def test_m1_requires_recorded_intersection_before_headline_grading():
    case = get_tc1_real_case("M1-controlled-airspace-context")

    assert tuple(case.metadata["bbox"]) == PHX_EXPERIMENT_BBOX
    assert "must contain at least one feature" in case.metadata["activation_condition"]


def test_unknown_case_fails_closed():
    try:
        get_tc1_real_case("unknown")
    except KeyError as exc:
        assert "unknown TC1-Real case" in str(exc)
    else:
        raise AssertionError("unknown case should fail closed")
