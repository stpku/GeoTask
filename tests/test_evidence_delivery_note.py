"""Tests for Evidence Delivery Note v0.1.1.

Validates delivery package completeness and content integrity.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

PATENT_EVIDENCE = REPO_ROOT / "patent_evidence"
DELIVERY_NOTE = PATENT_EVIDENCE / "DELIVERY_NOTE_v0_1_1.md"
ATTORNEY_BRIEF = PATENT_EVIDENCE / "00_attorney_brief" / "attorney_one_page_summary.md"
CLAIM_MAPPING = PATENT_EVIDENCE / "06_claim_mapping" / "claim_to_evidence_matrix.md"
EVIDENCE_MANIFEST = PATENT_EVIDENCE / "EVIDENCE_MANIFEST.md"
BENCHMARK_SUMMARY = PATENT_EVIDENCE / "03_benchmark" / "encoding_benchmark_v0_1_summary.md"
PATENT_GUIDE = REPO_ROOT / "docs" / "patent_evidence_guide.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Delivery Note File Existence ──────────────────────────────────────

def test_delivery_note_exists():
    """DELIVERY_NOTE_v0_1_1.md exists."""
    assert DELIVERY_NOTE.exists(), f"Missing: {DELIVERY_NOTE}"


# ── Delivery Note Content Sections ────────────────────────────────────

def test_delivery_note_has_recommended_files():
    """Delivery note includes recommended files section."""
    text = _read(DELIVERY_NOTE)
    assert "Recommended Files" in text or "Recommended files" in text, \
        "Delivery note missing recommended files section"


def test_delivery_note_has_claim_support_summary():
    """Delivery note includes claim support summary."""
    text = _read(DELIVERY_NOTE)
    assert "Claim Support" in text or "claim support" in text.lower(), \
        "Delivery note missing claim support summary"


def test_delivery_note_has_what_evidence_proves():
    """Delivery note includes what this evidence proves section."""
    text = _read(DELIVERY_NOTE)
    assert "What This Evidence Proves" in text, \
        "Delivery note missing 'what evidence proves' section"


def test_delivery_note_has_what_evidence_does_not_prove():
    """Delivery note includes what this evidence does NOT prove section."""
    text = _read(DELIVERY_NOTE)
    assert "Does NOT" in text or "does not prove" in text.lower(), \
        "Delivery note missing 'what evidence does not prove' section"


def test_delivery_note_has_reproducibility():
    """Delivery note includes reproducibility commands."""
    text = _read(DELIVERY_NOTE)
    assert "run_benchmark.py" in text, "Delivery note missing reproducibility commands"


def test_delivery_note_has_confidentiality():
    """Delivery note includes confidentiality notes."""
    text = _read(DELIVERY_NOTE)
    assert "Confidentiality" in text, "Delivery note missing confidentiality notes"


def test_delivery_note_has_next_plan():
    """Delivery note includes next evidence plan."""
    text = _read(DELIVERY_NOTE)
    assert "Next Evidence Plan" in text or "Next" in text, \
        "Delivery note missing next evidence plan"


# ── Evidence Manifest Updates ─────────────────────────────────────────

def test_manifest_has_evidence_version():
    """EVIDENCE_MANIFEST includes evidence version v0.1.1."""
    text = _read(EVIDENCE_MANIFEST)
    assert "v0.1.1" in text, "Manifest missing evidence version v0.1.1"


def test_manifest_has_recommended_tag():
    """EVIDENCE_MANIFEST includes recommended tag evidence-encoding-v0.1.1."""
    text = _read(EVIDENCE_MANIFEST)
    assert "evidence-encoding-v0.1.1" in text, \
        "Manifest missing recommended tag evidence-encoding-v0.1.1"


def test_manifest_has_delivery_package():
    """EVIDENCE_MANIFEST includes Delivery Package section."""
    text = _read(EVIDENCE_MANIFEST)
    assert "Delivery Package" in text, "Manifest missing Delivery Package section"


def test_manifest_has_delivery_note_reference():
    """EVIDENCE_MANIFEST references DELIVERY_NOTE."""
    text = _read(EVIDENCE_MANIFEST)
    assert "DELIVERY_NOTE" in text, "Manifest missing DELIVERY_NOTE reference"


# ── Patent Evidence Guide Updates ─────────────────────────────────────

def test_evidence_guide_has_delivery_workflow():
    """patent_evidence_guide includes Delivery Workflow for Attorney Review."""
    text = _read(PATENT_GUIDE)
    assert "Delivery Workflow" in text, \
        "patent_evidence_guide missing Delivery Workflow section"


# ── Summary Content Integrity ─────────────────────────────────────────

def test_summary_no_empty_table_cells():
    """Benchmark summary has no headings-only tables (must have data rows)."""
    text = _read(BENCHMARK_SUMMARY)
    lines = text.split("\n")

    # Find table sections and verify they have at least one data row after headers
    in_table = False
    header_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if "---" in stripped:
                in_table = True
                header_count = 0
            elif in_table:
                header_count += 1
        else:
            # Table ended - verify it had data
            if in_table and header_count == 0:
                # Find the separator line to report context
                pytest.fail(
                    f"Empty table found in summary (no data rows after header). "
                    f"Check near: ..."
                )
            in_table = False
            header_count = 0


def test_attorney_brief_has_token_reduction():
    """Attorney brief includes token reduction or compression ratio."""
    text = _read(ATTORNEY_BRIEF)
    has_reduction = "77.7%" in text or "77.6%" in text
    has_compression = "4.5" in text
    assert has_reduction or has_compression, \
        "Attorney brief missing token reduction/compression metrics"


# ── Claim Mapping Content ─────────────────────────────────────────────

def test_claim_mapping_has_encoding():
    """Claim mapping includes task-related spatial encoding."""
    text = _read(CLAIM_MAPPING)
    assert "编码" in text or "encoding" in text.lower(), \
        "Claim mapping missing encoding references"


def test_claim_mapping_has_object_operator_binding():
    """Claim mapping includes object-operator-proposition binding."""
    text = _read(CLAIM_MAPPING)
    assert "算子" in text or "operator" in text.lower(), \
        "Claim mapping missing object-operator references"


def test_claim_mapping_has_verification():
    """Claim mapping includes local deterministic verification."""
    text = _read(CLAIM_MAPPING)
    assert "验证" in text or "verification" in text.lower(), \
        "Claim mapping missing verification references"


# ── Delivery Note Metrics ─────────────────────────────────────────────

def test_delivery_note_has_token_metrics():
    """Delivery note includes token cost metrics with actual values."""
    text = _read(DELIVERY_NOTE)
    assert "404" in text, "Delivery note missing NL token count"
    assert "262" in text, "Delivery note missing YAML token count"
    assert "90" in text and "77.6" in text, "Delivery note missing DSL token count or reduction"


def test_delivery_note_has_benchmark_score():
    """Delivery note includes benchmark scores."""
    text = _read(DELIVERY_NOTE)
    assert "95.0" in text, "Delivery note missing DSL benchmark score"
    assert "79.6" in text, "Delivery note missing NL benchmark score"


def test_delivery_note_has_suggested_wording():
    """Delivery note includes suggested wording for prosecution."""
    text = _read(DELIVERY_NOTE)
    assert "Suggested Wording" in text, "Delivery note missing suggested wording section"
