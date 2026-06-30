"""Tests for GeoTask Encoding Benchmark v0.1."""

import csv
import json
import math
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.encoding_v0_1.token_counter import estimate_tokens


# ── Paths ────────────────────────────────────────────────────────────

BENCHMARK_DIR = REPO_ROOT / "benchmarks" / "encoding_v0_1"
CASES_FILE = BENCHMARK_DIR / "cases.yaml"
INPUTS_DIR = BENCHMARK_DIR / "inputs"
OUTPUTS_DIR = BENCHMARK_DIR / "simulated_model_outputs"
RESULTS_DIR = BENCHMARK_DIR / "outputs"

ENCODING_TYPES = ["natural_language", "geotask_yaml", "compact_dsl"]

INPUT_EXTENSIONS = {
    "natural_language": ".txt",
    "geotask_yaml": ".yaml",
    "compact_dsl": ".gt",
}


# ── Token Counter Tests ──────────────────────────────────────────────

def test_estimate_tokens_positive():
    """estimate_tokens returns positive integer."""
    result = estimate_tokens("Hello world")
    assert isinstance(result, int)
    assert result > 0


def test_estimate_tokens_empty():
    """Empty string returns 1."""
    assert estimate_tokens("") == 1


def test_estimate_tokens_english():
    """English text estimate scales with length."""
    short = estimate_tokens("hello world")
    long = estimate_tokens("hello world " * 10)
    assert long > short


def test_estimate_tokens_chinese():
    """Chinese characters contribute to token count."""
    result = estimate_tokens("起飞点到学校的距离为 144.22 米")
    assert result > 5  # at least a few tokens


def test_estimate_tokens_numbers():
    """Numbers are counted as tokens."""
    result = estimate_tokens("120 80 144.22")
    assert result >= 3


# ── Cases YAML Tests ─────────────────────────────────────────────────

def test_cases_yaml_readable():
    """cases.yaml can be loaded."""
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "cases" in data
    assert len(data["cases"]) == 4


def test_cases_have_required_fields():
    """Each case has case_id, description, expected."""
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for case in data["cases"]:
        assert "case_id" in case
        assert "description" in case
        assert "expected" in case


# ── Input Files Tests ────────────────────────────────────────────────

@pytest.mark.parametrize("case_id", [
    "case_001_distance_intersection",
    "case_002_wrong_distance",
    "case_003_not_intersect",
    "case_004_missing_operator",
])
@pytest.mark.parametrize("encoding", ENCODING_TYPES)
def test_input_files_exist(case_id, encoding):
    """Each case × encoding input file exists."""
    ext = INPUT_EXTENSIONS[encoding]
    filepath = INPUTS_DIR / encoding / f"{case_id}{ext}"
    assert filepath.exists(), f"Missing input file: {filepath}"


# ── Simulated Output Tests ───────────────────────────────────────────

@pytest.mark.parametrize("case_id", [
    "case_001_distance_intersection",
    "case_002_wrong_distance",
    "case_003_not_intersect",
    "case_004_missing_operator",
])
@pytest.mark.parametrize("encoding", ENCODING_TYPES)
def test_simulated_outputs_exist(case_id, encoding):
    """Each case × encoding simulated output exists."""
    filepath = OUTPUTS_DIR / encoding / f"{case_id}_output.md"
    assert filepath.exists(), f"Missing output file: {filepath}"


# ── Benchmark Runner Tests ───────────────────────────────────────────

def test_run_benchmark_generates_csv():
    """run_benchmark.py generates CSV file."""
    csv_path = RESULTS_DIR / "encoding_benchmark_v0_1_results.csv"
    assert csv_path.exists(), (
        f"CSV not found at {csv_path}. Run: python benchmarks/encoding_v0_1/run_benchmark.py"
    )


def test_run_benchmark_generates_json():
    """run_benchmark.py generates JSON file."""
    json_path = RESULTS_DIR / "encoding_benchmark_v0_1_results.json"
    assert json_path.exists(), (
        f"JSON not found at {json_path}. Run: python benchmarks/encoding_v0_1/run_benchmark.py"
    )


def test_run_benchmark_generates_markdown():
    """run_benchmark.py generates Markdown summary."""
    md_path = RESULTS_DIR / "encoding_benchmark_v0_1_summary.md"
    assert md_path.exists(), (
        f"Summary not found at {md_path}. Run: python benchmarks/encoding_v0_1/run_benchmark.py"
    )


# ── Results Validation Tests ─────────────────────────────────────────

@pytest.fixture(scope="module")
def benchmark_rows():
    """Load benchmark CSV results."""
    csv_path = RESULTS_DIR / "encoding_benchmark_v0_1_results.csv"
    if not csv_path.exists():
        pytest.skip("Benchmark CSV not found. Run benchmark first.")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_results_have_12_rows(benchmark_rows):
    """12 total results (4 cases × 3 encodings)."""
    assert len(benchmark_rows) == 12, f"Expected 12 rows, got {len(benchmark_rows)}"


def test_compact_dsl_less_tokens_than_nl(benchmark_rows):
    """Compact DSL average tokens < Natural Language average tokens."""
    nl_tokens = [
        int(r["total_token_estimate"])
        for r in benchmark_rows
        if r["encoding_type"] == "natural_language"
    ]
    dsl_tokens = [
        int(r["total_token_estimate"])
        for r in benchmark_rows
        if r["encoding_type"] == "compact_dsl"
    ]
    nl_avg = sum(nl_tokens) / len(nl_tokens) if nl_tokens else 0
    dsl_avg = sum(dsl_tokens) / len(dsl_tokens) if dsl_tokens else 0
    assert dsl_avg < nl_avg, (
        f"Compact DSL avg tokens ({dsl_avg:.0f}) should be less than "
        f"Natural Language avg tokens ({nl_avg:.0f})"
    )


def test_wrong_distance_contradicted(benchmark_rows):
    """case_002 has at least one contradicted measurement."""
    case_002 = [r for r in benchmark_rows if r["case_id"] == "case_002_wrong_distance"]
    for r in case_002:
        assert int(r["contradicted_count"]) >= 1, (
            f"case_002 [{r['encoding_type']}] should have contradicted count >= 1, "
            f"got {r['contradicted_count']}"
        )


def test_missing_operator_has_review_reason(benchmark_rows):
    """case_004 has operator_reference_missing in review reasons."""
    case_004 = [r for r in benchmark_rows if r["case_id"] == "case_004_missing_operator"]
    found = False
    for r in case_004:
        reasons = r.get("review_reasons", "")
        if "operator_reference_missing" in reasons:
            found = True
            break
    assert found, "case_004 should have operator_reference_missing in review_reasons"


def test_benchmark_scores_in_range(benchmark_rows):
    """All benchmark scores are between 0 and 100."""
    for r in benchmark_rows:
        score = float(r["benchmark_score"])
        assert 0.0 <= score <= 100.0, f"Score {score} out of range for {r['case_id']} [{r['encoding_type']}]"
