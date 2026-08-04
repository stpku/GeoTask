from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT25_PAGE = ROOT / "site" / "gt25" / "index.html"
GT26_PAGE = ROOT / "site" / "gt26" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt26_page_contains_concrete_schedule_scenario() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8")
    required = (
        'id: "gt26-flight-service-station-schedule-correction"',
        'start: "08:00"',
        'end: "22:00"',
        'start: "09:00"',
        'end: "18:00"',
        'requested_service_time: "20:30"',
        'location_code: "fictional-east-hub"',
        "radio_frequency_mhz: 125.75",
        'contact_channel: "fictional-ops-desk"',
        'world_state_semantic_fingerprint: "d1d73bd3ee443a0f506311a4d68f85ab713d60674e9cc98d630584f49edaa26c"',
        'discrepancy_semantic_fingerprint: "bcbc6d5644c9bcbde03163dc9024f9c5a9d0e9dc0c3cdcd8df8ba2bff0f91b83"',
        'correction_semantic_fingerprint: "aa165ba2e6ee673008c8bcbaeab719c4d99ce19ab5a103f1f7ef5303b700b259"',
    )
    for fragment in required:
        assert fragment in html


def test_gt26_page_is_scenario_first_and_explains_necessity() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8")
    assert "飞行服务站营业时间已经失效，系统应该改哪条数据，而不是推翻全部结果？" in html
    assert "为什么不能删除整条站点记录？" in html
    assert "整站作废" in html
    assert "直接改完继续派发" in html
    assert "普通AI容易犯什么错误？" in html
    assert "保留”表示这些字段不在本次纠偏范围内" in html
    assert "技术实现：差异报告与纠偏请求分别做什么？" in html


def test_gt26_page_shows_one_mutable_and_four_preserved_fields() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8")
    assert "/objects/flight-service-station-east/attributes/operating_schedule/value" in html
    assert "08:00—22:00" in html
    assert "09:00—18:00" in html
    assert "fictional-east-hub" in html
    assert "125.75 MHz" in html
    assert "飞行情报、气象简报" in html
    assert "fictional-ops-desk" in html
    assert "允许修改路径</small><code>1" in html
    assert "不可变字段</small><code>4" in html


def test_gt26_page_exposes_three_actions_and_local_check() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8")
    assert 'id="btn-discard"' in html
    assert 'id="btn-release"' in html
    assert 'id="btn-bounded"' in html
    assert "discard_entire_station" in html
    assert "replace_schedule_and_release" in html
    assert "correct_schedule_then_recheck" in html
    assert "function localCheck" in html
    assert "local_deterministic" in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "https://chat.deepseek.com/" in html


def test_gt26_page_preserves_correction_safety_boundary() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8")
    for fragment in (
        "source_compared_by_core: false",
        "declared_scope_validated: true",
        "correction_applied: false",
        "successor_materialized: false",
        "mission_rechecked: false",
        "outputs_released: false",
        "external_truth_verified: false",
        "action_authorized: false",
        "action_executed: false",
        "不证明Core获取或比较了真实公告",
        "1 output / 1 action",
    ):
        assert fragment in html


def test_gt26_page_is_static_and_secret_free() -> None:
    html = GT26_PAGE.read_text(encoding="utf-8").lower()
    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt25_navigation_readme_and_sitemap_include_gt26() -> None:
    gt25_html = GT25_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert 'href="../gt26/"' in gt25_html
    assert "GT26" in readme
    assert "https://stpku.github.io/GeoTask/gt26/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt26/" in readme
    assert "https://stpku.github.io/GeoTask/gt26/" in sitemap
    assert "gt26" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
