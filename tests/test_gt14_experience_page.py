from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT13_PAGE = ROOT / "site" / "gt13" / "index.html"
GT14_PAGE = ROOT / "site" / "gt14" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt14_page_contains_emergency_dispatch_task() -> None:
    html = GT14_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt14-emergency-response-fastest-arrival"',
        'scenario: "emergency_response_fastest_arrival"',
        'maximum_response_time_min: 12',
        'status: "current"',
        'straight_distance_km: 2.4',
        'route_distance_km: 7.8',
        'estimated_arrival_min: 14',
        'straight_distance_km: 5.6',
        'route_distance_km: 6.3',
        'estimated_arrival_min: 8',
        'nearest_team: "team_a"',
        'fastest_verified_team: "team_b"',
        'selected_action: "dispatch_team_b"',
        'expected_status: "verified_dispatch"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt14_page_visualizes_nearest_and_fastest_teams() -> None:
    html = GT14_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "应急救援" in html
    assert "A队" in html
    assert "B队" in html
    assert "直线 2.4 km" in html
    assert "绕行 7.8 km" in html
    assert "路线 6.3 km" in html
    assert "ETA 14分钟" in html
    assert "ETA 8分钟" in html
    assert "响应时限 12分钟" in html


def test_gt14_page_calculates_eta_locally() -> None:
    html = GT14_PAGE.read_text(encoding="utf-8")

    assert "function distance2d" in html
    assert "function calculateEta" in html
    assert "function evaluateCandidate" in html
    assert "teamAEtaMin" in html
    assert "teamBEtaMin" in html
    assert "arrivalAdvantageMin" in html
    assert "routeTimeEvidenceStatus" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt14_page_exposes_three_candidate_actions() -> None:
    html = GT14_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-nearest"' in html
    assert 'id="btn-fastest"' in html
    assert 'id="btn-refresh"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt14_page_is_static_and_secret_free() -> None:
    html = GT14_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt13_readme_deploy_and_sitemap_include_gt14() -> None:
    gt13_html = GT13_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt14/"' in gt13_html
    assert "GT14" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt14/" in readme
    assert "https://stpku.github.io/GeoTask/gt14/" in sitemap
