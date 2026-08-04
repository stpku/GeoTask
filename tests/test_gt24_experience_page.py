from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT23_PAGE = ROOT / "site" / "gt23" / "index.html"
GT24_PAGE = ROOT / "site" / "gt24" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt24_page_contains_concrete_temporary_zone_scenario() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt24-temporary-no-fly-zone-impact"',
        'active_window: "2026-08-04T14:00:00+08:00/2026-08-04T16:00:00+08:00"',
        "route-medical-a",
        "route-inspection-b",
        "mission-medical-17",
        "approval-medical-17",
        "mission-inspection-08",
        "approval-inspection-08",
        "intersects_active_zone: true",
        "intersects_active_zone: false",
        "assertions_requiring_recheck: 2",
        'world_state_semantic_fingerprint: "819d68c21176a6d0f5b78946b37ed80a7c7d31074b30c823fc0ddded6af348f0"',
        'discrepancy_semantic_fingerprint: "250aa032c3908dff58f1bad5e85c5eba36cc195fa76d4ff6e40ba0bd34fd1512"',
        'impact_graph_semantic_fingerprint: "12e7908066d35dc9d7cbe161996b7d22aaddeec32b0cb6013eddf5c1a83a2a2e"',
    )
    for fragment in required:
        assert fragment in html


def test_gt24_page_is_scenario_first_and_explains_necessity() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8")

    assert "临时禁飞区发布后，哪些航线、任务和审批结论必须重新检查？" in html
    assert "为什么必须先确定影响范围？" in html
    assert "全部重算" in html
    assert "只更新地图" in html
    assert "普通AI容易犯什么错误？" in html
    assert "哪些下游结论依赖这项变化" in html
    assert "技术实现：Impact Graph记录了什么？" in html


def test_gt24_page_visualizes_affected_and_unaffected_routes() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "临时禁飞区" in html
    assert "14:00—16:00" in html
    assert "医疗航线A" in html
    assert "巡检航线B" in html
    assert "航线A：相交 true" in html
    assert "航线B：相交 false" in html
    assert "医疗任务17" in html
    assert "审批结论17" in html
    assert "起飞动作" in html


def test_gt24_page_exposes_three_candidate_actions_and_local_check() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-all"' in html
    assert 'id="btn-map"' in html
    assert 'id="btn-scope"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "recompute_all_operations" in html
    assert "update_map_only_keep_clearances" in html
    assert "validate_declared_impact_chain" in html
    assert "function localCheck" in html
    assert "nodeCount===7" in html
    assert "blockedOutputs===2" in html
    assert "blockedActions===1" in html
    assert "local_deterministic" in html
    assert "https://chat.deepseek.com/" in html


def test_gt24_page_preserves_impact_graph_safety_boundary() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8")

    for fragment in (
        "geometry_intersection_computed_by_core: false",
        "impact_discovered_by_core: false",
        "declared_scope_validated: true",
        "propagation_executed: false",
        "reevaluation_executed: false",
        "outputs_released: false",
        "external_truth_verified: false",
        "action_authorized: false",
        "不证明Core完成了几何求交",
        "自动影响发现",
        "公共v0.1不会自动发现依赖关系或执行传播",
    ):
        assert fragment in html


def test_gt24_page_is_static_and_secret_free() -> None:
    html = GT24_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt23_catalog_readme_and_sitemap_include_gt24() -> None:
    gt23_html = GT23_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt24/"' in gt23_html
    assert "GT24" in readme
    assert "https://stpku.github.io/GeoTask/gt24/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt24/" in readme
    assert "https://stpku.github.io/GeoTask/gt24/" in sitemap
    assert "gt24" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
