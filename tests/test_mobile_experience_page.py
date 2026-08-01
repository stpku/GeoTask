from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "gt01" / "index.html"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
MANIFEST = ROOT / ".release" / "public-manifest.yaml"


def test_mobile_experience_page_has_copy_and_deepseek_actions() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="task-source"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert "document.execCommand(\"copy\")" in html


def test_mobile_experience_page_contains_gt01_task() -> None:
    html = PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "minimal-distance-v1"',
        'operator: "distance_2d"',
        'object_refs: ["point_a", "point_b"]',
        'required_fields:',
        '- "ab_distance"',
        "ab_distance = 5.0 meter",
    )
    for fragment in required_fragments:
        assert fragment in html


def test_mobile_experience_page_is_static_and_secret_free() -> None:
    html = PAGE.read_text(encoding="utf-8").lower()

    assert '<script src="../assets/case-navigation.js"' in html
    assert '<script src="http' not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_pages_workflow_validates_catalog_before_deploying_site() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    assert workflow["permissions"]["pages"] == "write"
    assert '"cases/catalog.yaml"' in text
    assert '"tools/generate_case_catalog.py"' in text

    steps = workflow["jobs"]["deploy"]["steps"]
    assert any(step.get("uses") == "actions/setup-python@v6" for step in steps)
    assert any(
        step.get("run") == "python tools/generate_case_catalog.py --check"
        for step in steps
    )
    upload_step = next(
        step for step in steps if step.get("uses") == "actions/upload-pages-artifact@v4"
    )
    assert upload_step["with"]["path"] == "site"
    assert any(step.get("uses") == "actions/deploy-pages@v5" for step in steps)


def test_public_manifest_exports_page_and_workflow() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    assert "site/**" in manifest["include"]
    assert "site/**" not in manifest.get("exclude", [])
    assert ".github/workflows/pages.yml" in manifest["include"]
