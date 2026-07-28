from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT18_PAGE = ROOT / "site" / "gt18" / "index.html"
GT19_PAGE = ROOT / "site" / "gt19" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt19_page_contains_arrival_and_release_gate_task() -> None:
    html = GT19_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt19-uav-arrival-ground-clearance-release"',
        "projection_inside_drop_zone: true",
        "release_altitude_authorized: true",
        "release_time_authorized: true",
        "target_overhead_reached: true",
        "planned_impact_point_clearance_m: 10",
        "minimum_release_clearance_m: 30",
        "ground_zone_clear: false",
        "freshness_limit_seconds: 15",
        "release_system_ready: true",
        "immediate_release_authorized: false",
        'selected_action: "hold_position_and_request_ground_clearance"',
        'expected_status: "verified_release_hold"',
    )
    for fragment in required:
        assert fragment in html


def test_gt19_page_visualizes_arrival_and_occupied_drop_zone() -> None:
    html = GT19_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "无人机已到达目标上空" in html
    assert "距落点10米" in html
    assert "最低净空30米" in html
    assert "immediate_release_authorized = false" in html


def test_gt19_page_recomputes_core_conditions_locally() -> None:
    html = GT19_PAGE.read_text(encoding="utf-8")

    assert "function rectContainsPoint" in html
    assert "function overlap" in html
    assert "function distance" in html
    assert "projectionInside=rectContainsPoint" in html
    assert "altitudeAuthorized=overlap" in html
    assert "timeAuthorized=overlap" in html
    assert "clearance=distance" in html
    assert "local_deterministic" in html
    assert "application_verified" in html
    assert "model_generated" in html


def test_gt19_page_exposes_three_candidate_actions() -> None:
    html = GT19_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-release"' in html
    assert 'id="btn-abort"' in html
    assert 'id="btn-hold"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "release_cargo_because_over_target" in html
    assert "abort_delivery_mission" in html
    assert "hold_position_and_request_ground_clearance" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt19_page_is_static_and_secret_free() -> None:
    html = GT19_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt18_readme_deploy_and_sitemap_include_gt19() -> None:
    gt18_html = GT18_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt19/"' in gt18_html
    assert "GT19" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt19/" in readme
    assert "https://stpku.github.io/GeoTask/gt19/" in sitemap
