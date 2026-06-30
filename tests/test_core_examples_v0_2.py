"""Public-safe Core example and schema-gap tests."""

from pathlib import Path

from geotask_core.parser import load_geotask, validate_geotask
from geotask_core.runner import run_geotask


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_EXAMPLES = REPO_ROOT / "examples" / "core"


def _base_doc(objects: dict, ops: dict) -> dict:
    return {
        "geotask": {"version": "0.2", "name": "schema test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter", "axes": {"x": "east", "y": "north"}},
        "objects": objects,
        "ops": ops,
        "task": {"questions": ["Run deterministic checks."]},
    }


def test_parser_accepts_generic_time_and_altitude_objects():
    """Parser accepts generic time and altitude objects already supported by runner."""
    data = _base_doc(
        objects={
            "window_a": {"type": "time", "interval": ["08:00", "10:00"]},
            "window_b": {"type": "time", "interval": ["09:00", "11:00"]},
            "band_a": {"type": "altitude", "range": [100, 200]},
            "band_b": {"type": "altitude", "range": [150, 250]},
        },
        ops={"time_overlap": "", "altitude_overlap": ""},
    )

    assert validate_geotask(data) == []


def test_parser_rejects_invalid_time_interval_order():
    """Time intervals with start after end produce a stable diagnostic code."""
    data = _base_doc(
        objects={
            "window_a": {"type": "time", "interval": ["12:00", "10:00"]},
            "window_b": {"type": "time", "interval": ["09:00", "11:00"]},
        },
        ops={"time_overlap": ""},
    )

    errors = validate_geotask(data)
    assert any("invalid_interval" in error for error in errors)
    assert any("objects.window_a.interval" in error for error in errors)


def test_parser_rejects_invalid_altitude_range_order():
    """Altitude ranges with min above max produce a stable diagnostic code."""
    data = _base_doc(
        objects={
            "band_a": {"type": "altitude", "range": [300, 100]},
            "band_b": {"type": "altitude", "range": [150, 250]},
        },
        ops={"altitude_overlap": ""},
    )

    errors = validate_geotask(data)
    assert any("invalid_interval" in error for error in errors)
    assert any("objects.band_a.range" in error for error in errors)


def test_public_safe_core_examples_validate_and_run():
    """Core examples validate and produce deterministic measurements."""
    expected_examples = [
        CORE_EXAMPLES / "minimal_valid.yaml",
        CORE_EXAMPLES / "time_altitude_overlap.yaml",
        CORE_EXAMPLES / "assertions_expected_results.yaml",
    ]

    for example in expected_examples:
        data = load_geotask(example)
        assert validate_geotask(data) == []
        result = run_geotask(data)
        assert result["measurements"], f"{example.name} produced no measurements"


def test_examples_readme_lists_core_examples():
    """examples/README.md lists the public-safe Core examples."""
    readme = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")

    assert "examples/core/minimal_valid.yaml" in readme
    assert "examples/core/time_altitude_overlap.yaml" in readme
    assert "examples/core/assertions_expected_results.yaml" in readme
    assert "public-safe" in readme


def test_geotask_yaml_schema_doc_covers_time_altitude_examples():
    """Schema docs cover generic time/altitude objects and diagnostics."""
    text = (REPO_ROOT / "docs" / "geotask_yaml_schema.md").read_text(encoding="utf-8")

    assert "time" in text
    assert "altitude" in text
    assert "invalid_interval" in text
    assert "examples/core/time_altitude_overlap.yaml" in text
    assert "assertions" in text
    assert "expected_results" in text
