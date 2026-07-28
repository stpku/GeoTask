#!/usr/bin/env python3
"""Create the four authored inputs for the next GeoTask public case.

The command defaults to preview mode. Pass ``--write`` to create one example
YAML, one experience page, one combined case test, and one catalog entry. The
existing case catalog generator then updates portal, sitemap, deployment, and
navigation outputs.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CASE_ID_RE = re.compile(r"GT(?P<number>\d{2})$")
CASE_KEY_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")


class ScaffoldError(ValueError):
    """Raised when a scaffold request is unsafe or inconsistent."""


@dataclass(frozen=True)
class ScaffoldPlan:
    root: Path
    case_id: str
    case_number: int
    slug: str
    stage: str
    case_key: str
    title_zh: str
    summary_zh: str
    question_zh: str
    lastmod: str
    example_path: Path
    page_path: Path
    test_path: Path

    @property
    def geotask_id(self) -> str:
        return f"{self.slug}-{self.case_key}"

    @property
    def relative_example(self) -> str:
        return self.example_path.relative_to(self.root).as_posix()

    @property
    def relative_page(self) -> str:
        return self.page_path.relative_to(self.root).as_posix()

    @property
    def relative_test(self) -> str:
        return self.test_path.relative_to(self.root).as_posix()


@dataclass(frozen=True)
class RenderedScaffold:
    plan: ScaffoldPlan
    catalog_path: Path
    catalog_text: str
    example_text: str
    page_text: str
    test_text: str


def load_catalog(root: Path) -> tuple[Path, str, dict[str, Any]]:
    catalog_path = root / "cases" / "catalog.yaml"
    if not catalog_path.is_file():
        raise ScaffoldError(f"missing case catalog: {catalog_path}")
    catalog_text = catalog_path.read_text(encoding="utf-8")
    data = yaml.safe_load(catalog_text)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ScaffoldError("case catalog must contain a cases list")
    if not isinstance(data.get("stages"), list):
        raise ScaffoldError("case catalog must contain a stages list")
    return catalog_path, catalog_text, data


def next_case_id(cases: list[dict[str, Any]]) -> str:
    expected = len(cases) + 1
    actual = [case.get("id") for case in cases]
    contiguous = [f"GT{number:02d}" for number in range(1, expected)]
    if actual != contiguous:
        raise ScaffoldError(
            "existing case ids must be contiguous before scaffolding: "
            f"expected {contiguous}, got {actual}"
        )
    if expected > 99:
        raise ScaffoldError("two-digit public case ids are exhausted")
    return f"GT{expected:02d}"


def validate_lastmod(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ScaffoldError("lastmod must use YYYY-MM-DD") from exc
    return parsed.isoformat()


def build_plan(
    *,
    root: Path,
    requested_id: str | None,
    stage: str,
    case_key: str,
    title_zh: str,
    summary_zh: str,
    question_zh: str | None,
    lastmod: str,
) -> tuple[ScaffoldPlan, Path, str, dict[str, Any]]:
    root = root.resolve()
    catalog_path, catalog_text, data = load_catalog(root)
    expected_id = next_case_id(data["cases"])
    case_id = (requested_id or expected_id).upper()
    if case_id != expected_id:
        raise ScaffoldError(f"next case id must be {expected_id}, got {case_id}")
    match = CASE_ID_RE.fullmatch(case_id)
    if not match:
        raise ScaffoldError("case id must use GT followed by two digits")
    if not CASE_KEY_RE.fullmatch(case_key):
        raise ScaffoldError(
            "case-key must be lower-case kebab-case, for example uav-weather-diversion"
        )

    stage_ids = {item.get("id") for item in data["stages"] if isinstance(item, dict)}
    if stage not in stage_ids:
        raise ScaffoldError(f"unknown stage {stage!r}; choose one of {sorted(stage_ids)}")

    title_zh = title_zh.strip()
    summary_zh = summary_zh.strip()
    resolved_question = (question_zh or title_zh).strip()
    if not title_zh or not summary_zh or not resolved_question:
        raise ScaffoldError("title, summary, and question must be non-empty")
    if any("\n" in value or "\r" in value for value in (title_zh, summary_zh, resolved_question)):
        raise ScaffoldError("title, summary, and question must each fit on one line")

    case_number = int(match.group("number"))
    slug = case_id.lower()
    test_suffix = case_key.replace("-", "_")
    plan = ScaffoldPlan(
        root=root,
        case_id=case_id,
        case_number=case_number,
        slug=slug,
        stage=stage,
        case_key=case_key,
        title_zh=title_zh,
        summary_zh=summary_zh,
        question_zh=resolved_question,
        lastmod=validate_lastmod(lastmod),
        example_path=root / "examples" / "core" / f"{case_key}.yaml",
        page_path=root / "site" / slug / "index.html",
        test_path=root / "tests" / f"test_{slug}_{test_suffix}_case.py",
    )
    for path in (plan.example_path, plan.page_path, plan.test_path):
        if path.exists():
            raise ScaffoldError(f"refusing to overwrite existing path: {path}")
    return plan, catalog_path, catalog_text, data


def render_example(plan: ScaffoldPlan) -> str:
    payload = {
        "geotask": {
            "id": plan.geotask_id,
            "name": f"{plan.case_id} {plan.case_key.replace('-', ' ').title()}",
            "schema_version": "1.0",
            "goal": plan.summary_zh,
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": f"{plan.slug}_starter_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "point_a": {"type": "point", "coordinates": [0, 0]},
            "point_b": {"type": "point", "coordinates": [3, 4]},
        },
        "operator_set": ["distance_2d"],
        "tasks": [
            {
                "id": "verify_starter_distance",
                "family": "scaffold_starter",
                "goal": "Replace this starter assertion with the case-specific deterministic checks.",
                "assertions": [
                    {
                        "id": "starter_distance",
                        "operator": "distance_2d",
                        "object_refs": ["point_a", "point_b"],
                        "expected_type": "number",
                        "unit": "meter",
                    }
                ],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "run_starter_check",
                    "executor": "local",
                    "assertion_refs": ["starter_distance"],
                }
            ],
        },
        "output_contract": {"format": "structured", "required_fields": []},
        "extensions": {
            "scaffold": {
                "status": "starter",
                "generated_by": "tools/scaffold_case.py",
                "replace_before_publication": True,
            },
            "application_context": {
                "question_zh": plan.question_zh,
                "candidate_actions": [
                    "accept_model_answer_without_verification",
                    "run_local_deterministic_verification",
                ],
                "selected_action": "run_local_deterministic_verification",
            },
        },
    }
    return yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )


def render_page(plan: ScaffoldPlan, example_text: str) -> str:
    escaped_yaml = html.escape(example_text.rstrip())
    title = html.escape(plan.title_zh)
    summary = html.escape(plan.summary_zh)
    question = html.escape(plan.question_zh)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#163d52">
  <meta name="description" content="GeoTask {plan.case_id}：{summary}">
  <title>GeoTask {plan.case_id}｜{title}</title>
  <style>
    :root{{--navy:#163d52;--blue:#2779ad;--teal:#16877d;--green:#18845d;--red:#c5483f;--ink:#17252e;--muted:#64747d;--line:#d8e3e9;--soft:#f2f7f9;--shadow:0 14px 38px rgba(22,61,82,.12)}}
    *{{box-sizing:border-box}}body{{margin:0;color:var(--ink);line-height:1.65;background:linear-gradient(180deg,#edf5f8,#fff 70%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}.shell{{width:min(100%,780px);margin:auto;padding:20px 16px 46px}}.brand{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}.brand a{{color:var(--blue);text-decoration:none;font-weight:800}}.hero,.card{{border-radius:22px;box-shadow:var(--shadow)}}.hero{{padding:28px 22px;color:white;background:linear-gradient(145deg,#163d52,#1c627b)}}.hero p{{color:#dceaf0}}h1{{margin:0;font-size:clamp(28px,7vw,42px);line-height:1.2}}.card{{margin-top:16px;padding:21px 18px;border:1px solid var(--line);background:white}}.starter{{padding:12px 14px;border:1px solid #e3ba76;border-radius:14px;background:#fff7e7;color:#80520e}}button{{padding:11px 15px;border:0;border-radius:11px;font:inherit;font-weight:800;cursor:pointer}}.primary{{background:var(--blue);color:white}}.secondary{{background:var(--soft);color:var(--navy);border:1px solid var(--line)}}.actions{{display:flex;flex-wrap:wrap;gap:10px}}.result{{margin-top:14px;padding:14px;border-radius:14px;background:var(--soft)}}pre{{overflow:auto;padding:15px;border-radius:14px;background:#102733;color:#eaf5f7;font-size:12px}}details{{margin-top:12px}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}@media(max-width:560px){{.actions button{{width:100%}}}}
  </style>
  <link rel="stylesheet" href="../assets/case-shared.css" data-geotask-case-shared>
</head>
<body>
  <main class="shell">
    <div class="brand"><strong>GeoTask · {plan.case_id}</strong><a href="../#cases">返回案例目录</a></div>
    <section class="hero">
      <p>案例脚手架 · Starter</p>
      <h1>{title}</h1>
      <p>{summary}</p>
    </section>
    <section class="card">
      <div class="starter"><strong>发布前必须替换：</strong>当前页面使用3-4-5两点距离作为最小可运行模板，请改造成真实对象、约束、候选动作和确定性验证逻辑。</div>
      <h2>问题</h2>
      <p>{question}</p>
      <div class="actions">
        <button class="secondary" id="btn-accept">直接采纳模型答案</button>
        <button class="primary" id="btn-verify">执行本地确定性复算</button>
      </div>
      <div class="result" id="result" aria-live="polite">尚未选择动作。</div>
    </section>
    <section class="card">
      <h2>GeoTask Starter YAML</h2>
      <div class="actions">
        <button class="primary" id="copy-open">复制并打开DeepSeek</button>
        <button class="secondary" id="copy-only">仅复制</button>
      </div>
      <p id="copy-status" aria-live="polite"></p>
      <details><summary>展开任务</summary><pre id="task-source">{escaped_yaml}</pre></details>
    </section>
  </main>
  <script>
    (() => {{
      const byId = id => document.getElementById(id);
      const result = byId("result");
      function localDistance() {{
        const a = [0, 0];
        const b = [3, 4];
        return Math.hypot(b[0] - a[0], b[1] - a[1]);
      }}
      byId("btn-accept").addEventListener("click", () => {{
        result.textContent = "contradicted：Starter要求先执行local_deterministic验证，不能直接采纳模型答案。";
      }});
      byId("btn-verify").addEventListener("click", () => {{
        const value = localDistance();
        result.textContent = `verified：starter_distance = ${{value.toFixed(1)}} meter；evidence = local_deterministic。`;
      }});
      async function copyTask(openModel) {{
        const text = byId("task-source").textContent.trim() + "\\n";
        let copied = false;
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(text);
            copied = true;
          }}
        }} catch (_) {{}}
        if (!copied) {{
          const area = document.createElement("textarea");
          area.value = text;
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();
          copied = document.execCommand("copy");
          area.remove();
        }}
        byId("copy-status").textContent = copied ? "已复制。" : "复制失败，请展开任务手动复制。";
        if (copied && openModel) setTimeout(() => location.assign("https://chat.deepseek.com/"), 500);
      }}
      byId("copy-open").addEventListener("click", () => copyTask(true));
      byId("copy-only").addEventListener("click", () => copyTask(false));
    }})();
  </script>
  <script src="../assets/case-navigation.js" defer data-geotask-case-shared></script>
</body>
</html>
'''


def render_test(plan: ScaffoldPlan) -> str:
    return f'''from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "{plan.relative_example}"
PAGE = ROOT / "{plan.relative_page}"


def test_{plan.slug}_starter_contract_validates_and_executes() -> None:
    data = load_geotask(EXAMPLE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {{check.assertion_id: check for check in result.checks}}
    assert checks["starter_distance"].value == 5.0
    assert checks["starter_distance"].status == "verified"
    assert result.execution.status == "completed"


def test_{plan.slug}_page_contains_case_metadata_and_starter_warning() -> None:
    page = PAGE.read_text(encoding="utf-8")
    assert "{plan.case_id}" in page
    assert {plan.title_zh!r} in page
    assert {plan.summary_zh!r} in page
    assert 'id="btn-accept"' in page
    assert 'id="btn-verify"' in page
    assert "local_deterministic" in page
    assert "发布前必须替换" in page
    assert '../assets/case-shared.css' in page
    assert '../assets/case-navigation.js' in page


def test_{plan.slug}_starter_is_explicitly_marked_for_replacement() -> None:
    data = load_geotask(EXAMPLE)
    scaffold = data["extensions"]["scaffold"]
    assert scaffold == {{
        "status": "starter",
        "generated_by": "tools/scaffold_case.py",
        "replace_before_publication": True,
    }}
'''


def render_catalog(catalog_text: str, plan: ScaffoldPlan) -> str:
    entry = {
        "id": plan.case_id,
        "slug": plan.slug,
        "stage": plan.stage,
        "title_zh": plan.title_zh,
        "summary_zh": plan.summary_zh,
        "page": plan.relative_page,
        "example": plan.relative_example,
        "lastmod": plan.lastmod,
    }
    block = yaml.safe_dump(
        [entry],
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).rstrip()
    first_case = re.search(r"(?m)^(?P<indent>[ \t]*)- id:\s*GT\d{2}\s*$", catalog_text)
    if not first_case:
        raise ScaffoldError("catalog must contain at least one formatted case entry")
    case_indent = first_case.group("indent")
    updated = catalog_text.rstrip() + "\n" + textwrap.indent(block, case_indent) + "\n"
    updated, count = re.subn(
        r'^portal_lastmod:\s*["\']?\d{4}-\d{2}-\d{2}["\']?\s*$',
        f'portal_lastmod: "{plan.lastmod}"',
        updated,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ScaffoldError("catalog must contain one portal_lastmod date")
    return updated


def render_scaffold(
    *,
    root: Path,
    requested_id: str | None,
    stage: str,
    case_key: str,
    title_zh: str,
    summary_zh: str,
    question_zh: str | None,
    lastmod: str,
) -> RenderedScaffold:
    plan, catalog_path, catalog_text, _ = build_plan(
        root=root,
        requested_id=requested_id,
        stage=stage,
        case_key=case_key,
        title_zh=title_zh,
        summary_zh=summary_zh,
        question_zh=question_zh,
        lastmod=lastmod,
    )
    example_text = render_example(plan)
    return RenderedScaffold(
        plan=plan,
        catalog_path=catalog_path,
        catalog_text=render_catalog(catalog_text, plan),
        example_text=example_text,
        page_text=render_page(plan, example_text),
        test_text=render_test(plan),
    )


def print_preview(rendered: RenderedScaffold) -> None:
    plan = rendered.plan
    print(f"case: {plan.case_id} ({plan.slug})")
    print(f"stage: {plan.stage}")
    print("authored files:")
    print(f"  - modify cases/catalog.yaml")
    print(f"  - create {plan.relative_example}")
    print(f"  - create {plan.relative_page}")
    print(f"  - create {plan.relative_test}")
    print("generated outputs: portal, sitemap, cases.txt, cases.json, shared asset tags")
    print("mode: preview; add --write to create files")


def apply_scaffold(rendered: RenderedScaffold) -> None:
    plan = rendered.plan
    original_catalog = rendered.catalog_path.read_text(encoding="utf-8")
    created: list[Path] = []
    try:
        for path, content in (
            (plan.example_path, rendered.example_text),
            (plan.page_path, rendered.page_text),
            (plan.test_path, rendered.test_text),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            created.append(path)
        rendered.catalog_path.write_text(rendered.catalog_text, encoding="utf-8", newline="\n")

        generator = plan.root / "tools" / "generate_case_catalog.py"
        if not generator.is_file():
            raise ScaffoldError(f"missing case generator: {generator}")
        subprocess.run(
            [sys.executable, str(generator), "--write"],
            cwd=plan.root,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(generator), "--check"],
            cwd=plan.root,
            check=True,
        )
    except Exception:
        rendered.catalog_path.write_text(original_catalog, encoding="utf-8", newline="\n")
        for path in reversed(created):
            path.unlink(missing_ok=True)
        page_directory = plan.page_path.parent
        if page_directory.is_dir() and not any(page_directory.iterdir()):
            page_directory.rmdir()
        generator = plan.root / "tools" / "generate_case_catalog.py"
        if generator.is_file():
            subprocess.run(
                [sys.executable, str(generator), "--write"],
                cwd=plan.root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        raise

    print(f"created {plan.case_id} starter scaffold")
    print(f"  {plan.relative_example}")
    print(f"  {plan.relative_page}")
    print(f"  {plan.relative_test}")
    print("  cases/catalog.yaml")
    print("next: replace the starter objects, assertions, actions, page copy, and tests before commit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--id", dest="requested_id", help="optional next id, for example GT21")
    parser.add_argument("--stage", required=True, help="catalog stage id")
    parser.add_argument("--case-key", required=True, help="lower-case kebab-case file key")
    parser.add_argument("--title-zh", required=True, help="Chinese case title")
    parser.add_argument("--summary-zh", required=True, help="Chinese portal summary")
    parser.add_argument("--question-zh", help="Chinese decision question; defaults to title")
    parser.add_argument("--lastmod", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--write", action="store_true", help="create files and regenerate indexes")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rendered = render_scaffold(
            root=args.root,
            requested_id=args.requested_id,
            stage=args.stage,
            case_key=args.case_key,
            title_zh=args.title_zh,
            summary_zh=args.summary_zh,
            question_zh=args.question_zh,
            lastmod=args.lastmod,
        )
        if args.write:
            apply_scaffold(rendered)
        else:
            print_preview(rendered)
        return 0
    except (OSError, ScaffoldError, subprocess.CalledProcessError) as exc:
        print(f"scaffold error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
