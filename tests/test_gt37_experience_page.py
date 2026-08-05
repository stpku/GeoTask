"""GT37 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt37" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt37_page_leads_with_identity_candidate_problem() -> None:
    html = _html()
    assert "两段轨迹只差60秒和5米，就能自动认定为同一个对象吗？" in html
    assert "对象身份候选合同" in html
    assert "候选结论不等于现实身份已经核验" in html


def test_gt37_page_shows_declared_policy_and_candidate_result() -> None:
    html = _html()
    for token in (
        "最大120秒",
        "最大10米",
        "必须同为UAV",
        "same_object_candidate",
        "provisional_alpha",
        "provisional_beta",
        "operator: trajectory_identity_candidate",
    ):
        assert token in html


def test_gt37_page_rejects_merge_rewrite_and_external_identity_overclaim() -> None:
    html = _html()
    assert "直接合并两个临时身份" in html
    assert "把track_beta改绑到provisional_alpha" in html
    assert "宣称现实身份已经核验" in html
    assert "不能自动合并对象、改写引用或证明现实身份" in html


def test_gt37_page_exposes_non_mutation_and_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "identity_merge_performed: false",
        "subject_refs_mutated: false",
        "real_world_identity_verified: false",
        "trajectory_interpolated: false",
        "future_position_predicted: false",
        "production_output_released: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt37_page_is_static_secret_free_and_links_project() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()
    assert 'href="../"' in html
    assert 'href="../gt36/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
