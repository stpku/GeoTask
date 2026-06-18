"""Tests for P1/P2 boundary audit evidence v0.1."""
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_p1_coverage_audit_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "p1_coverage_audit.md")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "INV-001" in content
    assert "INV-010" in content

def test_p2_non_overlap_design_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "p2_non_overlap_design.md")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "joint" in content.lower() and "scheduling" in content.lower()

def test_attorney_questions_exist():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "attorney_questions_for_p1_p2.md")
    assert os.path.exists(path)

def test_disclosure_boundary_note_exists():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "disclosure_boundary_note.md")
    assert os.path.exists(path)

def test_p2_doc_not_just_encoding_selection():
    """P2 doc must not reduce to 'selecting DSL or YAML'. Must cover joint planning."""
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "p2_non_overlap_design.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    has_joint = "joint" in lower or "联合" in content
    assert has_joint, "P2 must describe joint optimization, not just encoding selection"

def test_disclosure_doc_has_no_disclose_warning():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "disclosure_boundary_note.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    assert "not be disclosed" in lower or "不得公开" in content or "do not disclose" in lower

def test_p1_audit_has_attorney_confirmation():
    """If no formal P1 text exists, doc must state attorney confirmation required."""
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "p1_coverage_audit.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lower = content.lower()
    assert "attorney confirmation" in lower or "代理人" in content

def test_audit_includes_all_inv_points():
    path = os.path.join(PROJECT_ROOT, "patent_evidence", "10_p1_p2_boundary_audit", "p1_coverage_audit.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for i in range(1, 11):
        assert f"INV-{i:03d}" in content, f"Missing INV-{i:03d}"
