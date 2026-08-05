"""GT38 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt38" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt38_page_leads_with_identity_adjudication_problem() -> None:
    html = _html()
    assert "两个独立证据都支持同一对象，Core就可以直接合并身份吗？" in html
    assert "身份候选证据与显式裁决" in html
    assert "裁决最多建议进入身份合并复核" in html


def test_gt38_page_shows_exact_candidate_provider_policy_chain() -> None:
    html = _html()
    for token in (
        "GT37",
        "same_object_candidate",
        "精确SHA-256",
        "2个Provider / 2个组",
        "Assurance Profile",
        "冲突时保持unknown",
    ):
        assert token in html


def test_gt38_page_shows_confirmation_but_only_review_recommendation() -> None:
    html = _html()
    for token in (
        "same_object_confirmed",
        "candidate_alignment: aligned",
        "recommend_identity_merge_review",
        "next_action: review_identity_merge",
        "same_object_confirmed ≠ identity_merge_performed",
    ):
        assert token in html


def test_gt38_page_rejects_merge_rewrite_and_publish_actions() -> None:
    html = _html()
    assert "Core直接合并两个身份" in html
    assert "自动改写track_beta的subject_ref" in html
    assert "立即发布生产身份更新" in html
    assert "保留全部证据并进入合并复核" in html
    assert "不能直接合并身份、改写引用或发布生产更新" in html


def test_gt38_page_exposes_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "external_identity_verified_by_core: false",
        "identity_merge_performed: false",
        "subject_refs_mutated: false",
        "production_output_released: false",
        "action_authorized: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt38_page_is_static_secret_free_and_links_project() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()
    assert 'href="../"' in html
    assert 'href="../gt37/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
