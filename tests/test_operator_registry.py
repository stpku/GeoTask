"""Tests for the public-safe Core operator registry."""

from pathlib import Path

import pytest

from geotask_core.verifier import SUPPORTED_OPERATORS


EXPECTED_PUBLIC_SAFE_OPERATORS = {
    "distance_2d",
    "line_intersects_rect",
    "point_to_line_distance_2d",
    "rect_contains_point",
    "time_overlap",
    "altitude_overlap",
}


def test_operator_registry_lists_production_core_operators():
    """Registry exposes exactly the public-safe production Core operators."""
    from geotask_core.operator_registry import operator_names

    assert set(operator_names()) == EXPECTED_PUBLIC_SAFE_OPERATORS
    assert operator_names() == SUPPORTED_OPERATORS


def test_operator_metadata_has_required_fields():
    """Every operator has complete discoverability metadata."""
    from geotask_core.operator_registry import (
        REQUIRED_OPERATOR_METADATA_FIELDS,
        list_operator_metadata,
    )

    for metadata in list_operator_metadata():
        missing = REQUIRED_OPERATOR_METADATA_FIELDS - set(metadata)
        assert not missing, f"{metadata.get('name')} missing {missing}"
        assert metadata["name"] in EXPECTED_PUBLIC_SAFE_OPERATORS
        assert metadata["input_shape"]
        assert metadata["output_type"] in {"float", "bool"}
        assert metadata["deterministic"] is True
        assert metadata["supported_geometry"]
        assert metadata["error_codes"]
        assert metadata["examples"]


def test_get_operator_metadata_unknown_operator_has_clear_error():
    """Unknown operators fail with a stable, user-facing error code."""
    from geotask_core.operator_registry import get_operator_metadata

    with pytest.raises(KeyError) as exc_info:
        get_operator_metadata("bogus_operator")

    message = str(exc_info.value)
    assert "unsupported_operator" in message
    assert "bogus_operator" in message


def test_operator_registry_docs_cover_public_safe_operators():
    """Public docs list every registry operator and the inspect command."""
    docs_path = Path(__file__).resolve().parent.parent / "docs" / "operator_registry.md"
    text = docs_path.read_text(encoding="utf-8")

    assert "Operator Registry" in text
    assert "inspect operators" in text
    for operator_name in EXPECTED_PUBLIC_SAFE_OPERATORS:
        assert operator_name in text
