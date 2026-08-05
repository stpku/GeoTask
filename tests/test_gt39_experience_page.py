"""GT39 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt39" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt39_page_uses_current_chinese_identity_terms() -> None:
    html = _html()
    assert "对象同一性审定" in html
    assert "对象身份归并提案" in html
    assert "主对象引用" in html
    assert "拟归并对象" in html
    assert "保留别名" in html
    assert "归并回退方案" in html
    assert "身份合并合同" not in html
    assert "可信保证档案" not in html


def test_gt39_page_leads_with_proposal_not_execution() -> None:
    html = _html()
    assert "证据支持同一对象后，系统可以直接归并身份吗？" in html
    assert "仍然不可以" in html
    assert "ready_for_review ≠ proposal_approved" in html
    assert "提出subject_ref改写方案，也不等于已经改写对象关系图" in html


def test_gt39_page_shows_closed_scope_alias_and_reversal() -> None:
    html = _html()
    for token in (
        "provisional_alpha",
        "provisional_beta",
        "track_alpha",
        "track_beta",
        "不能创建新身份",
        "阻断、撤销、审批要求和归并回退方案",
        "request_identity_merge_approval",
    ):
        assert token in html


def test_gt39_page_rejects_direct_mutation_choices() -> None:
    html = _html()
    assert "立即改写track_beta的subject_ref" in html
    assert "删除provisional_beta" in html
    assert "创建一个新的主身份" in html
    assert "保留别名并提交归并提案审批" in html
    assert "公共核心不能直接改写引用、删除旧标识或创建新身份" in html


def test_gt39_page_exposes_all_non_execution_flags() -> None:
    html = _html()
    for token in (
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
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
