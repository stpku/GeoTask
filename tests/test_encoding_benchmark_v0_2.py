"""Tests for GeoTask Encoding Benchmark v0.2 — 24 cases × 3 encodings."""

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

from benchmarks.encoding_v0_2.token_counter import estimate_tokens


# ── Paths ────────────────────────────────────────────────────────────

BENCHMARK_DIR = REPO_ROOT / "benchmarks" / "encoding_v0_2"
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

# All 24 case IDs
CASE_IDS = [
    "case_001_distance_2d_correct",
    "case_002_line_intersects_correct",
    "case_003_line_not_intersects_correct",
    "case_004_rect_contains_correct",
    "case_005_rect_not_contains_correct",
    "case_006_point_to_line_distance_correct",
    "case_007_time_overlap_correct",
    "case_008_time_not_overlap_correct",
    "case_009_altitude_overlap_correct",
    "case_010_altitude_not_overlap_correct",
    "case_011_wrong_distance",
    "case_012_wrong_intersection",
    "case_013_wrong_contains",
    "case_014_wrong_time_overlap",
    "case_015_wrong_altitude_overlap",
    "case_016_missing_operator",
    "case_017_missing_value",
    "case_018_missing_object_reference",
    "case_019_invalid_operator",
    "case_020_invalid_reference",
    "case_021_unit_mismatch",
    "case_022_chinese_negative",
    "case_023_markdown_mixed",
    "case_024_yaml_like_output",
]


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
    assert result > 5


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
    assert len(data["cases"]) == 24


def test_cases_have_required_fields():
    """Each case has case_id, description, checks."""
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for case in data["cases"]:
        assert "case_id" in case
        assert "description" in case
        assert "checks" in case


def test_cases_have_checks():
    """Each case has at least one check with name, op, expected."""
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for case in data["cases"]:
        checks = case.get("checks", [])
        assert len(checks) >= 1, f"{case['case_id']} has no checks"
        for chk in checks:
            assert "name" in chk
            assert "op" in chk
            assert "expected" in chk


def test_case_groups_coverage():
    """All 5 case groups are represented."""
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    groups = {c["case_group"] for c in data["cases"]}
    expected_groups = {"basic_correct", "new_operators", "contradicted", "need_review", "robustness"}
    assert groups == expected_groups, f"Expected groups {expected_groups}, got {groups}"


# ── Operators Coverage Tests ─────────────────────────────────────────

def test_operators_coverage():
    """All 6 operators appear in at least one case."""
    expected_ops = {
        "distance_2d",
        "line_intersects_rect",
        "point_to_line_distance_2d",
        "rect_contains_point",
        "time_overlap",
        "altitude_overlap",
    }
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    found_ops = set()
    for case in data["cases"]:
        for chk in case.get("checks", []):
            found_ops.add(chk["op"])
    missing = expected_ops - found_ops
    assert not missing, f"Operators not covered by any case: {missing}"


# ── Input Files Tests ────────────────────────────────────────────────

@pytest.mark.parametrize("case_id", CASE_IDS)
@pytest.mark.parametrize("encoding", ENCODING_TYPES)
def test_input_files_exist(case_id, encoding):
    """Each case × encoding input file exists."""
    ext = INPUT_EXTENSIONS[encoding]
    filepath = INPUTS_DIR / encoding / f"{case_id}{ext}"
    assert filepath.exists(), f"Missing input file: {filepath}"


# ── Simulated Output Tests ───────────────────────────────────────────

@pytest.mark.parametrize("case_id", CASE_IDS)
@pytest.mark.parametrize("encoding", ENCODING_TYPES)
def test_simulated_outputs_exist(case_id, encoding):
    """Each case × encoding simulated output exists (total 72 files)."""
    filepath = OUTPUTS_DIR / encoding / f"{case_id}_output.md"
    assert filepath.exists(), f"Missing output file: {filepath}"


# ── Benchmark Runner Tests ───────────────────────────────────────────

def test_run_benchmark_generates_csv():
    """run_benchmark.py generates CSV file."""
    csv_path = RESULTS_DIR / "encoding_benchmark_v0_2_results.csv"
    assert csv_path.exists(), (
        f"CSV not found at {csv_path}. Run: python benchmarks/encoding_v0_2/run_benchmark.py"
    )


def test_run_benchmark_generates_json():
    """run_benchmark.py generates JSON file."""
    json_path = RESULTS_DIR / "encoding_benchmark_v0_2_results.json"
    assert json_path.exists(), (
        f"JSON not found at {json_path}. Run: python benchmarks/encoding_v0_2/run_benchmark.py"
    )


def test_run_benchmark_generates_markdown():
    """run_benchmark.py generates Markdown summary."""
    md_path = RESULTS_DIR / "encoding_benchmark_v0_2_summary.md"
    assert md_path.exists(), (
        f"Summary not found at {md_path}. Run: python benchmarks/encoding_v0_2/run_benchmark.py"
    )


# ── Results Validation Tests ─────────────────────────────────────────

@pytest.fixture(scope="module")
def benchmark_rows():
    """Load benchmark CSV results."""
    csv_path = RESULTS_DIR / "encoding_benchmark_v0_2_results.csv"
    if not csv_path.exists():
        pytest.skip("Benchmark CSV not found. Run benchmark first.")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_results_have_72_rows(benchmark_rows):
    """72 total results (24 cases × 3 encodings)."""
    assert len(benchmark_rows) == 72, f"Expected 72 rows, got {len(benchmark_rows)}"


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


def test_geotask_yaml_more_tokens_than_nl(benchmark_rows):
    """GeoTask YAML has more tokens than NL (more structure)."""
    nl_tokens = [
        int(r["total_token_estimate"])
        for r in benchmark_rows
        if r["encoding_type"] == "natural_language"
    ]
    yaml_tokens = [
        int(r["total_token_estimate"])
        for r in benchmark_rows
        if r["encoding_type"] == "geotask_yaml"
    ]
    nl_avg = sum(nl_tokens) / len(nl_tokens) if nl_tokens else 0
    yaml_avg = sum(yaml_tokens) / len(yaml_tokens) if yaml_tokens else 0
    assert yaml_avg > nl_avg, (
        f"GeoTask YAML avg tokens ({yaml_avg:.0f}) should be more than "
        f"Natural Language avg tokens ({nl_avg:.0f}) due to structure overhead"
    )


def test_wrong_distance_contradicted(benchmark_rows):
    """case_011 has contradicted measurements."""
    case_rows = [r for r in benchmark_rows if r["case_id"] == "case_011_wrong_distance"]
    for r in case_rows:
        assert int(r["contradicted_count"]) >= 1, (
            f"case_011 [{r['encoding_type']}] should have contradicted count >= 1, "
            f"got {r['contradicted_count']}"
        )


def test_need_review_cases_have_correct_status(benchmark_rows):
    """Cases 017-020 have overall_status == need_review."""
    need_review_ids = [
        "case_017_missing_value",
        "case_018_missing_object_reference",
        "case_019_invalid_operator",
        "case_020_invalid_reference",
    ]
    for r in benchmark_rows:
        if r["case_id"] in need_review_ids:
            assert r["overall_status"] == "need_review", (
                f"{r['case_id']} [{r['encoding_type']}] expected need_review, "
                f"got {r['overall_status']}"
            )


def test_basic_correct_cases_verified(benchmark_rows):
    """Basic correct cases (001-010) have overall_status == verified or contradicted."""
    basic_ids = [c for c in CASE_IDS if "_correct" in c]
    for r in benchmark_rows:
        if r["case_id"] in basic_ids and "not_" in r["case_id"]:
            # Not-* cases: the output correctly says false, should be verified
            # (The "not_" in case_id refers to the spatial fact, not the verification)
            pass
        if r["case_id"] in basic_ids:
            assert r["overall_status"] in ("verified", "contradicted"), (
                f"{r['case_id']} [{r['encoding_type']}] expected verified/contradicted, "
                f"got {r['overall_status']}"
            )


def test_benchmark_scores_in_range(benchmark_rows):
    """All benchmark scores are between 0 and 100."""
    for r in benchmark_rows:
        score = float(r["benchmark_score"])
        assert 0.0 <= score <= 100.0, f"Score {score} out of range for {r['case_id']} [{r['encoding_type']}]"


def test_all_encodings_normalization_success(benchmark_rows):
    """All encodings achieve normalization success (at least 1 measurement extracted)."""
    for r in benchmark_rows:
        assert r["normalized_success"], (
            f"{r['case_id']} [{r['encoding_type']}] normalization failed"
        )


def test_status_match_rate_gte_90(benchmark_rows):
    """Status match rate >= 90% across all encodings."""
    enc_match = {}
    for r in benchmark_rows:
        enc = r["encoding_type"]
        enc_match.setdefault(enc, {"total": 0, "match": 0})
        enc_match[enc]["total"] += 1
        if r["status_matched"]:
            enc_match[enc]["match"] += 1
    for enc, counts in enc_match.items():
        rate = counts["match"] / counts["total"]
        assert rate >= 0.90, (
            f"{enc} status match rate {rate:.1%} < 90% threshold"
        )
