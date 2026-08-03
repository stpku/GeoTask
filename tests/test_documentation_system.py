import fnmatch
import json
import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "geotask-v1.0.schema.json"
PUBLIC_MANIFEST = ROOT / ".release" / "public-manifest.yaml"
ROOT_README_ZH = ROOT / "README.md"
ROOT_README_EN = ROOT / "README.en.md"
DOC_INDEX_ZH = ROOT / "docs" / "README.md"
DOC_INDEX_EN = ROOT / "docs" / "README.en.md"
WHITEPAPER = ROOT / "docs" / "whitepaper" / "GeoTask_White_Paper_v0.1.md"
WHITEPAPER_BUILD = ROOT / "docs" / "whitepaper" / "README.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
LANGUAGE_SPEC = ROOT / "docs" / "spec" / "geotask-language-spec-v1.0.md"
RESULT_SPEC = ROOT / "docs" / "spec" / "geotask-result-v1.0.md"
RESULT_SCHEMA = ROOT / "schemas" / "geotask-result-v1.0.schema.json"
WORLD_STATE_SPEC = ROOT / "docs" / "spec" / "geotask-world-state-v0.1.md"
WORLD_STATE_SCHEMA = ROOT / "schemas" / "geotask-world-state-v0.1.schema.json"
STATE_TRANSITION_SPEC = ROOT / "docs" / "spec" / "geotask-state-transition-v0.1.md"
STATE_TRANSITION_SCHEMA = ROOT / "schemas" / "geotask-state-transition-v0.1.schema.json"
VERIFICATION_SESSION_SPEC = ROOT / "docs" / "spec" / "geotask-verification-session-v0.1.md"
VERIFICATION_SESSION_SCHEMA = ROOT / "schemas" / "geotask-verification-session-v0.1.schema.json"
DISCREPANCY_REPORT_SPEC = ROOT / "docs" / "spec" / "geotask-discrepancy-report-v0.1.md"
DISCREPANCY_REPORT_SCHEMA = ROOT / "schemas" / "geotask-discrepancy-report-v0.1.schema.json"
CORRECTION_REQUEST_SPEC = ROOT / "docs" / "spec" / "geotask-correction-request-v0.1.md"
CORRECTION_REQUEST_SCHEMA = ROOT / "schemas" / "geotask-correction-request-v0.1.schema.json"
IMPACT_GRAPH_SPEC = ROOT / "docs" / "spec" / "geotask-impact-graph-v0.1.md"
IMPACT_GRAPH_SCHEMA = ROOT / "schemas" / "geotask-impact-graph-v0.1.schema.json"
INCREMENTAL_REEVALUATION_SPEC = (
    ROOT / "docs" / "spec" / "geotask-incremental-reevaluation-result-v0.1.md"
)
INCREMENTAL_REEVALUATION_SCHEMA = (
    ROOT / "schemas" / "geotask-incremental-reevaluation-result-v0.1.schema.json"
)
WORLD_STATE_MATERIALIZATION_SPEC = (
    ROOT / "docs" / "spec" / "geotask-world-state-materialization-result-v0.1.md"
)
WORLD_STATE_MATERIALIZATION_SCHEMA = (
    ROOT / "schemas" / "geotask-world-state-materialization-result-v0.1.schema.json"
)
RECOMPUTE_DERIVATION_SPEC = (
    ROOT / "docs" / "spec" / "geotask-recompute-derivation-result-v0.1.md"
)
RECOMPUTE_DERIVATION_SCHEMA = (
    ROOT / "schemas" / "geotask-recompute-derivation-result-v0.1.schema.json"
)
OBSERVATION_MERGE_SPEC = (
    ROOT / "docs" / "spec" / "geotask-observation-merge-result-v0.1.md"
)
OBSERVATION_MERGE_SCHEMA = (
    ROOT / "schemas" / "geotask-observation-merge-result-v0.1.schema.json"
)
ARTIFACT_REGISTRY_SPEC = (
    ROOT / "docs" / "spec" / "geotask-artifact-registry-v1.0.md"
)
ARTIFACT_REGISTRY_SCHEMA = (
    ROOT / "schemas" / "geotask-artifact-registry-v1.0.schema.json"
)
VERSIONED_VALIDATION_SPEC = (
    ROOT / "docs" / "spec" / "geotask-versioned-payload-validation-v1.0.md"
)
CONTROL_PROFILE_SPEC = ROOT / "docs" / "spec" / "geotask-control-extension-profile-v1.0.md"
CONTROL_EXPRESSION_SPEC = ROOT / "docs" / "spec" / "geotask-control-expression-language-v1.0.md"
CONTROL_EVALUATION_SPEC = ROOT / "docs" / "spec" / "geotask-control-evaluation-v1.0.md"
CONTROL_EVALUATION_SCHEMA = ROOT / "schemas" / "geotask-control-evaluation-v1.0.schema.json"
AGENT_INTEGRATION_SPEC = (
    ROOT / "docs" / "spec" / "geotask-agent-integration-profile-v0.1.md"
)
RUNTIME_INTERFACE_SPEC = (
    ROOT / "docs" / "spec" / "geotask-runtime-interface-profile-v0.1.md"
)
AGENT_SKILL = ROOT / "skills" / "geotask-core" / "SKILL.md"
TARGET_SPEC_STATUS = ROOT / "docs" / "spec" / "target-specification-status.md"
QUICKSTART_EN = ROOT / "docs" / "tutorials" / "quickstart.md"
QUICKSTART_ZH = ROOT / "docs" / "tutorials" / "quickstart.zh-CN.md"
STATUS_MODEL = ROOT / "docs" / "reference" / "status-model.md"
EVIDENCE_REFERENCE = ROOT / "docs" / "reference" / "evidence-and-recovery.md"
COOKBOOK_EN = ROOT / "docs" / "cookbook" / "gt01-gt20.md"
COOKBOOK_ZH = ROOT / "docs" / "cookbook" / "gt01-gt20.zh-CN.md"
CONTRIBUTING_EN = ROOT / "CONTRIBUTING.md"
CONTRIBUTING_ZH = ROOT / "CONTRIBUTING.zh-CN.md"
CODE_OF_CONDUCT = ROOT / "CODE_OF_CONDUCT.md"
CITATION = ROOT / "CITATION.cff"
PYPROJECT = ROOT / "pyproject.toml"
ROADMAP = ROOT / "ROADMAP.md"
RELEASE_NOTES_010 = ROOT / "docs" / "release_v0_1_0.md"
RELEASE_NOTES_011 = ROOT / "docs" / "release_v0_1_1.md"
RELEASE_NOTES = ROOT / "docs" / "release_v0_3_0.md"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
PYPI_WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"


DOCUMENTS = (
    ROOT_README_ZH,
    ROOT_README_EN,
    DOC_INDEX_ZH,
    DOC_INDEX_EN,
    WHITEPAPER,
    WHITEPAPER_BUILD,
    ARCHITECTURE,
    LANGUAGE_SPEC,
    RESULT_SPEC,
    RESULT_SCHEMA,
    WORLD_STATE_SPEC,
    WORLD_STATE_SCHEMA,
    STATE_TRANSITION_SPEC,
    STATE_TRANSITION_SCHEMA,
    VERIFICATION_SESSION_SPEC,
    VERIFICATION_SESSION_SCHEMA,
    DISCREPANCY_REPORT_SPEC,
    DISCREPANCY_REPORT_SCHEMA,
    CORRECTION_REQUEST_SPEC,
    CORRECTION_REQUEST_SCHEMA,
    IMPACT_GRAPH_SPEC,
    IMPACT_GRAPH_SCHEMA,
    INCREMENTAL_REEVALUATION_SPEC,
    INCREMENTAL_REEVALUATION_SCHEMA,
    WORLD_STATE_MATERIALIZATION_SPEC,
    WORLD_STATE_MATERIALIZATION_SCHEMA,
    RECOMPUTE_DERIVATION_SPEC,
    RECOMPUTE_DERIVATION_SCHEMA,
    OBSERVATION_MERGE_SPEC,
    OBSERVATION_MERGE_SCHEMA,
    ARTIFACT_REGISTRY_SPEC,
    ARTIFACT_REGISTRY_SCHEMA,
    VERSIONED_VALIDATION_SPEC,
    CONTROL_PROFILE_SPEC,
    CONTROL_EXPRESSION_SPEC,
    CONTROL_EVALUATION_SPEC,
    CONTROL_EVALUATION_SCHEMA,
    AGENT_INTEGRATION_SPEC,
    RUNTIME_INTERFACE_SPEC,
    AGENT_SKILL,
    TARGET_SPEC_STATUS,
    QUICKSTART_EN,
    QUICKSTART_ZH,
    STATUS_MODEL,
    EVIDENCE_REFERENCE,
    COOKBOOK_EN,
    COOKBOOK_ZH,
    CONTRIBUTING_EN,
    CONTRIBUTING_ZH,
    CODE_OF_CONDUCT,
    ROADMAP,
    RELEASE_NOTES_010,
    RELEASE_NOTES_011,
    RELEASE_NOTES,
    SCHEMA_PATH,
)


SCHEMA_EXAMPLES = (
    ROOT / "examples" / "core" / "v1_minimal_distance.yaml",
    ROOT / "examples" / "core" / "v1_multi_operator.yaml",
    ROOT / "examples" / "core" / "multi_constraint_conflict.yaml",
    ROOT / "examples" / "core" / "unverifiable_constraint.yaml",
    ROOT / "examples" / "core" / "evidence_request_plan.yaml",
    ROOT / "examples" / "core" / "evidence_conflict_review.yaml",
    ROOT / "examples" / "core" / "robot_corridor_coordination.yaml",
    ROOT / "examples" / "core" / "robot_accessible_route.yaml",
    ROOT / "examples" / "core" / "uav_energy_reserve.yaml",
    ROOT / "examples" / "core" / "vehicle_clearance_envelope.yaml",
    ROOT / "examples" / "core" / "emergency_response_fastest_arrival.yaml",
    ROOT / "examples" / "core" / "robot_live_obstacle_stop.yaml",
    ROOT / "examples" / "core" / "uav_route_crossing_temporal_separation.yaml",
    ROOT / "examples" / "core" / "city_event_report_deduplication.yaml",
    ROOT / "examples" / "core" / "rescue_robot_shortest_route_hazard.yaml",
    ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml",
    ROOT / "examples" / "core" / "vehicle_green_light_downstream_blockage.yaml",
)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _manifest() -> dict:
    return yaml.safe_load(PUBLIC_MANIFEST.read_text(encoding="utf-8"))


def _pattern_matches(relative_path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(relative_path, pattern):
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return relative_path == prefix or relative_path.startswith(prefix + "/")
    return False


def _manifest_pattern_files(pattern: str):
    if pattern.endswith("/**"):
        directory = ROOT / pattern[:-3].rstrip("/")
        if not directory.is_dir():
            return ()
        return directory.rglob("*")
    return ROOT.glob(pattern)


def _public_source_paths() -> set[Path]:
    manifest = _manifest()
    included: set[Path] = set()

    for pattern in manifest["include"]:
        for path in _manifest_pattern_files(pattern):
            if path.is_file():
                included.add(path.resolve())

    excluded_patterns = manifest.get("exclude", [])
    return {
        path
        for path in included
        if not any(
            _pattern_matches(path.relative_to(ROOT).as_posix(), pattern)
            for pattern in excluded_patterns
        )
    }


def _markdown_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)


def test_documentation_system_files_exist_and_are_substantive() -> None:
    for path in DOCUMENTS:
        assert path.is_file(), path
        assert path.stat().st_size > 1000, path


def test_json_schema_is_valid_draft_2020_12() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "GeoTask Language and Execution Specification v1.0"
    assert "extensions" in schema["properties"]


def test_representative_v1_examples_match_json_schema() -> None:
    validator = Draft202012Validator(_schema())

    for path in SCHEMA_EXAMPLES:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
        assert errors == [], f"{path}: {[error.message for error in errors]}"


def test_chinese_and_english_entrypoints_are_bidirectionally_linked() -> None:
    root_zh = ROOT_README_ZH.read_text(encoding="utf-8")
    root_en = ROOT_README_EN.read_text(encoding="utf-8")
    docs_zh = DOC_INDEX_ZH.read_text(encoding="utf-8")
    docs_en = DOC_INDEX_EN.read_text(encoding="utf-8")

    assert "[English](README.en.md)" in root_zh
    assert "[简体中文](README.md)" in root_en
    assert "[English](README.en.md)" in docs_zh
    assert "[简体中文](README.md)" in docs_en
    assert "面向智能体的可验证时空世界模型" in root_zh
    assert "可验证时空任务协议" in root_zh
    assert "Explicit and verifiable spatiotemporal world model" in root_en
    assert "verifiable task protocol" in root_en


def test_whitepaper_separates_positioning_implementation_and_roadmap() -> None:
    text = WHITEPAPER.read_text(encoding="utf-8")

    for fragment in (
        "面向智能体的显式、可验证时空世界模型",
        "为什么是现在：从直接给答案到开放推理与后验验证",
        "GeoTask通过显式描述世界对象、位置、时间、状态、关系、约束、证据及其变化",
        "面向智能体的可验证时空任务协议、Canonical IR、Artifact体系和本地验证内核",
        "与隐式神经世界模型的区别",
        "八类Canonical对象",
        "九个本地确定性算子",
        "World State",
        "受限Observation Merge v0.1",
        "State Transition",
        "对象身份发现",
    ):
        assert fragment in text

    assert "GeoTask 不负责提供完整地图、原始多模态识别、设备控制" in text
    assert "初始正确不代表后续持续正确" in text
    assert "GeoTask可以连接神经世界模型" in text
    assert "自动差异计算、Observation合并" not in text


def test_document_indexes_link_primary_layers_and_localized_guides() -> None:
    zh_text = DOC_INDEX_ZH.read_text(encoding="utf-8")
    en_text = DOC_INDEX_EN.read_text(encoding="utf-8")

    expected_links = (
        "whitepaper/GeoTask_White_Paper_v0.1.md",
        "whitepaper/README.md",
        "spec/geotask-language-spec-v1.0.md",
        "spec/geotask-result-v1.0.md",
        "spec/geotask-artifact-registry-v1.0.md",
        "spec/geotask-versioned-payload-validation-v1.0.md",
        "spec/geotask-control-extension-profile-v1.0.md",
        "spec/geotask-control-expression-language-v1.0.md",
        "spec/geotask-control-evaluation-v1.0.md",
        "spec/geotask-agent-integration-profile-v0.1.md",
        "spec/geotask-runtime-interface-profile-v0.1.md",
        "../skills/geotask-core/SKILL.md",
        "tutorials/quickstart.md",
        "tutorials/quickstart.zh-CN.md",
        "reference/status-model.md",
        "reference/evidence-and-recovery.md",
        "cookbook/gt01-gt20.md",
        "cookbook/gt01-gt20.zh-CN.md",
        "release_v0_1_0.md",
        "../ROADMAP.md",
        "../schemas/geotask-v1.0.schema.json",
        "spec/target-specification-status.md",
    )
    for link in expected_links:
        assert link in zh_text or link in en_text

    assert "当前公共实现规范" in zh_text
    assert "体系级目标方向" in zh_text
    assert "历史兼容格式" in zh_text
    assert "Implemented public profile" in en_text
    assert "System-level target direction" in en_text
    assert "Legacy compatibility" in en_text
    assert "23类公共Artifact" in zh_text
    assert "twenty-three public Artifacts" in en_text


def test_architecture_and_target_status_include_bounded_observation_merge() -> None:
    architecture_text = ARCHITECTURE.read_text(encoding="utf-8")
    target_text = TARGET_SPEC_STATUS.read_text(encoding="utf-8")

    for fragment in (
        "→ bounded Observation Merge",
        "Observation Merge Result v0.1 is implemented as the bounded snapshot-update contract",
        "caller-declared `require_equal` consolidation",
        "complete `explicit_precedence`",
        "does not infer identity",
        "resolve an undeclared ambiguous conflict",
        "→ successor WorldState",
    ):
        assert fragment in architecture_text

    for fragment in (
        "7. [GeoTask Observation Merge Result v0.1]",
        "13. [GeoTask Recompute Derivation Result v0.1]",
        "14. [GeoTask World State Materialization Result v0.1]",
        "19. [Operator Registry]",
        "World State, Observation Merge Result, State Transition",
        "caller-declared `require_equal`",
        "undeclared ambiguous-conflict resolution",
    ):
        assert fragment in target_text


def test_whitepaper_states_architecture_and_public_boundary() -> None:
    text = WHITEPAPER.read_text(encoding="utf-8")

    required_fragments = (
        "面向智能体的显式、可验证时空世界模型",
        "可验证时空任务协议",
        "与隐式神经世界模型的区别",
        "对象、算子和命题显式绑定",
        "生成与验证分离",
        "证据冲突",
        "GT01–GT20",
        "开源边界与知识产权",
        "让模型负责理解与生成",
    )
    for fragment in required_fragments:
        assert fragment in text

    assert "模型密钥" in text
    assert "专利" in text
    assert "Domain Pack" in text


def test_language_spec_matches_current_public_enums_and_operators() -> None:
    text = LANGUAGE_SPEC.read_text(encoding="utf-8")

    for operator in (
        "distance_2d",
        "line_intersects_rect",
        "point_to_line_distance_2d",
        "rect_contains_point",
        "time_overlap",
        "altitude_overlap",
    ):
        assert f"`{operator}`" in text

    for object_type in (
        "point",
        "polyline",
        "rect",
        "time_interval",
        "altitude_interval",
        "feature_collection",
    ):
        assert f"`{object_type}`" in text

    for status in (
        "verified",
        "contradicted",
        "need_review",
        "need_data",
        "unverifiable",
        "execution_error",
    ):
        assert f"`{status}`" in text

    assert "current public Core" in text
    assert "does not call a hosted model" in text
    assert "unsupported_execution_mode" in text
    assert "unsupported_executor" in text
    assert "MUST NOT substitute local execution" in text
    assert "geotask.control/1.0" in text
    assert "geotask-control-extension-profile-v1.0.md" in text
    assert "geotask-control-expression-language-v1.0.md" in text

    result_text = RESULT_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Execution Result v1.0",
        "GeotaskResult.to_dict()",
        "geotask result validate",
        "summary.total_checks == len(checks)",
        "does not execute the task",
    ):
        assert fragment in result_text

    result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(result_schema)
    assert result_schema["$id"].endswith("geotask-result-v1.0.schema.json")
    assert result_schema["properties"]["geotask_result"]["$ref"] == (
        "#/$defs/geotaskResult"
    )

    world_state_text = WORLD_STATE_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask World State v0.1",
        "geotask.world-state",
        "versioned snapshot",
        "semantic fingerprint",
        "ingest Observations",
        "verify external truth",
        "does **not**",
        "State Transition",
        "action eligibility",
    ):
        assert fragment in world_state_text
    world_state_schema = json.loads(WORLD_STATE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(world_state_schema)
    assert world_state_schema["$id"].endswith("geotask-world-state-v0.1.schema.json")
    assert world_state_schema["properties"]["world_state"]["$ref"] == (
        "#/$defs/worldState"
    )

    transition_text = STATE_TRANSITION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask State Transition v0.1",
        "geotask.state-transition",
        "semantic fingerprint",
        "identity-based JSON Pointer",
        "validate_state_transition_bindings",
        "does **not** compare snapshot contents",
        "calculate a diff",
        "action_authorized",
    ):
        assert fragment in transition_text
    transition_schema = json.loads(STATE_TRANSITION_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(transition_schema)
    assert transition_schema["$id"].endswith(
        "geotask-state-transition-v0.1.schema.json"
    )
    assert transition_schema["properties"]["state_transition"]["$ref"] == (
        "#/$defs/stateTransition"
    )

    session_text = VERIFICATION_SESSION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Verification Session v0.1",
        "geotask.verification-session",
        "immutable audit snapshot",
        "validate_verification_session_bindings",
        "exact raw bytes",
        "Linked artifact semantics verified",
        "rechecks_executed",
        "action_authorized",
    ):
        assert fragment in session_text
    session_schema = json.loads(VERIFICATION_SESSION_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(session_schema)
    assert session_schema["$id"].endswith(
        "geotask-verification-session-v0.1.schema.json"
    )
    assert session_schema["properties"]["verification_session"]["$ref"] == (
        "#/$defs/verificationSession"
    )

    discrepancy_text = DISCREPANCY_REPORT_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Discrepancy Report v0.1",
        "geotask.discrepancy-report",
        "immutable audit record",
        "validate_discrepancy_report_bindings",
        "identity-based JSON Pointer",
        "Mutable and immutable paths",
        "does **not** prove",
        "action authorization",
    ):
        assert fragment in discrepancy_text
    discrepancy_schema = json.loads(
        DISCREPANCY_REPORT_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(discrepancy_schema)
    assert discrepancy_schema["$id"].endswith(
        "geotask-discrepancy-report-v0.1.schema.json"
    )
    assert discrepancy_schema["properties"]["discrepancy_report"]["$ref"] == (
        "#/$defs/discrepancyReport"
    )

    correction_text = CORRECTION_REQUEST_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Correction Request v0.1",
        "geotask.correction-request",
        "successor World State",
        "validate_correction_request_bindings",
        "Identity-based correction paths",
        "Acceptance criteria",
        "does **not** modify",
        "outputs released or actions authorized",
    ):
        assert fragment in correction_text
    correction_schema = json.loads(
        CORRECTION_REQUEST_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(correction_schema)
    assert correction_schema["$id"].endswith(
        "geotask-correction-request-v0.1.schema.json"
    )
    assert correction_schema["properties"]["correction_request"]["$ref"] == (
        "#/$defs/correctionRequest"
    )

    impact_text = IMPACT_GRAPH_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Impact Graph v0.1",
        "geotask.impact-graph",
        "directed acyclic graph",
        "validate_impact_graph_bindings",
        "Source entities",
        "Reevaluation targets",
        "does **not** discover impact",
        "outputs released or actions authorized",
    ):
        assert fragment in impact_text
    impact_schema = json.loads(IMPACT_GRAPH_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(impact_schema)
    assert impact_schema["$id"].endswith("geotask-impact-graph-v0.1.schema.json")
    assert impact_schema["properties"]["impact_graph"]["$ref"] == (
        "#/$defs/impactGraph"
    )

    incremental_text = INCREMENTAL_REEVALUATION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Incremental Reevaluation Result v0.1",
        "geotask.incremental-reevaluation-result",
        "immutable, bounded record",
        "validate_incremental_reevaluation_result_bindings",
        "Successor-state confinement",
        "Output and action gates",
        "authorized` and `executed` are always `false",
        "does **not** itself prove",
    ):
        assert fragment in incremental_text
    incremental_schema = json.loads(
        INCREMENTAL_REEVALUATION_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(incremental_schema)
    assert incremental_schema["$id"].endswith(
        "geotask-incremental-reevaluation-result-v0.1.schema.json"
    )
    assert incremental_schema["properties"]["incremental_reevaluation_result"][
        "$ref"
    ] == "#/$defs/incrementalReevaluationResult"

    materialization_text = WORLD_STATE_MATERIALIZATION_SPEC.read_text(
        encoding="utf-8"
    )
    for fragment in (
        "GeoTask World State Materialization Result v0.1",
        "geotask.world-state-materialization-result",
        "materialize_successor_world_state",
        "validate_world_state_materialization_result_bindings",
        "explicit recompute values",
        "Observation and Evidence reference sets are preserved",
        "does **not**",
        "action_authorized",
    ):
        assert fragment in materialization_text
    materialization_schema = json.loads(
        WORLD_STATE_MATERIALIZATION_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(materialization_schema)
    assert materialization_schema["$id"].endswith(
        "geotask-world-state-materialization-result-v0.1.schema.json"
    )
    assert materialization_schema["properties"][
        "world_state_materialization_result"
    ]["$ref"] == "#/$defs/materializationResult"

    recompute_text = RECOMPUTE_DERIVATION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Recompute Derivation Result v0.1",
        "geotask.recompute-derivation-result",
        "validate_recompute_derivation_bindings",
        "copy_input",
        "interval_gap_minus_delay_seconds",
        "Arbitrary Python",
        "materialize_successor_world_state",
        "action_authorized",
    ):
        assert fragment in recompute_text
    recompute_schema = json.loads(
        RECOMPUTE_DERIVATION_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(recompute_schema)
    assert recompute_schema["$id"].endswith(
        "geotask-recompute-derivation-result-v0.1.schema.json"
    )
    assert recompute_schema["properties"]["recompute_derivation_result"]["$ref"] == (
        "#/$defs/result"
    )

    observation_merge_text = OBSERVATION_MERGE_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Observation Merge Result v0.1",
        "geotask.observation-merge-result",
        "validate_observation_merge_result_bindings",
        "Every claim in every supplied Observation must be mapped exactly once",
        "existing object attribute",
        "require_equal",
        "explicit_precedence",
        "conflict_resolutions",
        "does not infer that it is more authoritative",
        "compute_state_transition",
        "action_authorized",
    ):
        assert fragment in observation_merge_text
    observation_merge_schema = json.loads(
        OBSERVATION_MERGE_SCHEMA.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(observation_merge_schema)
    assert observation_merge_schema["$id"].endswith(
        "geotask-observation-merge-result-v0.1.schema.json"
    )
    assert observation_merge_schema["properties"]["observation_merge_result"][
        "$ref"
    ] == "#/$defs/result"
    assert observation_merge_schema["$defs"]["appliedClaim"]["properties"][
        "state"
    ]["enum"] == ["applied", "consolidated", "superseded"]
    assert observation_merge_schema["$defs"]["conflictResolution"]["properties"][
        "strategy"
    ]["enum"] == ["require_equal", "explicit_precedence"]
    assert observation_merge_schema["$defs"]["result"]["properties"][
        "conflict_resolutions"
    ]["items"]["$ref"] == "#/$defs/conflictResolution"
    assert observation_merge_schema["$defs"]["result"]["properties"][
        "conflict_resolutions"
    ]["minItems"] == 1

    registry_text = ARTIFACT_REGISTRY_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Artifact Registry v1.0",
        "geotask inspect schemas --format json",
        "ArtifactDescriptor",
        "geotask.document",
        "geotask.observation",
        "geotask.world-state",
        "geotask.state-transition",
        "geotask.verification-session",
        "geotask.discrepancy-report",
        "geotask.correction-request",
        "geotask.impact-graph",
        "geotask.recompute-derivation-result",
        "geotask.observation-merge-result",
        "geotask.world-state-materialization-result",
        "geotask.incremental-reevaluation-result",
        "geotask.execution-result",
        "geotask.control-evaluation",
        "geotask.agent-generation-preparation",
        "geotask.agent-revision-verification",
        "geotask.agent-revision-retry",
        "geotask.agent-evidence-recovery",
        "geotask.runtime-descriptor",
        "geotask.runtime-request",
        "geotask.runtime-response",
        "geotask.core-benchmark-report",
        "exactly twenty-three artifacts",
        "all twenty-four public JSON Schemas",
        "does not scan the filesystem",
    ):
        assert fragment in registry_text

    registry_schema = json.loads(ARTIFACT_REGISTRY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(registry_schema)
    assert registry_schema["$id"].endswith(
        "geotask-artifact-registry-v1.0.schema.json"
    )
    assert registry_schema["properties"]["artifact_registry"]["properties"][
        "registry_version"
    ]["const"] == "1.0"

    validation_text = VERSIONED_VALIDATION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "GeoTask Versioned Payload Validation v1.0",
        "VersionedPayloadContract",
        "EXECUTION_RESULT_VALIDATION_CONTRACT",
        "CONTROL_EVALUATION_VALIDATION_CONTRACT",
        "geotask control validate",
        "do not evaluate control expressions",
    ):
        assert fragment in validation_text

    profile_text = CONTROL_PROFILE_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "decision_rule",
        "evidence_request",
        "evidence_conflict",
        "task_gate",
        "unsupported_extension_profile",
        "extension_profile_violation",
        "invalid_expression",
    ):
        assert f"`{fragment}`" in profile_text

    expression_text = CONTROL_EXPRESSION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "geotask.control-expression",
        "Three-valued boolean semantics",
        "parse_control_expression",
        "evaluate_control_expression",
        "invalid_expression",
        "4096 characters",
        "1024",
        "64",
    ):
        assert fragment in expression_text
    assert "eval(" not in expression_text

    evaluation_text = CONTROL_EVALUATION_SPEC.read_text(encoding="utf-8")
    for fragment in (
        "Control Evaluation Result v1.0",
        "build_control_context",
        "evaluate_control_profile",
        "blocked_outputs",
        "eligible_outputs",
        '"action_executed": false',
        "does not automatically call it",
    ):
        assert fragment in evaluation_text

    evaluation_schema = CONTROL_EVALUATION_SCHEMA.read_text(encoding="utf-8")
    for fragment in (
        '"schema_version"',
        '"gate_satisfied"',
        '"control_context"',
        '"eligible_outputs"',
        '"action_executed": {"const": false}',
    ):
        assert fragment in evaluation_schema


def test_agent_integration_profile_and_skill_define_safe_recovery() -> None:
    specification = AGENT_INTEGRATION_SPEC.read_text(encoding="utf-8")
    skill = AGENT_SKILL.read_text(encoding="utf-8")

    for fragment in (
        "GeoTask Agent Integration Profile v0.1",
        "geotask.agent-integration",
        "inspect_artifacts",
        "validate_artifact",
        "execute_task",
        "evaluate_control",
        "geotask agent prepare",
        "agent_generated_distance_draft.yaml",
        "mechanical_only",
        "domain_inference_used=false",
        "revision_request/0.1",
        "agent_revision_verification/0.1",
        "agent_revision_retry/0.1",
        "geotask.agent-generation-preparation",
        "geotask.agent-revision-verification",
        "geotask.agent-revision-retry",
        "geotask-agent-generation-preparation-v0.1.schema.json",
        "geotask-agent-revision-verification-v0.1.schema.json",
        "geotask-agent-revision-retry-v0.1.schema.json",
        "registered public Artifacts",
        "candidate_values",
        "selected_value",
        "requested paths",
        "revision_base_sha256",
        "agent_generated_distance_blocked.yaml",
        "agent_generated_distance_revised.yaml",
        "geotask agent retry",
        "geotask agent recover",
        "task_reexecuted",
        "next_action_executed",
        "model_guess_used",
        "single named boolean condition",
    ):
        assert fragment in specification

    for fragment in (
        "name: geotask-core",
        "geotask agent inspect",
        "geotask agent prepare",
        "preparation-report.json",
        "geotask agent retry",
        "retry-report.json",
        "--verification-output revision-verification.json",
        "changed-path check",
        "artifact validate geotask.agent-generation-preparation",
        "artifact validate geotask.agent-revision-retry",
        "geotask agent recover",
        "geotask runtime inspect runtime-descriptor.json",
        "geotask runtime check runtime-descriptor.json runtime-request.json",
        "submitted=false",
        "side_effects_executed=false",
        "completed outputs must exactly match",
        "Do not answer `full_conflict=true`",
        "never invent an `explicit_precedence` order",
        "independently corroborate one another",
        "next_action_executed = false",
        "model_guess_used = false",
    ):
        assert fragment in skill

    assert "execute production actions" not in skill.lower()
    assert "Public Core examples must use fictional evidence" in skill


def test_runtime_interface_profile_defines_public_fail_closed_boundary() -> None:
    specification = RUNTIME_INTERFACE_SPEC.read_text(encoding="utf-8")

    for fragment in (
        "GeoTask Runtime Interface Profile v0.1",
        "geotask.runtime-interface",
        "RuntimeAdapter",
        "geotask.runtime-descriptor",
        "geotask.runtime-request",
        "geotask.runtime-response",
        "geotask.runtime.validate-artifact",
        "geotask.runtime.execute-nonlocal",
        "geotask.runtime.resolve-evidence",
        "geotask.runtime.execute-action",
        "geotask.reference.fail-closed",
        "geotask runtime inspect <runtime-descriptor.json>",
        "geotask runtime check",
        "submitted=false",
        "min_input_artifacts",
        "max_input_artifacts",
        "validate_runtime_response_contract",
        "structurally valid but contract-inconsistent",
        "side_effects_executed=false",
        "authorization_ref",
        "idempotency_key",
        "audit_ref",
        "never contain a password",
        "not a production Runtime",
    ):
        assert fragment in specification

    assert "model/provider routing" in specification
    assert "token and cost governance" in specification
    assert "outside Core" in specification
    assert "src/geotask_runtime" not in specification


def test_legacy_compatibility_docs_match_distributed_package() -> None:
    init_text = (ROOT / "src" / "geotask_core" / "__init__.py").read_text(
        encoding="utf-8"
    )
    migration_text = (ROOT / "MIGRATION.md").read_text(encoding="utf-8")

    assert "Old import paths (stir_core.*) are still supported" not in init_text
    assert "old ``stir_core`` Python package path is not" in init_text
    assert "old `stir_core` Python package path is not distributed" in migration_text
    assert "scripts/migrate_remote_to_geotask.sh" not in migration_text
    assert "git remote set-url origin" in migration_text


def test_root_readmes_match_current_capabilities() -> None:
    texts = (
        ROOT_README_ZH.read_text(encoding="utf-8"),
        ROOT_README_EN.read_text(encoding="utf-8"),
    )
    for text in texts:
        for operator in (
            "distance_2d",
            "line_intersects_rect",
            "point_to_line_distance_2d",
            "rect_contains_point",
            "time_overlap",
            "altitude_overlap",
        ):
            assert f"`{operator}`" in text
        for object_type in (
            "point",
            "polyline",
            "rect",
            "time_interval",
            "altitude_interval",
            "feature_collection",
        ):
            assert f"`{object_type}`" in text
        assert "geotask agent prepare" in text
        assert "geotask agent retry" in text
        assert "geotask runtime inspect" in text
        assert "geotask runtime check" in text
        assert "geotask runtime mock" in text
        assert "Runtime Interface Profile" in text or "Runtime接口Profile" in text

    zh_text, en_text = texts
    assert "调用方显式声明的语义相等合并或完整优先级选择" in zh_text
    assert "未声明策略的歧义命题冲突消解" in zh_text
    assert "caller-declared semantic-equality consolidation or complete precedence" in en_text
    assert "ambiguous claims without a declared policy" in en_text


def test_quickstarts_use_pypi_first_and_keep_source_install_for_contributors() -> None:
    for path in (QUICKSTART_EN, QUICKSTART_ZH):
        text = path.read_text(encoding="utf-8")
        assert "python -m pip install --no-cache-dir geotask-core==0.3.0" in text
        assert "from importlib.metadata import version" in text
        assert "geotask --help" in text
        assert "geotask inspect operators" in text
        assert "https://github.com/stpku/GeoTask.git" in text
        assert 'python -m pip install -e ".[dev]"' in text
        assert "geotask validate my_distance.yaml" in text
        assert "geotask run my_distance.yaml" in text
        assert "schemas/geotask-v1.0.schema.json" in text
        assert ".vscode/settings.json" in text
        assert '"yaml.schemas"' in text
        assert '"examples/core/v1_*.yaml"' in text


def test_vscode_schema_example_uses_local_native_v1_contract() -> None:
    settings_path = ROOT / ".vscode" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    assert settings == {
        "yaml.schemas": {
            "./schemas/geotask-v1.0.schema.json": [
                "**/*.geotask.yaml",
                "**/*.geotask.yml",
                "examples/core/v1_*.yaml",
            ]
        }
    }


def test_whitepaper_embeds_one_english_abstract_and_terminology_map() -> None:
    text = WHITEPAPER.read_text(encoding="utf-8")

    assert text.count("## English Abstract") == 1
    assert "explicit and verifiable spatiotemporal world model for AI agents" in text
    assert "| 世界状态 | world state |" in text
    assert "| 限定修订 | bounded revision |" in text
    assert "| 行动资格 | action eligibility |" in text

    for path in (ROOT_README_ZH, ROOT_README_EN, DOC_INDEX_ZH, DOC_INDEX_EN):
        navigation = path.read_text(encoding="utf-8")
        assert "GeoTask_White_Paper_v0.1.md#english-abstract" in navigation


def test_status_and_evidence_references_keep_core_and_workflow_states_separate() -> None:
    status_text = STATUS_MODEL.read_text(encoding="utf-8")
    evidence_text = EVIDENCE_REFERENCE.read_text(encoding="utf-8")

    assert "These belong under `extensions` or a Domain Pack" in status_text
    assert "They are not current Core `ClaimStatus` enum members" in status_text
    assert "value: false" in status_text
    assert "status: verified" in status_text

    assert "blocked_outputs" in evidence_text
    assert "resume_when" in evidence_text
    assert "request_conflict_review" in evidence_text
    assert "It does not mean all verified sources agree" in evidence_text


def test_all_public_markdown_relative_links_resolve_inside_public_export() -> None:
    public_paths = _public_source_paths()
    public_relative_paths = {
        path.relative_to(ROOT).as_posix()
        for path in public_paths
    }
    public_markdown = sorted(path for path in public_paths if path.suffix.lower() == ".md")
    missing: list[tuple[str, str, str]] = []

    for path in public_markdown:
        for raw_target in _markdown_links(path):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.exists():
                missing.append((path.relative_to(ROOT).as_posix(), raw_target, "missing"))
                continue
            if resolved.is_file():
                resolved_relative = resolved.relative_to(ROOT).as_posix()
                if resolved_relative not in public_relative_paths:
                    missing.append((path.relative_to(ROOT).as_posix(), raw_target, "excluded"))

    assert missing == []


def test_public_markdown_contains_no_obsolete_repository_urls() -> None:
    obsolete = (
        "github.com/GeoTask/geotask-core",
        "github.com/GeoTask/GeoTask",
    )
    findings: list[tuple[str, str]] = []
    for path in _public_source_paths():
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for value in obsolete:
            if value in text:
                findings.append((path.relative_to(ROOT).as_posix(), value))
    assert findings == []


def test_public_manifest_requires_localized_and_community_entrypoints() -> None:
    manifest = _manifest()
    required = set(manifest["required"])
    expected = {
        "README.md",
        "README.en.md",
        "docs/README.md",
        "docs/README.en.md",
        "docs/tutorials/quickstart.zh-CN.md",
        "docs/cookbook/gt01-gt20.zh-CN.md",
        "docs/spec/geotask-result-v1.0.md",
        "docs/spec/geotask-artifact-registry-v1.0.md",
        "docs/spec/geotask-versioned-payload-validation-v1.0.md",
        "docs/spec/geotask-agent-integration-profile-v0.1.md",
        "docs/spec/geotask-runtime-interface-profile-v0.1.md",
        "skills/geotask-core/SKILL.md",
        ".vscode/settings.json",
        "examples/core/v1_point_to_line_distance_minimal.en.yaml",
        "examples/core/v1_point_to_line_distance_minimal.zh-CN.yaml",
        "src/geotask_core/v1/agent_generation.py",
        "src/geotask_core/v1/agent_artifacts.py",
        "src/geotask_core/v1/runtime_interface.py",
        "examples/core/agent_generated_distance_draft.yaml",
        "examples/core/agent_generated_distance_blocked.yaml",
        "examples/core/agent_generated_distance_revised.yaml",
        "examples/core/runtime_reference_descriptor.json",
        "examples/core/runtime_validate_artifact_request.json",
        "tests/test_agent_generated_document_preparation.py",
        "tests/test_agent_generated_document_revision.py",
        "tests/test_agent_artifacts.py",
        "tests/test_agent_evidence_recovery_artifact.py",
        "tests/test_runtime_interface.py",
        "schemas/geotask-agent-generation-preparation-v0.1.schema.json",
        "schemas/geotask-agent-integration-v0.1.schema.json",
        "schemas/geotask-agent-revision-verification-v0.1.schema.json",
        "schemas/geotask-agent-revision-retry-v0.1.schema.json",
        "schemas/geotask-runtime-descriptor-v0.1.schema.json",
        "schemas/geotask-runtime-request-v0.1.schema.json",
        "schemas/geotask-runtime-response-v0.1.schema.json",
        "schemas/geotask-artifact-registry-v1.0.schema.json",
        "schemas/geotask-result-v1.0.schema.json",
        "CONTRIBUTING.zh-CN.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
    }
    assert expected <= required


def test_package_metadata_uses_english_readme_and_core_only_discovery() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'readme = "README.en.md"' in pyproject
    assert 'include = ["geotask_core*"]' in pyproject


def test_bilingual_community_files_exist() -> None:
    expected = (
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "operator_proposal.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "case_proposal.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "documentation.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        ROOT / ".github" / "dependabot.yml",
        CODEOWNERS,
        PYPI_WORKFLOW,
    )
    for path in expected:
        assert path.is_file(), path
        assert path.stat().st_size > 200, path


def test_public_preview_release_assets_are_consistent() -> None:
    citation = yaml.safe_load(CITATION.read_text(encoding="utf-8"))
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    release = RELEASE_NOTES.read_text(encoding="utf-8")
    codeowners = CODEOWNERS.read_text(encoding="utf-8")
    workflow = yaml.safe_load(PYPI_WORKFLOW.read_text(encoding="utf-8"))

    assert citation["cff-version"] == "1.2.0"
    assert citation["version"] == "0.3.0"
    assert str(citation["date-released"]) == "2026-07-31"
    assert citation["repository-code"] == "https://github.com/stpku/GeoTask"
    assert citation["url"] == "https://stpku.github.io/GeoTask/"
    assert citation["license"] == "MIT"
    assert "Explicit and Verifiable Spatiotemporal World Model" in citation["title"]
    assert "world models" in citation["keywords"]
    assert "explicit and verifiable spatiotemporal" in citation["abstract"]

    assert "public contracts and deterministic kernel for explicit, verifiable spatiotemporal world models" in pyproject
    assert '"world-model"' in pyproject
    assert '"embodied-ai"' in pyproject

    assert "v0.1：公共预览" in roadmap
    assert "v0.2.0：制品契约" in roadmap
    assert "v0.3.0：Agent集成（当前稳定）" in roadmap
    assert "v0.4：Runtime接口、模型适配与对象扩展" in roadmap
    assert "v0.5：Verifiable World-State Cycle" in roadmap
    assert "v0.6：Local Verification Providers与Domain Pack生态" in roadmap
    assert "Observation v0.1 Artifact" in roadmap
    assert "World State v0.1 Artifact" in roadmap
    assert "State Transition v0.1 Artifact" in roadmap
    assert "Verification Session v0.1 Artifact" in roadmap
    assert "geotask recheck" in roadmap

    assert "GeoTask Core v0.3.0 Agent Integration Release" in release
    assert "v0.3.0" in release
    assert "geotask-core==0.3.0" in release
    assert "geotask.agent-evidence-recovery" in release
    assert "1149 passed, 1 skipped" in release
    assert "153 passed" in release
    assert "272 files" in release
    assert "eight public Artifacts" in release
    assert "nine valid Schemas" in release
    assert "task_reexecuted=true" in release
    assert "model_guess_used=false" in release

    assert "/src/geotask_core/ @stpku" in codeowners
    assert "/.release/ @stpku" in codeowners
    assert workflow["name"] == "Publish geotask-core to PyPI"
    assert "workflow_dispatch" in workflow[True]
    assert workflow["concurrency"]["group"] == "publish-geotask-core-pypi"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert workflow["jobs"]["build"]["outputs"]["already_exists"] == "${{ steps.pypi-check.outputs.already_exists }}"
    assert workflow["jobs"]["publish"]["if"] == "needs.build.outputs.already_exists != 'true'"
    assert workflow["jobs"]["publish"]["permissions"]["id-token"] == "write"


def test_package_metadata_exposes_public_project_urls() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    required = (
        'license = "MIT"',
        'license-files = ["LICENSE"]',
        '"Programming Language :: Python :: 3.13"',
        'Homepage = "https://stpku.github.io/GeoTask/"',
        'Repository = "https://github.com/stpku/GeoTask"',
        'Roadmap = "https://github.com/stpku/GeoTask/blob/main/ROADMAP.md"',
    )
    for fragment in required:
        assert fragment in pyproject

    for private_or_dev_path in (
        "prune tests",
        "prune benchmarks",
        "prune patent_evidence",
        "prune src/geotask_domain_packs",
        "prune src/geotask_runtime",
    ):
        assert private_or_dev_path in manifest


def test_public_manifest_requires_release_governance_files() -> None:
    required = set(_manifest()["required"])
    expected = {
        "ROADMAP.md",
        "CITATION.cff",
        "docs/release_v0_1_0.md",
        "docs/release_v0_1_1.md",
        "docs/release_v0_2_0.md",
        "docs/release_v0_3_0.md",
        ".github/CODEOWNERS",
        ".github/workflows/publish-pypi.yml",
        "MANIFEST.in",
    }
    assert expected <= required


def test_cookbooks_cover_all_public_weekly_cases() -> None:
    for path in (COOKBOOK_EN, COOKBOOK_ZH):
        text = path.read_text(encoding="utf-8")
        for number in range(1, 21):
            assert f"GT{number:02d}" in text

        for example in (
            "v1_minimal_distance.yaml",
            "multi_constraint_conflict.yaml",
            "evidence_request_plan.yaml",
            "evidence_conflict_review.yaml",
            "robot_corridor_coordination.yaml",
            "robot_accessible_route.yaml",
            "uav_energy_reserve.yaml",
            "vehicle_clearance_envelope.yaml",
            "emergency_response_fastest_arrival.yaml",
            "robot_live_obstacle_stop.yaml",
            "uav_route_crossing_temporal_separation.yaml",
            "city_event_report_deduplication.yaml",
            "rescue_robot_shortest_route_hazard.yaml",
            "uav_arrival_ground_clearance_release.yaml",
            "vehicle_green_light_downstream_blockage.yaml",
        ):
            assert example in text
