"""GT-C6 independent consumer: warehouse robot picking context assembly.

This example intentionally lives outside ``src/geotask_core``. It demonstrates that
an independent consumer can compose the GeoTask Task Context Engine from three
non-WorldState runtime providers:

* indoor GIS / topology data;
* inventory API data;
* aisle-clearance sensor data.

The consumer never decides whether the robot should execute the pick. A narrow aisle
may still yield *sufficient context* when the measurement is relevant, applicable,
fresh, and spatially/temporally adequate. Domain action remains downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Mapping, Sequence

from geotask_core.v1.assessment_composition import (
    RequirementAssessmentEvidence,
    assess_requirement_from_evidence,
    compose_sufficiency_assessment,
)
from geotask_core.v1.construction_binding import (
    bind_sufficiency_to_construction,
    construct_bound_context,
)
from geotask_core.v1.context_construction import (
    AssessedContextItem,
    ContextConstructionRequest,
    ContextConstructionResult,
    DeterministicContextConstructor,
)
from geotask_core.v1.context_minimality import (
    ContextContribution,
    ContextCostVector,
    ContextMinimalityAssessment,
    MinimumSufficientTaskContext,
    assess_context_minimality,
    build_minimum_sufficient_task_context,
)
from geotask_core.v1.context_provider import (
    ApplicabilityResult,
    ContextCandidate,
    ContextProvider,
    RelevanceResult,
    ResolutionRequirement,
    validate_provider_candidates,
)
from geotask_core.v1.requirement_derivation import (
    RequirementDerivationResult,
    RequirementDerivationRule,
    RequirementTemplate,
    derive_context_requirements,
)
from geotask_core.v1.resolution_adequacy import (
    ResolutionAdequacyResult,
    ResolutionDimensionEvidence,
    assess_resolution_adequacy,
)
from geotask_core.v1.task_context import (
    ContextAssessment,
    ContextGap,
    ContextRequirement,
    JSONValue,
    SufficiencyAssessment,
    TaskContext,
    TaskFrame,
)
from geotask_core.v1.temporal_continuity import (
    TemporalContextContinuityPlan,
    TemporalContextRefreshResult,
    TemporalRequirementRefresh,
    apply_temporal_context_refresh,
    plan_temporal_context_continuity,
)
from geotask_core.v1.temporal_reassessment import (
    TemporalReassessmentPlan,
    plan_temporal_reassessment,
)

WAREHOUSE_CONSUMER_VERSION = "0.1"
DEFAULT_AS_OF = "2026-08-25T20:00:00+08:00"
DEFAULT_REFRESHED_AT = "2026-08-25T20:05:00+08:00"

WAREHOUSE_ID = "warehouse-7"
TARGET_BIN = "bin-17"
ROUTE_AISLE = "aisle-3"
PACKING_STATION = "packing-2"

GIS_PROVIDER_REF = "provider://warehouse-gis/v0.1"
INVENTORY_PROVIDER_REF = "provider://inventory-api/v0.1"
SENSOR_PROVIDER_REF = "provider://aisle-clearance-sensor/v0.1"

GIS_SOURCE_REF = "gis://warehouse-7/floor-map/revision-4"
ZONE_SOURCE_REF = "gis://warehouse-7/zone-annotation/revision-2"
INVENTORY_SOURCE_REF = "api://inventory/bin-17/current"
SENSOR_SOURCE_REF = "sensor://warehouse-7/aisle-3/clearance"

REQUIREMENT_METHOD_REF = "geotask://independent-consumer/warehouse/requirement-method-v0.1"
SUFFICIENCY_METHOD_REF = "geotask://independent-consumer/warehouse/sufficiency-method-v0.1"
RESOLUTION_METHOD_REF = "geotask://independent-consumer/warehouse/resolution-method-v0.1"
MINIMALITY_METHOD_REF = "geotask://independent-consumer/warehouse/minimality-method-v0.1"
TEMPORAL_SUFFICIENCY_METHOD_REF = (
    "geotask://independent-consumer/warehouse/temporal-sufficiency-method-v0.1"
)


@dataclass(frozen=True, slots=True)
class WarehouseProviderSnapshot:
    """Deterministic provider state used by the independent consumer proof."""

    map_cell_size_m: float = 0.25
    inventory_age_seconds: float = 15.0
    sensor_age_seconds: float = 2.0
    sensor_aisle: str = ROUTE_AISLE
    sensor_clearance_m: float = 1.60
    zone_annotation_cell_size_m: float = 1.0
    inventory_quantity: int = 8
    revision: str = "r1"


@dataclass(frozen=True, slots=True)
class RequirementCognition:
    requirement: ContextRequirement
    candidate: ContextCandidate
    relevance: RelevanceResult
    applicability: ApplicabilityResult
    resolution: ResolutionAdequacyResult
    item: AssessedContextItem


@dataclass(frozen=True, slots=True)
class WarehouseContextRun:
    task: TaskFrame
    derivation: RequirementDerivationResult
    cognition: tuple[RequirementCognition, ...]
    construction: ContextConstructionResult
    minimum: MinimumSufficientTaskContext | None
    providers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WarehouseTemporalRun:
    reassessment: TemporalReassessmentPlan
    continuity: TemporalContextContinuityPlan
    refresh: TemporalContextRefreshResult
    reminimum: MinimumSufficientTaskContext | None


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _payload_bytes(value: object) -> int:
    return len(
        json.dumps(
            _plain(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def warehouse_pick_task(*, task_id: str = "task-warehouse-pick-1") -> TaskFrame:
    return TaskFrame(
        task_id=task_id,
        task_type="warehouse_pick",
        goal="Build sufficient context for picking an item and returning to packing",
        scope_refs=(WAREHOUSE_ID, TARGET_BIN, ROUTE_AISLE, PACKING_STATION),
        metadata={
            "warehouse_id": WAREHOUSE_ID,
            "target_bin": TARGET_BIN,
            "route_aisles": [ROUTE_AISLE],
            "packing_station": PACKING_STATION,
            "robot_width_m": 0.90,
        },
    )


def warehouse_requirement_rules() -> tuple[RequirementDerivationRule, ...]:
    """Domain profile lives in the consumer, not GeoTask Core."""

    return (
        RequirementDerivationRule(
            rule_id="warehouse-pick-independent-consumer-v0.1",
            task_types=("warehouse_pick",),
            templates=(
                RequirementTemplate(
                    template_id="route-geometry",
                    kind="route-geometry",
                    description="Indoor route geometry covering the pick path",
                    critical=True,
                    constraints={"max_cell_size_m": 0.5},
                ),
                RequirementTemplate(
                    template_id="bin-inventory",
                    kind="bin-inventory",
                    description="Current inventory state for the target bin",
                    critical=True,
                    constraints={"max_age_seconds": 60.0},
                ),
                RequirementTemplate(
                    template_id="aisle-clearance",
                    kind="aisle-clearance",
                    description="Current measured clearance on the planned aisle",
                    critical=True,
                    constraints={"max_age_seconds": 10.0},
                ),
                RequirementTemplate(
                    template_id="zone-annotation",
                    kind="zone-annotation",
                    description="Optional storage-zone annotation useful for explanation",
                    critical=False,
                    constraints={"max_cell_size_m": 2.0},
                ),
            ),
        ),
    )


class WarehouseGISProvider(ContextProvider):
    def __init__(self, snapshot: WarehouseProviderSnapshot) -> None:
        self.snapshot = snapshot

    @property
    def provider_ref(self) -> str:
        return GIS_PROVIDER_REF

    def get_candidates(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        *,
        as_of: str,
    ) -> tuple[ContextCandidate, ...]:
        if requirement.kind == "route-geometry":
            return (
                ContextCandidate(
                    candidate_ref=f"candidate://warehouse-gis/route/{self.snapshot.revision}",
                    requirement_id=requirement.requirement_id,
                    provider_ref=self.provider_ref,
                    payload={
                        "warehouse_id": WAREHOUSE_ID,
                        "route_aisles": [ROUTE_AISLE],
                        "segments": [
                            {"from": "start", "to": ROUTE_AISLE, "length_m": 18.0},
                            {"from": ROUTE_AISLE, "to": TARGET_BIN, "length_m": 6.5},
                        ],
                    },
                    source_refs=(GIS_SOURCE_REF,),
                    metadata={
                        "purpose": "route-geometry",
                        "warehouse_id": WAREHOUSE_ID,
                        "cell_size_m": self.snapshot.map_cell_size_m,
                        "as_of": as_of,
                    },
                ),
            )
        if requirement.kind == "zone-annotation":
            return (
                ContextCandidate(
                    candidate_ref=f"candidate://warehouse-gis/zones/{self.snapshot.revision}",
                    requirement_id=requirement.requirement_id,
                    provider_ref=self.provider_ref,
                    payload={
                        "warehouse_id": WAREHOUSE_ID,
                        "zone": "storage-zone-b",
                        "annotation": "high-rack storage",
                    },
                    source_refs=(ZONE_SOURCE_REF,),
                    metadata={
                        "purpose": "zone-annotation",
                        "warehouse_id": WAREHOUSE_ID,
                        "cell_size_m": self.snapshot.zone_annotation_cell_size_m,
                        "as_of": as_of,
                    },
                ),
            )
        return ()


class WarehouseInventoryAPIProvider(ContextProvider):
    def __init__(self, snapshot: WarehouseProviderSnapshot) -> None:
        self.snapshot = snapshot

    @property
    def provider_ref(self) -> str:
        return INVENTORY_PROVIDER_REF

    def get_candidates(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        *,
        as_of: str,
    ) -> tuple[ContextCandidate, ...]:
        if requirement.kind != "bin-inventory":
            return ()
        return (
            ContextCandidate(
                candidate_ref=f"candidate://inventory/bin-17/{self.snapshot.revision}",
                requirement_id=requirement.requirement_id,
                provider_ref=self.provider_ref,
                payload={
                    "bin_id": TARGET_BIN,
                    "sku": "sku-42",
                    "quantity": self.snapshot.inventory_quantity,
                },
                source_refs=(INVENTORY_SOURCE_REF,),
                metadata={
                    "purpose": "bin-inventory",
                    "bin_id": TARGET_BIN,
                    "age_seconds": self.snapshot.inventory_age_seconds,
                    "as_of": as_of,
                },
            ),
        )


class WarehouseAisleSensorProvider(ContextProvider):
    def __init__(self, snapshot: WarehouseProviderSnapshot) -> None:
        self.snapshot = snapshot

    @property
    def provider_ref(self) -> str:
        return SENSOR_PROVIDER_REF

    def get_candidates(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        *,
        as_of: str,
    ) -> tuple[ContextCandidate, ...]:
        if requirement.kind != "aisle-clearance":
            return ()
        source_ref = (
            SENSOR_SOURCE_REF
            if self.snapshot.sensor_aisle == ROUTE_AISLE
            else f"sensor://warehouse-7/{self.snapshot.sensor_aisle}/clearance"
        )
        return (
            ContextCandidate(
                candidate_ref=(
                    f"candidate://aisle-sensor/{self.snapshot.sensor_aisle}/{self.snapshot.revision}"
                ),
                requirement_id=requirement.requirement_id,
                provider_ref=self.provider_ref,
                payload={
                    "aisle_id": self.snapshot.sensor_aisle,
                    "clearance_m": self.snapshot.sensor_clearance_m,
                },
                source_refs=(source_ref,),
                metadata={
                    "purpose": "aisle-clearance",
                    "aisle_id": self.snapshot.sensor_aisle,
                    "age_seconds": self.snapshot.sensor_age_seconds,
                    "as_of": as_of,
                },
            ),
        )


class WarehouseResolutionMethod:
    @property
    def method_ref(self) -> str:
        return RESOLUTION_METHOD_REF

    def assess_resolution(
        self,
        requirement: ResolutionRequirement,
        candidate: ContextCandidate,
        *,
        as_of: str,
    ) -> ResolutionAdequacyResult:
        dimensions: list[ResolutionDimensionEvidence] = []
        for name, required in requirement.dimensions.items():
            if name == "max_cell_size_m":
                observed = candidate.metadata.get("cell_size_m")
            elif name == "max_age_seconds":
                observed = candidate.metadata.get("age_seconds")
            else:
                observed = None

            if not isinstance(required, (int, float)) or isinstance(required, bool):
                status = "unknown"
                reason = "benchmark method supports numeric maximum dimensions only"
            elif not isinstance(observed, (int, float)) or isinstance(observed, bool):
                status = "unknown"
                reason = "candidate did not expose the required observed resolution"
            elif float(observed) <= float(required):
                status = "adequate"
                reason = f"observed {observed} <= required maximum {required}"
            else:
                status = "inadequate"
                reason = f"observed {observed} exceeds required maximum {required}"

            dimensions.append(
                ResolutionDimensionEvidence(
                    dimension=name,
                    status=status,
                    required=required,
                    observed=observed,
                    reason=reason,
                    source_refs=(candidate.candidate_ref, *candidate.source_refs),
                )
            )

        statuses = {item.status for item in dimensions}
        if "inadequate" in statuses:
            aggregate = "inadequate"
        elif "unknown" in statuses or not dimensions:
            aggregate = "unknown"
        elif "degraded" in statuses:
            aggregate = "degraded"
        else:
            aggregate = "adequate"
        return ResolutionAdequacyResult(
            adequacy_ref=f"{candidate.candidate_ref}/resolution/{self.method_ref.rsplit('/', 1)[-1]}",
            resolution_ref=requirement.resolution_ref,
            requirement_id=requirement.requirement_id,
            candidate_ref=candidate.candidate_ref,
            method_ref=self.method_ref,
            status=aggregate,
            assessed_at=as_of,
            reason="warehouse consumer task-relative resolution assessment",
            dimensions=tuple(dimensions),
            source_refs=_dedupe((self.method_ref, candidate.candidate_ref, *candidate.source_refs)),
        )


class WarehouseRequirementAssessmentMethod:
    @property
    def method_ref(self) -> str:
        return REQUIREMENT_METHOD_REF

    def assess_requirement(
        self,
        task_frame: TaskFrame,
        requirement: ContextRequirement,
        candidate: ContextCandidate,
        evidence: RequirementAssessmentEvidence,
        *,
        as_of: str,
    ) -> ContextAssessment:
        relevance = None if evidence.relevance is None else evidence.relevance.status
        applicability = None if evidence.applicability is None else evidence.applicability.status
        resolution = (
            None if evidence.resolution_adequacy is None else evidence.resolution_adequacy.status
        )

        if relevance == "not_relevant":
            status = "insufficient"
            reason = "candidate does not concern the derived task requirement"
        elif relevance == "unknown":
            status = "unknown"
            reason = "candidate relevance is unresolved"
        elif applicability == "not_applicable":
            status = "not_applicable"
            reason = "candidate is relevant but outside current task scope"
        elif applicability == "unknown":
            status = "unknown"
            reason = "candidate applicability is unresolved"
        elif resolution == "inadequate":
            status = "insufficient"
            reason = "candidate resolution is inadequate for this task"
        elif resolution == "unknown":
            status = "unknown"
            reason = "candidate resolution adequacy is unresolved"
        elif resolution == "degraded":
            status = "degraded"
            reason = "candidate is usable only with degraded resolution"
        else:
            status = "satisfied"
            reason = "candidate is relevant, applicable, and resolution-adequate"

        return ContextAssessment(
            requirement_id=requirement.requirement_id,
            critical=requirement.critical,
            status=status,
            assessed_at=as_of,
            reason=reason,
            source_refs=_dedupe(
                (
                    self.method_ref,
                    evidence.evidence_ref,
                    candidate.candidate_ref,
                    candidate.provider_ref,
                    *candidate.source_refs,
                    *evidence.source_refs,
                )
            ),
        )


class WarehouseSufficiencyMethod:
    @property
    def method_ref(self) -> str:
        return SUFFICIENCY_METHOD_REF

    def compose_sufficiency(
        self,
        *,
        context_ref: str,
        requirements: tuple[ContextRequirement, ...],
        assessments: tuple[ContextAssessment, ...],
        gaps: tuple[ContextGap, ...],
        as_of: str,
        valid_until: str | None,
        trace_ref: str | None,
    ) -> SufficiencyAssessment:
        status = _sufficiency_status(requirements, assessments)
        return SufficiencyAssessment(
            assessment_ref=f"{context_ref}/sufficiency",
            context_ref=context_ref,
            assessed_at=as_of,
            status=status,
            assessments=assessments,
            gaps=gaps,
            source_refs=_dedupe(
                (
                    self.method_ref,
                    *(ref for assessment in assessments for ref in assessment.source_refs),
                    *(ref for gap in gaps for ref in gap.source_refs),
                )
            ),
            valid_until=valid_until,
            trace_ref=trace_ref,
        )


class WarehouseMinimalityMethod:
    @property
    def method_ref(self) -> str:
        return MINIMALITY_METHOD_REF

    def assess_minimality(
        self,
        context: TaskContext,
        sufficiency: SufficiencyAssessment,
        costs: Mapping[str, ContextCostVector],
        *,
        target_context_ref: str,
        as_of: str,
    ) -> ContextMinimalityAssessment:
        requirement_by_id = {item.requirement_id: item for item in context.requirements}
        contributions: list[ContextContribution] = []
        retained: list[str] = []
        removed: list[str] = []
        for requirement_id in context.values:
            requirement = requirement_by_id[requirement_id]
            removable = requirement.kind == "zone-annotation" and not requirement.critical
            status = "removable" if removable else "required"
            if removable:
                removed.append(requirement_id)
                reason = "optional explanatory zone annotation is not required for task sufficiency"
            else:
                retained.append(requirement_id)
                reason = "value supports a critical warehouse-pick context requirement"
            contributions.append(
                ContextContribution(
                    contribution_ref=f"{context.context_ref}/contribution/{requirement.kind}",
                    context_ref=context.context_ref,
                    requirement_id=requirement_id,
                    status=status,
                    reason=reason,
                    cost=costs[requirement_id],
                    source_refs=(self.method_ref,),
                )
            )
        return ContextMinimalityAssessment(
            assessment_ref=f"{context.context_ref}/minimality",
            source_context_ref=context.context_ref,
            target_context_ref=target_context_ref,
            method_ref=self.method_ref,
            assessed_at=as_of,
            status="minimal",
            contributions=tuple(contributions),
            retained_requirement_ids=tuple(retained),
            removed_requirement_ids=tuple(removed),
            source_refs=(self.method_ref,),
        )


def _sufficiency_status(
    requirements: Sequence[ContextRequirement],
    assessments: Sequence[ContextAssessment],
) -> str:
    requirement_by_id = {item.requirement_id: item for item in requirements}
    critical = [
        item
        for item in assessments
        if requirement_by_id[item.requirement_id].critical
    ]
    statuses = {item.status for item in critical}
    if "blocked" in statuses:
        return "blocked"
    if "unknown" in statuses:
        return "unknown"
    if any(item.status != "satisfied" for item in critical):
        return "insufficient"
    return "sufficient"


def _provider_for_requirement(
    requirement: ContextRequirement,
    providers: Sequence[ContextProvider],
) -> ContextProvider:
    expected = {
        "route-geometry": GIS_PROVIDER_REF,
        "zone-annotation": GIS_PROVIDER_REF,
        "bin-inventory": INVENTORY_PROVIDER_REF,
        "aisle-clearance": SENSOR_PROVIDER_REF,
    }[requirement.kind]
    return next(provider for provider in providers if provider.provider_ref == expected)


def _relevance(
    requirement: ContextRequirement,
    candidate: ContextCandidate,
    *,
    as_of: str,
) -> RelevanceResult:
    purpose = candidate.metadata.get("purpose")
    relevant = purpose == requirement.kind
    return RelevanceResult(
        relevance_ref=f"{candidate.candidate_ref}/relevance",
        requirement_id=requirement.requirement_id,
        candidate_ref=candidate.candidate_ref,
        status="relevant" if relevant else "not_relevant",
        assessed_at=as_of,
        reason=(
            "candidate purpose matches requirement kind"
            if relevant
            else "candidate purpose differs from requirement kind"
        ),
        source_refs=(candidate.candidate_ref, *candidate.source_refs),
    )


def _applicability(
    task: TaskFrame,
    requirement: ContextRequirement,
    candidate: ContextCandidate,
    *,
    as_of: str,
) -> ApplicabilityResult:
    if requirement.kind in {"route-geometry", "zone-annotation"}:
        applicable = candidate.metadata.get("warehouse_id") == task.metadata.get("warehouse_id")
        reason = "candidate warehouse matches task warehouse"
    elif requirement.kind == "bin-inventory":
        applicable = candidate.metadata.get("bin_id") == task.metadata.get("target_bin")
        reason = "candidate bin matches task target bin"
    elif requirement.kind == "aisle-clearance":
        route_aisles = task.metadata.get("route_aisles", ())
        applicable = candidate.metadata.get("aisle_id") in route_aisles
        reason = "sensor aisle intersects the planned route"
    else:
        applicable = False
        reason = "consumer has no applicability method for this requirement kind"
    return ApplicabilityResult(
        applicability_ref=f"{candidate.candidate_ref}/applicability",
        requirement_id=requirement.requirement_id,
        candidate_ref=candidate.candidate_ref,
        status="applicable" if applicable else "not_applicable",
        assessed_at=as_of,
        reason=reason if applicable else f"not applicable: {reason}",
        source_refs=(candidate.candidate_ref, *candidate.source_refs),
    )


def _resolution_requirement(requirement: ContextRequirement) -> ResolutionRequirement:
    dimensions = {
        key: value
        for key, value in requirement.constraints.items()
        if key in {"max_cell_size_m", "max_age_seconds"}
    }
    return ResolutionRequirement(
        resolution_ref=f"{requirement.requirement_id}/resolution-requirement",
        requirement_id=requirement.requirement_id,
        critical=requirement.critical,
        dimensions=dimensions,
        reason="warehouse-pick task-relative provider resolution requirement",
        source_refs=(requirement.requirement_id,),
    )


def _assess_candidate(
    task: TaskFrame,
    requirement: ContextRequirement,
    candidate: ContextCandidate,
    *,
    as_of: str,
) -> RequirementCognition:
    relevance = _relevance(requirement, candidate, as_of=as_of)
    applicability = _applicability(task, requirement, candidate, as_of=as_of)
    resolution_requirement = _resolution_requirement(requirement)
    resolution = assess_resolution_adequacy(
        WarehouseResolutionMethod(),
        resolution_requirement,
        candidate,
        as_of=as_of,
    )
    evidence = RequirementAssessmentEvidence(
        evidence_ref=f"{candidate.candidate_ref}/assessment-evidence/{as_of}",
        requirement_id=requirement.requirement_id,
        candidate_ref=candidate.candidate_ref,
        assembled_at=as_of,
        relevance=relevance,
        applicability=applicability,
        resolution_adequacy=resolution,
        source_refs=(
            relevance.relevance_ref,
            applicability.applicability_ref,
            resolution.adequacy_ref,
        ),
    )
    item = assess_requirement_from_evidence(
        WarehouseRequirementAssessmentMethod(),
        task,
        requirement,
        candidate,
        evidence,
        as_of=as_of,
    )
    return RequirementCognition(
        requirement=requirement,
        candidate=candidate,
        relevance=relevance,
        applicability=applicability,
        resolution=resolution,
        item=item,
    )


def _context_costs(context: TaskContext) -> Mapping[str, ContextCostVector]:
    requirement_by_id = {item.requirement_id: item for item in context.requirements}
    declared = {
        "route-geometry": (5.0, 64, 18.0),
        "bin-inventory": (2.0, 36, 7.0),
        "aisle-clearance": (1.0, 28, 3.0),
        "zone-annotation": (1.0, 24, 5.0),
    }
    result: dict[str, ContextCostVector] = {}
    for requirement_id, value in context.values.items():
        requirement = requirement_by_id[requirement_id]
        acquisition, llm_units, latency = declared[requirement.kind]
        result[requirement_id] = ContextCostVector(
            acquisition_units=acquisition,
            carried_bytes=_payload_bytes(value),
            llm_units=llm_units,
            provider_latency_ms=latency,
            human_recovery_units=1.0 if requirement.critical else 0.0,
        )
    return MappingProxyType(result)


def _minimum_context(
    construction: ContextConstructionResult,
    *,
    as_of: str,
    target_context_ref: str,
) -> MinimumSufficientTaskContext | None:
    if construction.sufficiency.status != "sufficient":
        return None
    minimality = assess_context_minimality(
        WarehouseMinimalityMethod(),
        construction.context,
        construction.sufficiency,
        _context_costs(construction.context),
        target_context_ref=target_context_ref,
        as_of=as_of,
    )
    target_sufficiency = SufficiencyAssessment(
        assessment_ref=f"{target_context_ref}/sufficiency",
        context_ref=target_context_ref,
        assessed_at=as_of,
        status="sufficient",
        assessments=construction.sufficiency.assessments,
        gaps=construction.sufficiency.gaps,
        source_refs=_dedupe(
            (
                MINIMALITY_METHOD_REF,
                minimality.assessment_ref,
                *construction.sufficiency.source_refs,
            )
        ),
        valid_until=construction.sufficiency.valid_until,
        trace_ref=None,
    )
    return build_minimum_sufficient_task_context(
        construction.context,
        construction.sufficiency,
        minimality,
        target_sufficiency,
    )


def build_warehouse_pick_context(
    snapshot: WarehouseProviderSnapshot = WarehouseProviderSnapshot(),
    *,
    as_of: str = DEFAULT_AS_OF,
    task_id: str = "task-warehouse-pick-1",
) -> WarehouseContextRun:
    task = warehouse_pick_task(task_id=task_id)
    derivation = derive_context_requirements(task, warehouse_requirement_rules())
    providers: tuple[ContextProvider, ...] = (
        WarehouseGISProvider(snapshot),
        WarehouseInventoryAPIProvider(snapshot),
        WarehouseAisleSensorProvider(snapshot),
    )

    cognition: list[RequirementCognition] = []
    for requirement in derivation.requirements:
        provider = _provider_for_requirement(requirement, providers)
        candidates = provider.get_candidates(task, requirement, as_of=as_of)
        validate_provider_candidates(provider, requirement, candidates)
        if len(candidates) != 1:
            raise ValueError(
                f"warehouse independent consumer expects exactly one candidate for {requirement.kind}"
            )
        cognition.append(_assess_candidate(task, requirement, candidates[0], as_of=as_of))

    items = tuple(item.item for item in cognition)
    assessments = tuple(item.assessment for item in items)
    gaps = tuple(item.gap for item in items if item.gap is not None)
    context_ref = f"geotask://independent-consumer/warehouse/{task_id}/full"
    trace_ref = f"{context_ref}/trace"
    sufficiency = compose_sufficiency_assessment(
        WarehouseSufficiencyMethod(),
        context_ref=context_ref,
        requirements=derivation.requirements,
        assessments=assessments,
        gaps=gaps,
        as_of=as_of,
        valid_until=None,
        trace_ref=trace_ref,
    )
    request = ContextConstructionRequest(
        request_ref=f"{context_ref}/request",
        context_ref=context_ref,
        assessment_ref=sufficiency.assessment_ref,
        trace_ref=trace_ref,
        task_frame=task,
        requirements=derivation.requirements,
        items=items,
        constructed_at=as_of,
        assessed_at=as_of,
        sufficiency_status=sufficiency.status,
        valid_until=None,
        method="warehouse-independent-consumer-v0.1",
        version=WAREHOUSE_CONSUMER_VERSION,
        source_refs=(derivation.result_ref,),
    )
    bound = bind_sufficiency_to_construction(
        request,
        sufficiency,
        binding_ref=f"{context_ref}/sufficiency-binding",
        sufficiency_method_ref=SUFFICIENCY_METHOD_REF,
        bound_at=as_of,
    )
    construction = construct_bound_context(DeterministicContextConstructor(), bound)
    minimum = _minimum_context(
        construction,
        as_of=as_of,
        target_context_ref=f"geotask://independent-consumer/warehouse/{task_id}/minimum",
    )
    return WarehouseContextRun(
        task=task,
        derivation=derivation,
        cognition=tuple(cognition),
        construction=construction,
        minimum=minimum,
        providers=tuple(provider.provider_ref for provider in providers),
    )


def provider_delta_for_sensor_change(*, delta_id: str = "warehouse-sensor-change-1") -> dict[str, object]:
    """Map an independent sensor change to the existing provider-neutral delta wire.

    This is a wire-shape adapter only. No official WorldState runtime is imported or
    required by the consumer.
    """

    return {
        "contract": "worldstate.delta",
        "contract_version": "0.1",
        "delta_id": f"delta://independent-consumer/{delta_id}",
        "changes": [
            {
                "affected_state_refs": [SENSOR_SOURCE_REF],
                "source_refs": [f"sensor-change://{delta_id}"],
            }
        ],
    }


def refresh_after_sensor_change(
    prior: WarehouseContextRun,
    updated_snapshot: WarehouseProviderSnapshot,
    *,
    refreshed_at: str = DEFAULT_REFRESHED_AT,
) -> WarehouseTemporalRun:
    if prior.minimum is None:
        raise ValueError("temporal continuity proof requires a prior minimum sufficient context")

    prior_minimum = prior.minimum
    reassessment = plan_temporal_reassessment(
        prior_minimum.context,
        prior_minimum.sufficiency,
        provider_delta_for_sensor_change(delta_id=updated_snapshot.revision),
    )
    continuity = plan_temporal_context_continuity(
        prior_minimum.context,
        prior_minimum.sufficiency,
        reassessment,
        prior_minimality=prior_minimum.minimality,
    )

    requirement_by_id = {item.requirement_id: item for item in prior_minimum.context.requirements}
    refreshes: list[TemporalRequirementRefresh] = []
    sensor_provider = WarehouseAisleSensorProvider(updated_snapshot)
    for requirement_id in continuity.refresh_requirement_ids:
        requirement = requirement_by_id[requirement_id]
        if requirement.kind != "aisle-clearance":
            raise ValueError("this reference temporal proof expects only the aisle sensor to change")
        candidates = sensor_provider.get_candidates(prior.task, requirement, as_of=refreshed_at)
        validate_provider_candidates(sensor_provider, requirement, candidates)
        cognition = _assess_candidate(prior.task, requirement, candidates[0], as_of=refreshed_at)
        refresh_ref = (
            f"geotask://independent-consumer/warehouse/refresh/"
            f"{updated_snapshot.revision}/{requirement.kind}"
        )
        refreshes.append(
            TemporalRequirementRefresh(
                refresh_ref=refresh_ref,
                requirement_id=requirement_id,
                assessment=cognition.item.assessment,
                value_present=cognition.item.selected_candidate is not None,
                value=(
                    None
                    if cognition.item.selected_candidate is None
                    else cognition.item.selected_candidate.payload
                ),
                gap=cognition.item.gap,
                source_refs=_dedupe(
                    (
                        refresh_ref,
                        sensor_provider.provider_ref,
                        candidates[0].candidate_ref,
                        *candidates[0].source_refs,
                    )
                ),
            )
        )

    refresh_by_id = {item.requirement_id: item for item in refreshes}
    merged_assessments = tuple(
        refresh_by_id.get(assessment.requirement_id, None).assessment
        if assessment.requirement_id in refresh_by_id
        else assessment
        for assessment in prior_minimum.sufficiency.assessments
    )
    affected = set(continuity.refresh_requirement_ids)
    merged_gaps = tuple(
        gap for gap in prior_minimum.sufficiency.gaps if gap.requirement_id not in affected
    ) + tuple(item.gap for item in refreshes if item.gap is not None)
    target_context_ref = (
        f"geotask://independent-consumer/warehouse/{prior.task.task_id}/temporal/{updated_snapshot.revision}"
    )
    target_sufficiency = SufficiencyAssessment(
        assessment_ref=f"{target_context_ref}/sufficiency",
        context_ref=target_context_ref,
        assessed_at=refreshed_at,
        status=_sufficiency_status(prior_minimum.context.requirements, merged_assessments),
        assessments=merged_assessments,
        gaps=merged_gaps,
        source_refs=_dedupe(
            (
                TEMPORAL_SUFFICIENCY_METHOD_REF,
                continuity.continuity_ref,
                *(item.refresh_ref for item in refreshes),
            )
        ),
        trace_ref=None,
    )
    refresh = apply_temporal_context_refresh(
        prior_minimum.context,
        prior_minimum.sufficiency,
        continuity,
        tuple(refreshes),
        target_sufficiency,
        target_context_ref=target_context_ref,
        refreshed_at=refreshed_at,
    )

    reminimum = None
    if refresh.sufficiency.status == "sufficient":
        # Temporal refresh has no construction trace by design. Re-prove minimality
        # directly from the refreshed context+sufficiency pair rather than fabricating one.
        minimality = assess_context_minimality(
            WarehouseMinimalityMethod(),
            refresh.context,
            refresh.sufficiency,
            _context_costs(refresh.context),
            target_context_ref=f"{target_context_ref}/minimum",
            as_of=refreshed_at,
        )
        minimum_sufficiency = SufficiencyAssessment(
            assessment_ref=f"{target_context_ref}/minimum/sufficiency",
            context_ref=f"{target_context_ref}/minimum",
            assessed_at=refreshed_at,
            status="sufficient",
            assessments=refresh.sufficiency.assessments,
            gaps=refresh.sufficiency.gaps,
            source_refs=_dedupe(
                (
                    MINIMALITY_METHOD_REF,
                    minimality.assessment_ref,
                    *refresh.sufficiency.source_refs,
                )
            ),
            trace_ref=None,
        )
        reminimum = build_minimum_sufficient_task_context(
            refresh.context,
            refresh.sufficiency,
            minimality,
            minimum_sufficiency,
        )

    return WarehouseTemporalRun(
        reassessment=reassessment,
        continuity=continuity,
        refresh=refresh,
        reminimum=reminimum,
    )


def requirement_kind_map(requirements: Sequence[ContextRequirement]) -> Mapping[str, str]:
    return MappingProxyType({item.requirement_id: item.kind for item in requirements})
