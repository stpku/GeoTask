"""GeoTask Runtime Domain Pack v0.1 — MOCK/SKELETON.

THIS IS A MOCK IMPLEMENTATION for future development.
A real Domain Pack would inject industry-specific objects, operators,
verification rules, and data source connectors.

Current implementation: GenericSpatialDomainPack that exposes the
6 Core operators and builds simple verification plans.
"""

from typing import Protocol

from geotask_runtime.contracts import (
    TaskContext,
    TaskRequest,
    VerificationPlan,
)

CORE_OPERATORS = [
    "distance_2d",
    "line_intersects_rect",
    "point_to_line_distance_2d",
    "rect_contains_point",
    "time_overlap",
    "altitude_overlap",
]

_OPERATOR_OUTPUT_TYPE: dict[str, str] = {
    "distance_2d": "float",
    "line_intersects_rect": "bool",
    "point_to_line_distance_2d": "float",
    "rect_contains_point": "bool",
    "time_overlap": "bool",
    "altitude_overlap": "bool",
}


class DomainPack(Protocol):
    """Contract for domain packs.

    A DomainPack enriches task context with domain-specific objects,
    operators, rules, and builds verification plans.
    """

    name: str
    version: str

    def enrich_context(
        self, request: TaskRequest, context: TaskContext
    ) -> TaskContext:
        """Enrich a TaskContext with domain-specific information."""
        ...

    def build_verification_plan(
        self, request: TaskRequest, context: TaskContext
    ) -> VerificationPlan:
        """Build a VerificationPlan for the given request and context."""
        ...


class GenericSpatialDomainPack:
    """MOCK generic spatial domain pack — demo only, no real industry rules.

    Shows how a Domain Pack would:
      - Inject available operators from Core
      - Mark known gaps if required operators are missing
      - Map requested outputs to required operators for verification

    A real implementation would add:
      - Industry-specific object libraries (UAV, surveying, logistics)
      - Domain validation rules and constraints
      - External data source registration
      - Custom operator definitions
    """

    name: str = "generic_spatial"
    version: str = "0.1-mock"

    def enrich_context(
        self, request: TaskRequest, context: TaskContext
    ) -> TaskContext:
        context.available_operators = list(CORE_OPERATORS)
        context.available_data_sources = ["local_geotask_yaml"]

        for obj in request.input_objects:
            obj_name = obj.get("name", "")
            if obj_name:
                context.local_objects[obj_name] = obj

        for constraint in request.constraints:
            op_name = constraint.split(":")[0].strip() if ":" in constraint else ""
            if op_name and op_name not in CORE_OPERATORS:
                context.known_gaps.append(
                    f"operator_not_available:{op_name}"
                )

        return context

    def build_verification_plan(
        self, request: TaskRequest, context: TaskContext
    ) -> VerificationPlan:
        verifiable: list[str] = []
        non_verifiable: list[str] = []
        required_ops: list[str] = []
        required_data: list[str] = []

        for output in request.requested_outputs:
            matched_op = self._match_output_to_operator(output)
            if matched_op and matched_op in context.available_operators:
                verifiable.append(output)
                if matched_op not in required_ops:
                    required_ops.append(matched_op)
            else:
                non_verifiable.append(output)

        if request.input_objects:
            required_data.append("local_geotask_yaml")

        review_requirements = []
        if non_verifiable:
            review_requirements.append(
                f"manual_review_needed_for: {', '.join(non_verifiable)}"
            )

        return VerificationPlan(
            verifiable_claims=verifiable,
            non_verifiable_claims=non_verifiable,
            required_operators=required_ops,
            required_data=required_data,
            review_requirements=review_requirements,
        )

    @staticmethod
    def _match_output_to_operator(output_name: str) -> str | None:
        """Map a requested output name to a Core operator (simple heuristic)."""
        lower = output_name.lower()
        if "distance" in lower and "line" not in lower:
            return "distance_2d"
        if "intersect" in lower:
            return "line_intersects_rect"
        if "point_to_line" in lower or ("distance" in lower and "line" in lower):
            return "point_to_line_distance_2d"
        if "contains" in lower:
            return "rect_contains_point"
        if "time" in lower and "overlap" in lower:
            return "time_overlap"
        if "altitude" in lower and "overlap" in lower:
            return "altitude_overlap"
        return None
