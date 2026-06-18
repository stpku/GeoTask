"""Tests for GeoTask Encoding Benchmark v0.2 Evidence Addendum."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

EVIDENCE_DIR = REPO_ROOT / "patent_evidence" / "07_benchmark_v0_2"
MANIFEST_PATH = REPO_ROOT / "patent_evidence" / "EVIDENCE_MANIFEST.md"
CLAIM_MAPPING_PATH = REPO_ROOT / "patent_evidence" / "06_claim_mapping" / "claim_to_evidence_matrix.md"
DOCS_BENCHMARK_PATH = REPO_ROOT / "docs" / "encoding_benchmark_v0_2.md"
DOCS_GUIDE_PATH = REPO_ROOT / "docs" / "patent_evidence_guide.md"


# ── File Existence Tests ───────────────────────────────────────────────────

def test_normalizer_boundary_exists():
    """v0_2_normalizer_boundary.md exists."""
    path = EVIDENCE_DIR / "v0_2_normalizer_boundary.md"
    assert path.exists(), f"Missing: {path}"


def test_attorney_addendum_exists():
    """v0_2_attorney_addendum.md exists."""
    path = EVIDENCE_DIR / "v0_2_attorney_addendum.md"
    assert path.exists(), f"Missing: {path}"


# ── Normalizer Boundary Document Content ────────────────────────────────────

@pytest.fixture(scope="module")
def boundary_text():
    """Load normalizer boundary document."""
    path = EVIDENCE_DIR / "v0_2_normalizer_boundary.md"
    return path.read_text(encoding="utf-8")


def test_boundary_mentions_benchmark_local_verifier(boundary_text):
    """Normalizer boundary doc mentions 'benchmark local verifier' or 'benchmark-local verifier'."""
    lower = boundary_text.lower()
    assert "benchmark local verifier" in lower or "benchmark-local verifier" in lower, (
        "Must mention benchmark local verifier"
    )


def test_boundary_mentions_not_full_core_support(boundary_text):
    """Normalizer boundary doc states v0.2 is not a claim of full Core Normalizer support."""
    lower = boundary_text.lower()
    # Must contain equivalent of "not as a claim that the production ... fully supports all"
    has_disclaimer = (
        "not as a claim that the production" in lower
        or "not a claim that the production" in lower
        or "does not claim that the production" in lower
        or "not prove that the production" in lower
    )
    assert has_disclaimer, "Must state v0.2 does not claim production normalizer fully supports all operators"


def test_boundary_mentions_v0_1_1_relationship(boundary_text):
    """Normalizer boundary doc explains relationship between v0.1.1 and v0.2."""
    assert "v0.1.1" in boundary_text.lower(), "Must mention v0.1.1"


def test_boundary_has_recommended_wording(boundary_text):
    """Normalizer boundary doc has recommended attorney wording section."""
    assert "recommended wording" in boundary_text.lower(), (
        "Must have recommended wording for attorney communication"
    )


def test_boundary_has_v0_3_plan(boundary_text):
    """Normalizer boundary doc mentions v0.3 plan."""
    assert "v0.3" in boundary_text.lower(), "Must mention v0.3 plan"


# ── Attorney Addendum Document Content ──────────────────────────────────────

@pytest.fixture(scope="module")
def attorney_text():
    """Load attorney addendum document."""
    path = EVIDENCE_DIR / "v0_2_attorney_addendum.md"
    return path.read_text(encoding="utf-8")


def test_attorney_mentions_24_cases(attorney_text):
    """Attorney addendum mentions 24 cases."""
    # Multiple possible formats: "24 cases", "24 cas"
    assert ("24 cases" in attorney_text.lower() or "24 cas" in attorney_text.lower()), (
        "Must mention 24 cases"
    )


def test_attorney_mentions_6_operators(attorney_text):
    """Attorney addendum mentions 6 operators."""
    assert "6 operators" in attorney_text.lower() or "6 operator" in attorney_text.lower(), (
        "Must mention 6 operators"
    )


def test_attorney_mentions_35_percent_token_reduction(attorney_text):
    """Attorney addendum mentions 35% fewer tokens than natural language."""
    lower = attorney_text.lower()
    has_35 = "35%" in lower and ("fewer tokens" in lower or "token reduction" in lower or "less tokens" in lower)
    assert has_35, "Must mention 35% token reduction vs natural language"


def test_attorney_mentions_60_percent_token_reduction(attorney_text):
    """Attorney addendum mentions 60% fewer tokens than GeoTask YAML."""
    lower = attorney_text.lower()
    has_60 = "60%" in lower and ("fewer" in lower or "less" in lower or "reduction" in lower)
    assert has_60, "Must mention 60% token reduction vs GeoTask YAML"


def test_attorney_mentions_100_percent_status_match(attorney_text):
    """Attorney addendum mentions 100% status match."""
    lower = attorney_text.lower()
    assert "100% status match" in lower, "Must mention 100% status match"


def test_attorney_mentions_boundary_note(attorney_text):
    """Attorney addendum has boundary note section."""
    lower = attorney_text.lower()
    assert "boundary" in lower, "Must include boundary note"


# ── v0.2 README Tests ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def readme_text():
    """Load v0.2 README."""
    path = EVIDENCE_DIR / "README.md"
    return path.read_text(encoding="utf-8")


def test_readme_has_normalizer_boundary_section(readme_text):
    """v0.2 README contains Normalizer / Verifier boundary section."""
    lower = readme_text.lower()
    has_section = (
        "normalizer" in lower and "verifier" in lower and "boundary" in lower
    )
    assert has_section, "v0.2 README must have Normalizer / Verifier boundary section"


# ── Manifest Tests ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def manifest_text():
    """Load EVIDENCE_MANIFEST.md."""
    return MANIFEST_PATH.read_text(encoding="utf-8")


def test_manifest_has_attorney_addendum(manifest_text):
    """Manifest lists v0_2_attorney_addendum.md."""
    assert "v0_2_attorney_addendum.md" in manifest_text, (
        "Manifest must list v0_2_attorney_addendum.md"
    )


def test_manifest_has_normalizer_boundary(manifest_text):
    """Manifest lists v0_2_normalizer_boundary.md."""
    assert "v0_2_normalizer_boundary.md" in manifest_text, (
        "Manifest must list v0_2_normalizer_boundary.md"
    )


# ── Claim Mapping Tests ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def claim_mapping_text():
    """Load claim_to_evidence_matrix.md."""
    return CLAIM_MAPPING_PATH.read_text(encoding="utf-8")


def test_claim_mapping_has_v0_2_boundary(claim_mapping_text):
    """Claim mapping mentions v0.2 should be used as structural encoding evidence."""
    lower = claim_mapping_text.lower()
    assert "v0.2" in lower or "v0_2" in lower, "Must mention v0.2"
    assert "structural encoding" in lower or "verification-readiness" in lower, (
        "Must include structural encoding or verification-readiness boundary"
    )


# ── Docs Tests ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def docs_benchmark_text():
    """Load docs/encoding_benchmark_v0_2.md."""
    return DOCS_BENCHMARK_PATH.read_text(encoding="utf-8")


def test_docs_benchmark_has_local_verifier_boundary(docs_benchmark_text):
    """docs/encoding_benchmark_v0_2.md mentions local verifier boundary."""
    lower = docs_benchmark_text.lower()
    assert "local verifier" in lower or "local_verifier" in lower, (
        "Must mention local verifier boundary"
    )


@pytest.fixture(scope="module")
def docs_guide_text():
    """Load docs/patent_evidence_guide.md."""
    return DOCS_GUIDE_PATH.read_text(encoding="utf-8")


def test_docs_guide_has_how_to_explain_v0_2(docs_guide_text):
    """docs/patent_evidence_guide.md explains v0.2 boundary and relationship to v0.1.1."""
    lower = docs_guide_text.lower()
    # Guide was restructured for v0.3; v0.2 explanation is under "Key points when discussing v0.2"
    assert ("key points when discussing v0.2" in lower
            or "how to explain" in lower), (
        "Must have v0.2 explanation section"
    )
    assert "v0.2" in lower


# ── Integration Test ────────────────────────────────────────────────────────

def test_all_addendum_files_reference_each_other():
    """Addendum files form a coherent cross-referenced package."""
    boundary = (EVIDENCE_DIR / "v0_2_normalizer_boundary.md").read_text(encoding="utf-8").lower()
    attorney = (EVIDENCE_DIR / "v0_2_attorney_addendum.md").read_text(encoding="utf-8").lower()

    # boundary doc references attorney addendum
    assert "v0_2_attorney_addendum" in boundary, "Boundary doc should reference attorney addendum"

    # attorney doc references boundary doc
    assert "v0_2_normalizer_boundary" in attorney, "Attorney addendum should reference boundary doc"
