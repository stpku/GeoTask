"""Harness-neutral example consumer for Task Context refinement signals.

This module deliberately lives outside ``geotask_core``. It demonstrates how a
caller that already owns the TaskFrame, ContextRequirement set, and selected
ContextCandidate set can consume the existing TaskContext gap/refinement ids,
ask an external provider for more context, and reassess sufficiency.

It is a reference integration pattern, not a provider registry, scheduler,
agent loop, or automatic refinement algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from geotask_core.task_context import (
    ContextCandidate,
    ContextRequirement,
    TaskContext,
    TaskFrame,
    assess_task_context,
)


class RefinementProvider(Protocol):
    """Minimal external provider surface required by this reference consumer."""

    def acquire_refinement(
        self,
        task: TaskFrame,
        requirement: ContextRequirement,
    ) -> Sequence[ContextCandidate]:
        """Return additional candidates for one explicit refinement requirement."""


@dataclass(frozen=True)
class RefinementCycle:
    """Observable result of one external acquire -> reassess cycle."""

    initial_context: TaskContext
    final_context: TaskContext
    provider_call_requirement_ids: tuple[str, ...]
    skipped_non_refinement_gap_ids: tuple[str, ...]
    acquired_candidate_ids: tuple[str, ...]

    @property
    def provider_call_count(self) -> int:
        return len(self.provider_call_requirement_ids)

    @property
    def closed_refinement_requirement_ids(self) -> tuple[str, ...]:
        remaining = set(self.final_context.refinement_requirement_ids)
        return tuple(
            requirement_id
            for requirement_id in self.initial_context.refinement_requirement_ids
            if requirement_id not in remaining
        )


def run_refinement_cycle(
    task: TaskFrame,
    requirements: Sequence[ContextRequirement],
    selected_candidates: Sequence[ContextCandidate],
    provider: RefinementProvider,
) -> RefinementCycle:
    """Run exactly one caller-owned refinement cycle.

    The consumer never parses requirement prose and never invents provider
    parameters. It resolves ids emitted by Core back to the caller's original
    structured ContextRequirement objects, asks the external provider only for
    requirements explicitly marked refinable, appends returned candidates, and
    calls ``assess_task_context`` again.

    Ordinary gaps that are not also refinement requirements are intentionally
    skipped. Missing evidence and refinable resolution remain distinct.
    """

    initial = assess_task_context(task, requirements, selected_candidates)
    requirements_by_id = {item.requirement_id: item for item in requirements}
    if len(requirements_by_id) != len(requirements):
        raise ValueError("requirements must not contain duplicate ids")

    refinement_ids = tuple(initial.refinement_requirement_ids)
    skipped_gap_ids = tuple(
        requirement_id
        for requirement_id in initial.gap_requirement_ids
        if requirement_id not in set(refinement_ids)
    )

    acquired: list[ContextCandidate] = []
    provider_calls: list[str] = []
    for requirement_id in refinement_ids:
        requirement = requirements_by_id.get(requirement_id)
        if requirement is None:
            raise ValueError(
                "TaskContext refinement id is not present in the caller's "
                f"ContextRequirement set: {requirement_id}"
            )
        provider_calls.append(requirement_id)
        acquired.extend(provider.acquire_refinement(task, requirement))

    final_candidates = tuple(selected_candidates) + tuple(acquired)
    final = assess_task_context(task, requirements, final_candidates)

    return RefinementCycle(
        initial_context=initial,
        final_context=final,
        provider_call_requirement_ids=tuple(provider_calls),
        skipped_non_refinement_gap_ids=skipped_gap_ids,
        acquired_candidate_ids=tuple(item.candidate_id for item in acquired),
    )
