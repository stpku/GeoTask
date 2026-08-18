"""Offline replay of compact TC1-Real spatial-planning measurements.

This module deliberately remains in the benchmark layer. It converts already
measured provider evidence into the existing GeoTask Task Context contracts;
it does not add spatial-containment semantics or planning rules to Core.

A broader provider scope is normalized to a narrower requirement scope only
when the compact measurement explicitly proves the required subset relation.

The real Phoenix experiment discovered that the frozen broad R0 population
context has a source coverage gap. R0 is therefore retained as a diagnostic
upper bound rather than forced into the headline comparison. The scored
headline comparison is R1 vs RG, because both use the same task-area P1/P2
requirements and differ only in the predeclared P3 refinement scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
)

from benchmarks.tc1_real.spatial_planning.experiment_spec import (
    EXISTING_LIBRARIES_REQUIREMENT_ID,
    FROZEN_POPULATION_VARIABLE,
    FROZEN_POPULATION_YEAR,
    HOTSPOT_LAND_USE_REQUIREMENT_ID,
    PROJECTED_POPULATION_REQUIREMENT_ID,
)


NETWORK_BYTES = "network_bytes"
TASK_SCOPE = "phx-planning-task-area"
HOTSPOT_SCOPE = "phx-planning-hotspot"


@dataclass(frozen=True)
class PlanningPolicyResult:
    policy: str
    context: TaskContext
    irrelevant_land_use_admission_rate: float


@dataclass(frozen=True)
class PlanningComparison:
    """Three-policy comparison for fixtures where R0 itself is complete.

    This remains useful for synthetic/controlled fixtures. The recorded Phoenix
    headline result must use :class:`TaskScopedPlanningComparison` because the
    frozen broad R0 population requirement has a measured coverage gap.
    """

    r0: PlanningPolicyResult
    r1: PlanningPolicyResult
    rg: PlanningPolicyResult
    rg_vs_r1_network_reduction_ratio: float


@dataclass(frozen=True)
class TaskScopedPlanningComparison:
    """Headline comparison for the real planning proof.

    R1 and RG cover the same frozen critical requirements. They differ only in
    P3 land-use refinement scope: task area for R1 versus the predeclared
    hotspot for RG.
    """

    r1: PlanningPolicyResult
    rg: PlanningPolicyResult
    rg_vs_r1_network_reduction_ratio: float


@dataclass(frozen=True)
class BroadPopulationDiagnostic:
    """Explicit status of frozen R0 P1 coverage; never coerced to zero."""

    complete_acquisition: bool
    unit_coverage_complete: bool
    unit_count: int
    covered_unit_count: int
    missing_unit_count: int



def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _scope_entry(
    measurement: Mapping[str, object], family: str, scope: str
) -> Mapping[str, object]:
    family_value = _mapping(measurement.get(family), family)
    entry = _mapping(family_value.get(scope), f"{family}.{scope}")
    if entry.get("complete") is not True:
        raise ValueError(f"{family}.{scope} is not proven complete")
    return entry


def _nonnegative_int(entry: Mapping[str, object], field: str, label: str) -> int:
    value = entry.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label}.{field} must be a non-negative integer")
    return value


def _relation(measurement: Mapping[str, object], name: str) -> bool:
    relations = _mapping(measurement.get("relations"), "relations")
    if relations.get(name) is not True:
        raise ValueError(f"required measured relation is not proven: {name}")
    return True


def _population_entry(
    measurement: Mapping[str, object], scope: str
) -> Mapping[str, object]:
    entry = _scope_entry(measurement, "population", scope)
    if entry.get("variable") != FROZEN_POPULATION_VARIABLE:
        raise ValueError("population variable differs from frozen experiment input")
    if entry.get("year") != FROZEN_POPULATION_YEAR:
        raise ValueError("population year differs from frozen experiment input")
    if entry.get("unit_coverage_complete") is not True:
        raise ValueError(f"population.{scope} does not cover every selected base unit")
    missing = entry.get("missing_unit_count")
    if missing != 0:
        raise ValueError(f"population.{scope} has missing selected base units")
    return entry


def broad_population_diagnostic(
    measurement: Mapping[str, object],
) -> BroadPopulationDiagnostic:
    population = _mapping(measurement.get("population"), "population")
    entry = _mapping(population.get("broad"), "population.broad")
    return BroadPopulationDiagnostic(
        complete_acquisition=entry.get("complete") is True,
        unit_coverage_complete=entry.get("unit_coverage_complete") is True,
        unit_count=_nonnegative_int(entry, "unit_count", "population.broad"),
        covered_unit_count=_nonnegative_int(
            entry, "covered_unit_count", "population.broad"
        ),
        missing_unit_count=_nonnegative_int(
            entry, "missing_unit_count", "population.broad"
        ),
    )


def _task(policy: str) -> TaskFrame:
    return TaskFrame(
        task_id=f"tc1-real-phx-library-context:{policy}",
        goal=(
            "Prepare bounded public-library service-coverage planning context; "
            "do not make an investment recommendation"
        ),
        subject_refs=("phoenix-public-library-service-coverage",),
        spatial_scope=TASK_SCOPE,
        temporal_scope=f"planning-horizon-{FROZEN_POPULATION_YEAR}",
        outputs=("planning_context_input",),
    )


def requirements() -> tuple[ContextRequirement, ...]:
    return (
        ContextRequirement(
            requirement_id=PROJECTED_POPULATION_REQUIREMENT_ID,
            what=f"{FROZEN_POPULATION_VARIABLE} population context for {FROZEN_POPULATION_YEAR}",
            reason="the frozen planning task needs projected household-population context",
            spatial_scope=TASK_SCOPE,
        ),
        ContextRequirement(
            requirement_id=EXISTING_LIBRARIES_REQUIREMENT_ID,
            what="existing public-library locations in the task area",
            reason="the planning context must include the currently represented service locations",
            spatial_scope=TASK_SCOPE,
        ),
        ContextRequirement(
            requirement_id=HOTSPOT_LAND_USE_REQUIREMENT_ID,
            what="land-use detail for the frozen local hotspot",
            reason="only the predeclared hotspot requires local land-use refinement",
            spatial_scope=HOTSPOT_SCOPE,
        ),
    )


def _candidate(
    *,
    candidate_id: str,
    source: str,
    requirement_id: str,
    spatial_scope: str,
    network_bytes: int,
    metadata: Mapping[str, object],
) -> ContextCandidate:
    return ContextCandidate(
        candidate_id=candidate_id,
        source=source,
        requirement_ids=(requirement_id,),
        spatial_scope=spatial_scope,
        acquisition_cost=float(network_bytes),
        cost_unit=NETWORK_BYTES,
        metadata=dict(metadata),
    )


def _population_candidate(
    measurement: Mapping[str, object], *, policy: str, scope: str
) -> ContextCandidate:
    growth = _scope_entry(measurement, "growth", scope)
    population = _population_entry(measurement, scope)
    if scope == "broad":
        _relation(measurement, "task_units_subset_broad")
    network = _nonnegative_int(growth, "network_bytes", f"growth.{scope}") + _nonnegative_int(
        population, "network_bytes", f"population.{scope}"
    )
    return _candidate(
        candidate_id=f"{policy}-population-{scope}",
        source="phx-growth-projections",
        requirement_id=PROJECTED_POPULATION_REQUIREMENT_ID,
        spatial_scope=TASK_SCOPE,
        network_bytes=network,
        metadata={
            "provider_scope": scope,
            "normalized_requirement_scope": TASK_SCOPE,
            "base_unit_complete": True,
            "population_unit_coverage_complete": True,
            "population_variable": FROZEN_POPULATION_VARIABLE,
            "population_year": FROZEN_POPULATION_YEAR,
        },
    )


def _libraries_candidate(
    measurement: Mapping[str, object], *, policy: str, scope: str
) -> ContextCandidate:
    entry = _scope_entry(measurement, "libraries", scope)
    if scope == "broad":
        _relation(measurement, "library_task_subset_broad")
    return _candidate(
        candidate_id=f"{policy}-libraries-{scope}",
        source="phx-libraries",
        requirement_id=EXISTING_LIBRARIES_REQUIREMENT_ID,
        spatial_scope=TASK_SCOPE,
        network_bytes=_nonnegative_int(entry, "network_bytes", f"libraries.{scope}"),
        metadata={
            "provider_scope": scope,
            "normalized_requirement_scope": TASK_SCOPE,
        },
    )


def _land_use_candidate(
    measurement: Mapping[str, object], *, policy: str, scope: str
) -> ContextCandidate:
    entry = _scope_entry(measurement, "land_use", scope)
    if scope == "broad":
        _relation(measurement, "land_task_subset_broad")
        _relation(measurement, "land_hotspot_subset_task")
    elif scope == "task":
        _relation(measurement, "land_hotspot_subset_task")
    elif scope != "hotspot":
        raise ValueError(f"unsupported land-use scope: {scope}")
    return _candidate(
        candidate_id=f"{policy}-land-use-{scope}",
        source="phx-land-use-zones",
        requirement_id=HOTSPOT_LAND_USE_REQUIREMENT_ID,
        spatial_scope=HOTSPOT_SCOPE,
        network_bytes=_nonnegative_int(entry, "network_bytes", f"land_use.{scope}"),
        metadata={
            "provider_scope": scope,
            "normalized_requirement_scope": HOTSPOT_SCOPE,
        },
    )


def _irrelevant_land_use_rate(
    measurement: Mapping[str, object], scope: str
) -> float:
    entry = _scope_entry(measurement, "land_use", scope)
    hotspot = _scope_entry(measurement, "land_use", "hotspot")
    admitted = _nonnegative_int(entry, "id_count", f"land_use.{scope}")
    required = _nonnegative_int(hotspot, "id_count", "land_use.hotspot")
    if admitted == 0:
        raise ValueError("land-use admitted count must be > 0")
    if required > admitted:
        raise ValueError("hotspot land-use count cannot exceed admitted scope count")
    if scope == "hotspot":
        if admitted != required:
            raise ValueError("hotspot land-use measurement is internally inconsistent")
        return 0.0
    return (admitted - required) / admitted


def assess_policy(
    measurement: Mapping[str, object], policy: str
) -> PlanningPolicyResult:
    if policy == "R0":
        population_scope = library_scope = land_scope = "broad"
    elif policy == "R1":
        population_scope = library_scope = land_scope = "task"
    elif policy == "RG":
        population_scope = library_scope = "task"
        land_scope = "hotspot"
    else:
        raise ValueError(f"unsupported planning policy: {policy}")

    candidates = (
        _population_candidate(measurement, policy=policy, scope=population_scope),
        _libraries_candidate(measurement, policy=policy, scope=library_scope),
        _land_use_candidate(measurement, policy=policy, scope=land_scope),
    )
    context = assess_task_context(_task(policy), requirements(), candidates)
    return PlanningPolicyResult(
        policy=policy,
        context=context,
        irrelevant_land_use_admission_rate=_irrelevant_land_use_rate(
            measurement, land_scope
        ),
    )


def _headline_pair(
    measurement: Mapping[str, object],
) -> tuple[PlanningPolicyResult, PlanningPolicyResult, float]:
    r1 = assess_policy(measurement, "R1")
    rg = assess_policy(measurement, "RG")
    if not (r1.context.sufficient and rg.context.sufficient):
        raise ValueError("R1/RG must both cover the frozen critical requirements")
    if r1.context.total_acquisition_cost <= 0:
        raise ValueError("R1 network burden must be > 0")
    reduction = 1.0 - rg.context.total_acquisition_cost / r1.context.total_acquisition_cost
    return r1, rg, reduction


def compare_task_scoped_policies(
    measurement: Mapping[str, object],
) -> TaskScopedPlanningComparison:
    """Compare the two real headline policies without repairing broad R0 gaps."""

    r1, rg, reduction = _headline_pair(measurement)
    return TaskScopedPlanningComparison(
        r1=r1,
        rg=rg,
        rg_vs_r1_network_reduction_ratio=reduction,
    )


def compare_policies(measurement: Mapping[str, object]) -> PlanningComparison:
    """Compare R0/R1/RG only when the supplied fixture proves R0 complete."""

    r0 = assess_policy(measurement, "R0")
    r1, rg, reduction = _headline_pair(measurement)
    if not r0.context.sufficient:
        raise ValueError("R0 must cover the frozen critical requirements")
    return PlanningComparison(
        r0=r0,
        r1=r1,
        rg=rg,
        rg_vs_r1_network_reduction_ratio=reduction,
    )
