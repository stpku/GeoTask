"""GT39 composite-case stage page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt39" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt39_page_leads_with_concrete_canonical_subject_choice() -> None:
    html = _html()
    for fragment in (
        "确认是同一架无人机后，哪个主体记录应保留为主身份？",
        "UAV-017",
        "第2/5阶段：归并提案",
        "ready_for_review ≠ proposal_approved",
        "提出subject_ref改写方案，也不等于已经改写对象关系图",
    ):
        assert fragment in html


def test_gt39_page_maps_machine_subjects_to_operational_meaning() -> None:
    html = _html()
    for fragment in (
        "UAV-017原始主体",
        "遮挡后临时主体",
        "provisional_alpha",
        "provisional_beta",
        "track_alpha",
        "track_beta",
        "保留为主身份",
        "保留为别名",
    ):
        assert fragment in html


def test_gt39_page_shows_closed_scope_alias_and_reversal() -> None:
    html = _html()
    for token in (
        "不能创建新身份",
        "不能删除旧标识",
        "不能扩大范围",
        "阻断、撤销、审批要求和归并回退方案",
        "保留别名并提交归并提案审批",
        "公共核心不能直接改写引用、删除旧标识或创建新身份",
        "request_identity_merge_approval",
    ):
        assert token in html


def test_gt39_page_shows_composite_case_navigation() -> None:
    html = _html()
    for fragment in (
        "GT38 · 1/5",
        "GT39 · 2/5",
        "GT40 · 3/5",
        "GT41 · 4/5",
        "GT42 · 5/5",
    ):
        assert fragment in html


def test_gt39_page_exposes_all_non_execution_flags() -> None:
    html = _html()
    for token in (
        "artifact_id: geotask.identity-merge-proposal",
        "new_identity_created: false",
        "alias_deleted: false",
        "proposal_approved: false",
        "object_graph_mutated: false",
        "identity_merge_performed: false",
        "subject_refs_mutated: false",
        "world_state_updated: false",
        "production_output_released: false",
        "action_authorized: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt39_page_is_static_secret_free_and_links_project() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()
    assert 'href="../"' in html
    assert 'href="../gt38/"' in html
    assert 'href="../gt40/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
