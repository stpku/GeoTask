"""Case catalog conformance tests.

Cross-case metadata is generated from ``cases/catalog.yaml``. These tests keep
portal, sitemap, deployment inputs, navigation metadata, and public export in
sync without adding one assertion block per new case.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "cases" / "catalog.yaml"
PORTAL = ROOT / "site" / "index.html"
SITEMAP = ROOT / "site" / "sitemap.xml"
CASE_SLUGS = ROOT / "site" / "cases.txt"
CASE_NAVIGATION = ROOT / "site" / "cases.json"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
PUBLIC_MANIFEST = ROOT / ".release" / "public-manifest.yaml"
GENERATOR = ROOT / "tools" / "generate_case_catalog.py"
SHARED_STYLE = ROOT / "site" / "assets" / "case-shared.css"
SHARED_NAVIGATION = ROOT / "site" / "assets" / "case-navigation.js"
STYLE_TAG = '<link rel="stylesheet" href="../assets/case-shared.css" data-geotask-case-shared>'
SCRIPT_TAG = '<script src="../assets/case-navigation.js" defer data-geotask-case-shared></script>'


def _catalog() -> dict:
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


def _generator_module():
    spec = importlib.util.spec_from_file_location("case_catalog_generator", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_has_contiguous_case_ids_and_existing_assets() -> None:
    data = _catalog()
    cases = data["cases"]
    stage_ids = {stage["id"] for stage in data["stages"]}

    assert [case["id"] for case in cases] == [
        f"GT{number:02d}" for number in range(1, len(cases) + 1)
    ]
    assert [case["slug"] for case in cases] == [
        f"gt{number:02d}" for number in range(1, len(cases) + 1)
    ]
    assert len({case["slug"] for case in cases}) == len(cases)

    for case in cases:
        assert case["stage"] in stage_ids
        assert case["title_zh"].strip()
        assert case["summary_zh"].strip()
        assert (ROOT / case["page"]).is_file(), case["page"]
        assert (ROOT / case["example"]).is_file(), case["example"]


def test_world_state_cycle_titles_are_scenario_first() -> None:
    module = _generator_module()
    data = _catalog()
    forbidden = tuple(
        term.casefold() for term in module.SCENARIO_FIRST_FORBIDDEN_TITLE_TERMS
    )

    for case in data["cases"]:
        if int(case["id"][2:]) < module.SCENARIO_FIRST_CASE_NUMBER:
            continue
        title = case["title_zh"].casefold()
        assert not any(term in title for term in forbidden), case["id"]

    invalid = copy.deepcopy(data)
    invalid["cases"][20]["title_zh"] = "用World State revision处理Observation冲突"
    with pytest.raises(module.CatalogError, match="scenario-first title"):
        module.validate_catalog(invalid)


def test_generated_case_outputs_are_current() -> None:
    completed = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_portal_cards_are_generated_from_catalog() -> None:
    cases = _catalog()["cases"]
    html = PORTAL.read_text(encoding="utf-8")

    assert "<!-- CASE_CATALOG:START -->" in html
    assert "<!-- CASE_CATALOG:END -->" in html
    assert html.count('<a class="case" href="') == len(cases)
    for case in cases:
        assert f'href="{case["slug"]}/"' in html
        assert f'<span class="case-id">{case["id"]}</span>' in html
        assert case["title_zh"] in html
        assert case["summary_zh"] in html


def test_sitemap_and_deployment_slug_list_match_catalog() -> None:
    data = _catalog()
    cases = data["cases"]
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ElementTree.parse(SITEMAP).getroot()
    urls = [item.text for item in root.findall("sm:url/sm:loc", namespace)]
    expected_urls = [data["base_url"], f'{data["base_url"]}en/'] + [
        f'{data["base_url"]}{case["slug"]}/' for case in cases
    ]

    assert urls == expected_urls
    assert CASE_SLUGS.read_text(encoding="utf-8").splitlines() == [
        case["slug"] for case in cases
    ]


def test_navigation_index_has_contiguous_previous_and_next_links() -> None:
    cases = _catalog()["cases"]
    navigation = json.loads(CASE_NAVIGATION.read_text(encoding="utf-8"))
    entries = navigation["cases"]

    assert navigation["case_count"] == len(cases)
    assert [entry["slug"] for entry in entries] == [case["slug"] for case in cases]
    for index, entry in enumerate(entries):
        expected_previous = cases[index - 1]["slug"] if index > 0 else None
        expected_next = cases[index + 1]["slug"] if index + 1 < len(cases) else None
        assert entry["previous"] == expected_previous
        assert entry["next"] == expected_next


def test_case_pages_load_only_the_shared_local_assets() -> None:
    cases = _catalog()["cases"]

    for case in cases:
        html = (ROOT / case["page"]).read_text(encoding="utf-8")
        script_sources = re.findall(r'<script[^>]+src="([^"]+)"', html)
        stylesheet_sources = re.findall(
            r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html
        )

        assert html.count(STYLE_TAG) == 1, case["id"]
        assert html.count(SCRIPT_TAG) == 1, case["id"]
        assert script_sources == ["../assets/case-navigation.js"], case["id"]
        assert stylesheet_sources == ["../assets/case-shared.css"], case["id"]


def test_shared_navigation_reads_only_the_same_origin_case_index() -> None:
    script = SHARED_NAVIGATION.read_text(encoding="utf-8")
    stylesheet = SHARED_STYLE.read_text(encoding="utf-8")

    assert 'new URL("../", script.src)' in script
    assert 'new URL("cases.json", siteRoot)' in script
    assert 'fetch(catalogUrl, { credentials: "same-origin" })' in script
    assert "XMLHttpRequest" not in script
    assert "localStorage" not in script
    assert "document.cookie" not in script
    assert "http://" not in script
    assert "https://" not in script
    assert "url(" not in stylesheet.lower()


def test_deployment_and_public_export_consume_generated_catalog_outputs() -> None:
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    manifest = yaml.safe_load(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    included = set(manifest["include"])
    required = set(manifest["required"])

    assert 'CASE_LIST="$SOURCE/cases.txt"' in script
    assert 'mapfile -t CASE_SLUGS' in script
    assert 'require_file "$SOURCE/$slug/index.html"' in script
    assert 'require_file "$TARGET/$slug/index.html"' in script

    for path in (
        "cases/catalog.yaml",
        "tools/generate_case_catalog.py",
        "tools/scaffold_case.py",
        "tests/test_case_catalog.py",
        "tests/test_case_scaffold.py",
    ):
        assert path in included
        assert path in required
    for path in (
        "site/cases.txt",
        "site/cases.json",
        "site/assets/case-shared.css",
        "site/assets/case-navigation.js",
    ):
        assert path in required
