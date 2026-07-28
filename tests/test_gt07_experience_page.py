from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT06_PAGE = ROOT / "site" / "gt06" / "index.html"
GT07_PAGE = ROOT / "site" / "gt07" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt07_page_contains_unverifiable_task_and_three_valued_rule() -> None:
    html = GT07_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt07-unverifiable-constraint"',
        'condition: "restricted_schedule_verified"',
        'id: "route_intersects_zone"',
        'id: "altitude_conflict"',
        'id: "temporal_conflict"',
        'logic: "three_valued_and"',
        'unknown_policy: "propagate"',
        'full_conflict_status = unverifiable',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt07_page_visualizes_true_true_unknown() -> None:
    html = GT07_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "路线相交" in html
    assert "高度重叠" in html
    assert "时间条件" in html
    assert "true ∧ true ∧ unknown" in html
    assert "不可验证" in html


def test_gt07_page_runs_local_checks_and_propagates_unknown() -> None:
    html = GT07_PAGE.read_text(encoding="utf-8")

    assert "function lineIntersectsRect" in html
    assert "function altitudeOverlap" in html
    assert "function evaluateEvidenceCondition" in html
    assert "function threeValuedAnd" in html
    assert 'return "unverifiable"' in html
    assert "const localDecision = threeValuedAnd" in html
    assert "unverifiable_condition" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "model_generated" in html
    assert "local_deterministic" in html


def test_gt07_page_exposes_three_candidate_choices() -> None:
    html = GT07_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-true"' in html
    assert 'id="btn-false"' in html
    assert 'id="btn-unverifiable"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt07_page_is_static_and_secret_free() -> None:
    html = GT07_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt06_readme_and_deploy_script_include_gt07() -> None:
    gt06_html = GT06_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt07/"' in gt06_html
    assert "GT07" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt07/" in readme
