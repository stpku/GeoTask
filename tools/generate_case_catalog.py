#!/usr/bin/env python3
"""Generate GeoTask public case indexes from ``cases/catalog.yaml``.

The catalog is the single source of truth for cross-case metadata. This tool
updates the portal case section, sitemap, deployment slug list, and a compact
JSON navigation index. Individual case pages remain hand-authored experiences.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "cases" / "catalog.yaml"
PORTAL_PATH = ROOT / "site" / "index.html"
SITEMAP_PATH = ROOT / "site" / "sitemap.xml"
SLUGS_PATH = ROOT / "site" / "cases.txt"
NAVIGATION_PATH = ROOT / "site" / "cases.json"
START_MARKER = "<!-- CASE_CATALOG:START -->"
END_MARKER = "<!-- CASE_CATALOG:END -->"
CASE_STYLE_TAG = (
    '  <link rel="stylesheet" href="../assets/case-shared.css" '
    'data-geotask-case-shared>'
)
CASE_SCRIPT_TAG = (
    '  <script src="../assets/case-navigation.js" defer '
    'data-geotask-case-shared></script>'
)
SCENARIO_FIRST_CASE_NUMBER = 21
SCENARIO_FIRST_FORBIDDEN_TITLE_TERMS = (
    "Observation",
    "World State",
    "State Transition",
    "Impact Graph",
    "Correction Request",
    "Incremental Reevaluation",
    "Artifact",
    "revision",
    "semantic fingerprint",
    "materialization",
    "制品",
    "语义指纹",
    "物化",
)


class CatalogError(ValueError):
    """Raised when the case catalog is internally inconsistent."""


def load_catalog() -> dict[str, Any]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CatalogError("catalog root must be a mapping")
    validate_catalog(data)
    return data


def validate_catalog(data: dict[str, Any]) -> None:
    stages = data.get("stages")
    cases = data.get("cases")
    if not isinstance(stages, list) or not stages:
        raise CatalogError("stages must be a non-empty list")
    if not isinstance(cases, list) or not cases:
        raise CatalogError("cases must be a non-empty list")

    handbook = data.get("handbook")
    if handbook is not None:
        if not isinstance(handbook, dict):
            raise CatalogError("handbook must be a mapping")
        for field in ("path", "label_zh"):
            if not isinstance(handbook.get(field), str) or not handbook[field].strip():
                raise CatalogError(f"handbook requires non-empty {field}")
        if not (ROOT / handbook["path"]).is_file():
            raise CatalogError(f"missing handbook file {handbook['path']}")

    stage_ids = [stage.get("id") for stage in stages]
    if len(stage_ids) != len(set(stage_ids)):
        raise CatalogError("stage ids must be unique")
    if any(not isinstance(stage_id, str) or not stage_id for stage_id in stage_ids):
        raise CatalogError("every stage needs a non-empty id")

    expected_ids = [f"GT{index:02d}" for index in range(1, len(cases) + 1)]
    actual_ids = [case.get("id") for case in cases]
    if actual_ids != expected_ids:
        raise CatalogError(
            f"case ids must be contiguous and ordered: expected {expected_ids}, got {actual_ids}"
        )

    slugs: set[str] = set()
    for case in cases:
        case_id = case["id"]
        slug = case.get("slug")
        expected_slug = case_id.lower()
        if slug != expected_slug or not re.fullmatch(r"gt\d{2}", str(slug)):
            raise CatalogError(f"{case_id}: slug must be {expected_slug}")
        if slug in slugs:
            raise CatalogError(f"duplicate case slug: {slug}")
        slugs.add(slug)
        if case.get("stage") not in stage_ids:
            raise CatalogError(f"{case_id}: unknown stage {case.get('stage')!r}")
        for field in ("title_zh", "summary_zh", "page", "lastmod"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise CatalogError(f"{case_id}: missing non-empty {field}")
        if int(case_id[2:]) >= SCENARIO_FIRST_CASE_NUMBER:
            normalized_title = case["title_zh"].casefold()
            forbidden = [
                term
                for term in SCENARIO_FIRST_FORBIDDEN_TITLE_TERMS
                if term.casefold() in normalized_title
            ]
            if forbidden:
                raise CatalogError(
                    f"{case_id}: scenario-first title must describe the real task; "
                    f"move technical terms to the explanation: {', '.join(forbidden)}"
                )
        for path_field in ("page", "example"):
            value = case.get(path_field)
            if value and not (ROOT / value).is_file():
                raise CatalogError(f"{case_id}: missing {path_field} file {value}")


def render_case_section(data: dict[str, Any]) -> str:
    cases = data["cases"]
    latest_id = cases[-1]["id"]
    handbook = data.get("handbook") or {
        "path": f"docs/cookbook/gt01-{latest_id.lower()}.zh-CN.md",
        "label_zh": "查看中文案例手册 →",
    }
    lines = [
        START_MARKER,
        '    <section class="block" id="cases">',
        '      <div class="shell">',
        '        <div class="section-head">',
        f'          <div><h2>GT01—{latest_id}渐进式案例</h2><p>从一个5米距离开始，逐步进入三值逻辑、证据冲突、对象可行性、高风险动作门控，以及多源运行数据冲突、统一快照和状态变化。</p></div>',
        f'          <a class="text-link" href="https://github.com/stpku/GeoTask/blob/main/{html.escape(handbook["path"])}">{html.escape(handbook["label_zh"])}</a>',
        '        </div>',
    ]
    for stage in data["stages"]:
        stage_cases = [case for case in cases if case["stage"] == stage["id"]]
        if not stage_cases:
            continue
        lines.extend(
            [
                '        <div class="stage">',
                f'          <h3 class="stage-heading"><span class="stage-num">{stage["number"]}</span>{html.escape(stage["title_zh"])}</h3>',
                '          <div class="case-grid">',
            ]
        )
        for case in stage_cases:
            lines.append(
                f'            <a class="case" href="{case["slug"]}/"><span class="case-id">{case["id"]}</span><h3>{html.escape(case["title_zh"])}</h3><p>{html.escape(case["summary_zh"])}</p><span class="go">进入体验 →</span></a>'
            )
        lines.extend(['          </div>', '        </div>'])
    lines.extend(['      </div>', '    </section>', END_MARKER])
    return "\n".join(lines)


def render_portal(data: dict[str, Any], current: str) -> str:
    section = render_case_section(data)
    if START_MARKER in current and END_MARKER in current:
        pattern = re.compile(
            re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
        )
    else:
        pattern = re.compile(
            r'<section class="block" id="cases">.*?</section>', re.DOTALL
        )
    updated, count = pattern.subn(section, current, count=1)
    if count != 1:
        raise CatalogError("could not locate exactly one portal case section")

    case_count = len(data["cases"])
    latest_id = data["cases"][-1]["id"]
    updated = re.sub(
        r"<strong>\d+</strong><span>公开应用案例</span>",
        f"<strong>{case_count}</strong><span>公开应用案例</span>",
        updated,
        count=1,
    )
    updated = re.sub(r"GT01[—–-]GT\d{2}", f"GT01—{latest_id}", updated)
    return updated


def render_sitemap(data: dict[str, Any]) -> str:
    base_url = str(data["base_url"]).rstrip("/") + "/"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{base_url}</loc><lastmod>{data["portal_lastmod"]}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>',
    ]
    for case in data["cases"]:
        lines.append(
            f'  <url><loc>{base_url}{case["slug"]}/</loc><lastmod>{case["lastmod"]}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_slugs(data: dict[str, Any]) -> str:
    return "\n".join(case["slug"] for case in data["cases"]) + "\n"


def render_navigation(data: dict[str, Any]) -> str:
    cases = data["cases"]
    entries = []
    for index, case in enumerate(cases):
        entries.append(
            {
                "id": case["id"],
                "slug": case["slug"],
                "title_zh": case["title_zh"],
                "previous": cases[index - 1]["slug"] if index > 0 else None,
                "next": cases[index + 1]["slug"] if index + 1 < len(cases) else None,
            }
        )
    payload = {
        "catalog_version": data["catalog_version"],
        "case_count": len(cases),
        "cases": entries,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_case_page(current: str) -> str:
    """Ensure one case page loads the shared navigation assets."""
    updated = current
    if CASE_STYLE_TAG not in updated:
        if "</head>" not in updated:
            raise CatalogError("case page is missing </head>")
        updated = updated.replace("</head>", f"{CASE_STYLE_TAG}\n</head>", 1)
    if CASE_SCRIPT_TAG not in updated:
        if "</body>" not in updated:
            raise CatalogError("case page is missing </body>")
        updated = updated.replace("</body>", f"{CASE_SCRIPT_TAG}\n</body>", 1)
    return updated


def generated_outputs(data: dict[str, Any]) -> dict[Path, str]:
    outputs = {
        PORTAL_PATH: render_portal(data, PORTAL_PATH.read_text(encoding="utf-8")),
        SITEMAP_PATH: render_sitemap(data),
        SLUGS_PATH: render_slugs(data),
        NAVIGATION_PATH: render_navigation(data),
    }
    for case in data["cases"]:
        page_path = ROOT / case["page"]
        outputs[page_path] = render_case_page(page_path.read_text(encoding="utf-8"))
    return outputs


def write_outputs(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"generated {path.relative_to(ROOT).as_posix()}")


def check_outputs(outputs: dict[Path, str]) -> int:
    stale = []
    for path, expected in outputs.items():
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        if actual != expected:
            stale.append(path.relative_to(ROOT).as_posix())
    if stale:
        print("stale generated files:", file=sys.stderr)
        for path in stale:
            print(f"  - {path}", file=sys.stderr)
        print("run: python tools/generate_case_catalog.py --write", file=sys.stderr)
        return 1
    print(f"case catalog outputs are current ({len(outputs)} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="update generated files")
    mode.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()

    data = load_catalog()
    outputs = generated_outputs(data)
    if args.write:
        write_outputs(outputs)
        return 0
    return check_outputs(outputs)


if __name__ == "__main__":
    raise SystemExit(main())
