"""Tests for GeoTask Core v0.3 evidence package integrity."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

EVIDENCE_DIR = REPO_ROOT / "patent_evidence" / "08_core_v0_3"
MANIFEST_PATH = REPO_ROOT / "patent_evidence" / "EVIDENCE_MANIFEST.md"
CLAIM_MAPPING_PATH = REPO_ROOT / "patent_evidence" / "06_claim_mapping" / "claim_to_evidence_matrix.md"
DOCS_PATH = REPO_ROOT / "docs" / "core_normalizer_verifier_v0_3.md"


# ── File existence ─────────────────────────────────────────────────────

def test_readme_exists():
    assert (EVIDENCE_DIR / "README.md").exists()


def test_capability_summary_exists():
    assert (EVIDENCE_DIR / "core_v0_3_capability_summary.md").exists()


def test_end_to_end_cases_exists():
    assert (EVIDENCE_DIR / "core_v0_3_end_to_end_cases.md").exists()


def test_claim_support_exists():
    assert (EVIDENCE_DIR / "core_v0_3_claim_support_update.md").exists()


def test_boundary_exists():
    assert (EVIDENCE_DIR / "core_v0_3_boundary.md").exists()


def test_docs_exists():
    assert DOCS_PATH.exists()


# ── Content checks ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def readme_text():
    return (EVIDENCE_DIR / "README.md").read_text(encoding="utf-8").lower()


@pytest.fixture(scope="module")
def docs_text():
    return DOCS_PATH.read_text(encoding="utf-8").lower()


def test_readme_mentions_production_core(readme_text):
    assert "production" in readme_text or "production core" in readme_text


def test_docs_mentions_production_core_normalizer(docs_text):
    """Docs mention 'production GeoTask Core Normalizer and Verifier' or similar."""
    assert ("production geotask core" in docs_text or
            "production core" in docs_text or
            "production-grade" in docs_text)


def test_docs_mentions_not_live_llm(docs_text):
    """Docs state does not claim live LLM accuracy."""
    assert ("does not claim live llm" in docs_text or
            "no real llm" in docs_text or
            "not a live llm" in docs_text)


# ── Manifest checks ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def manifest_text():
    return MANIFEST_PATH.read_text(encoding="utf-8").lower()


def test_manifest_mentions_v0_3(manifest_text):
    assert "08_core_v0_3" in manifest_text or "core_v0_3" in manifest_text or "v0.3" in manifest_text


# ── Claim mapping checks ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def claim_text():
    return CLAIM_MAPPING_PATH.read_text(encoding="utf-8").lower()


def test_claim_mapping_mentions_v0_3(claim_text):
    assert "v0.3" in claim_text or "v0_3" in claim_text
