from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT19_PAGE = ROOT / "site" / "gt19" / "index.html"
GT20_PAGE = ROOT / "site" / "gt20" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt20_page_contains_signal_downstream_and_entry_gate_task() -> None:
    html = GT20_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt20-vehicle-green-light-downstream-blockage"',
        'signal_aspect: "green"',
        "signal_permission_valid: true",
        "green_phase_matches_entry_window: true",
        "path_intersects_downstream_queue: true",
        "available_downstream_storage_m: 4.0",
        "vehicle_length_m: 4.8",
        "minimum_exit_buffer_m: 2.0",
        "required_storage_m: 6.8",
        "downstream_exit_clear: false",
        "intersection_entry_authorized: false",
        'selected_action: "wait_before_stop_line_and_recheck_downstream"',
        'expected_status: "verified_intersection_hold"',
    )
    for fragment in required:
        assert fragment in html


def test_gt20_page_visualizes_green_signal_and_queue_spillback() -> None:
    html = GT20_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "绿灯许可有效" in html
    assert "下游排队回溢" in html
    assert "仅4米" in html
    assert "需要6.8米" in html
    assert "intersection_entry_authorized = false" in html


def test_gt20_page_recomputes_core_conditions_locally() -> None:
    html = GT20_PAGE.read_text(encoding="utf-8")

    assert "function overlap" in html
    assert "function distance" in html
    assert "function pointInRect" in html
    assert "function segmentsIntersect" in html
    assert "function lineIntersectsRect" in html
    assert "greenValid=overlap" in html
    assert "pathBlocked=lineIntersectsRect" in html
    assert "available=distance" in html
    assert "local_deterministic" in html
    assert "application_verified" in html
    assert "model_generated" in html


def test_gt20_page_exposes_three_candidate_actions() -> None:
    html = GT20_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-enter"' in html
    assert 'id="btn-inside"' in html
    assert 'id="btn-wait"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "enter_intersection_because_green" in html
    assert "enter_intersection_and_wait_inside" in html
    assert "wait_before_stop_line_and_recheck_downstream" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt20_page_is_static_and_secret_free() -> None:
    html = GT20_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt19_readme_deploy_and_sitemap_include_gt20() -> None:
    gt19_html = GT19_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt20/"' in gt19_html
    assert "GT20" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt20/" in readme
    assert '"$SOURCE/gt20/index.html"' in script
    assert 'test -f "$TARGET/gt20/index.html"' in script
    assert "https://stpku.github.io/GeoTask/gt20/" in sitemap
