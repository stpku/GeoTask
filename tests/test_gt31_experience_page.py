"""GT31 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt31" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt31_page_leads_with_human_adjudication_after_gt30() -> None:
    html = _html()
    for fragment in (
        "人工复核解决气象冲突后，天气合格就能自动起飞吗？",
        "8、13、13米/秒",
        "共享局部测试气流",
        "三份原始响应全部保留",
    ):
        assert fragment in html


def test_gt31_page_separates_three_gate_layers() -> None:
    html = _html()
    for fragment in (
        "证据裁决完成",
        "天气结论可用",
        "起飞授权仍未成立",
        "天气条件已核验 ≠ 自动起飞已获授权",
    ):
        assert fragment in html


def test_gt31_page_preserves_conflicting_evidence_and_rejects_majority_shortcut() -> None:
    html = _html()
    for fragment in (
        "不采用二比一",
        "不删除两份13米/秒响应",
        "只调整它们对当前任务命题的适用范围",
        "shared_local_test_interference",
    ):
        assert fragment in html


def test_gt31_page_exposes_weather_eligible_takeoff_blocked_boundary() -> None:
    html = _html()
    for fragment in (
        "weather_condition_verified: eligible",
        "automatic_takeoff_authorization: blocked",
        "takeoff_command: blocked",
        "production_output_released: false",
        "action_authorized: false",
        "action_executed: false",
    ):
        assert fragment in html


def test_gt31_page_has_deterministic_local_interaction() -> None:
    html = _html()
    for fragment in (
        'id="btn-majority"',
        'id="btn-auto"',
        'id="btn-bounded"',
        'id="verify"',
        "responsesRetained===3",
        "selectedWind===8",
        "selected===allowed",
    ):
        assert fragment in html


def test_gt31_page_is_static_secret_free_and_chinese_first() -> None:
    html = _html()
    lower = html.lower()
    assert '<html lang="zh-cn">' in lower
    assert "fetch(" not in lower
    assert "xmlhttprequest" not in lower
    assert "authorization: bearer" not in lower
    assert "api_key" not in lower
    assert "analytics" not in lower
    assert "cookie" not in lower
    assert "Verification Provider" not in html


def test_gt31_page_links_project_gt30_and_shared_navigation() -> None:
    html = _html()
    assert 'aria-label="返回GeoTask项目首页"' in html
    assert 'href="../gt30/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert "data-geotask-case-shared" in html
