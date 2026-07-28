from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT17_PAGE = ROOT / "site" / "gt17" / "index.html"
GT18_PAGE = ROOT / "site" / "gt18" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt18_page_contains_route_and_robot_capability_task() -> None:
    html = GT18_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt18-rescue-robot-shortest-route-hazard"',
        "shortest_route_length_m: 120",
        "safe_route_length_m: 260",
        "shortest_route_is_geometrically_shortest: true",
        "shortest_route_intersects_high_temperature_zone: true",
        "safe_route_intersects_high_temperature_zone: false",
        "shortest_route_max_temperature_c: 120",
        "safe_route_max_temperature_c: 60",
        "maximum_operating_temperature_c: 80",
        "shortest_route_executable: false",
        "safe_route_executable: true",
        'selected_action: "enter_via_safe_route"',
        'expected_status: "verified_safe_route_entry"',
    )
    for fragment in required:
        assert fragment in html


def test_gt18_page_visualizes_shortest_and_safe_routes() -> None:
    html = GT18_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "120℃高温区" in html
    assert "机器人上限80℃" in html
    assert "最短路线 120米 · 不可执行" in html
    assert "安全路线 260米 · 可执行" in html
    assert "true AND NOT true" in html


def test_gt18_page_recomputes_distance_and_hazard_intersection_locally() -> None:
    html = GT18_PAGE.read_text(encoding="utf-8")

    assert "function distance" in html
    assert "function lineIntersectsRect" in html
    assert "shortestLength=distance(entry,target)" in html
    assert "safeLength=distance(entry,safe1)+distance(safe1,safe2)+distance(safe2,target)" in html
    assert "shortestHazard=lineIntersectsRect" in html
    assert "safeHazard=lineIntersectsRect" in html
    assert "local_deterministic" in html
    assert "application_verified" in html
    assert "model_generated" in html


def test_gt18_page_exposes_three_candidate_actions() -> None:
    html = GT18_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-shortest"' in html
    assert 'id="btn-abort"' in html
    assert 'id="btn-safe"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "enter_via_shortest_route" in html
    assert "abort_rescue_mission" in html
    assert "enter_via_safe_route" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt18_page_is_static_and_secret_free() -> None:
    html = GT18_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt17_readme_deploy_and_sitemap_include_gt18() -> None:
    gt17_html = GT17_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt18/"' in gt17_html
    assert "GT18" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt18/" in readme
    assert "https://stpku.github.io/GeoTask/gt18/" in sitemap
