from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_SCRIPT = ROOT / ".release" / "release_public.py"


def test_boundary_summary_is_not_nested_in_tree_walk() -> None:
    """The release pre-check should report its summary once, not once per file."""
    source = RELEASE_SCRIPT.read_text(encoding="utf-8")
    summary = "Boundary check complete — forbidden paths handled by export exclude"

    assert "os.walk(PROJECT_ROOT)" not in source
    assert source.count(summary) == 1
