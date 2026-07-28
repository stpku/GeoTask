"""Regression tests for the public case scaffold command."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "tools" / "scaffold_case.py"
GENERATOR = ROOT / "tools" / "generate_case_catalog.py"


def _create_minimal_repository(tmp_path: Path, *, include_generator: bool = True) -> Path:
    repo = tmp_path / "repo"
    for directory in (
        repo / "cases",
        repo / "examples" / "core",
        repo / "site" / "gt01",
        repo / "site" / "assets",
        repo / "tests",
        repo / "tools",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    catalog = {
        "catalog_version": "1.0",
        "base_url": "https://example.test/GeoTask/",
        "portal_lastmod": "2026-07-27",
        "stages": [
            {
                "id": "action_feasibility",
                "number": 1,
                "title_zh": "行动与可行性",
            }
        ],
        "cases": [
            {
                "id": "GT01",
                "slug": "gt01",
                "stage": "action_feasibility",
                "title_zh": "种子案例",
                "summary_zh": "用于脚手架测试的现有案例。",
                "page": "site/gt01/index.html",
                "example": "examples/core/seed.yaml",
                "lastmod": "2026-07-27",
            }
        ],
    }
    (repo / "cases" / "catalog.yaml").write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (repo / "examples" / "core" / "seed.yaml").write_text("seed: true\n", encoding="utf-8")
    (repo / "site" / "gt01" / "index.html").write_text(
        "<html><head></head><body><footer></footer></body></html>\n",
        encoding="utf-8",
    )
    (repo / "site" / "index.html").write_text(
        '<html><body><strong>1</strong><span>公开应用案例</span>'
        '<section class="block" id="cases"></section></body></html>\n',
        encoding="utf-8",
    )
    (repo / "site" / "cases.txt").write_text("gt01\n", encoding="utf-8")
    (repo / "site" / "cases.json").write_text("{}\n", encoding="utf-8")
    (repo / "site" / "sitemap.xml").write_text("<urlset/>\n", encoding="utf-8")
    (repo / "site" / "assets" / "case-shared.css").write_text("/* shared */\n", encoding="utf-8")
    (repo / "site" / "assets" / "case-navigation.js").write_text("(() => {})();\n", encoding="utf-8")
    shutil.copy2(SCAFFOLD, repo / "tools" / "scaffold_case.py")
    if include_generator:
        shutil.copy2(GENERATOR, repo / "tools" / "generate_case_catalog.py")
    return repo


def _command(repo: Path, *, write: bool = False, case_id: str = "GT02") -> list[str]:
    command = [
        sys.executable,
        str(repo / "tools" / "scaffold_case.py"),
        "--root",
        str(repo),
        "--id",
        case_id,
        "--stage",
        "action_feasibility",
        "--case-key",
        "uav-weather-diversion",
        "--title-zh",
        "天气恶化后，无人机为什么不能继续直飞？",
        "--summary-zh",
        "用一个最小可运行模板启动新的行动可行性案例。",
        "--question-zh",
        "天气证据发生变化时，下一步动作是否仍然可执行？",
        "--lastmod",
        "2026-07-28",
    ]
    if write:
        command.append("--write")
    return command


def test_scaffold_defaults_to_preview_without_mutating_repository(tmp_path: Path) -> None:
    repo = _create_minimal_repository(tmp_path)
    catalog_path = repo / "cases" / "catalog.yaml"
    original_catalog = catalog_path.read_text(encoding="utf-8")

    completed = subprocess.run(
        _command(repo),
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "mode: preview" in completed.stdout
    assert "modify cases/catalog.yaml" in completed.stdout
    assert "create examples/core/uav-weather-diversion.yaml" in completed.stdout
    assert catalog_path.read_text(encoding="utf-8") == original_catalog
    assert not (repo / "site" / "gt02").exists()
    assert not (repo / "examples" / "core" / "uav-weather-diversion.yaml").exists()


def test_scaffold_write_creates_three_files_one_catalog_entry_and_generated_outputs(
    tmp_path: Path,
) -> None:
    repo = _create_minimal_repository(tmp_path)

    completed = subprocess.run(
        _command(repo, write=True),
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "created GT02 starter scaffold" in completed.stdout

    example = repo / "examples" / "core" / "uav-weather-diversion.yaml"
    page = repo / "site" / "gt02" / "index.html"
    test_file = repo / "tests" / "test_gt02_uav_weather_diversion_case.py"
    assert example.is_file()
    assert page.is_file()
    assert test_file.is_file()

    catalog = yaml.safe_load((repo / "cases" / "catalog.yaml").read_text(encoding="utf-8"))
    assert catalog["portal_lastmod"] == "2026-07-28"
    assert [case["id"] for case in catalog["cases"]] == ["GT01", "GT02"]
    assert catalog["cases"][-1]["example"] == "examples/core/uav-weather-diversion.yaml"

    data = load_geotask(example)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []
    result = execute_canonical(canonicalize(data))
    assert result.checks[0].assertion_id == "starter_distance"
    assert result.checks[0].value == 5.0
    assert result.checks[0].status == "verified"

    page_text = page.read_text(encoding="utf-8")
    assert page_text.count('../assets/case-shared.css') == 1
    assert page_text.count('../assets/case-navigation.js') == 1
    assert "发布前必须替换" in page_text
    compile(test_file.read_text(encoding="utf-8"), str(test_file), "exec")

    assert (repo / "site" / "cases.txt").read_text(encoding="utf-8").splitlines() == [
        "gt01",
        "gt02",
    ]
    navigation = json.loads((repo / "site" / "cases.json").read_text(encoding="utf-8"))
    assert navigation["case_count"] == 2
    assert navigation["cases"][-1]["previous"] == "gt01"
    assert navigation["cases"][-1]["next"] is None
    assert "GT02" in (repo / "site" / "index.html").read_text(encoding="utf-8")

    checked = subprocess.run(
        [sys.executable, str(repo / "tools" / "generate_case_catalog.py"), "--check"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr or checked.stdout


def test_scaffold_rejects_non_contiguous_case_id_without_writing(tmp_path: Path) -> None:
    repo = _create_minimal_repository(tmp_path)
    catalog_path = repo / "cases" / "catalog.yaml"
    original_catalog = catalog_path.read_text(encoding="utf-8")

    completed = subprocess.run(
        _command(repo, write=True, case_id="GT03"),
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "next case id must be GT02" in completed.stderr
    assert catalog_path.read_text(encoding="utf-8") == original_catalog
    assert not (repo / "site" / "gt03").exists()


def test_scaffold_rolls_back_authored_files_when_generation_fails(tmp_path: Path) -> None:
    repo = _create_minimal_repository(tmp_path, include_generator=False)
    catalog_path = repo / "cases" / "catalog.yaml"
    original_catalog = catalog_path.read_text(encoding="utf-8")

    completed = subprocess.run(
        _command(repo, write=True),
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "missing case generator" in completed.stderr
    assert catalog_path.read_text(encoding="utf-8") == original_catalog
    assert not (repo / "examples" / "core" / "uav-weather-diversion.yaml").exists()
    assert not (repo / "site" / "gt02").exists()
    assert not (repo / "tests" / "test_gt02_uav_weather_diversion_case.py").exists()
