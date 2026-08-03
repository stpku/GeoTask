from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT22_PAGE = ROOT / "site" / "gt22" / "index.html"
GT23_PAGE = ROOT / "site" / "gt23" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt23_page_contains_concrete_five_minute_flight_scenario() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt23-uav-state-change"',
        'as_of: "2026-07-16T10:02:00+08:00"',
        'as_of: "2026-07-16T10:07:00+08:00"',
        "revision: 1",
        "revision: 2",
        "battery_percent: 68",
        "battery_percent: 52",
        'object_valid_until: "2026-07-16T10:02:30+08:00"',
        'object_valid_until: "2026-07-16T10:07:30+08:00"',
        'successor_semantic_fingerprint: "4a5112aa71e7286ef37c69ef25af961e15894b25cbe5b7f948dbc4d3b81e1419"',
        'transition_semantic_fingerprint: "bc12e7c9332e824f27386a43eeae137e493b759fe7dea20b5383539dfaf313e7"',
        "generic_diff_computed_by_core: false",
        "impact_propagation_executed: false",
        "external_truth_verified: false",
        "action_authorized: false",
    )
    for fragment in required:
        assert fragment in html


def test_gt23_page_is_scenario_first_and_explains_necessity() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8")

    assert "无人机飞行五分钟后位置和电量都变了" in html
    assert "为什么不能只保留最新值？" in html
    assert "历史被覆盖" in html
    assert "变化依据丢失" in html
    assert "普通AI容易犯什么错误？" in html
    assert "字段更新成功" in html
    assert "技术实现：State Transition绑定了什么？" in html


def test_gt23_page_visualizes_before_after_and_validity_refresh() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "10:02 · 刚才" in html
    assert "10:07 · 现在" in html
    assert "位置 (120, 80, 35)" in html
    assert "位置 (260, 180, 48)" in html
    assert "电量 68%" in html
    assert "电量 52%" in html
    assert "位置变化 · 电量变化 · 有效期刷新" in html
    assert "不能偷偷延长" in html


def test_gt23_page_exposes_three_candidate_actions_and_local_check() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-overwrite"' in html
    assert 'id="btn-declare"' in html
    assert 'id="btn-bind"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "overwrite_latest_fields" in html
    assert "declare_change_without_binding" in html
    assert "bind_before_after_and_record_explicit_changes" in html
    assert "function localCheck" in html
    assert "changes.length===3" in html
    assert "local_deterministic" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt23_page_preserves_state_transition_safety_boundary() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8")

    assert "不证明Core自动发现了全部差异" in html
    assert "不代表影响传播、风险重算或行动授权已经完成" in html
    assert "公共v0.1加载器本身不比较快照内容" in html
    assert "GT23构造器额外执行案例级路径核验" in html


def test_gt23_page_is_static_and_secret_free() -> None:
    html = GT23_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt22_catalog_readme_and_sitemap_include_gt23() -> None:
    gt22_html = GT22_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt23/"' in gt22_html
    assert "GT23" in readme
    assert "https://stpku.github.io/GeoTask/gt23/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt23/" in readme
    assert "https://stpku.github.io/GeoTask/gt23/" in sitemap
    assert "gt23" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
