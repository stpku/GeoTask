"""GT38 composite-case entry page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt38" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt38_page_leads_with_concrete_uav_reidentification_problem() -> None:
    html = _html()
    for fragment in (
        "巡检无人机失联后出现新轨迹编号",
        "UAV-017",
        "园区电力线路巡检",
        "第1/5阶段：证据审定",
        "60秒后",
        "5米外",
    ):
        assert fragment in html


def test_gt38_page_explains_timeline_and_machine_display_mapping() -> None:
    html = _html()
    for fragment in (
        "08:02",
        "08:03",
        "track_alpha",
        "track_beta",
        "provisional_alpha",
        "provisional_beta",
        "UAV-017原始主体",
        "遮挡后临时主体",
    ):
        assert fragment in html


def test_gt38_page_explains_false_merge_and_missed_merge_risks() -> None:
    html = _html()
    for fragment in (
        "错误归并",
        "把另一架无人机并入UAV-017",
        "漏归并",
        "同一架无人机被重复计数",
        "责任追溯",
        "风险状态会被拆成两个对象",
    ):
        assert fragment in html


def test_gt38_page_shows_exact_candidate_provider_policy_chain() -> None:
    html = _html()
    for token in (
        "GT37",
        "same_object_candidate",
        "精确SHA-256",
        "虚构资产登记系统",
        "相同Remote ID和设备序列号",
        "虚构人工复核",
        "任务、机型、运营人和时间连续",
        "Assurance Profile",
        "至少2个Provider、2个独立组",
        "冲突时保持unknown",
    ):
        assert token in html


def test_gt38_page_shows_one_five_stage_composite_case() -> None:
    html = _html()
    assert "GT38—GT42不是五个独立业务案例" in html
    for case_id, label in (
        ("GT38 · 1/5", "证据审定"),
        ("GT39 · 2/5", "归并提案"),
        ("GT40 · 3/5", "提案审批"),
        ("GT41 · 4/5", "变更请求"),
        ("GT42 · 5/5", "应用审批"),
    ):
        assert case_id in html
        assert label in html


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
    assert 'href="../gt39/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
