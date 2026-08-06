"""GT41 public experience page checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site/gt41/index.html"


def test_gt41_page_explains_change_request_without_application() -> None:
    html = PAGE.read_text(encoding="utf-8")
    for fragment in (
        "GT41 · 对象关系图变更请求",
        "系统究竟准备修改UAV-017的哪一条记录",
        "第4/5阶段",
        "change request ≠ change applied",
        "track_beta /subject_ref",
        "provisional_beta → provisional_alpha",
        "request_object_graph_change_application_approval",
        "geotask.object-graph-change-request",
        "application_review_required: true",
        "application_authorized: false",
        "change_applied: false",
        "subject_refs_mutated: false",
        "object_graph_mutated: false",
        "world_state_updated: false",
    ):
        assert fragment in html
    assert "只有恢复后轨迹的" in html
    assert "subject_ref" in html
    assert "发生变化" in html
    assert "GT38 · 1/5" in html
    assert "GT42 · 5/5" in html
    assert html.count("case-navigation.js") == 1
