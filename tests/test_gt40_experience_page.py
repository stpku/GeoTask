"""GT40 public experience page checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site/gt40/index.html"


def test_gt40_page_explains_approval_without_execution() -> None:
    html = PAGE.read_text(encoding="utf-8")
    for fragment in (
        "GT40 · 对象身份归并审批记录",
        "无人机身份归并提案由谁审批",
        "UAV-017",
        "第3/5阶段",
        "approved ≠ identity_merge_performed",
        "identity_governance_reviewer",
        "world_state_maintainer",
        "prepare_identity_merge_change_request",
        "geotask.identity-merge-approval-record",
        "proposal_approval_complete: true",
        "change_request_eligible: true",
        "identity_merge_performed: false",
        "subject_refs_mutated: false",
        "object_graph_mutated: false",
        "world_state_updated: false",
    ):
        assert fragment in html
    assert "UAV-017原始主体、遮挡后临时主体" in html
    assert "仍保持原样" in html
    assert "GT38 · 1/5" in html
    assert "GT42 · 5/5" in html
    assert html.count("case-navigation.js") == 1
