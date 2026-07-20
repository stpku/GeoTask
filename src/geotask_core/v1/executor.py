"""v1.0 assertion-driven execution engine.

Executes a CanonicalDocument by dispatching all assertions through
the AssertionDispatcher and producing structured GeotaskResult output.

Hardened with pre-execution validation, condition handling, on_error
semantics, output contract enforcement, execution status derivation,
and v1 result serialization.
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
from geotask_core.v1.validator import validate_canonical

logger = logging.getLogger(__name__)

#: Validator diagnostic codes that the executor handles per-assertion at
#: runtime — these should NOT cause a document-wide abort.  All other
#: severity=error diagnostics indicate structural/infrastructure problems
#: that prevent any meaningful execution.
_EXECUTOR_HANDLED_CODES: frozenset[str] = frozenset(
    {
        "invalid_operator",
        "invalid_reference",
        "arity_mismatch",
        "object_type_mismatch",
    }
)


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
    """Complete result of executing a CanonicalDocument.

    Legacy projections (measurements, conclusion, verified_by) are
    computed as ``@property`` from ``self.checks`` — they are NOT a
    second source of truth.
    """

    schema_version: str = "1.0"
    task_id: str = ""
    execution: ExecutionSummary = field(default_factory=ExecutionSummary)
    checks: list = field(default_factory=list)  # list[CheckResult]
    outputs: dict = field(default_factory=dict)
    summary: ResultSummary = field(default_factory=ResultSummary)
    overall: OverallResult = field(default_factory=OverallResult)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    # ── Legacy compatibility projections (computed, not stored) ──────────

    @property
    def measurements(self) -> list:
        """Legacy measurement list computed dynamically from checks."""
        result: list = []
        for check in self.checks:
            result.append(
                {
                    "name": check.assertion_id,
                    "value": check.value,
                    "unit": check.unit,
                    "object_refs": check.object_refs,
                    "verified_by": check.operator,
                    "status": check.status,
                }
            )
        return result

    @property
    def conclusion(self) -> dict:
        """Legacy conclusion dict computed dynamically from checks."""
        parts: list[str] = []
        for check in self.checks:
            unit_str = f" {check.unit}" if check.unit else ""
            val = check.value
            val_str = (
                str(val).lower()
                if isinstance(val, bool)
                else str(val)
                if val is not None
                else "N/A"
            )
            parts.append(f"{check.assertion_id}={val_str}{unit_str}")

        return {
            "summary": (
                "; ".join(parts) if parts else "no measurements computed"
            ),
            "external_data_used": False,
        }

    @property
    def verified_by(self) -> list:
        """Legacy verified_by list computed dynamically from checks."""
        return [
            {
                "operation": check.operator,
                "result": _format_value(check.value),
            }
            for check in self.checks
        ]

    # ── v1 Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize to v1.0 result dict format.

        AssuranceLevel enums are serialized as their lowercase ``.name``
        string, NEVER as integers.  Datetimes use RFC 3339 format.
        Legacy projections are NOT duplicated in the serialized output.
        """
        return {
            "geotask_result": {
                "schema_version": self.schema_version,
                "task_id": self.task_id,
                "execution": {
                    "mode": self.execution.mode,
                    "status": self.execution.status,
                    "started_at": self.execution.started_at,
                    "finished_at": self.execution.finished_at,
                },
                "checks": [
                    {
                        "assertion_id": c.assertion_id,
                        "operator": c.operator,
                        "object_refs": c.object_refs,
                        "executor": c.executor,
                        "value": c.value,
                        "unit": c.unit,
                        "status": c.status,
                        "assurance_level": _serialize_assurance(c.assurance_level),
                        "deterministic": c.deterministic,
                        "evidence_refs": c.evidence_refs,
                        "error": c.error,
                    }
                    for c in self.checks
                ],
                "outputs": dict(self.outputs),
                "summary": {
                    "total_checks": self.summary.total_checks,
                    "verified": self.summary.verified,
                    "contradicted": self.summary.contradicted,
                    "need_review": self.summary.need_review,
                    "invalid": self.summary.invalid,
                },
                "overall": {
                    "status": self.overall.status,
                    "assurance_level": _serialize_assurance(self.overall.assurance_level),
                },
                "warnings": list(self.warnings),
                "errors": list(self.errors),
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


def execute_canonical(doc: CanonicalDocument) -> GeotaskResult:
    """Execute a v1.0 CanonicalDocument by dispatching all assertions.

    Hardened flow:

    1. **Validate** via ``validate_canonical`` — abort on severity=error.
    2. Route by execution mode (model_only, steps, tasks).
    3. For each assertion: **condition** → depends_on → dispatch.
    4. **Enforce output contract** post-execution.
    5. **Derive execution status** from check results.
    6. Build legacy projections (computed properties from checks).

    Args:
        doc: The validated CanonicalDocument to execute.

    Returns:
        GeotaskResult with structured execution results.
    """
    # ── 1. Pre-execution validation ──────────────────────────────────────
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

    # Separate document-level errors (abort) from assertion-level errors
    # that the executor handles per-check at runtime.
    blocking_errors = [
        d for d in all_errors
        if d.get("code") not in _EXECUTOR_HANDLED_CODES
    ]

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
        # ── 2. Route by execution mode ───────────────────────────────────
        if doc.execution.mode == ExecutionMode.model_only.value:
            _execute_model_only(doc, result)
            _enforce_output_contract(result, doc)
            _finalize(result)
            return result

        # ── Route by execution steps ─────────────────────────────────────
        if doc.execution.steps:
            if _has_unsupported_executors(doc.execution.steps):
                _execute_unsupported(doc, result)
                _enforce_output_contract(result, doc)
                _finalize(result)
                return result
            _execute_steps(doc, dispatcher, result)
        else:
            _execute_tasks(doc, dispatcher, result)

        # ── 5. Derive execution status from checks ───────────────────────
        result.execution.status = _derive_execution_status(result.checks)

    except Exception as exc:  # pragma: no cover — defence in depth
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

    # ── 4. Output contract enforcement ───────────────────────────────────
    _enforce_output_contract(result, doc)
    _finalize(result)
    return result


def _finalize(result: GeotaskResult) -> None:
    """Post-execution: stamp timestamp, compute summary / overall."""
    result.execution.finished_at = _now_iso()
    _compute_summary(result)
    _compute_overall(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: model_only  (skeleton — MUST NOT give local_deterministic)
# ═══════════════════════════════════════════════════════════════════════════════


def _execute_model_only(doc: CanonicalDocument, result: GeotaskResult) -> None:
    """Create skeleton result for ``model_only`` execution mode.

    All assertions are marked ``proposed`` with ``model_generated``
    assurance.  No actual dispatch occurs.
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

    Each task's assertions are dispatched sequentially.  Condition
    handling and on_error semantics are applied per-assertion.
    Failing assertions are tracked so that downstream ``depends_on``
    chains are correctly skipped.
    """
    failed_assertion_ids: set[str] = set()

    for task in doc.tasks:
        if not task.assertions:
            continue

        assertion_iter = iter(task.assertions)
        for assertion in assertion_iter:
            check = _execute_single_assertion(
                assertion, doc, dispatcher, failed_assertion_ids
            )

            # ── Assertion-level on_error handling ────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: step-based (dependency order)
# ═══════════════════════════════════════════════════════════════════════════════


def _execute_steps(
    doc: CanonicalDocument,
    dispatcher: AssertionDispatcher,
    result: GeotaskResult,
) -> None:
    """Execute steps in dependency order with full on_error semantics.

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

    for step_idx, step in enumerate(steps):
        # ── Dependency check ─────────────────────────────────────────────
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

        # ── Execute assertions referenced by this step ────────────────────
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

            # ── Assertion-level on_error handling ────────────────────────
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

        # ── Step-level on_error handling ─────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Strategy: unsupported executors  (skeleton)
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
    status is set to ``pending``.  MUST NOT produce local_deterministic.
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
#  Single Assertion Execution  (with condition handling)
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


def _evaluate_condition(condition: str) -> str:
    """Evaluate a condition string for pre-execution gating.

    Returns:
        ``"execute"``  — condition is missing, empty, or ``"true"``
        ``"skip"``     — condition is ``"false"``
        ``"unverifiable"`` — any other non-empty value
    """
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
    """Validate and dispatch a single assertion.

    Pre-flight checks in order:

      0. **condition** — gate execution based on condition string
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

    # ── 0. condition check ───────────────────────────────────────────────
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

    # ── 1. depends_on check ──────────────────────────────────────────────
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

    # ── 2. operator registration ─────────────────────────────────────────
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

    # ── 3. arity check ───────────────────────────────────────────────────
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

    # ── 4. object reference check ────────────────────────────────────────
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

    # ── 5. object type check ─────────────────────────────────────────────
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

    # ── 6. dispatch ──────────────────────────────────────────────────────
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
#  On-Error Handling
# ═══════════════════════════════════════════════════════════════════════════════


def _handle_assertion_failure(
    check: CheckResult, assertion: Assertion
) -> tuple[CheckResult, bool]:
    """Apply assertion-level on_error policy to a failed check.

    Returns:
        ``(check, should_halt)`` — *check* may be modified in-place;
        *should_halt* is ``True`` when the caller should stop the
        current scope.
    """
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
    """Populate ``result.overall`` from checks and errors.

    - If execution already ``failed`` with errors (unhandled exception),
      keep the ``unverifiable`` overall that was already set.
    - If ``result.errors`` contains ``output_contract_violation``,
      overall is ``invalid_input`` / ``unverified`` regardless of checks.
    - Otherwise, derive *status* from the worst (lowest-priority)
      ``ClaimStatus`` across all checks and *assurance_level* from the
      weakest ``AssuranceLevel``.
    - Only set to ``verified`` when ALL checks are verified AND no errors
      exist.
    """
    # Guard: unhandled exception already set execution=failed + errors →
    #         do NOT overwrite with a computed "verified"
    if result.execution.status == ExecutionStatus.failed.value and result.errors:
        return

    # Guard: output contract violations override everything
    has_contract_violation = any(
        isinstance(e, dict) and e.get("code") == "output_contract_violation"
        for e in result.errors
    )

    if not result.checks:
        result.overall = OverallResult(
            status=(
                ClaimStatus.invalid_input.value
                if has_contract_violation
                else ClaimStatus.verified.value
            ),
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

    # Output contract violated → force invalid_input / unverified
    if has_contract_violation:
        result.overall = OverallResult(
            status=ClaimStatus.invalid_input.value,
            assurance_level=AssuranceLevel.unverified.name,
        )
        return

    result.overall = OverallResult(
        status=worst_status,
        assurance_level=assurance_name,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Output Contract Enforcement
# ═══════════════════════════════════════════════════════════════════════════════


def _enforce_output_contract(
    result: GeotaskResult, doc: CanonicalDocument
) -> None:
    """Populate ``result.outputs`` and validate against ``doc.output_contract``.

    Violations are recorded in ``result.errors``.  If ``allow_additional_fields``
    is ``False``, only fields listed in ``required_fields`` may appear in
    outputs.  ``numeric_precision.decimal_places`` is applied to float values.
    ``ordering.by`` must reference a field in ``required_fields`` and
    ``ordering.direction`` must be ``"ascending"`` or ``"descending"``.
    """
    oc = doc.output_contract

    # ── Populate outputs from successful checks ───────────────────────────
    for check in result.checks:
        if _is_success(check.status):
            result.outputs[check.assertion_id] = check.value

    required = set(oc.required_fields)
    present = set(result.outputs.keys())

    # ── Required fields must exist ────────────────────────────────────────
    missing = required - present
    if missing:
        for field in sorted(missing):
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Required field '{field}' not found in outputs."
                    ),
                    "path": "output_contract.required_fields",
                }
            )

    # ── Additional fields check ───────────────────────────────────────────
    if not oc.allow_additional_fields:
        extra = present - required
        if extra:
            for field in sorted(extra):
                result.errors.append(
                    {
                        "code": "output_contract_violation",
                        "message": (
                            f"Additional field '{field}' not allowed "
                            f"(allow_additional_fields=false)."
                        ),
                        "path": "output_contract.allow_additional_fields",
                    }
                )

    # ── Apply numeric precision ───────────────────────────────────────────
    np_dict = oc.numeric_precision
    if isinstance(np_dict, dict):
        dp = np_dict.get("decimal_places")
        if dp is not None and isinstance(dp, int) and not isinstance(dp, bool) and dp >= 0:
            for key, val in result.outputs.items():
                if isinstance(val, float):
                    result.outputs[key] = round(val, dp)

    # ── Validate ordering ─────────────────────────────────────────────────
    ordering = oc.ordering
    if isinstance(ordering, dict) and ordering:
        by_field = ordering.get("by", "")
        direction = ordering.get("direction", "")
        if by_field and by_field not in required:
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Ordering 'by' field '{by_field}' not in "
                        f"required_fields."
                    ),
                    "path": "output_contract.ordering.by",
                }
            )
        if direction and direction not in ("ascending", "descending"):
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Ordering direction must be 'ascending' or "
                        f"'descending', got '{direction}'."
                    ),
                    "path": "output_contract.ordering.direction",
                }
            )

    # ── Adjust execution status and overall on contract violation ─────────
    if result.errors:
        current = result.execution.status
        if current == ExecutionStatus.completed.value:
            result.execution.status = ExecutionStatus.partial.value
        result.overall.status = ClaimStatus.invalid_input.value
        result.overall.assurance_level = AssuranceLevel.unverified.name


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution Status Derivation
# ═══════════════════════════════════════════════════════════════════════════════


def _derive_execution_status(checks: list) -> str:
    """Derive the correct ``ExecutionStatus`` from all check results.

    Rules:
      - No checks                    → ``pending``
      - All skipped                  → ``skipped``
      - All verified/computed/skipped  → ``completed``
      - All failed/invalid           → ``failed``
      - Mix of success and failure   → ``partial``
      - Any need_review + others     → ``partial``
    """
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Serialization Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _serialize_assurance(level: str) -> str:
    """Ensure assurance level is serialized as lowercase ``.name`` string.

    If *level* is an integer string (should not happen), convert to
    the corresponding ``AssuranceLevel`` name.  Never output integers.
    """
    if not level:
        return AssuranceLevel.unverified.name
    # Already a lowercase name string — use as-is
    if isinstance(level, str) and not level.isdigit():
        return level
    # Defensive: if stored as integer string, convert
    try:
        return _assurance_level_by_int(int(level))
    except (ValueError, TypeError):
        return AssuranceLevel.unverified.name


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 / RFC 3339 string."""
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
