"""GT34 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt34" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt34_page_leads_with_segment_measurement_problem() -> None:
    html = _html()
    assert "三个轨迹样本之间，每一段到底移动了多远、多快？" in html
    assert "离散轨迹分段与平均速度合同" in html
    assert "不代表中间每一时刻的瞬时速度" in html


def test_gt34_page_shows_explicit_samples_and_segment_metrics() -> None:
    html = _html()
    for token in (
        "[0, 0]",
        "[36, 48]",
        "[36, 138]",
        "120秒 · 60水平单位 · 0.5水平单位/秒",
        "180秒 · 90水平单位 · 0.5水平单位/秒",
        "operator: trajectory_segment_metrics",
        "segment_count: 2",
        "speed_unit: horizontal_unit_per_second",
    ):
        assert token in html


def test_gt34_page_rejects_endpoint_collapse_instant_speed_and_prediction() -> None:
    html = _html()
    assert "只用首末点计算一段" in html
    assert "把平均速度当作瞬时速度" in html
    assert "根据两段速度预测未来" in html
    assert "必须按相邻明确样本绑定分段" in html


def test_gt34_page_exposes_non_inference_and_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "trajectory_interpolated: false",
        "trajectory_smoothed: false",
        "future_position_predicted: false",
        "acceleration_computed: false",
        "production_output_released: false",
        "command_sent: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt34_page_has_deterministic_local_interaction() -> None:
    html = _html()
    assert "const samples=[" in html
    assert "Math.hypot" in html
    assert "metrics.length===2" in html
    assert "metrics.every(m=>m.speed===0.5)" in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html


def test_gt34_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()


def test_gt34_page_links_project_gt33_and_shared_assets_once() -> None:
    html = _html()
    assert 'href="../"' in html
    assert 'href="../gt33/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
    assert html.count('src="../assets/case-navigation.js"') == 1
