from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT12_PAGE = ROOT / "site" / "gt12" / "index.html"
GT13_PAGE = ROOT / "site" / "gt13" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt13_page_contains_vehicle_clearance_task() -> None:
    html = GT13_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt13-vehicle-clearance-envelope"',
        'scenario: "autonomous_vehicle_roadwork_clearance"',
        'road_open: true',
        'narrowed_passage_width_m: 2.4',
        'vehicle_body_width_m: 2.1',
        'left_safety_buffer_m: 0.3',
        'right_safety_buffer_m: 0.3',
        'required_envelope_width_m: 2.7',
        'clearance_shortfall_m: 0.3',
        'object_specific_passability: false',
        'selected_action: "request_alternate_route_or_controlled_passage"',
        'next_action: "recover_clearance_margin"',
        'expected_status: "insufficient_clearance"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt13_page_visualizes_open_road_and_clearance_envelope() -> None:
    html = GT13_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "自动驾驶" in html
    assert "临时施工" in html
    assert "道路开放" in html
    assert "可用宽度 2.4 米" in html
    assert "车身宽度 2.1 米" in html
    assert "安全包络 2.7 米" in html
    assert "净缺口 0.3 米" in html


def test_gt13_page_calculates_envelope_locally() -> None:
    html = GT13_PAGE.read_text(encoding="utf-8")

    assert "function distance2d" in html
    assert "function pointInRect" in html
    assert "function lineIntersectsRect" in html
    assert "function calculateEnvelope" in html
    assert "function evaluateCandidate" in html
    assert "availableWidthM" in html
    assert "requiredEnvelopeWidthM" in html
    assert "clearanceShortfallM" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt13_page_exposes_three_candidate_actions() -> None:
    html = GT13_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-proceed"' in html
    assert 'id="btn-shrink"' in html
    assert 'id="btn-recover"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt13_page_is_static_and_secret_free() -> None:
    html = GT13_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt12_readme_and_deploy_script_include_gt13() -> None:
    gt12_html = GT12_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt13/"' in gt12_html
    assert "GT13" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt13/" in readme
