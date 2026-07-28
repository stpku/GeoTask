from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT10_PAGE = ROOT / "site" / "gt10" / "index.html"
GT11_PAGE = ROOT / "site" / "gt11" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt11_page_contains_delivery_robot_route_task() -> None:
    html = GT11_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt11-robot-accessible-route"',
        'scenario: "delivery_robot_accessible_route"',
        'mobility: "wheeled"',
        'can_use_stairs: false',
        'can_cross_fence: false',
        'can_enter_motor_vehicle_lane: false',
        'direct_path_distance_m: 50',
        'direct_path_accessible: false',
        'segment_lengths_m: [100, 75, 50, 25, 50]',
        'total_distance_m: 300',
        'detour_ratio: 6',
        'selected_action: "follow_accessible_network"',
        'next_action: "navigate_network"',
        'expected_status: "reachable"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt11_page_visualizes_distance_accessibility_and_obstacles() -> None:
    html = GT11_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "配送机器人" in html
    assert "收货点" in html
    assert "直线距离 50 米" in html
    assert "可通行路径 300 米" in html
    assert "台阶" in html
    assert "围栏" in html
    assert "机动车道" in html
    assert "6 倍" in html


def test_gt11_page_calculates_route_distances_locally() -> None:
    html = GT11_PAGE.read_text(encoding="utf-8")

    assert "function distance2d" in html
    assert "function sumRouteDistance" in html
    assert "function edgeKey" in html
    assert "function routeUsesOnlyAllowedEdges" in html
    assert "function evaluateCandidate" in html
    assert "directDistance" in html
    assert "accessibleDistance" in html
    assert "detourRatio" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt11_page_exposes_three_candidate_routes() -> None:
    html = GT11_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-direct"' in html
    assert 'id="btn-network"' in html
    assert 'id="btn-road"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt11_page_is_static_and_secret_free() -> None:
    html = GT11_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt10_readme_and_deploy_script_include_gt11() -> None:
    gt10_html = GT10_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt11/"' in gt10_html
    assert "GT11" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt11/" in readme
