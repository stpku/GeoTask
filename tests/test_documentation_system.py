import json
import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "geotask-v1.0.schema.json"
DOC_INDEX = ROOT / "docs" / "README.md"
WHITEPAPER = ROOT / "docs" / "whitepaper" / "GeoTask_White_Paper_v0.1.md"
WHITEPAPER_BUILD = ROOT / "docs" / "whitepaper" / "README.md"
LANGUAGE_SPEC = ROOT / "docs" / "spec" / "geotask-language-spec-v1.0.md"
TARGET_SPEC_STATUS = ROOT / "docs" / "spec" / "target-specification-status.md"
QUICKSTART = ROOT / "docs" / "tutorials" / "quickstart.md"
STATUS_MODEL = ROOT / "docs" / "reference" / "status-model.md"
EVIDENCE_REFERENCE = ROOT / "docs" / "reference" / "evidence-and-recovery.md"
COOKBOOK = ROOT / "docs" / "cookbook" / "gt01-gt13.md"


DOCUMENTS = (
    DOC_INDEX,
    WHITEPAPER,
    WHITEPAPER_BUILD,
    LANGUAGE_SPEC,
    TARGET_SPEC_STATUS,
    QUICKSTART,
    STATUS_MODEL,
    EVIDENCE_REFERENCE,
    COOKBOOK,
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
)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


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


def test_document_index_links_the_primary_documentation_layers() -> None:
    text = DOC_INDEX.read_text(encoding="utf-8")

    expected_links = (
        "whitepaper/GeoTask_White_Paper_v0.1.md",
        "whitepaper/README.md",
        "spec/geotask-language-spec-v1.0.md",
        "tutorials/quickstart.md",
        "reference/status-model.md",
        "reference/evidence-and-recovery.md",
        "cookbook/gt01-gt13.md",
        "../schemas/geotask-v1.0.schema.json",
        "spec/target-specification-status.md",
    )
    for link in expected_links:
        assert link in text

    assert "Implemented public profile" in text
    assert "System-level target direction" in text
    assert "Legacy compatibility" in text


def test_whitepaper_states_architecture_and_public_boundary() -> None:
    text = WHITEPAPER.read_text(encoding="utf-8")

    required_fragments = (
        "面向智能体的可验证时空任务表示与执行框架",
        "对象、算子和命题显式绑定",
        "生成与验证分离",
        "证据冲突",
        "GT01–GT13",
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


def test_quickstart_uses_real_repository_and_cli() -> None:
    text = QUICKSTART.read_text(encoding="utf-8")

    assert "https://github.com/stpku/GeoTask.git" in text
    assert "geotask validate my_distance.yaml" in text
    assert "geotask run my_distance.yaml" in text
    assert "geotask inspect operators" in text
    assert "schemas/geotask-v1.0.schema.json" in text


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
    assert "individually verified evidence can still" not in evidence_text.lower()
    assert "It does not mean all verified sources agree" in evidence_text


def test_primary_documentation_relative_links_resolve() -> None:
    primary_documents = (
        ROOT / "README.md",
        DOC_INDEX,
        WHITEPAPER,
        WHITEPAPER_BUILD,
        LANGUAGE_SPEC,
        TARGET_SPEC_STATUS,
        QUICKSTART,
        STATUS_MODEL,
        EVIDENCE_REFERENCE,
        COOKBOOK,
    )
    missing: list[tuple[str, str]] = []

    for path in primary_documents:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.exists():
                missing.append((str(path.relative_to(ROOT)), target))

    assert missing == []


def test_cookbook_covers_all_public_weekly_cases() -> None:
    text = COOKBOOK.read_text(encoding="utf-8")

    for number in range(1, 14):
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
    ):
        assert example in text
