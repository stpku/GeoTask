from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT05_PAGE = ROOT / "site" / "gt05" / "index.html"
GT06_PAGE = ROOT / "site" / "gt06" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt06_page_contains_three_operator_task_and_rule() -> None:
    html = GT06_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt06-multi-constraint-conflict"',
        'operator: "line_intersects_rect"',
        'operator: "altitude_overlap"',
        'operator: "time_overlap"',
        'id: "route_intersects_zone"',
        'id: "altitude_conflict"',
        'id: "temporal_conflict"',
        'expression: "route_intersects_zone AND altitude_conflict AND temporal_conflict"',
        'full_conflict = false',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt06_page_visualizes_three_local_results_and_final_rule() -> None:
    html = GT06_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "路线相交" in html
    assert "高度重叠" in html
    assert "时间重叠" in html
    assert "true ∧ true ∧ false" in html
    assert "最终冲突" in html


def test_gt06_page_runs_all_local_operators_and_combines_results() -> None:
    html = GT06_PAGE.read_text(encoding="utf-8")

    assert "function lineIntersectsRect" in html
    assert "function altitudeOverlap" in html
    assert "function timeOverlap" in html
    assert "function combineConflict" in html
    assert "routeResult && altitudeResult && timeResult" in html
    assert "const localDeterministic = combineConflict" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "model_generated" in html
    assert "local_deterministic" in html


def test_gt06_page_exposes_copy_and_boolean_verification() -> None:
    html = GT06_PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="btn-true"' in html
    assert 'id="btn-false"' in html
    assert 'id="verify"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt06_page_is_static_and_secret_free() -> None:
    html = GT06_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt05_readme_and_deploy_script_include_gt06() -> None:
    gt05_html = GT05_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt06/"' in gt05_html
    assert "GT06" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt06/" in readme
