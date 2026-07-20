"""GeoTask Runtime mock pipeline v0.1 — end-to-end MOCK orchestration.

THIS IS A MOCK IMPLEMENTATION for future development.
Runs the full pipeline with deterministic mock model responses.
No external APIs, no real LLM calls.

Pipeline:
  TaskRequest
  → DomainPack.enrich_context()
  → EncodingPlanner.plan()
  → MockModelRouter.prepare_request()
  → deterministic mock model response
  → Core Normalizer
  → Core Verifier
  → ResultGovernor.govern()
  → GovernedTaskResult
"""

from geotask_runtime.contracts import (
    EncodingType,
    GovernedTaskResult,
    ModelRequest,
    ModelResponse,
    TaskContext,
    TaskRequest,
    TokenUsage,
)
from geotask_runtime.domain_pack import GenericSpatialDomainPack
from geotask_runtime.planner import RuleBasedEncodingPlanner
from geotask_runtime.result_governance import DeterministicResultGovernor
from geotask_runtime.router import MockModelRouter


def _generate_mock_response(model_request: ModelRequest) -> ModelResponse:
    """Generate a deterministic mock model response.

    THIS IS A MOCK — not a real model. Produces simple structured text
    based on the encoding type so the Core normalizer can extract values.

    Uses object_refs from the encoding plan to name measurements.
    Falls back to simple mock values.
    """
    plan = model_request.encoding_plan
    encoding_type = plan.encoding_type if plan else EncodingType.natural_language

    objects = plan.required_objects if plan else []
    operators = plan.required_operators if plan else []

    if encoding_type == EncodingType.natural_language:
        raw_text = _generate_natural_language(objects, operators)
    elif encoding_type == EncodingType.geotask_yaml:
        raw_text = _generate_yaml(objects, operators)
    elif encoding_type == EncodingType.compact_dsl:
        raw_text = _generate_compact_dsl(objects, operators)
    else:
        raw_text = _generate_natural_language(objects, operators)

    prompt_tokens = len(model_request.prompt.split())
    completion_tokens = len(raw_text.split())

    return ModelResponse(
        raw_text=raw_text,
        structured_content={},
        provider_metadata={"provider": "mock", "model": "deterministic-placeholder"},
        token_usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def _generate_natural_language(
    objects: list[str], operators: list[str]
) -> str:
    lines = []
    if "distance_2d" in operators:
        lines.append(
            "The distance_2d from takeoff to school is approximately "
            "144.22 meter."
        )
    if "line_intersects_rect" in operators:
        lines.append(
            "Using line_intersects_rect, the route intersects the zone. "
            "The result is true."
        )
    if "point_to_line_distance_2d" in operators:
        lines.append(
            "The point_to_line_distance_2d from the point to the line "
            "is 80.0 meter."
        )
    if "rect_contains_point" in operators:
        lines.append(
            "Using rect_contains_point, the rectangle does not contain "
            "the point. Result: false."
        )
    if "time_overlap" in operators:
        lines.append("The two time intervals overlap (time_overlap = true).")
    if "altitude_overlap" in operators:
        lines.append(
            "The altitude ranges overlap (altitude_overlap = true)."
        )
    if not lines:
        lines.append("No applicable operators. Need review.")
    return "\n".join(lines)


def _generate_yaml(objects: list[str], operators: list[str]) -> str:
    lines = ["measurements:"]
    if "distance_2d" in operators:
        lines.extend([
            "  - name: takeoff_to_school_distance",
            "    value: 144.22",
            "    unit: meter",
            "    object_refs: [takeoff, school]",
            "    verified_by: distance_2d",
        ])
    if "line_intersects_rect" in operators:
        lines.extend([
            "  - name: route_intersects_zone",
            "    value: true",
            "    unit: null",
            "    object_refs: [route, zone]",
            "    verified_by: line_intersects_rect",
        ])
    if not any(op in operators for op in ["distance_2d", "line_intersects_rect"]):
        lines.append("  []")
    return "\n".join(lines)


def _generate_compact_dsl(objects: list[str], operators: list[str]) -> str:
    lines = []
    if "distance_2d" in operators:
        lines.append(
            "takeoff_to_school_distance=144.22 meter [distance_2d]"
        )
    if "line_intersects_rect" in operators:
        lines.append(
            "route_intersects_zone=true [line_intersects_rect]"
        )
    if not lines:
        lines.append("no_result=null [none]")
    return "\n".join(lines)


def run_mock_runtime(
    request: TaskRequest,
    geotask_data: dict | None = None,
) -> GovernedTaskResult:
    """Run the full mock runtime pipeline.

    Args:
        request: The task request to process.
        geotask_data: Optional parsed GeoTask YAML dict for verification.
                      If None, verification will use need_review status.

    Returns:
        GovernedTaskResult with normalization and verification results.
    """
    domain_pack = GenericSpatialDomainPack()
    planner = RuleBasedEncodingPlanner()
    router = MockModelRouter()
    governor = DeterministicResultGovernor()

    context = TaskContext()
    context = domain_pack.enrich_context(request, context)

    plan = planner.plan(request, context)

    model_request = router.prepare_request(plan, request, context)

    response = _generate_mock_response(model_request)

    verification_plan = domain_pack.build_verification_plan(request, context)

    effective_geotask_data = geotask_data or {}

    result = governor.govern(
        request=request,
        response=response,
        verification_plan=verification_plan,
        geotask_data=effective_geotask_data,
    )
    result.used_encoding_plan = plan

    return result


def _build_request_from_yaml(data: dict) -> TaskRequest:
    """Build a TaskRequest from parsed YAML task configuration."""
    geotask = data.get("geotask", data.get("stir", {}))
    task = data.get("task", {})
    objects = data.get("objects", {})

    input_objects = []
    for name, obj in objects.items():
        obj_dict = dict(obj) if isinstance(obj, dict) else {}
        obj_dict["name"] = name
        input_objects.append(obj_dict)

    requested_outputs = []
    for q in task.get("questions", []):
        requested_outputs.append(q)

    runtime = data.get("runtime", {})
    token_budget = runtime.get("token_budget", None)

    return TaskRequest(
        task_id=geotask.get("name", "unnamed_task"),
        task_type="spatial_verification",
        task_goal=geotask.get("goal", ""),
        domain="general_spatial",
        input_objects=input_objects,
        requested_outputs=requested_outputs,
        constraints=[],
        token_budget=token_budget,
    )


if __name__ == "__main__":
    import sys
    import yaml

    if len(sys.argv) < 2:
        print("Usage: python -m geotask_runtime.mock_runtime <yaml_file>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    request = _build_request_from_yaml(data)
    result = run_mock_runtime(request, geotask_data=data)

    print(f"Task ID:        {result.task_id}")
    print(f"Overall Status: {result.overall_status}")
    print(f"Review Reasons: {result.review_reasons}")
    if result.used_encoding_plan:
        print(f"Encoding:       {result.used_encoding_plan.encoding_type.value}")
        print(f"Reason:         {result.used_encoding_plan.reason}")
    print("---")
    print("Normalized measurements:")
    for m in result.normalized_result.get("measurements", []):
        print(f"  {m['name']} = {m['value']} {m.get('unit', '')}")
    print("Verification measurements:")
    for m in result.verification_result.get("measurements", []):
        status = m.get("status", "?")
        print(f"  {m['name']} = {m['value']} [{status}]")
    print("Runtime events:")
    for ev in result.runtime_events:
        print(f"  {ev.event_type}: {ev.detail}")
