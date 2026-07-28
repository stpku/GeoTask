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
LANGUAGE_SPEC = ROOT / "docs" / "spec" / "geotask-language-spec-v1.0.md"
TARGET_SPEC_STATUS = ROOT / "docs" / "spec" / "target-specification-status.md"
QUICKSTART_EN = ROOT / "docs" / "tutorials" / "quickstart.md"
QUICKSTART_ZH = ROOT / "docs" / "tutorials" / "quickstart.zh-CN.md"
STATUS_MODEL = ROOT / "docs" / "reference" / "status-model.md"
EVIDENCE_REFERENCE = ROOT / "docs" / "reference" / "evidence-and-recovery.md"
COOKBOOK_EN = ROOT / "docs" / "cookbook" / "gt01-gt16.md"
COOKBOOK_ZH = ROOT / "docs" / "cookbook" / "gt01-gt16.zh-CN.md"
CONTRIBUTING_EN = ROOT / "CONTRIBUTING.md"
CONTRIBUTING_ZH = ROOT / "CONTRIBUTING.zh-CN.md"
CODE_OF_CONDUCT = ROOT / "CODE_OF_CONDUCT.md"
CITATION = ROOT / "CITATION.cff"
ROADMAP = ROOT / "ROADMAP.md"
RELEASE_NOTES_010 = ROOT / "docs" / "release_v0_1_0.md"
RELEASE_NOTES = ROOT / "docs" / "release_v0_1_1.md"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
PYPI_WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"


DOCUMENTS = (
    ROOT_README_ZH,
    ROOT_README_EN,
    DOC_INDEX_ZH,
    DOC_INDEX_EN,
    WHITEPAPER,
    WHITEPAPER_BUILD,
    LANGUAGE_SPEC,
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
    assert "面向AI智能体的可验证时空任务协议" in root_zh
    assert "Verifiable spatiotemporal task protocol for AI agents" in root_en


def test_document_indexes_link_primary_layers_and_localized_guides() -> None:
    zh_text = DOC_INDEX_ZH.read_text(encoding="utf-8")
    en_text = DOC_INDEX_EN.read_text(encoding="utf-8")

    expected_links = (
        "whitepaper/GeoTask_White_Paper_v0.1.md",
        "whitepaper/README.md",
        "spec/geotask-language-spec-v1.0.md",
        "tutorials/quickstart.md",
        "tutorials/quickstart.zh-CN.md",
        "reference/status-model.md",
        "reference/evidence-and-recovery.md",
        "cookbook/gt01-gt16.md",
        "cookbook/gt01-gt16.zh-CN.md",
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


def test_whitepaper_states_architecture_and_public_boundary() -> None:
    text = WHITEPAPER.read_text(encoding="utf-8")

    required_fragments = (
        "面向智能体的可验证时空任务表示与执行框架",
        "对象、算子和命题显式绑定",
        "生成与验证分离",
        "证据冲突",
        "GT01–GT16",
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


def test_quickstarts_use_pypi_first_and_keep_source_install_for_contributors() -> None:
    for path in (QUICKSTART_EN, QUICKSTART_ZH):
        text = path.read_text(encoding="utf-8")
        assert "python -m pip install --no-cache-dir geotask-core==0.1.1" in text
        assert "from importlib.metadata import version" in text
        assert "geotask --help" in text
        assert "geotask inspect operators" in text
        assert "https://github.com/stpku/GeoTask.git" in text
        assert 'python -m pip install -e ".[dev]"' in text
        assert "geotask validate my_distance.yaml" in text
        assert "geotask run my_distance.yaml" in text
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
        "docs/cookbook/gt01-gt16.zh-CN.md",
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
    roadmap = ROADMAP.read_text(encoding="utf-8")
    release = RELEASE_NOTES.read_text(encoding="utf-8")
    codeowners = CODEOWNERS.read_text(encoding="utf-8")
    workflow = yaml.safe_load(PYPI_WORKFLOW.read_text(encoding="utf-8"))

    assert citation["cff-version"] == "1.2.0"
    assert citation["version"] == "0.1.1"
    assert citation["repository-code"] == "https://github.com/stpku/GeoTask"
    assert citation["url"] == "https://stpku.github.io/GeoTask/"
    assert citation["license"] == "MIT"

    assert "v0.1：公共预览" in roadmap
    assert "v0.2：扩展空间对象与开发体验" in roadmap
    assert "v0.3：Runtime接口与模型适配" in roadmap
    assert "v0.4：Domain Pack规范与生态" in roadmap

    assert "GeoTask Core v0.1.1 PyPI Hotfix" in release
    assert "v0.1.1" in release
    assert "geotask-core==0.1.1" in release
    assert "geotask_core.__version__" in release
    assert "Both lines should print `0.1.1`" in release

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
        ".github/CODEOWNERS",
        ".github/workflows/publish-pypi.yml",
        "MANIFEST.in",
    }
    assert expected <= required


def test_cookbooks_cover_all_public_weekly_cases() -> None:
    for path in (COOKBOOK_EN, COOKBOOK_ZH):
        text = path.read_text(encoding="utf-8")
        for number in range(1, 17):
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
        ):
            assert example in text
