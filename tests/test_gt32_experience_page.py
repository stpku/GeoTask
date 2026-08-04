"""GT32 public experience page tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt32" / "index.html"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_gt32_page_leads_with_progressive_authorization_problem() -> None:
    html = _html()
    for fragment in (
        "五项授权陆续到达后，什么时候才算可起飞？",
        "空域、运营人、起降场、气象放行和任务授权",
        "每份证据进入后重新计算门禁",
        "未知授权从5项逐步降到0",
    ):
        assert fragment in html


def test_gt32_page_shows_all_five_authorization_steps() -> None:
    html = _html()
    for fragment in (
        "空域授权",
        "运营人授权",
        "起降场授权",
        "气象放行",
        "任务授权",
        "剩余未知：4项",
        "剩余未知：0项",
    ):
        assert fragment in html


def test_gt32_page_separates_gate_output_and_real_action() -> None:
    html = _html()
    for fragment in (
        "全部条件满足",
        "起飞相关输出可用",
        "飞机仍未起飞",
        "最后一个授权到达，只让输出变为可用",
        "不代表指令已经发送",
    ):
        assert fragment in html


def test_gt32_page_exposes_non_execution_boundary() -> None:
    html = _html()
    for fragment in (
        "unknown_authorization_count: 5 -> 4 -> 3 -> 2 -> 1 -> 0",
        "control_state: satisfied",
        "automatic_takeoff_authorization: eligible",
        "takeoff_command: eligible",
        "production_output_released: false",
        "command_sent: false",
        "action_authorized_by_core: false",
        "action_executed: false",
    ):
        assert fragment in html


def test_gt32_page_has_deterministic_local_interaction() -> None:
    html = _html()
    for fragment in (
        'id="btn-early"',
        'id="btn-send"',
        'id="btn-handoff"',
        'id="verify"',
        "unknownCounts.join(',')==='4,3,2,1,0'",
        "finalEligible.length===2",
        "selected===allowed",
    ):
        assert fragment in html


def test_gt32_page_is_static_secret_free_and_chinese_first() -> None:
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


def test_gt32_page_links_project_gt31_and_shared_assets() -> None:
    html = _html()
    assert 'aria-label="返回GeoTask项目首页"' in html
    assert 'href="../gt31/"' in html
    assert 'href="https://github.com/stpku/GeoTask"' in html
    assert "data-geotask-case-shared" in html
