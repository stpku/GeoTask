"""GT29 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt29" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt29_page_leads_with_concrete_weather_conflict() -> None:
    html = _html()
    for fragment in (
        "气象服务数据和现场传感器冲突时，AI应该相信谁？",
        "8米/秒",
        "13米/秒",
        "任务风速上限：12米/秒",
        "单个来源各自有效 ≠ 多个来源已经形成一致结论",
    ):
        assert fragment in html


def test_gt29_page_explains_four_unsafe_shortcuts() -> None:
    html = _html()
    for fragment in (
        "直接相信“权威”标签",
        "直接相信更新时间更近的数据",
        "对8和13取平均",
        "任选一个来源后自动放行",
        "不得用平均值消除证据冲突",
    ):
        assert fragment in html


def test_gt29_page_exposes_bounded_assurance_outcome() -> None:
    html = _html()
    for fragment in (
        "两个不同的独立性分组",
        "天气结论保持未知",
        "天气核验输出、自动起飞授权和起飞指令",
        "请求第三个独立气象验证来源",
        "request_third_independent_weather_verification",
    ):
        assert fragment in html


def test_gt29_page_does_not_claim_external_truth_or_action() -> None:
    html = _html()
    for fragment in (
        "provider_precedence_inferred: false",
        "values_averaged: false",
        "production_output_released: false",
        "action_authorized: false",
        "action_executed: false",
        "无网络验证",
        "无行动执行",
    ):
        assert fragment in html


def test_gt29_page_has_deterministic_local_interaction() -> None:
    html = _html()
    for fragment in (
        'id="btn-authority"',
        'id="btn-average"',
        'id="btn-independent"',
        'id="verify"',
        "new Set(groups).size===2",
        "values[0]!==values[1]",
        "selected===allowed",
    ):
        assert fragment in html


def test_gt29_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    lower = html.lower()
    assert '<html lang="zh-cn">' in lower
    assert "fetch(" not in lower
    assert "xmlhttprequest" not in lower
    assert "authorization: bearer" not in lower
    assert "api_key" not in lower
    assert "analytics" not in lower
    assert "cookie" not in lower
    assert "普通AI容易犯什么错误" in html
    assert "验证提供方" in html
    assert "Verification Provider" not in html


def test_gt29_page_links_project_gt28_and_shared_navigation() -> None:
    html = _html()
    assert 'aria-label="返回GeoTask项目首页"' in html
    assert 'href="../gt28/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert "data-geotask-case-shared" in html or "case-navigation.js" not in html
