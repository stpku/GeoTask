"""GT36 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt36" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt36_page_leads_with_acceleration_and_continuity_problem() -> None:
    html = _html()
    assert "两段平均速度变了，就能证明瞬时加速度和连续运动吗？" in html
    assert "加速度与运动连续性合同" in html
    assert "标量加速度估计，不是瞬时加速度向量" in html


def test_gt36_page_shows_declared_midpoint_and_gap_contract() -> None:
    html = _html()
    for token in (
        "segment_midpoint",
        "300秒",
        "Δ平均速度 ÷ Δ中点时间",
        "continuous_observation",
        "unverifiable",
        "operator: trajectory_segment_acceleration_estimates",
    ):
        assert token in html


def test_gt36_page_shows_zero_positive_and_gap_transitions() -> None:
    html = _html()
    assert "0.5 → 0.5" in html
    assert "0.5 → 1.0" in html
    assert "1/300" in html
    assert "下一段持续600秒" in html
    assert "加速度和速度差均为null" in html


def test_gt36_page_rejects_gap_vector_and_prediction_overclaim() -> None:
    html = _html()
    assert "把600秒分段当连续运动并计算减速度" in html
    assert "输出加速度向量和转弯方向" in html
    assert "据此预测下一时刻位置" in html
    assert "平均速度大小不能证明瞬时或向量加速度" in html


def test_gt36_page_exposes_non_inference_and_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "instantaneous_acceleration_verified: false",
        "vector_acceleration_verified: false",
        "direction_change_inferred: false",
        "trajectory_interpolated: false",
        "future_position_predicted: false",
        "production_output_released: false",
        "command_sent: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt36_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()


def test_gt36_page_links_project_gt35_and_shared_assets() -> None:
    html = _html()
    assert 'href="../"' in html
    assert 'href="../gt35/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
