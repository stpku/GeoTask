"""Tests for product architecture evidence package v0.1."""
import os
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_product_architecture_doc_exists():
    path = os.path.join(PROJECT_ROOT, "docs", "product_architecture_v0_1.md")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Product Architecture" in content or "product architecture" in content.lower()
    assert "Core" in content
    assert "Runtime" in content


def test_productization_roadmap_exists():
    path = os.path.join(PROJECT_ROOT, "docs", "productization_roadmap_v0_1.md")
    assert os.path.exists(path)


def test_open_core_boundary_doc_exists():
    path = os.path.join(PROJECT_ROOT, "docs", "open_core_commercial_runtime_boundary.md")
    assert os.path.exists(path)


def test_domain_pack_architecture_exists():
    path = os.path.join(PROJECT_ROOT, "docs", "domain_pack_architecture.md")
    assert os.path.exists(path)


def test_adr_docs_exist():
    adr_dir = os.path.join(PROJECT_ROOT, "docs", "architecture_decisions")
    assert os.path.exists(os.path.join(adr_dir, "ADR-001-core-runtime-domain-pack.md"))
    assert os.path.exists(os.path.join(adr_dir, "ADR-002-private-runtime-boundary.md"))
    assert os.path.exists(os.path.join(adr_dir, "ADR-003-domain-pack-plugin-contract.md"))
    assert os.path.exists(os.path.join(adr_dir, "ADR-004-patent-and-open-source-boundary.md"))


def test_invention_ledger_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "invention_ledger.md")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "INV-001" in content
    assert "INV-005" in content


def test_patent_portfolio_roadmap_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "patent_portfolio_roadmap.md")
    assert os.path.exists(path)


def test_product_to_patent_mapping_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "product_to_patent_mapping.md")
    assert os.path.exists(path)


def test_commercial_boundary_note_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "commercial_boundary_note.md")
    assert os.path.exists(path)


def test_readme_does_not_disclose_unpatented():
    """README must not disclose detailed algorithms of unpatented inventions."""
    path = os.path.join(PROJECT_ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    never_disclose = [
        "encoding planner algorithm",
        "model routing strategy",
        "token budget optimization",
        "cost optimization",
        "context gap identification algorithm",
    ]
    lower = content.lower()
    for term in never_disclose:
        assert term not in lower, f"README should not disclose: {term}"


def test_docs_contain_disclosure_warning():
    """Architecture docs should contain disclosure risk warnings."""
    patent_dir = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1")
    for md_file in glob.glob(os.path.join(patent_dir, "*.md")):
        with open(md_file, encoding="utf-8") as f:
            content = f.read()
        lower = content.lower()
        has_warning = any(phrase in lower for phrase in [
            "do not disclose", "不得公开", "禁止公开", "disclosure risk",
            "private repository", "not public", "confidential"
        ])
        assert has_warning, f"{md_file} should contain disclosure warning"


def test_runtime_module_importable():
    """Runtime module should be importable."""
    import sys
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
    from geotask_runtime import __version__
    assert __version__ is not None
