"""GT42 public experience page checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site/gt42/index.html"


def test_gt42_page_explains_application_approval_without_application() -> None:
    html = PAGE.read_text(encoding="utf-8")
    for fragment in (
        "GT42 · 对象关系图变更应用审批",
        "应用审批通过后，UAV-017的轨迹引用已经改变了吗？",
        "第5/5阶段",
        "application approval complete ≠ application authorized ≠ change applied",
        "object_graph_change_owner",
        "world_state_governance_reviewer",
        "prepare_bounded_object_graph_change_application",
        "geotask.object-graph-change-application-approval-record",
        "application_approval_complete: true",
        "change_application_eligible: true",
        "application_authorized: false",
        "change_applied: false",
        "subject_refs_mutated: false",
        "object_graph_mutated: false",
        "world_state_updated: false",
    ):
        assert fragment in html
    assert "track_beta" in html
    assert "仍指向" in html
    assert "provisional_beta" in html
    assert "GT38 · 1/5" in html
    assert "GT42 · 5/5" in html
    assert html.count("case-navigation.js") == 1
