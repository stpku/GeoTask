from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT03_PAGE = ROOT / "site" / "gt03" / "index.html"
GT04_PAGE = ROOT / "site" / "gt04" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt04_page_contains_vertical_conflict_task() -> None:
    html = GT04_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt04-2d-overlap-3d-separation"',
        'type: "altitude_interval"',
        'min_altitude: 100',
        'max_altitude: 150',
        'min_altitude: 300',
        'max_altitude: 500',
        'operator: "altitude_overlap"',
        'object_refs: ["flight_altitude", "restricted_altitude"]',
        'altitude_conflict = false',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt04_page_visualizes_top_view_and_side_view() -> None:
    html = GT04_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "俯视图" in html
    assert "侧视图" in html
    assert "二维完全重叠" in html
    assert "100–150 米" in html or "100-150 米" in html
    assert "300–500 米" in html or "300-500 米" in html
    assert "垂直间隔 150 米" in html


def test_gt04_page_runs_local_altitude_overlap() -> None:
    html = GT04_PAGE.read_text(encoding="utf-8")

    assert "function altitudeOverlap" in html
    assert "a[0] <= b[1] && b[0] <= a[1]" in html
    assert "const localDeterministic = altitudeOverlap" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "model_generated" in html
    assert "local_deterministic" in html


def test_gt04_page_exposes_copy_and_boolean_verification() -> None:
    html = GT04_PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="btn-true"' in html
    assert 'id="btn-false"' in html
    assert 'id="verify"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt04_page_is_static_and_secret_free() -> None:
    html = GT04_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt03_readme_and_deploy_script_include_gt04() -> None:
    gt03_html = GT03_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt04/"' in gt03_html
    assert "GT04" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt04/" in readme
