"""GeoTask Runtime Model Router v0.1 — MOCK/SKELETON.

THIS IS A MOCK IMPLEMENTATION for future development.
A real implementation would route to actual model providers (OpenAI, Anthropic,
local models, etc.) based on task requirements, cost constraints, and
provider capabilities.

Current implementation: returns a deterministic ModelRequest with a
template prompt. No external API calls.
"""

from typing import Protocol

from geotask_runtime.contracts import (
    EncodingType,
    EncodingPlan,
    ModelRequest,
    TaskRequest,
    TaskContext,
)


class ModelRouter(Protocol):
    """Contract for model routers.

    A ModelRouter takes an EncodingPlan and TaskRequest and produces
    a ModelRequest ready for dispatch to a model provider.
    """

    def prepare_request(
        self, plan: EncodingPlan, request: TaskRequest, context: TaskContext
    ) -> ModelRequest:
        """Build a ModelRequest from the encoding plan, task request, and context."""
        ...


class MockModelRouter:
    """MOCK model router — deterministic, no external calls.

    This is a mock. Real implementation would route to actual model
    providers based on task requirements, cost, latency, and capability.

    Generates a clear prompt template incorporating:
      - task goal
      - objects
      - required outputs
      - constraints
      - encoding format
    """

    def prepare_request(
        self, plan: EncodingPlan, request: TaskRequest, context: TaskContext
    ) -> ModelRequest:
        lines = [
            f"[ENCODING: {plan.encoding_type.value}]",
            f"[TASK GOAL] {request.task_goal}",
        ]

        if plan.required_objects:
            lines.append(f"[OBJECTS] {', '.join(plan.required_objects)}")
        if request.requested_outputs:
            lines.append(
                f"[REQUIRED OUTPUTS] {', '.join(request.requested_outputs)}"
            )
        if plan.required_operators:
            lines.append(
                f"[AVAILABLE OPERATORS] {', '.join(plan.required_operators)}"
            )
        if plan.required_constraints:
            lines.append(
                f"[CONSTRAINTS] {', '.join(plan.required_constraints)}"
            )

        format_instruction = {
            EncodingType.NATURAL_LANGUAGE: (
                "Respond in natural language with measurement values."
            ),
            EncodingType.GEOTASK_YAML: (
                "Respond in YAML format with measurements and verified_by."
            ),
            EncodingType.COMPACT_DSL: (
                "Respond in compact DSL: name=value unit [operator]."
            ),
        }
        lines.append(
            f"[FORMAT] {format_instruction.get(plan.encoding_type, '')}"
        )

        prompt = "\n".join(lines)

        return ModelRequest(
            provider="mock",
            model="deterministic-placeholder",
            prompt=prompt,
            encoding_plan=plan,
            temperature=0.0,
            max_output_tokens=1024,
        )
