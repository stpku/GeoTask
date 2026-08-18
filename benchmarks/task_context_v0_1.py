"""Deterministic TC1 proof benchmark for GeoTask Task Context Engine.

This repository-local benchmark compares three context preparation strategies:

B0 full_context
    Select every candidate made available to the case.

B1 manual_template
    Select a fixed, human-authored candidate list declared by the case.

G0 declared_min_cost_v0
    For every critical ContextRequirement, select the lowest declared-cost
    candidate that is explicitly relevant, applicable, and resolution-sufficient.
    Non-critical requirements are intentionally optional. Ties prefer the
    coarsest still-sufficient declared spatial resolution, then candidate id.

G0 is an experiment policy, not GeoTask Core semantics. It does not discover
requirements, query providers, infer scope, or optimize globally across bundled
multi-requirement candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
    evaluate_context_candidate,
)


POLICY_FULL_CONTEXT = "B0/full_context"
POLICY_MANUAL_TEMPLATE = "B1/manual_template"
POLICY_DECLARED_MIN_COST = "G0/declared_min_cost_v0"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    domain: str
    task: TaskFrame
    requirements: tuple[ContextRequirement, ...]
    candidates: tuple[ContextCandidate, ...]
    manual_candidate_ids: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    domain: str
    policy: str
    selected_candidate_ids: tuple[str, ...]
    context_status: str
    critical_context_miss_rate: float
    context_preparation_cost: float
    cost_unit: str | None
    context_reduction_ratio_items: float
    refinement_requirement_ids: tuple[str, ...]
    task_outcome_regret: float | None = None


def _critical_requirement_ids(
    requirements: Sequence[ContextRequirement],
) -> tuple[str, ...]:
    return tuple(
        requirement.requirement_id
        for requirement in requirements
        if requirement.critical
    )


def _covered_requirement_ids(context: TaskContext) -> set[str]:
    return {
        item.requirement_id
        for item in context.coverage
        if item.candidate_ids
    }


def critical_context_miss_rate(
    requirements: Sequence[ContextRequirement],
    context: TaskContext,
) -> float:
    critical_ids = _critical_requirement_ids(requirements)
    if not critical_ids:
        return 0.0
    covered = _covered_requirement_ids(context)
    missed = sum(requirement_id not in covered for requirement_id in critical_ids)
    return missed / len(critical_ids)


def context_reduction_ratio_items(
    selected_count: int,
    full_count: int,
) -> float:
    if full_count <= 0:
        return 0.0
    return 1.0 - (selected_count / full_count)


def _candidate_index(
    candidates: Iterable[ContextCandidate],
) -> dict[str, ContextCandidate]:
    index: dict[str, ContextCandidate] = {}
    for candidate in candidates:
        if candidate.candidate_id in index:
            raise ValueError(f"duplicate candidate id: {candidate.candidate_id}")
        index[candidate.candidate_id] = candidate
    return index


def select_manual_template(case: BenchmarkCase) -> tuple[ContextCandidate, ...]:
    index = _candidate_index(case.candidates)
    unknown = sorted(set(case.manual_candidate_ids) - set(index))
    if unknown:
        raise ValueError(
            "manual template references unknown candidate ids: "
            + ", ".join(unknown)
        )
    return tuple(index[candidate_id] for candidate_id in case.manual_candidate_ids)


def _coarseness_rank(candidate: ContextCandidate) -> float:
    """Prefer coarser declared resolution only after equal acquisition cost.

    A missing spatial resolution is neutral because some requirements (for
    example an airspace notice) do not declare a raster/grid resolution.
    """

    if candidate.spatial_resolution is None:
        return 0.0
    return -candidate.spatial_resolution


def select_declared_min_cost(case: BenchmarkCase) -> tuple[ContextCandidate, ...]:
    """Select one cheapest usable candidate for each critical requirement.

    This intentionally simple greedy policy exists only to make TC1 falsifiable.
    It does not solve set cover and does not claim global optimality.
    """

    selected: dict[str, ContextCandidate] = {}

    for requirement in case.requirements:
        if not requirement.critical:
            continue
        usable = []
        for candidate in case.candidates:
            assessment = evaluate_context_candidate(case.task, requirement, candidate)
            if assessment.usable:
                usable.append(candidate)

        if not usable:
            # Leave the requirement uncovered. assess_task_context will expose
            # the critical gap instead of the benchmark inventing a substitute.
            continue

        usable.sort(
            key=lambda candidate: (
                candidate.acquisition_cost,
                _coarseness_rank(candidate),
                candidate.candidate_id,
            )
        )
        chosen = usable[0]
        selected[chosen.candidate_id] = chosen

    return tuple(selected[candidate_id] for candidate_id in sorted(selected))


def _evaluate_selection(
    case: BenchmarkCase,
    policy: str,
    selected: Sequence[ContextCandidate],
) -> BenchmarkResult:
    context = assess_task_context(case.task, case.requirements, selected)
    return BenchmarkResult(
        case_id=case.case_id,
        domain=case.domain,
        policy=policy,
        selected_candidate_ids=tuple(
            sorted(candidate.candidate_id for candidate in selected)
        ),
        context_status=context.status,
        critical_context_miss_rate=critical_context_miss_rate(
            case.requirements,
            context,
        ),
        context_preparation_cost=context.total_acquisition_cost,
        cost_unit=context.cost_unit,
        context_reduction_ratio_items=context_reduction_ratio_items(
            len(selected),
            len(case.candidates),
        ),
        refinement_requirement_ids=context.refinement_requirement_ids,
        # Synthetic TC1 fixtures do not contain an independently validated
        # downstream domain outcome model. Reporting zero regret would be a
        # false accuracy claim, so TOR remains explicitly unavailable.
        task_outcome_regret=None,
    )


def run_case(case: BenchmarkCase) -> tuple[BenchmarkResult, ...]:
    return (
        _evaluate_selection(
            case,
            POLICY_FULL_CONTEXT,
            case.candidates,
        ),
        _evaluate_selection(
            case,
            POLICY_MANUAL_TEMPLATE,
            select_manual_template(case),
        ),
        _evaluate_selection(
            case,
            POLICY_DECLARED_MIN_COST,
            select_declared_min_cost(case),
        ),
    )


def format_results(results: Sequence[BenchmarkResult]) -> str:
    lines = [
        "case | policy | CCMR | cost | reduction(items) | status | refine",
        "--- | --- | ---: | ---: | ---: | --- | ---",
    ]
    for result in results:
        cost = f"{result.context_preparation_cost:g} {result.cost_unit or '-'}"
        refine = ",".join(result.refinement_requirement_ids) or "-"
        lines.append(
            f"{result.case_id} | {result.policy} | "
            f"{result.critical_context_miss_rate:.3f} | {cost} | "
            f"{result.context_reduction_ratio_items:.3f} | "
            f"{result.context_status} | {refine}"
        )
    return "\n".join(lines)
