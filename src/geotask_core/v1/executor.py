"""v1.0 assertion-driven execution engine.

Executes a CanonicalDocument by dispatching all assertions through
the AssertionDispatcher and producing structured GeotaskResult output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from geotask_core.v1.enums import (
    AssuranceLevel,
    ClaimStatus,
    ExecutionMode,
    ExecutionStatus,
    ExecutorType,
    OnErrorPolicy,
)
from geotask_core.v1.ir import (
    Assertion,
    CanonicalDocument,
    ExecutionStep,
    OperatorContract,
)
from geotask_core.v1.operator_contracts import (
    AssertionDispatcher,
    default_registry,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Result Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CheckResult:
    """Result of dispatching a single assertion."""

    assertion_id: str
    operator: str
    object_refs: list
    executor: str  # "local", "model", "connector", "human"
    value: Any = None
    unit: str = ""
    status: str = ""  # ClaimStatus value
    assurance_level: str = ""  # AssuranceLevel name
    deterministic: bool = False
    evidence_refs: list = field(default_factory=list)
    error: dict | None = None  # structured error info if failed


@dataclass
class ExecutionSummary:
    """Metadata about the overall execution run."""

    mode: str = ""
    status: str = ""  # ExecutionStatus
    started_at: str = ""
    finished_at: str = ""


@dataclass
class ResultSummary:
    """Aggregate counts across all checks."""

    total_checks: int = 0
    verified: int = 0
    contradicted: int = 0
    need_review: int = 0
    invalid: int = 0


@dataclass
class OverallResult:
    """Synthesised overall verdict and confidence."""

    status: str = ""  # ClaimStatus
    assurance_level: str = ""  # AssuranceLevel name


@dataclass
class GeotaskResult:
    """Complete result of executing a CanonicalDocument."""

    schema_version: str = "1.0"
    task_id: str = ""
    execution: ExecutionSummary = field(default_factory=ExecutionSummary)
    checks: list = field(default_factory=list)  # list[CheckResult]
    outputs: dict = field(default_factory=dict)
    summary: ResultSummary = field(default_factory=ResultSummary)
    overall: OverallResult = field(default_factory=OverallResult)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    # Legacy compatibility projections
    measurements: list = field(default_factory=list)
    conclusion: dict = field(default_factory=dict)
    verified_by: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


def execute_canonical(doc: CanonicalDocument) -> GeotaskResult:
    """Execute a v1.0 CanonicalDocument by dispatching all assertions.

    Routes to the correct execution strategy based on the document's
    execution mode and step definitions:

    - ``model_only`` → skeleton ``proposed`` result
    - steps with unsupported executors → ``pending`` skeleton
    - steps with ``local``/``runtime`` executors → dependency-order execution
    - default: iterate ``doc.tasks`` and dispatch each assertion

    Args:
        doc: The validated CanonicalDocument to execute.

    Returns:
        GeotaskResult with structured execution results and legacy
        compatibility projections.
    """
    dispatcher = AssertionDispatcher(default_registry)

    result = GeotaskResult(
        task_id=doc.metadata.id,
        execution=ExecutionSummary(
            mode=doc.execution.mode,
            status=ExecutionStatus.running.value,
            started_at=_now_iso(),
        ),
    )

    try:
        # ── Route by execution mode ───────────────────────────────────
        if doc.execution.mode == ExecutionMode.model_only.value:
            _execute_model_only(doc, result)
            _finalize(result)
            return result

        # ── Route by execution steps ──────────────────────────────────
        if doc.execution.steps:
            if _has_unsupported_executors(doc.execution.steps):
                _execute_unsupported(doc, result)
                _finalize(result)
                return result
            _execute_steps(doc, dispatcher, result)
        else:
            _execute_tasks(doc, dispatcher, result)

        result.execution.status = ExecutionStatus.completed.value

    except Exception as exc:  # pragma: no cover — defence in depth
        logger.exception("Unhandled error during execution")
        result.execution.status = ExecutionStatus.failed.value
        result.errors.append(
            {
                "code": "unhandled_execution_error",
                "message": str(exc),
                "type": type(exc).__name__,
            }
        )

    _finalize(result)
    return result


def _finalize(result: GeotaskResult) -> None:
    """Post-execution: stamp timestamp, compute summary / overall / legacy."""
    result.execution.finished_at = _now_iso()
    _compute_summary(result)
    _compute_overall(result)
    _build_legacy(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: model_only
# ═══════════════════════════════════════════════════════════════════════════════


def _execute_model_only(doc: CanonicalDocument, result: GeotaskResult) -> None:
    """Create skeleton result for ``model_only`` execution mode.

    All assertions are marked ``proposed`` with ``model_generated``
    assurance. No actual dispatch occurs.
    """
    result.execution.status = ExecutionStatus.partial.value
    result.execution.mode = ExecutionMode.model_only.value
    result.warnings.append(
        "Model execution is skeleton only — no actual model calls are made."
    )

    for task in doc.tasks:
        for assertion in task.assertions:
            result.checks.append(
                CheckResult(
                    assertion_id=assertion.id,
                    operator=assertion.operator,
                    object_refs=list(assertion.object_refs),
                    executor=ExecutorType.model.value,
                    unit=_resolve_unit(assertion, None, doc),
                    status=ClaimStatus.proposed.value,
                    assurance_level=AssuranceLevel.model_generated.name,
                )
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: task-level iteration (no steps)
# ═══════════════════════════════════════════════════════════════════════════════


def _execute_tasks(
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    result: GeotaskResult,
) -> None:
    """Execute assertions by iterating over ``doc.tasks``.

    Each task's assertions are dispatched sequentially.  Failing
    assertions are tracked so that downstream ``depends_on`` chains
    are correctly skipped.
    """
    failed_assertion_ids: set[str] = set()

    for task in doc.tasks:
        if not task.assertions:
            continue

        for assertion in task.assertions:
            check = _execute_single_assertion(
                assertion, doc, dispatcher, failed_assertion_ids
            )
            result.checks.append(check)

            if _is_success(check.status):
                continue

            # Track failure for dependents
            failed_assertion_ids.add(assertion.id)

            # "stop" policy halts the *current task* only
            if check.status != "skipped" and (
                assertion.on_error == OnErrorPolicy.stop.value
            ):
                break


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: step-based (dependency order)
# ═══════════════════════════════════════════════════════════════════════════════


def _execute_steps(
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    result: GeotaskResult,
) -> None:
    """Execute steps in dependency order.

    Steps reference assertions by ID across all tasks.  The step
    executor must be ``local`` or ``runtime`` — unsupported executors
    are caught upstream by :func:`_has_unsupported_executors`.
    """
    # Build assertion lookup: assertion_id → assertion
    assertion_map: dict[str, Assertion] = {}
    for task in doc.tasks:
        for assertion in task.assertions:
            assertion_map[assertion.id] = assertion

    steps = _topological_order(doc.execution.steps)

    failed_assertions: set[str] = set()
    step_status: dict[str, str] = {}

    for step in steps:
        # ── Dependency check ──────────────────────────────────────────
        if step.depends_on:
            deps_failed = any(
                step_status.get(dep_id, "")
                != ExecutionStatus.completed.value
                for dep_id in step.depends_on
            )
            if deps_failed:
                step_status[step.id] = ExecutionStatus.skipped.value
                # Skip assertions from this step
                for assertion_id in step.assertion_refs:
                    failed_assertions.add(assertion_id)
                    result.checks.append(
                        CheckResult(
                            assertion_id=assertion_id,
                            operator="",
                            object_refs=[],
                            executor=step.executor,
                            status="skipped",
                        )
                    )
                continue

        # ── Execute assertions referenced by this step ─────────────────
        step_failed = False
        for assertion_id in step.assertion_refs:
            if assertion_id in failed_assertions:
                result.checks.append(
                    CheckResult(
                        assertion_id=assertion_id,
                        operator="",
                        object_refs=[],
                        executor=step.executor,
                        status="skipped",
                    )
                )
                continue

            if assertion_id not in assertion_map:
                result.checks.append(
                    CheckResult(
                        assertion_id=assertion_id,
                        operator="",
                        object_refs=[],
                        executor=step.executor,
                        status=ClaimStatus.invalid_reference.value,
                        error={
                            "code": "invalid_reference",
                            "message": (
                                f"Assertion '{assertion_id}' not found "
                                f"in any task."
                            ),
                        },
                    )
                )
                failed_assertions.add(assertion_id)
                step_failed = True
                continue

            assertion = assertion_map[assertion_id]
            check = _execute_single_assertion(
                assertion, doc, dispatcher, failed_assertions
            )
            result.checks.append(check)

            if not _is_success(check.status):
                failed_assertions.add(assertion_id)
                step_failed = True

        step_status[step.id] = (
            ExecutionStatus.failed.value
            if step_failed
            else ExecutionStatus.completed.value
        )

        # on_error handling for the step boundary
        if step_failed and step.on_error == OnErrorPolicy.stop.value:
            break


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: unsupported executors
# ═══════════════════════════════════════════════════════════════════════════════


def _has_unsupported_executors(steps: list[ExecutionStep]) -> bool:
    """Return ``True`` if any step uses a non-``local``/``runtime`` executor."""
    for step in steps:
        if step.executor not in (
            ExecutorType.local.value,
            ExecutorType.runtime.value,
        ):
            return True
    return False


def _execute_unsupported(
    doc: CanonicalDocument, result: GeotaskResult
) -> None:
    """Create skeleton result when steps reference unsupported executors.

    All referenced assertions are marked ``proposed`` and the execution
    status is set to ``pending``.
    """
    unsupported = sorted(
        {
            step.executor
            for step in doc.execution.steps
            if step.executor
            not in (ExecutorType.local.value, ExecutorType.runtime.value)
        }
    )

    result.execution.status = ExecutionStatus.pending.value
    result.warnings.append(
        f"Execution steps reference unsupported executors: {unsupported}. "
        f"Skeleton result returned."
    )

    for step in doc.execution.steps:
        for assertion_id in step.assertion_refs:
            result.checks.append(
                CheckResult(
                    assertion_id=assertion_id,
                    operator="",
                    object_refs=[],
                    executor=step.executor,
                    status=ClaimStatus.proposed.value,
                )
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  Single Assertion Execution
# ═══════════════════════════════════════════════════════════════════════════════


def _error_check(
    *,
    assertion_id: str,
    operator: str,
    object_refs: list,
    executor: str,
    status: str,
    error: dict | None = None,
    assurance: str = "",
) -> CheckResult:
    """Create a :class:`CheckResult` for a failed / errored assertion."""
    return CheckResult(
        assertion_id=assertion_id,
        operator=operator,
        object_refs=object_refs,
        executor=executor,
        status=status,
        assurance_level=assurance,
        error=error,
    )


def _execute_single_assertion(
    assertion: Assertion,
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    failed_ids: set[str],
) -> CheckResult:
    """Validate and dispatch a single assertion.

    Performs pre-flight checks in order of severity:
      1. ``depends_on`` — skip if any dependency has already failed
      2. Operator registration
      3. Arity vs ``object_refs``
      4. Object reference existence
      5. Object type compatibility
      6. Dispatch via :class:`AssertionDispatcher`

    Returns a :class:`CheckResult` regardless of outcome — errors are
    reported in the status and ``error`` fields, never raised.
    """
    executor_str = _executor_for_mode(doc)

    # ── 1. depends_on check ───────────────────────────────────────────
    if assertion.depends_on:
        failed_deps = failed_ids.intersection(assertion.depends_on)
        if failed_deps:
            return _error_check(
                assertion_id=assertion.id,
                operator=assertion.operator,
                object_refs=list(assertion.object_refs),
                executor=executor_str,
                status="skipped",
                error={
                    "code": "dependency_failed",
                    "message": (
                        f"Skipped because dependencies failed: "
                        f"{sorted(failed_deps)}"
                    ),
                },
            )

    # ── 2. operator registration ──────────────────────────────────────
    if not default_registry.is_registered(assertion.operator):
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.invalid_operator.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "invalid_operator",
                "message": (
                    f"Operator '{assertion.operator}' is not registered. "
                    f"Available: {default_registry.list_names()}"
                ),
            },
        )

    contract = default_registry.get(assertion.operator)

    # ── 3. arity check ────────────────────────────────────────────────
    actual_arity = len(assertion.object_refs)
    if actual_arity != contract.arity:
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.invalid_operator.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "arity_mismatch",
                "message": (
                    f"Operator '{contract.name}' expects "
                    f"{contract.arity} object ref(s), got "
                    f"{actual_arity}: {assertion.object_refs}"
                ),
                "expected": contract.arity,
                "actual": actual_arity,
            },
        )

    # ── 4. object reference check ─────────────────────────────────────
    missing_refs = [
        ref for ref in assertion.object_refs if ref not in doc.objects
    ]
    if missing_refs:
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.invalid_reference.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "invalid_reference",
                "message": (
                    f"Object(s) not found in document: {missing_refs}. "
                    f"Available: {sorted(doc.objects.keys())}"
                ),
                "missing": missing_refs,
            },
        )

    # ── 5. object type check ──────────────────────────────────────────
    type_errors: list[dict] = []
    for i, (ref, expected_type) in enumerate(
        zip(assertion.object_refs, contract.input_types)
    ):
        obj = doc.objects[ref]
        if not _type_matches(obj.type, expected_type):
            type_errors.append(
                {
                    "ref": ref,
                    "expected_type": expected_type,
                    "actual_type": obj.type,
                    "index": i,
                }
            )

    if type_errors:
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.invalid_operator.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "object_type_mismatch",
                "message": (
                    f"Type mismatch(es) for operator "
                    f"'{contract.name}': {type_errors}"
                ),
                "details": type_errors,
            },
        )

    # ── 6. dispatch ───────────────────────────────────────────────────
    try:
        value = dispatcher.dispatch(assertion, doc.objects)
        return CheckResult(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            value=value,
            unit=_resolve_unit(assertion, contract, doc),
            status=ClaimStatus.verified.value,
            assurance_level=AssuranceLevel.local_deterministic.name,
            deterministic=contract.deterministic,
        )
    except Exception as exc:
        logger.warning(
            "Execution error for assertion '%s' with operator '%s': %s",
            assertion.id,
            assertion.operator,
            exc,
        )
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.execution_error.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "execution_error",
                "message": str(exc),
                "type": type(exc).__name__,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Status / Success Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_SUCCESS_STATUSES: frozenset[str] = frozenset(
    {
        ClaimStatus.verified.value,
        ClaimStatus.computed.value,
        ClaimStatus.proposed.value,
    }
)


def _is_success(status: str) -> bool:
    """Return ``True`` if *status* represents successful execution."""
    return status in _SUCCESS_STATUSES


# ═══════════════════════════════════════════════════════════════════════════════
#  Summary & Overall Computation
# ═══════════════════════════════════════════════════════════════════════════════

# Lower number = worse (for determining overall status / assurance)
_STATUS_PRIORITY: dict[str, int] = {
    "execution_error": 0,
    "invalid_operator": 1,
    "invalid_reference": 2,
    "invalid_input": 3,
    "unverifiable": 4,
    "contradicted": 5,
    "need_review": 6,
    "need_data": 7,
    "proposed": 8,
    "computed": 9,
    "verified": 10,
    "skipped": 11,
}

_INVALID_STATUSES: frozenset[str] = frozenset(
    {
        ClaimStatus.invalid_operator.value,
        ClaimStatus.invalid_reference.value,
        ClaimStatus.execution_error.value,
        ClaimStatus.invalid_input.value,
        ClaimStatus.unverifiable.value,
    }
)


def _compute_summary(result: GeotaskResult) -> None:
    """Populate ``result.summary`` with per-status counts."""
    total = len(result.checks)
    verified = 0
    contradicted = 0
    need_review = 0
    invalid = 0

    for check in result.checks:
        status = check.status
        if status == ClaimStatus.verified.value:
            verified += 1
        elif status == ClaimStatus.contradicted.value:
            contradicted += 1
        elif status == ClaimStatus.need_review.value:
            need_review += 1
        elif status in _INVALID_STATUSES:
            invalid += 1

    result.summary = ResultSummary(
        total_checks=total,
        verified=verified,
        contradicted=contradicted,
        need_review=need_review,
        invalid=invalid,
    )


def _compute_overall(result: GeotaskResult) -> None:
    """Populate ``result.overall`` from the worst check.

    - *status*: the worst (lowest-priority) ``ClaimStatus`` across all checks.
    - *assurance_level*: the weakest (minimum int value) ``AssuranceLevel``
      across all checks.
    """
    if not result.checks:
        result.overall = OverallResult(
            status=ClaimStatus.verified.value,
            assurance_level=AssuranceLevel.unverified.name,
        )
        return

    worst_status = ClaimStatus.verified.value
    worst_priority = _STATUS_PRIORITY.get(worst_status, 99)

    min_assurance = AssuranceLevel.human_reviewed.value

    for check in result.checks:
        priority = _STATUS_PRIORITY.get(check.status, 99)
        if priority < worst_priority:
            worst_priority = priority
            worst_status = check.status

        if check.assurance_level:
            level_value = _assurance_level_int(check.assurance_level)
        else:
            level_value = AssuranceLevel.unverified.value
        if level_value < min_assurance:
            min_assurance = level_value

    assurance_name = _assurance_level_by_int(min_assurance)

    result.overall = OverallResult(
        status=worst_status,
        assurance_level=assurance_name,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Legacy Compatibility Projection
# ═══════════════════════════════════════════════════════════════════════════════


def _build_legacy(result: GeotaskResult) -> None:
    """Build legacy-compatible ``measurements``, ``conclusion``, and
    ``verified_by`` projections from ``result.checks``.
    """
    for check in result.checks:
        result.measurements.append(
            {
                "name": check.assertion_id,
                "value": check.value,
                "unit": check.unit,
                "object_refs": check.object_refs,
                "verified_by": check.operator,
                "status": check.status,
            }
        )

    # Build conclusion summary string
    parts: list[str] = []
    for m in result.measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val = m["value"]
        val_str = (
            str(val).lower()
            if isinstance(val, bool)
            else str(val)
            if val is not None
            else "N/A"
        )
        parts.append(f"{m['name']}={val_str}{unit_str}")

    result.conclusion = {
        "summary": (
            "; ".join(parts) if parts else "no measurements computed"
        ),
        "external_data_used": False,
    }

    result.verified_by = [
        {
            "operation": check.operator,
            "result": _format_value(check.value),
        }
        for check in result.checks
    ]


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _type_matches(actual_type: str, expected_type: str) -> bool:
    """Check if *actual_type* is compatible with *expected_type*.

    Mirrors the legacy-type handling in
    ``AssertionDispatcher._extract_typed_param`` so that pre-flight
    validation and dispatcher type checks are consistent.
    """
    if expected_type == "polyline":
        return actual_type in ("polyline", "line")
    if expected_type == "time_interval":
        return actual_type in ("time_interval", "time")
    if expected_type == "altitude_interval":
        return actual_type in ("altitude_interval", "altitude")
    return actual_type == expected_type


def _resolve_unit(
    assertion: Assertion,
    contract: OperatorContract | None,
    doc: CanonicalDocument,
) -> str:
    """Resolve the unit string for a check result.

    Priority: assertion-level unit > contract output > space definition.
    Boolean outputs always have an empty unit.
    """
    if assertion.unit:
        return assertion.unit
    if contract is not None:
        output_type = contract.output.get("type", "")
        if output_type == "boolean":
            return ""
        unit_behavior = contract.output.get("unit_behavior", "")
        if unit_behavior == "inherit_horizontal_unit":
            return doc.space.horizontal_unit
    return ""


def _executor_for_mode(doc: CanonicalDocument) -> str:
    """Return the executor label based on the document's execution mode."""
    if doc.execution.mode == ExecutionMode.model_only.value:
        return ExecutorType.model.value
    return ExecutorType.local.value


def _format_value(value: Any) -> str:
    """Format a value for legacy ``verified_by`` projection."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _topological_order(steps: list[ExecutionStep]) -> list[ExecutionStep]:
    """Sort *steps* in topological order via Kahn's algorithm.

    Steps with unresolved ``depends_on`` references are appended at the
    end so ordering degrades gracefully rather than failing.
    """
    step_map: dict[str, ExecutionStep] = {s.id: s for s in steps}

    in_degree: dict[str, int] = {s.id: 0 for s in steps}
    adjacency: dict[str, list[str]] = {s.id: [] for s in steps}

    for step in steps:
        for dep_id in step.depends_on:
            if dep_id in step_map:
                adjacency[dep_id].append(step.id)
                in_degree[step.id] += 1

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    ordered: list[ExecutionStep] = []

    while queue:
        sid = queue.pop(0)
        ordered.append(step_map[sid])
        for neighbor in adjacency.get(sid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any remaining (cyclic or self-referencing) at the end
    ordered_ids = {s.id for s in ordered}
    for step in steps:
        if step.id not in ordered_ids:
            ordered.append(step)

    return ordered


# ── Assurance level mapping helpers ──────────────────────────────────────────

_ASSURANCE_NAME_TO_INT: dict[str, int] = {
    level.name: level.value for level in AssuranceLevel
}

_ASSURANCE_INT_TO_NAME: dict[int, str] = {
    level.value: level.name for level in AssuranceLevel
}


def _assurance_level_int(name: str) -> int:
    """Convert an AssuranceLevel name (e.g. ``"local_deterministic"``)
    to its integer value.  Returns 0 for unrecognised names.
    """
    return _ASSURANCE_NAME_TO_INT.get(name, 0)


def _assurance_level_by_int(value: int) -> str:
    """Convert an integer back to an AssuranceLevel name string.
    Returns ``"unverified"`` for unrecognised values.
    """
    if value in _ASSURANCE_INT_TO_NAME:
        return _ASSURANCE_INT_TO_NAME[value]
    return AssuranceLevel.unverified.name
