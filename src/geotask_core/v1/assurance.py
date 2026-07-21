"""v1.0 Assurance aggregation logic.

Computes execution summaries, overall verdicts, and status
classification from a list of CheckResult objects.
"""

from __future__ import annotations

from geotask_core.v1.enums import (
    AssuranceLevel,
    ClaimStatus,
    ExecutionStatus,
)
from geotask_core.v1.result import (
    GeotaskResult,
    OverallResult,
    ResultSummary,
    _assurance_level_int,
    _assurance_level_by_int,
)


# -- Status / Success Helpers

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


# -- Summary & Overall Computation

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
    """Populate ``result.overall`` from checks and errors."""
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
