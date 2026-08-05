"""GT35 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt35" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt35_page_leads_with_stop_move_and_gap_problem() -> None:
    html = _html()
    assert "位置几乎没变就是停留，十分钟没观测就是失联吗？" in html
    assert "停留、移动与观测缺口合同" in html
    assert "不等于失联、异常或连续运动事实" in html


def test_gt35_page_shows_all_declared_thresholds_and_states() -> None:
    html = _html()
    for token in (
        "停留半径",
        "5 米",
        "最短停留时长",
        "120 秒",
        "最大观测间隔",
        "300 秒",
        "stationary_candidate",
        "moving_observed",
        "observation_gap",
        "unverifiable",
        "operator: trajectory_segment_classifications",
    ):
        assert token in html


def test_gt35_page_rejects_continuous_stop_lost_link_and_interpolation() -> None:
    html = _html()
    assert "直接判定连续停留10分钟" in html
    assert "直接判定设备失联" in html
    assert "自动补齐中间位置" in html
    assert "离散端点不能证明连续停留、失联或异常" in html


def test_gt35_page_exposes_non_inference_and_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "thresholds_caller_declared: true",
        "trajectory_interpolated: false",
        "loss_of_link_inferred: false",
        "anomaly_inferred: false",
        "future_position_predicted: false",
        "production_output_released: false",
        "command_sent: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt35_page_has_deterministic_local_interaction() -> None:
    html = _html()
    assert "allowedGap='observation_gap'" in html
    assert "disallowedGap='unverifiable'" in html
    assert "600秒超过300秒最大观测间隔" in html
    assert "不允许缺口标记" in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html


def test_gt35_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()


def test_gt35_page_links_project_gt34_and_shared_assets() -> None:
    html = _html()
    assert 'href="../"' in html
    assert 'href="../gt34/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert html.count('href="../assets/case-shared.css"') == 1
