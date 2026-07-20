"""GeoTask Runtime Encoding Planner v0.1 — MOCK/SKELETON.

THIS IS A MOCK IMPLEMENTATION for future development.
A real implementation would use more sophisticated heuristics, potentially
including task complexity analysis, domain-specific encoding rules, and
model-specific token estimation.

Current implementation: deterministic rule-based planner with simple
token-budget and complexity thresholds.
"""

from typing import Protocol

from geotask_runtime.contracts import (
    EncodingType,
    EncodingPlan,
    TaskRequest,
    TaskContext,
)


class EncodingPlanner(Protocol):
    """Contract for encoding planners.

    An EncodingPlanner decides HOW to encode a TaskRequest for a model:
    natural language, GeoTask YAML, or compact DSL.
    """

    def plan(self, request: TaskRequest, context: TaskContext) -> EncodingPlan:
        """Produce an EncodingPlan for the given request and context."""
        ...


class RuleBasedEncodingPlanner:
    """MOCK rule-based encoding planner.

    Uses simple heuristics based on token budget and task complexity.
    A real implementation would incorporate domain-specific rules,
    model capability profiles, and learned encoding preferences.

    Rules:
      - token_budget <= 120 → compact_dsl
      - token_budget <= 300 AND needs_human_readable → geotask_yaml
      - task_type contains "multiple" or 3+ requested_outputs → geotask_yaml
      - Otherwise → natural_language
    """

    def plan(self, request: TaskRequest, context: TaskContext) -> EncodingPlan:
        object_count = len(request.input_objects)
        output_count = len(request.requested_outputs)
        needs_human_readable = "human_readable" in request.metadata
        is_multi = "multiple" in request.task_type.lower() or output_count >= 3

        required_objects = [
            obj.get("name", f"obj_{i}")
            for i, obj in enumerate(request.input_objects)
        ]
        required_operators = list(context.available_operators)
        required_constraints = list(request.constraints)

        if request.token_budget is not None and request.token_budget <= 120:
            encoding_type = EncodingType.compact_dsl
            reason = (
                f"token_budget={request.token_budget} <= 120: "
                "compact DSL selected for minimal token usage"
            )
            estimated_tokens = min(request.token_budget, 100)

        elif is_multi:
            encoding_type = EncodingType.geotask_yaml
            reason = (
                f"task_type='{request.task_type}' or "
                f"{output_count} requested_outputs >= 3: "
                "YAML selected for structured multi-output clarity"
            )
            estimated_tokens = 150 + object_count * 30 + output_count * 20

        elif (
            request.token_budget is not None
            and request.token_budget <= 300
            and needs_human_readable
        ):
            encoding_type = EncodingType.geotask_yaml
            reason = (
                f"token_budget={request.token_budget} <= 300 "
                "with human_readable flag: YAML selected"
            )
            estimated_tokens = min(request.token_budget, 250)

        else:
            encoding_type = EncodingType.natural_language
            reason = "default: natural language encoding"
            estimated_tokens = 200 + object_count * 40 + output_count * 30

        return EncodingPlan(
            encoding_type=encoding_type,
            encoded_task="",
            estimated_tokens=estimated_tokens,
            required_objects=required_objects,
            required_operators=required_operators,
            required_constraints=required_constraints,
            verification_requirements=[
                f"verify_{out}" for out in request.requested_outputs
            ],
            reason=reason,
        )
