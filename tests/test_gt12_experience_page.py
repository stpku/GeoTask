from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT11_PAGE = ROOT / "site" / "gt11" / "index.html"
GT12_PAGE = ROOT / "site" / "gt12" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt12_page_contains_uav_energy_reserve_task() -> None:
    html = GT12_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt12-uav-energy-reserve"',
        'scenario: "uav_delivery_energy_reserve"',
        'remaining_range_km: 12',
        'required_reserve_km: 2',
        'direct_distance_km: 8',
        'direct_route_legal: false',
        'compliant_detour_distance_km: 11',
        'total_required_range_km: 13',
        'shortfall_km: 1',
        'safe_completion_possible: false',
        'selected_action: "request_recharge_or_replan"',
        'next_action: "recover_energy_margin"',
        'expected_status: "insufficient_margin"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt12_page_visualizes_route_and_energy_budget() -> None:
    html = GT12_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "无人机物流" in html
    assert "临时禁飞区" in html
    assert "直线 8 公里" in html
    assert "合法绕飞 11 公里" in html
    assert "剩余航程 12 公里" in html
    assert "安全余量 2 公里" in html
    assert "总需求 13 公里" in html
    assert "缺口 1 公里" in html


def test_gt12_page_calculates_route_and_margin_locally() -> None:
    html = GT12_PAGE.read_text(encoding="utf-8")

    assert "function distance2d" in html
    assert "function pointInRect" in html
    assert "function lineIntersectsRect" in html
    assert "function sumRouteDistance" in html
    assert "function calculateEnergyBudget" in html
    assert "function evaluateCandidate" in html
    assert "directDistanceKm" in html
    assert "detourDistanceKm" in html
    assert "totalRequiredRangeKm" in html
    assert "shortfallKm" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt12_page_exposes_three_candidate_actions() -> None:
    html = GT12_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-direct"' in html
    assert 'id="btn-no-reserve"' in html
    assert 'id="btn-recover"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt12_page_is_static_and_secret_free() -> None:
    html = GT12_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt11_readme_and_deploy_script_include_gt12() -> None:
    gt11_html = GT11_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt12/"' in gt11_html
    assert "GT12" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt12/" in readme
