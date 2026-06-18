"""Tests for patent evidence hardening v0.1.1.

Validates evidence package integrity, completeness, and boundary compliance.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


# ── Paths ────────────────────────────────────────────────────────────

PATENT_EVIDENCE = REPO_ROOT / "patent_evidence"
ATTORNEY_BRIEF = PATENT_EVIDENCE / "00_attorney_brief" / "attorney_one_page_summary.md"
CLAIM_MAPPING = PATENT_EVIDENCE / "06_claim_mapping" / "claim_to_evidence_matrix.md"
EVIDENCE_MANIFEST = PATENT_EVIDENCE / "EVIDENCE_MANIFEST.md"
BENCHMARK_SUMMARY = PATENT_EVIDENCE / "03_benchmark" / "encoding_benchmark_v0_1_summary.md"
BENCHMARK_REPORT = REPO_ROOT / "benchmarks" / "encoding_v0_1" / "outputs" / "encoding_benchmark_v0_1_report.md"
DOCS_REPORT = REPO_ROOT / "docs" / "encoding_benchmark_v0_1.md"
README = REPO_ROOT / "README.md"
FILING_DIR = PATENT_EVIDENCE / "01_filing"


# ── File existence tests ─────────────────────────────────────────────

def test_attorney_brief_exists():
    """Attorney one-page summary exists."""
    assert ATTORNEY_BRIEF.exists(), f"Missing: {ATTORNEY_BRIEF}"


def test_claim_mapping_exists():
    """Claim-to-evidence mapping matrix exists."""
    assert CLAIM_MAPPING.exists(), f"Missing: {CLAIM_MAPPING}"


def test_evidence_manifest_exists():
    """Evidence manifest exists."""
    assert EVIDENCE_MANIFEST.exists(), f"Missing: {EVIDENCE_MANIFEST}"


# ── Content tests: benchmark summary ─────────────────────────────────

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_summary_has_verification_success():
    """Benchmark summary includes Verification Success Rate."""
    text = _read(BENCHMARK_SUMMARY)
    assert "Verification Success" in text, "Summary missing Verification Success column"


def test_summary_has_avg_total_tokens():
    """Benchmark summary includes Avg Total Tokens."""
    text = _read(BENCHMARK_SUMMARY)
    assert "Avg Total Tokens" in text or "avg_total_tokens" in text.lower(), \
        "Summary missing Avg Total Tokens"


def test_summary_has_token_reduction():
    """Benchmark summary includes Token Reduction."""
    text = _read(BENCHMARK_SUMMARY)
    assert "reduction" in text.lower() or "compression" in text.lower(), \
        "Summary missing token reduction/compression metrics"


def test_summary_has_core_conclusion():
    """Benchmark summary includes Core Conclusion section."""
    text = _read(BENCHMARK_SUMMARY)
    assert "Core Conclusion" in text, "Summary missing Core Conclusion section"


# ── Content tests: report ─────────────────────────────────────────────

def test_report_has_simulated_disclaimer():
    """Report includes deterministic simulated benchmark disclaimer."""
    for path in [BENCHMARK_REPORT, DOCS_REPORT]:
        if path.exists():
            text = _read(path)
            assert "deterministic simulated" in text.lower(), \
                f"{path.name} missing simulated benchmark disclaimer"


def test_report_has_boundary_section():
    """Report includes Simulated Benchmark Boundary section."""
    for path in [BENCHMARK_REPORT, DOCS_REPORT]:
        if path.exists():
            text = _read(path)
            # Either explicit boundary section or clear disclaimer
            has_boundary = (
                "Simulated Benchmark Boundary" in text
                or "deterministic simulated benchmark" in text.lower()
            )
            assert has_boundary, f"{path.name} missing boundary/disclaimer section"


# ── Content tests: attorney brief ────────────────────────────────────

def test_attorney_brief_has_simulated_limitation():
    """Attorney brief mentions simulated benchmark limitation."""
    text = _read(ATTORNEY_BRIEF)
    assert "simulated" in text.lower(), "Attorney brief missing simulated limitation"


def test_attorney_brief_has_key_evidence():
    """Attorney brief has Key Evidence section with metrics."""
    text = _read(ATTORNEY_BRIEF)
    assert "Key Evidence" in text, "Attorney brief missing Key Evidence section"


def test_attorney_brief_has_limitations():
    """Attorney brief has Limitations section."""
    text = _read(ATTORNEY_BRIEF)
    assert "Limitations" in text, "Attorney brief missing Limitations section"


# ── Content tests: claim mapping ─────────────────────────────────────

def test_claim_mapping_has_encoding():
    """Claim mapping includes task-related spatial encoding."""
    text = _read(CLAIM_MAPPING)
    assert "编码" in text or "encoding" in text.lower(), \
        "Claim mapping missing encoding references"


def test_claim_mapping_has_object_operator():
    """Claim mapping includes object-operator-proposition binding."""
    text = _read(CLAIM_MAPPING)
    assert "对象" in text or "object" in text.lower(), \
        "Claim mapping missing object-operator references"


def test_claim_mapping_has_verification():
    """Claim mapping includes local deterministic verification."""
    text = _read(CLAIM_MAPPING)
    assert "验证" in text or "verification" in text.lower(), \
        "Claim mapping missing verification references"


def test_claim_mapping_has_evidence_files():
    """Claim mapping references actual evidence file paths."""
    text = _read(CLAIM_MAPPING)
    assert "benchmarks" in text.lower() or "patent_evidence" in text.lower(), \
        "Claim mapping missing evidence file references"


# ── Content tests: evidence manifest ─────────────────────────────────

def test_manifest_has_private_repo():
    """Evidence manifest states repository is private."""
    text = _read(EVIDENCE_MANIFEST)
    assert "private" in text.lower(), "Manifest missing private repository statement"


def test_manifest_has_no_external_apis():
    """Evidence manifest states no external APIs used."""
    text = _read(EVIDENCE_MANIFEST)
    assert "external api" in text.lower() or "no llm" in text.lower(), \
        "Manifest missing external API statement"


def test_manifest_has_reproducibility():
    """Evidence manifest includes reproducibility commands."""
    text = _read(EVIDENCE_MANIFEST)
    assert "run_benchmark.py" in text, "Manifest missing reproducibility commands"


# ── Integrity tests ───────────────────────────────────────────────────

def test_filing_dir_no_real_docs():
    """01_filing/ contains no real filing documents (PDF, DOCX, images)."""
    if not FILING_DIR.exists():
        return
    dangerous_extensions = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
    for f in FILING_DIR.rglob("*"):
        if f.is_file() and f.suffix.lower() in dangerous_extensions:
            pytest.fail(f"Real document found in filing dir: {f}")


def test_compact_dsl_reduction_positive():
    """Compact DSL token reduction vs NL is positive (> 0%)."""
    import json
    json_path = PATENT_EVIDENCE / "03_benchmark" / "encoding_benchmark_v0_1_results.json"
    if not json_path.exists():
        pytest.skip("Benchmark JSON not found. Run benchmark first.")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_enc = data["aggregates"]["by_encoding"]
    nl_total = by_enc["natural_language"]["avg_total_tokens"]
    dsl_total = by_enc["compact_dsl"]["avg_total_tokens"]

    reduction = (nl_total - dsl_total) / nl_total * 100
    assert reduction > 0, (
        f"Compact DSL ({dsl_total}) should have fewer tokens than NL ({nl_total}). "
        f"Reduction: {reduction:.1f}%"
    )


def test_all_encodings_have_full_metrics():
    """JSON aggregates include all required metric keys for each encoding."""
    import json
    json_path = PATENT_EVIDENCE / "03_benchmark" / "encoding_benchmark_v0_1_results.json"
    if not json_path.exists():
        pytest.skip("Benchmark JSON not found.")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = {
        "avg_input_tokens", "avg_output_tokens", "avg_total_tokens",
        "normalization_success_rate", "status_match_rate",
        "avg_benchmark_score", "avg_token_efficiency",
    }
    for enc in ["natural_language", "geotask_yaml", "compact_dsl"]:
        agg = data["aggregates"]["by_encoding"].get(enc, {})
        missing = required_keys - set(agg.keys())
        assert not missing, f"Encoding '{enc}' missing keys in aggregate: {missing}"
