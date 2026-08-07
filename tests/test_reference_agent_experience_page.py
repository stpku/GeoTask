from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "reference-agent" / "index.html"
PORTAL = ROOT / "site" / "index.html"


def test_reference_agent_experience_page_explains_product_track_lifecycle() -> None:
    text = PAGE.read_text(encoding="utf-8")
    for fragment in (
        "P1 PRODUCT TRACK",
        "不是GT43",
        "REV 1",
        "REV 2",
        "DISCREPANCY",
        "IMPACT",
        "REV 3",
        "CONTROL",
        "eligible ≠ refreshed ≠ executed",
        "注册制品",
        "生产",
    ):
        assert fragment in text


def test_reference_agent_experience_page_covers_all_five_scenarios() -> None:
    text = PAGE.read_text(encoding="utf-8")
    for fragment in (
        "Fresh / 70m",
        "Missing",
        "Conflict / 70m vs 30m",
        "Stale",
        "Fresh / 30m",
        "unverifiable",
        "contradicted",
    ):
        assert fragment in text


def test_project_portal_surfaces_reference_agent_outside_gt_catalog() -> None:
    text = PORTAL.read_text(encoding="utf-8")
    assert 'id="reference-agent"' in text
    assert 'href="reference-agent/"' in text
    assert "P1 Reference Agent" in text
    assert "GT01—GT42证明单项能力" in text
