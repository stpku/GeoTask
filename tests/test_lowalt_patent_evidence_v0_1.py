"""Tests for LowAlt patent evidence v0.1."""
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_lowalt_doc_exists():
    path = os.path.join(PROJECT_ROOT, "docs", "lowalt_site_precheck_pack_v0_1.md")
    assert os.path.exists(path)

def test_lowalt_evidence_dir_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "11_lowalt_site_precheck_v0_1")
    assert os.path.isdir(path)

def test_lowalt_disclosure_boundary_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "11_lowalt_site_precheck_v0_1", "lowalt_disclosure_boundary.md")
    assert os.path.exists(path)

def test_invention_ledger_has_p5_marking():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "invention_ledger.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    has_p5_or_lowalt = "lowalt" in lower or "low-altitude" in lower or "p5" in lower
    assert has_p5_or_lowalt, "Invention ledger should reference P5/LowAlt"

def test_invention_ledger_p2_p5_do_not_disclose():
    """P2 and P5 should be marked DO NOT DISCLOSE."""
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "09_product_architecture_v0_1", "invention_ledger.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    assert "do not disclose" in lower or "禁止公开" in content or "不得公开" in content

def test_readme_no_p2_p5_algorithm():
    """README must not disclose P2/P5 detailed algorithms."""
    path = os.path.join(PROJECT_ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    forbidden = [
        "joint scheduling algorithm",
        "verification-cost model",
        "model routing optimization",
        "token budget optimizer",
        "encoding planner algorithm detailed",
    ]
    for term in forbidden:
        assert term not in lower, f"README must not disclose: {term}"

def test_evidence_manifest_updated():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "EVIDENCE_MANIFEST.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "10_p1_p2_boundary_audit" in content
    assert "11_lowalt_site_precheck" in content

def test_all_patent_evidence_dirs_confidential():
    """All patent evidence dirs 09-11 should contain confidentiality warnings."""
    for dir_name in ["09_product_architecture_v0_1", "10_p1_p2_boundary_audit", "11_lowalt_site_precheck_v0_1"]:
        dir_path = os.path.join(PROJECT_ROOT, "patent_evidence", dir_name)
        if not os.path.isdir(dir_path):
            continue
        import glob
        for md_file in glob.glob(os.path.join(dir_path, "*.md")):
            with open(md_file, encoding="utf-8") as f:
                content = f.read()
            lower = content.lower()
            has_warning = any(w in lower for w in [
                "confidential", "do not disclose", "not public",
                "不得公开", "禁止公开", "private repository",
            ])
            assert has_warning, f"{md_file} missing confidentiality warning"
