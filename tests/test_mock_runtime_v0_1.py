"""Tests for GeoTask mock runtime v0.1."""
import sys; sys.path.insert(0, 'src')
import yaml
from geotask_runtime.contracts import TaskRequest, TaskContext, EncodingType
from geotask_runtime.planner import RuleBasedEncodingPlanner
from geotask_runtime.router import MockModelRouter
from geotask_runtime.domain_pack import GenericSpatialDomainPack
from geotask_runtime.mock_runtime import run_mock_runtime, _build_request_from_yaml
from geotask_core.result_schema import STATUS_VERIFIED, STATUS_CONTRADICTED, STATUS_NEED_REVIEW, STATUS_INVALID_REFERENCE


# --- Planner Tests ---

def test_planner_compact_dsl_low_budget():
    planner = RuleBasedEncodingPlanner()
    req = TaskRequest(task_id="t1", task_type="distance", task_goal="Dist", token_budget=80)
    ctx = TaskContext(available_operators=["distance_2d"])
    plan = planner.plan(req, ctx)
    assert plan.encoding_type == EncodingType.compact_dsl
    assert len(plan.reason) > 0


def test_planner_compact_dsl_boundary():
    planner = RuleBasedEncodingPlanner()
    req = TaskRequest(task_id="t1", task_type="distance", task_goal="Dist", token_budget=120)
    ctx = TaskContext()
    plan = planner.plan(req, ctx)
    assert plan.encoding_type == EncodingType.compact_dsl


def test_planner_geotask_yaml_mid_budget():
    planner = RuleBasedEncodingPlanner()
    req = TaskRequest(task_id="t2", task_type="distance", task_goal="Dist", token_budget=300,
                      requested_outputs=["o1", "o2", "o3"])
    ctx = TaskContext(available_operators=["distance_2d"])
    plan = planner.plan(req, ctx)
    assert plan.encoding_type == EncodingType.geotask_yaml


def test_planner_natural_language_no_budget():
    planner = RuleBasedEncodingPlanner()
    req = TaskRequest(task_id="t3", task_type="simple", task_goal="Check", token_budget=1000)
    ctx = TaskContext()
    plan = planner.plan(req, ctx)
    assert plan.encoding_type == EncodingType.natural_language


def test_planner_produces_reason():
    planner = RuleBasedEncodingPlanner()
    req = TaskRequest(task_id="t4", task_type="x", task_goal="x", token_budget=50)
    plan = planner.plan(req, TaskContext())
    assert len(plan.reason) > 0


# --- Router Tests ---

def test_router_no_external_api():
    router = MockModelRouter()
    req = TaskRequest(task_id="r1", task_type="d", task_goal="Calculate")
    ctx = TaskContext()
    plan = RuleBasedEncodingPlanner().plan(req, ctx)
    result = router.prepare_request(plan, req, ctx)
    assert result.provider == "mock"
    assert result.model == "deterministic-placeholder"
    assert len(result.prompt) > 0


def test_router_prompt_contains_encoding_type():
    router = MockModelRouter()
    req = TaskRequest(task_id="r2", task_type="d", task_goal="Check intersection")
    ctx = TaskContext()
    plan = RuleBasedEncodingPlanner().plan(req, ctx)
    result = router.prepare_request(plan, req, ctx)
    assert "[ENCODING:" in result.prompt


# --- Domain Pack Tests ---

def test_domain_pack_enriches_context():
    dp = GenericSpatialDomainPack()
    req = TaskRequest(task_id="d1", task_type="spatial", task_goal="Test",
                      input_objects=[{"name": "takeoff", "type": "point", "xy": [0, 0]}])
    ctx = TaskContext()
    enriched = dp.enrich_context(req, ctx)
    assert "takeoff" in enriched.local_objects
    assert "distance_2d" in enriched.available_operators


def test_domain_pack_builds_verification_plan():
    dp = GenericSpatialDomainPack()
    req = TaskRequest(task_id="d2", task_type="spatial", task_goal="Test",
                      requested_outputs=["Calculate distance", "Check intersection"])
    ctx = TaskContext(available_operators=["distance_2d", "line_intersects_rect"])
    enriched = dp.enrich_context(req, ctx)
    vplan = dp.build_verification_plan(req, enriched)
    assert len(vplan.verifiable_claims) >= 1
    assert len(vplan.required_operators) >= 1


def test_domain_pack_version():
    dp = GenericSpatialDomainPack()
    assert dp.name == "generic_spatial"
    assert dp.version == "0.1-mock"


# --- Mock Runtime Tests ---

def test_mock_runtime_verified_distance():
    """Correct distance output should be verified."""
    import os
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'geotask_core_lite.yaml')
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    req = _build_request_from_yaml(data)
    result = run_mock_runtime(req, geotask_data=data)
    assert result.overall_status == STATUS_VERIFIED


def test_mock_runtime_need_review_without_geotask_data():
    """Without geotask_data, verifier cannot compute ground truth."""
    import os
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'geotask_core_lite.yaml')
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    req = _build_request_from_yaml(data)
    result = run_mock_runtime(req, geotask_data=None)
    assert result.overall_status == STATUS_NEED_REVIEW


def test_mock_runtime_need_review_missing_operator():
    """Task with missing operator should produce need_review."""
    req = TaskRequest(
        task_id="missing_op",
        task_type="spatial",
        task_goal="Calculate using non-existent op",
        requested_outputs=["Use haversine to calculate distance"],
        input_objects=[{"name": "a", "type": "point", "xy": [0, 0]},
                       {"name": "b", "type": "point", "xy": [5, 5]}],
    )
    result = run_mock_runtime(req, geotask_data=None)
    assert result.overall_status == STATUS_NEED_REVIEW


def test_mock_runtime_invalid_reference():
    """Task with invalid object reference should handle gracefully."""
    req = TaskRequest(
        task_id="invalid_ref",
        task_type="spatial",
        task_goal="Check with missing object",
        requested_outputs=["Calculate distance from A to B"],
        input_objects=[],
    )
    result = run_mock_runtime(req, geotask_data=None)
    assert result.overall_status in (STATUS_NEED_REVIEW, STATUS_INVALID_REFERENCE)


def test_mock_runtime_returns_governed_result():
    """Mock runtime should return GovernedTaskResult with all fields."""
    import os
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'geotask_core_lite.yaml')
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    req = _build_request_from_yaml(data)
    result = run_mock_runtime(req, geotask_data=data)
    assert result.task_id is not None
    assert result.overall_status is not None
    assert result.used_encoding_plan is not None
    assert len(result.runtime_events) > 0


# --- Old Core tests still pass ---

def test_core_imports_still_work():
    """Core module imports should not be affected by runtime."""
    from geotask_core.models import PointObject, LineObject, RectObject
    from geotask_core.ops import distance_2d, line_intersects_rect
    from geotask_core.result_schema import STATUS_VERIFIED, STATUS_CONTRADICTED
    p = PointObject(name="p", xy=[0, 0])
    assert p.name == "p"
    d = distance_2d([0, 0], [3, 4])
    assert abs(d - 5.0) < 0.01
