"""v1.0 assertion-driven execution engine.

Executes a CanonicalDocument by dispatching all assertions through
the AssertionDispatcher and producing structured GeotaskResult output.

Pre-execution validation, condition handling, on_error
semantics, output contract enforcement, execution status derivation,
and v1 result serialization.
"""

from __future__ import annotations

import logging
from typing import Any

from geotask_core.v1.assurance import (
    _compute_overall,
    _compute_summary,
    _is_success,
)
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
from geotask_core.v1.output_contract import _enforce_output_contract
from geotask_core.v1.result import (
    CheckResult,
    ExecutionSummary,
    GeotaskResult,
    _now_iso,
)
from geotask_core.v1.validator import validate_canonical

logger = logging.getLogger(__name__)


# -- Main Entry Point


def execute_canonical(doc: CanonicalDocument) -> GeotaskResult:
    """Execute a v1.0 CanonicalDocument by dispatching all assertions.

    1. Validate via ``validate_canonical`` — abort on severity=error.
    2. Route by execution mode (model_only, steps, tasks).
    3. For each assertion: condition → depends_on → dispatch.
    4. Enforce output contract post-execution.
    5. Derive execution status from check results.
    6. Build legacy projections (computed properties from checks).

    Args:
        doc: The validated CanonicalDocument to execute.

    Returns:
        GeotaskResult with structured execution results.
    """
    # -- 1. Pre-execution validation ──────────────────────────────────────
    diagnostics = validate_canonical(doc)
    all_errors = [d for d in diagnostics if d.get("severity") == "error"]

    result = GeotaskResult(
        task_id=doc.metadata.id,
        execution=ExecutionSummary(
            mode=doc.execution.mode,
            status=ExecutionStatus.running.value,
            started_at=_now_iso(),
        ),
    )

    # All severity=error diagnostics are document-level blocking errors.
    # Per-assertion issues (invalid operator, arity mismatch, bad reference,
    # type mismatch) are produced as severity=warning by the validator and
    # handled per-check by _execute_single_assertion at runtime.
    blocking_errors = all_errors  # No allowlist — all errors block

    if blocking_errors:
        # Abort — never give local_deterministic to invalid input
        result.execution.status = ExecutionStatus.failed.value
        result.overall.status = ClaimStatus.unverifiable.value
        result.overall.assurance_level = AssuranceLevel.unverified.name
        for d in diagnostics:
            if d.get("severity") == "error":
                result.errors.append(
                    {
                        "path": d.get("path", ""),
                        "code": d.get("code", ""),
                        "message": d.get("message", ""),
                        "severity": "error",
                    }
                )
            elif d.get("severity") == "warning":
                result.warnings.append(
                    f"{d.get('path', '')}: {d.get('code', '')}: "
                    f"{d.get('message', '')}"
                )
        result.execution.finished_at = _now_iso()
        return result

    # Attach non-blocking validation warnings to result
    for d in diagnostics:
        if d.get("severity") == "warning":
            result.warnings.append(
                f"{d.get('path', '')}: {d.get('code', '')}: "
                f"{d.get('message', '')}"
            )

    dispatcher = AssertionDispatcher(default_registry)

    try:
        # -- 2. Route by execution mode ───────────────────────────────────
        if doc.execution.mode == ExecutionMode.model_only.value:
            _execute_model_only(doc, result)
            _enforce_output_contract(result, doc)
            _finalize(result)
            return result

        # -- Route by execution steps ─────────────────────────────────────
        if doc.execution.steps:
            if _has_unsupported_executors(doc.execution.steps):
                _execute_unsupported(doc, result)
                _enforce_output_contract(result, doc)
                _finalize(result)
                return result
            _execute_steps(doc, dispatcher, result)
        else:
            _execute_tasks(doc, dispatcher, result)

        # -- 5. Derive execution status from checks ───────────────────────
        result.execution.status = _derive_execution_status(result.checks)

    except Exception as exc:  # pragma: no cover
        logger.exception("Unhandled error during execution")
        result.execution.status = ExecutionStatus.failed.value
        result.overall.status = ClaimStatus.unverifiable.value
        result.overall.assurance_level = AssuranceLevel.unverified.name
        result.errors.append(
            {
                "code": "unhandled_execution_error",
                "message": str(exc),
                "type": type(exc).__name__,
            }
        )

    # -- 4. Output contract enforcement ───────────────────────────────────
    _enforce_output_contract(result, doc)
    _finalize(result)
    return result


def _finalize(result: GeotaskResult) -> None:
    """Post-execution: stamp timestamp, compute summary / overall."""
    result.execution.finished_at = _now_iso()
    _compute_summary(result)
    _compute_overall(result)


# -- Execution Strategy: model_only (skeleton)


def _execute_model_only(doc: CanonicalDocument, result: GeotaskResult) -> None:
    """Create skeleton result for ``model_only`` execution mode."""
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


# -- Execution Strategy: task-level iteration (no steps)


def _execute_tasks(
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    result: GeotaskResult,
) -> None:
    """Execute assertions by iterating over ``doc.tasks``."""
    failed_assertion_ids: set[str] = set()

    for task in doc.tasks:
        if not task.assertions:
            continue

        assertion_iter = iter(task.assertions)
        for assertion in assertion_iter:
            check = _execute_single_assertion(
                assertion, doc, dispatcher, failed_assertion_ids
            )

            # -- Assertion-level on_error handling ────────────────────────
            if not _is_success(check.status):
                # Distinguish: condition=false skip vs dependency skip vs real failure.
                # Do NOT apply on_error to non-failure skips.
                is_dependency_skip = (
                    check.status == ExecutionStatus.skipped.value
                    and check.error is not None
                    and check.error.get("code") == "dependency_failed"
                )
                is_condition_skip = (
                    check.status == ExecutionStatus.skipped.value
                    and not is_dependency_skip
                )

                if is_condition_skip:
                    # condition=false → continue to next assertion,
                    # regardless of on_error
                    result.checks.append(check)
                    continue

                if is_dependency_skip:
                    # depends_on failure → continue (don't re-apply on_error)
                    result.checks.append(check)
                    failed_assertion_ids.add(assertion.id)
                    continue

                # Real failure — apply on_error policy
                check, should_halt = _handle_assertion_failure(check, assertion)
                if should_halt:
                    # stop: mark current, then mark remaining as skipped
                    result.checks.append(check)
                    failed_assertion_ids.add(assertion.id)
                    for remaining in assertion_iter:
                        result.checks.append(
                            CheckResult(
                                assertion_id=remaining.id,
                                operator=remaining.operator,
                                object_refs=list(remaining.object_refs),
                                executor=_executor_for_mode(doc),
                                status=ExecutionStatus.skipped.value,
                            )
                        )
                        failed_assertion_ids.add(remaining.id)
                    # halt the current task (not all tasks)
                    break
                failed_assertion_ids.add(assertion.id)

            result.checks.append(check)


# -- Execution Strategy: step-based (dependency order)


def _execute_steps(
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    result: GeotaskResult,
) -> None:
    """Execute steps in dependency order with full on_error semantics."""
    # Build assertion lookup: assertion_id → assertion
    assertion_map: dict[str, Assertion] = {}
    for task in doc.tasks:
        for assertion in task.assertions:
            assertion_map[assertion.id] = assertion

    steps = _topological_order(doc.execution.steps)

    failed_assertions: set[str] = set()
    step_status: dict[str, str] = {}

    for step_idx, step in enumerate(steps):
        # -- Dependency check ─────────────────────────────────────────────
        if step.depends_on:
            deps_failed = any(
                step_status.get(dep_id, "")
                != ExecutionStatus.completed.value
                for dep_id in step.depends_on
            )
            if deps_failed:
                step_status[step.id] = ExecutionStatus.skipped.value
                for assertion_id in step.assertion_refs:
                    failed_assertions.add(assertion_id)
                    result.checks.append(
                        CheckResult(
                            assertion_id=assertion_id,
                            operator="",
                            object_refs=[],
                            executor=step.executor,
                            status=ExecutionStatus.skipped.value,
                        )
                    )
                continue

        # -- Execute assertions referenced by this step ────────────────────
        step_failed = False
        for ai_idx, assertion_id in enumerate(step.assertion_refs):
            if assertion_id in failed_assertions:
                result.checks.append(
                    CheckResult(
                        assertion_id=assertion_id,
                        operator="",
                        object_refs=[],
                        executor=step.executor,
                        status=ExecutionStatus.skipped.value,
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

            # -- Assertion-level on_error handling ────────────────────────
            if not _is_success(check.status):
                # Distinguish: condition=false skip vs dependency skip vs real failure.
                # Do NOT apply on_error to non-failure skips.
                is_dependency_skip = (
                    check.status == ExecutionStatus.skipped.value
                    and check.error is not None
                    and check.error.get("code") == "dependency_failed"
                )
                is_condition_skip = (
                    check.status == ExecutionStatus.skipped.value
                    and not is_dependency_skip
                )

                if is_condition_skip:
                    # condition=false → continue to next assertion,
                    # regardless of on_error
                    result.checks.append(check)
                    continue

                if is_dependency_skip:
                    # depends_on failure → continue (don't re-apply on_error)
                    result.checks.append(check)
                    failed_assertions.add(assertion_id)
                    continue

                # Real failure — apply on_error policy
                check, should_halt = _handle_assertion_failure(check, assertion)
                if should_halt:
                    # stop: mark current, then mark remaining in this step as skipped
                    result.checks.append(check)
                    failed_assertions.add(assertion_id)
                    step_failed = True
                    for remaining_aid in step.assertion_refs[ai_idx + 1:]:
                        if remaining_aid not in failed_assertions:
                            result.checks.append(
                                CheckResult(
                                    assertion_id=remaining_aid,
                                    operator="",
                                    object_refs=[],
                                    executor=step.executor,
                                    status=ExecutionStatus.skipped.value,
                                )
                            )
                            failed_assertions.add(remaining_aid)
                    break  # break the assertions inner loop
                failed_assertions.add(assertion_id)
                step_failed = True

            result.checks.append(check)

        # -- Step-level on_error handling ─────────────────────────────────
        if step_failed:
            if step.on_error == OnErrorPolicy.stop.value:
                step_status[step.id] = ExecutionStatus.failed.value
                # Mark remaining steps' assertions as skipped
                for remaining_step in steps[step_idx + 1:]:
                    for assertion_id in remaining_step.assertion_refs:
                        if assertion_id not in failed_assertions:
                            result.checks.append(
                                CheckResult(
                                    assertion_id=assertion_id,
                                    operator="",
                                    object_refs=[],
                                    executor=remaining_step.executor,
                                    status=ExecutionStatus.skipped.value,
                                )
                            )
                            failed_assertions.add(assertion_id)
                    step_status[remaining_step.id] = ExecutionStatus.skipped.value
                break
            elif step.on_error == OnErrorPolicy.need_review.value:
                step_status[step.id] = ClaimStatus.need_review.value
            elif step.on_error == OnErrorPolicy.skip.value:
                step_status[step.id] = ExecutionStatus.skipped.value
            elif step.on_error == OnErrorPolicy.fallback.value:
                step_status[step.id] = ClaimStatus.unverifiable.value
                result.warnings.append(
                    f"Step '{step.id}' failed with on_error=fallback "
                    f"but no fallback target configured — set to unverifiable."
                )
            else:
                step_status[step.id] = ExecutionStatus.failed.value
        else:
            step_status[step.id] = ExecutionStatus.completed.value


# -- Execution Strategy: unsupported executors (skeleton)


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
    """Create skeleton result when steps reference unsupported executors."""
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


# -- Single Assertion Execution (with condition handling)


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


def _evaluate_condition(condition: str) -> str:
    """Evaluate a condition string for pre-execution gating."""
    if not condition or not condition.strip():
        return "execute"
    stripped = condition.strip().lower()
    if stripped == "true":
        return "execute"
    if stripped == "false":
        return "skip"
    return "unverifiable"


def _execute_single_assertion(
    assertion: Assertion,
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    failed_ids: set[str],
) -> CheckResult:
    """Validate and dispatch a single assertion with pre-flight checks."""
    executor_str = _executor_for_mode(doc)

    # -- 0. condition check ───────────────────────────────────────────────
    cond_result = _evaluate_condition(assertion.condition)
    if cond_result == "skip":
        return CheckResult(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ExecutionStatus.skipped.value,
        )
    if cond_result == "unverifiable":
        return _error_check(
            assertion_id=assertion.id,
            operator=assertion.operator,
            object_refs=list(assertion.object_refs),
            executor=executor_str,
            status=ClaimStatus.unverifiable.value,
            assurance=AssuranceLevel.unverified.name,
            error={
                "code": "unverifiable_condition",
                "message": (
                    f"Cannot interpret condition: "
                    f"{assertion.condition!r}"
                ),
            },
        )

    # -- 1. depends_on check ──────────────────────────────────────────────
    if assertion.depends_on:
        failed_deps = failed_ids.intersection(assertion.depends_on)
        if failed_deps:
            return _error_check(
                assertion_id=assertion.id,
                operator=assertion.operator,
                object_refs=list(assertion.object_refs),
                executor=executor_str,
                status=ExecutionStatus.skipped.value,
                error={
                    "code": "dependency_failed",
                    "message": (
                        f"Skipped because dependencies failed: "
                        f"{sorted(failed_deps)}"
                    ),
                },
            )

    # -- 2. operator registration ─────────────────────────────────────────
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

    # -- 3. arity check ───────────────────────────────────────────────────
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

    # -- 4. object reference check ────────────────────────────────────────
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

    # -- 5. object type check ─────────────────────────────────────────────
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

    # -- 6. dispatch ──────────────────────────────────────────────────────
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


# -- On-Error Handling


def _handle_assertion_failure(
    check: CheckResult, assertion: Assertion
) -> tuple[CheckResult, bool]:
    """Apply assertion-level on_error policy to a failed check."""
    policy = assertion.on_error

    if policy == OnErrorPolicy.stop.value:
        return check, True

    if policy == OnErrorPolicy.continue_.value:
        # Record failure and continue — no transformation needed
        return check, False

    if policy == OnErrorPolicy.skip.value:
        check.status = ExecutionStatus.skipped.value
        return check, False

    if policy == OnErrorPolicy.need_review.value:
        check.status = ClaimStatus.need_review.value
        check.assurance_level = AssuranceLevel.unverified.name
        return check, False

    if policy == OnErrorPolicy.fallback.value:
        # No fallback target → unverifiable; do NOT silently continue
        check.status = ClaimStatus.unverifiable.value
        check.assurance_level = AssuranceLevel.unverified.name
        if not check.error:
            check.error = {
                "code": "fallback_no_target",
                "message": "on_error=fallback but no fallback target configured.",
            }
        return check, False

    # Unknown or default: treat as stop
    return check, True


# -- Execution Status Derivation


def _derive_execution_status(checks: list) -> str:
    """Derive ``ExecutionStatus`` from check results."""
    if not checks:
        return ExecutionStatus.pending.value

    statuses = {c.status for c in checks}

    # All skipped
    if statuses == {ExecutionStatus.skipped.value}:
        return ExecutionStatus.skipped.value

    # Classify statuses
    failure_set = {
        ClaimStatus.contradicted.value,
        ClaimStatus.execution_error.value,
        ClaimStatus.invalid_input.value,
        ClaimStatus.invalid_operator.value,
        ClaimStatus.invalid_reference.value,
        ClaimStatus.unverifiable.value,
    }

    success_set = {
        ClaimStatus.verified.value,
        ClaimStatus.computed.value,
        ClaimStatus.proposed.value,
        ExecutionStatus.skipped.value,
    }

    has_failure = bool(statuses & failure_set)
    has_success = bool(statuses & success_set)
    has_need_review = ClaimStatus.need_review.value in statuses
    has_pending_like = bool(
        statuses - failure_set - success_set - {ClaimStatus.need_review.value}
    )

    # All failures, no success → failed
    if has_failure and not has_success and not has_need_review:
        return ExecutionStatus.failed.value

    # Any mixture of failure/success/need_review → partial
    if has_failure:
        return ExecutionStatus.partial.value
    if has_need_review and has_success:
        return ExecutionStatus.partial.value

    # All success or skipped → completed
    if has_success and not has_failure and not has_need_review:
        return ExecutionStatus.completed.value

    # Fallback (e.g. need_review only, pending-like only)
    if has_pending_like or has_need_review:
        return ExecutionStatus.partial.value

    return ExecutionStatus.completed.value


# -- Utility Helpers


def _type_matches(actual_type: str, expected_type: str) -> bool:
    """Check if *actual_type* is compatible with *expected_type*."""
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
    """Resolve the unit string for a check result."""
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
    """Return the executor label for the document's execution mode."""
    if doc.execution.mode == ExecutionMode.model_only.value:
        return ExecutorType.model.value
    return ExecutorType.local.value


def _topological_order(steps: list[ExecutionStep]) -> list[ExecutionStep]:
    """Sort *steps* in topological order via Kahn's algorithm."""
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
