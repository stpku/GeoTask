"""Bilingual public examples for point-to-line distance."""

from pathlib import Path

import pytest

from geotask_core.parser import load_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.validator import validate_canonical


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = (
    ROOT / "examples" / "core" / "v1_point_to_line_distance_minimal.en.yaml",
    ROOT / "examples" / "core" / "v1_point_to_line_distance_minimal.zh-CN.yaml",
)


@pytest.mark.parametrize("example", EXAMPLES, ids=("english", "chinese"))
def test_bilingual_point_to_line_examples_validate_and_execute(example: Path) -> None:
    payload = load_geotask(example)
    canonical = canonicalize(payload)

    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    checks = {
        check.assertion_id: (check.value, check.unit, check.status)
        for check in result.checks
    }
    assert checks == {
        "off_route_distance": (4.0, "meter", "verified"),
        "on_route_distance": (0.0, "meter", "verified"),
    }


def test_bilingual_examples_keep_identical_machine_contracts() -> None:
    english = canonicalize(load_geotask(EXAMPLES[0]))
    chinese = canonicalize(load_geotask(EXAMPLES[1]))

    assert english.space == chinese.space
    assert english.objects == chinese.objects
    assert english.operator_set == chinese.operator_set
    assert len(english.tasks) == len(chinese.tasks) == 1
    assert english.tasks[0].id == chinese.tasks[0].id
    assert english.tasks[0].family == chinese.tasks[0].family
    assert english.tasks[0].assertions == chinese.tasks[0].assertions
    assert english.tasks[0].outputs == chinese.tasks[0].outputs
    assert english.execution == chinese.execution
    assert english.output_contract == chinese.output_contract
    assert english.expected_results == chinese.expected_results
