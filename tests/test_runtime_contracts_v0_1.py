"""Tests for GeoTask Runtime contracts v0.1."""
import sys; sys.path.insert(0, 'src')
from geotask_runtime.contracts import (
    TaskRequest, TaskContext, EncodingPlan, ModelRequest, ModelResponse,
    VerificationPlan, GovernedTaskResult, RuntimeEvent,
    EncodingType, TaskStatus, TokenUsage,
)


def test_task_request_defaults():
    req = TaskRequest(task_id="test-1", task_type="distance", task_goal="Calculate distance")
    assert req.task_id == "test-1"
    assert req.domain == "general_spatial"
    assert req.token_budget is None


def test_task_context_defaults():
    ctx = TaskContext()
    assert ctx.available_operators == []
    assert ctx.local_objects == {}


def test_encoding_plan():
    plan = EncodingPlan(encoding_type=EncodingType.COMPACT_DSL, reason="token_budget")
    assert plan.encoding_type == EncodingType.COMPACT_DSL
    assert plan.estimated_tokens == 0


def test_model_request():
    req = ModelRequest()
    assert req.provider == "mock"
    assert req.model == "deterministic-placeholder"


def test_model_response():
    resp = ModelResponse(raw_text="test")
    assert resp.raw_text == "test"
    assert resp.error is None


def test_verification_plan():
    vp = VerificationPlan(verifiable_claims=["claim1"], required_operators=["distance_2d"])
    assert len(vp.verifiable_claims) == 1


def test_governed_task_result():
    result = GovernedTaskResult(task_id="t1")
    assert result.task_id == "t1"
    assert result.overall_status == TaskStatus.NEED_REVIEW.value


def test_runtime_event():
    ev = RuntimeEvent(event_type="test_event")
    assert ev.event_type == "test_event"


def test_encoding_type_values():
    assert EncodingType.NATURAL_LANGUAGE.value == "natural_language"
    assert EncodingType.geotask_yaml.value == "geotask_yaml"
    assert EncodingType.COMPACT_DSL.value == "compact_dsl"


def test_task_status_values():
    assert TaskStatus.VERIFIED.value == "verified"
    assert TaskStatus.CONTRADICTED.value == "contradicted"


def test_token_usage():
    tu = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    assert tu.total_tokens == 150
