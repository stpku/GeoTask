from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT15_PAGE = ROOT / "site" / "gt15" / "index.html"
GT16_PAGE = ROOT / "site" / "gt16" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt16_page_contains_crossing_separation_task() -> None:
    html = GT16_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt16-uav-route-crossing-temporal-separation"',
        "horizontal_crossing: true",
        "altitude_overlap: true",
        "temporal_overlap: false",
        'uav_a_crossing_window: "09:00-09:01"',
        'uav_b_crossing_window: "09:03-09:04"',
        "actual_separation_minutes: 2",
        "minimum_separation_minutes: 1",
        "separation_requirement_met: true",
        'selected_action: "maintain_planned_time_separation"',
        'expected_status: "verified_separation"',
    )
    for fragment in required:
        assert fragment in html


def test_gt16_page_visualizes_route_altitude_and_time_conditions() -> None:
    html = GT16_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "路线相交" in html
    assert "高度重叠" in html
    assert "时间不重叠" in html
    assert "A机：09:00—09:01" in html
    assert "B机：09:03—09:04" in html
    assert "true AND true AND false" in html


def test_gt16_page_calculates_conditions_locally() -> None:
    html = GT16_PAGE.read_text(encoding="utf-8")

    assert "function pointSegmentDistance" in html
    assert "function pointPolylineDistance" in html
    assert "function overlap" in html
    assert "routeADistance" in html
    assert "routeBDistance" in html
    assert "horizontalCrossing" in html
    assert "altitudeOverlap" in html
    assert "temporalOverlap" in html
    assert "actualSeparation" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt16_page_exposes_three_candidate_actions() -> None:
    html = GT16_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-route"' in html
    assert 'id="btn-altitude"' in html
    assert 'id="btn-separation"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt16_page_is_static_and_secret_free() -> None:
    html = GT16_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt15_readme_deploy_and_sitemap_include_gt16() -> None:
    gt15_html = GT15_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt16/"' in gt15_html
    assert "GT16" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt16/" in readme
    assert '"$SOURCE/gt16/index.html"' in script
    assert 'test -f "$TARGET/gt16/index.html"' in script
    assert "https://stpku.github.io/GeoTask/gt16/" in sitemap
