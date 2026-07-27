from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT01_PAGE = ROOT / "site" / "gt01" / "index.html"
GT02_PAGE = ROOT / "site" / "gt02" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt02_page_exposes_copy_and_local_verification_actions() -> None:
    html = GT02_PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="model-result"' in html
    assert 'id="verify"' in html
    assert 'id="verification-card"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'Math.hypot(120, 80)' in html


def test_gt02_page_contains_the_144_22_meter_task() -> None:
    html = GT02_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt02-independent-distance-verification"',
        'coordinates: [0, 0]',
        'coordinates: [120, 80]',
        'operator: "distance_2d"',
        'object_refs: ["takeoff", "school"]',
        'takeoff_to_school_distance',
        '144.22 meter',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt02_page_marks_matching_and_conflicting_results() -> None:
    html = GT02_PAGE.read_text(encoding="utf-8")

    assert "const tolerance = 0.01" in html
    assert 'state: "verified"' in html
    assert 'state: "contradicted"' in html
    assert "model_generated" in html
    assert "local_deterministic" in html
    assert "Math.abs(modelValue - deterministicValue)" in html


def test_gt02_page_is_static_and_does_not_call_a_backend() -> None:
    html = GT02_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt01_and_readme_link_to_gt02() -> None:
    gt01_html = GT01_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert 'href="../gt02/"' in gt01_html
    assert "GT02" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt02/" in readme


def test_nginx_deployment_syncs_the_complete_site_tree() -> None:
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert "rsync -a --delete site/ /var/www/geotask-experience/" in readme
    assert "copy `site/index.html`" not in readme
    assert "try_files $uri $uri/ /geotask/index.html;" not in readme
    assert "index index.html;" in readme
    assert "rsync -a --delete" in script
    assert 'test -f "$TARGET/gt02/index.html"' in script
