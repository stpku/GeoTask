from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT14_PAGE = ROOT / "site" / "gt14" / "index.html"
GT15_PAGE = ROOT / "site" / "gt15" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt15_page_contains_live_obstacle_task() -> None:
    html = GT15_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt15-robot-live-obstacle-stop"',
        'scenario: "inspection_robot_static_map_live_obstacle"',
        'corridor_passable: true',
        'scope: "structural_passability"',
        'proves_current_occupancy: false',
        'status: "current"',
        'obstacle_type: "temporary_pallet"',
        'confidence: 0.97',
        'planned_route_intersects_obstacle: true',
        'current_passability: false',
        'safe_stop_clearance_m: 4.0',
        'minimum_stop_clearance_m: 3.0',
        'selected_action: "stop_and_replan_route"',
        'expected_status: "verified_stop"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt15_page_visualizes_map_and_live_state() -> None:
    html = GT15_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "巡检机器人" in html
    assert "静态地图" in html
    assert "临时托盘" in html
    assert "live obstacle" in html
    assert "current_passability = false" in html
    assert "净距 4.0 米 ≥ 3.0 米" in html


def test_gt15_page_calculates_intersection_and_clearance_locally() -> None:
    html = GT15_PAGE.read_text(encoding="utf-8")

    assert "function distance2d" in html
    assert "function pointInRect" in html
    assert "function lineIntersectsRect" in html
    assert "function evaluateCandidate" in html
    assert "routeIntersectsLiveObstacle" in html
    assert "stopClearanceM" in html
    assert "stopPointIsSafe" in html
    assert "livePerceptionStatus" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt15_page_exposes_three_candidate_actions() -> None:
    html = GT15_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-map"' in html
    assert 'id="btn-ignore"' in html
    assert 'id="btn-stop"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt15_page_is_static_and_secret_free() -> None:
    html = GT15_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt14_readme_deploy_and_sitemap_include_gt15() -> None:
    gt14_html = GT14_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt15/"' in gt14_html
    assert "GT15" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt15/" in readme
    assert '"$SOURCE/gt15/index.html"' in script
    assert 'test -f "$TARGET/gt15/index.html"' in script
    assert "https://stpku.github.io/GeoTask/gt15/" in sitemap
