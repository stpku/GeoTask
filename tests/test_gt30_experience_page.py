"""GT30 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt30" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt30_page_leads_with_three_source_two_to_one_conflict() -> None:
    html = _html()
    for fragment in (
        "第三个独立气象来源加入后，冲突就自动解决了吗？",
        "模拟气象服务报告8米/秒",
        "现场传感器和移动测风激光雷达都报告13米/秒",
        "三个独立分组",
        "两个来源给出相同数值 ≠ 系统已经获得多数表决权",
    ):
        assert fragment in html


def test_gt30_page_explains_unsafe_implicit_majority() -> None:
    html = _html()
    for fragment in (
        "自动采用多数票",
        "静默删除少数来源",
        "两票通过后自动阻断或放行",
        "没有任何已声明的多数表决规则",
    ):
        assert fragment in html


def test_gt30_page_exposes_unknown_and_explicit_adjudication() -> None:
    html = _html()
    for fragment in (
        "可信保证状态保持未知",
        "天气核验输出：阻断",
        "自动起飞授权：阻断",
        "起飞指令：阻断",
        "request_explicit_weather_adjudication",
    ):
        assert fragment in html


def test_gt30_page_preserves_public_core_boundaries() -> None:
    html = _html()
    for fragment in (
        "majority_policy_declared: false",
        "minority_source_discarded: false",
        "provider_precedence_inferred: false",
        "external_truth_verified: false",
        "production_output_released: false",
        "action_authorized: false",
        "action_executed: false",
    ):
        assert fragment in html


def test_gt30_page_has_deterministic_local_interaction() -> None:
    html = _html()
    for fragment in (
        'id="btn-majority"',
        'id="btn-discard"',
        'id="btn-adjudicate"',
        'id="verify"',
        "new Set(groups).size===3",
        "values.filter(v=>v===13).length===2",
        "new Set(values).size===2",
        "selected===allowed",
    ):
        assert fragment in html


def test_gt30_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    lower = html.lower()
    assert '<html lang="zh-cn">' in lower
    assert "fetch(" not in lower
    assert "xmlhttprequest" not in lower
    assert "authorization: bearer" not in lower
    assert "api_key" not in lower
    assert "analytics" not in lower
    assert "cookie" not in lower
    assert "验证提供方" not in html or "Verification Provider" not in html


def test_gt30_page_links_project_gt29_and_shared_navigation() -> None:
    html = _html()
    assert 'aria-label="返回GeoTask项目首页"' in html
    assert 'href="../gt29/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert "data-geotask-case-shared" in html
