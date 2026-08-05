"""GT33 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt33" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt33_page_leads_with_dynamic_object_problem() -> None:
    html = _html()
    assert "三个带时间位置点连起来，就是一条可验证轨迹吗？" in html
    assert "移动对象与离散轨迹合同" in html
    assert "静态折线只有几何顺序，没有对象身份和观测时间" in html


def test_gt33_page_shows_explicit_samples_and_duration() -> None:
    html = _html()
    for token in (
        "08:00:00 +08:00",
        "08:02:00 +08:00",
        "08:05:00 +08:00",
        "[0, 0]",
        "[12, 5]",
        "[30, 40]",
        "trajectory_duration_seconds: 300.0",
    ):
        assert token in html


def test_gt33_page_rejects_static_polyline_interpolation_and_prediction() -> None:
    html = _html()
    assert "把三个点当作静态折线" in html
    assert "自动线性插值中间位置" in html
    assert "预测下一时刻位置" in html
    assert "静态折线不能替代带时间轨迹" in html


def test_gt33_page_exposes_non_execution_boundary() -> None:
    html = _html()
    for token in (
        "future_position_predicted: false",
        "map_matched: false",
        "production_output_released: false",
        "command_sent: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert token in html


def test_gt33_page_has_deterministic_local_interaction() -> None:
    html = _html()
    assert "const samples=[" in html
    assert "Date.parse" in html
    assert "duration===300" in html
    assert "validate_discrete_trajectory" in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html


def test_gt33_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    assert '<html lang="zh-CN">' in html
    assert "api_key" not in html.lower()
    assert "bearer " not in html.lower()
    assert "password" not in html.lower()
    assert "localhost" not in html.lower()


def test_gt33_page_links_project_gt32_and_shared_assets() -> None:
    html = _html()
    assert 'href="../"' in html
    assert 'href="../gt32/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert 'href="../assets/case-shared.css"' in html
    assert 'src="../assets/case-navigation.js"' in html
