"""Regression tests for truthful execution and executable operator contracts."""

from __future__ import annotations

from typing import Callable

import geotask_core.ops as ops_module

from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.ir import OperatorContract
from geotask_core.v1.operator_contracts import default_registry


def _distance_document(
    *,
    mode: str = "local_only",
    executor: str | None = None,
    expected_type: str = "",
) -> dict:
    execution: dict = {"mode": mode}
    if executor is not None:
        execution["steps"] = [
            {
                "id": "calculate",
                "executor": executor,
                "assertion_refs": ["distance"],
            }
        ]
    return {
        "geotask": {
            "id": "execution-truthfulness",
            "name": "Execution Truthfulness",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [3, 4]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [
            {
                "id": "task",
                "assertions": [
                    {
                        "id": "distance",
                        "operator": "distance_2d",
                        "object_refs": ["a", "b"],
                        "expected_type": expected_type,
                    }
                ],
            }
        ],
        "execution": execution,
        "output_contract": {"format": "structured", "required_fields": []},
    }


def test_hybrid_mode_is_not_substituted_with_local_execution() -> None:
    result = execute_canonical(
        canonicalize(_distance_document(mode="hybrid", executor="local"))
    )

    assert result.execution.status == "pending"
    assert result.overall.status == "unverifiable"
    assert len(result.checks) == 1
    check = result.checks[0]
    assert check.value is None
    assert check.status == "unverifiable"
    assert check.assurance_level == "unverified"
    assert check.error is not None
    assert check.error["code"] == "unsupported_execution_mode"


def test_runtime_executor_is_not_substituted_with_local_execution() -> None:
    result = execute_canonical(
        canonicalize(_distance_document(mode="local_only", executor="runtime"))
    )

    assert result.execution.status == "pending"
    assert result.overall.status == "unverifiable"
    check = result.checks[0]
    assert check.executor == "runtime"
    assert check.value is None
    assert check.status == "unverifiable"
    assert check.error is not None
    assert check.error["code"] == "unsupported_executor"


def test_mixed_plan_does_not_mislabel_local_executor_as_unsupported() -> None:
    data = _distance_document(mode="local_only")
    data["tasks"][0]["assertions"].append(
        {
            "id": "distance_runtime",
            "operator": "distance_2d",
            "object_refs": ["a", "b"],
        }
    )
    data["execution"]["steps"] = [
        {
            "id": "local_step",
            "executor": "local",
            "assertion_refs": ["distance"],
        },
        {
            "id": "runtime_step",
            "executor": "runtime",
            "assertion_refs": ["distance_runtime"],
        },
    ]

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert result.execution.status == "pending"
    assert checks["distance"].error is not None
    assert checks["distance"].error["code"] == "unsupported_execution_plan"
    assert checks["distance_runtime"].error is not None
    assert checks["distance_runtime"].error["code"] == "unsupported_executor"


def test_assertion_expected_type_is_enforced() -> None:
    result = execute_canonical(
        canonicalize(_distance_document(expected_type="bool"))
    )

    check = result.checks[0]
    assert check.value == 5.0
    assert check.status == "invalid_input"
    assert check.assurance_level == "unverified"
    assert check.error is not None
    assert check.error["code"] == "expected_type_mismatch"
    assert check.error["expected"] == "boolean"
    assert check.error["actual"] == "float"


def _register_temporary_operator(
    *,
    name: str,
    implementation: Callable,
    output_type: str,
    invariants: list[dict] | None = None,
) -> None:
    setattr(ops_module, name, implementation)
    if default_registry.is_registered(name):
        del default_registry._contracts[name]
    default_registry.register(
        OperatorContract(
            name=name,
            version="1.0",
            family="test",
            description="Temporary output-contract test operator.",
            arity=1,
            input_types=["point"],
            output={"type": output_type},
            deterministic=True,
            invariants=invariants or [],
            implementation=f"geotask_core.ops.{name}",
        )
    )


def _remove_temporary_operator(name: str) -> None:
    if default_registry.is_registered(name):
        del default_registry._contracts[name]
    if hasattr(ops_module, name):
        delattr(ops_module, name)


def _temporary_operator_document(operator_name: str) -> dict:
    return {
        "geotask": {
            "id": "operator-output-contract",
            "name": "Operator Output Contract",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "point": {"type": "point", "data": {"coordinates": [0, 0]}},
        },
        "operator_set": [operator_name],
        "tasks": [
            {
                "id": "task",
                "assertions": [
                    {
                        "id": "check",
                        "operator": operator_name,
                        "object_refs": ["point"],
                    }
                ],
            }
        ],
        "execution": {"mode": "local_only"},
        "output_contract": {"format": "structured", "required_fields": []},
    }


def test_operator_declared_output_type_is_enforced() -> None:
    name = "_test_returns_text_for_number"
    _register_temporary_operator(
        name=name,
        implementation=lambda _point: "not-a-number",
        output_type="number",
    )
    try:
        result = execute_canonical(
            canonicalize(_temporary_operator_document(name))
        )
        check = result.checks[0]
        assert check.value == "not-a-number"
        assert check.status == "execution_error"
        assert check.error is not None
        assert check.error["code"] == "operator_output_type_mismatch"
    finally:
        _remove_temporary_operator(name)


def test_basic_operator_invariant_is_enforced() -> None:
    name = "_test_returns_negative_number"
    _register_temporary_operator(
        name=name,
        implementation=lambda _point: -1.0,
        output_type="number",
        invariants=[{"id": "non_negative", "expression": "result >= 0"}],
    )
    try:
        result = execute_canonical(
            canonicalize(_temporary_operator_document(name))
        )
        check = result.checks[0]
        assert check.value == -1.0
        assert check.status == "execution_error"
        assert check.error is not None
        assert check.error["code"] == "contract_invariant_violation"
        assert check.error["invariant"] == "non_negative"
    finally:
        _remove_temporary_operator(name)
