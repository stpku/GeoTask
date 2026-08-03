from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT20_PAGE = ROOT / "site" / "gt20" / "index.html"
GT21_PAGE = ROOT / "site" / "gt21" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt21_page_contains_observation_conflict_scenario() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt21-observation-conflict-precedence"',
        'world_state_id: "fictional-uav-separation-state"',
        "revision: 1",
        "claim_value: 60",
        "claim_value: 55",
        'target_path: "/objects/uav-b/attributes/delay_seconds"',
        'expected_state: "blocked"',
        'strategy: "explicit_precedence"',
        'selected_value: 55',
        'selected_application_state: "applied"',
        'other_application_state: "superseded"',
        "successor_revision: 2",
        'next_action: "compute_state_transition"',
        "state_transition_computed: false",
        "external_truth_verified: false",
        "action_authorized: false",
    )
    for fragment in required:
        assert fragment in html


def test_gt21_page_visualizes_fail_closed_and_auditable_resolution() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "Observation A · sensor" in html
    assert "Observation B · review" in html
    assert "无策略 → blocked" in html
    assert "B applied" in html
    assert "A superseded" in html
    assert "55 s" in html
    assert "Core机械执行调用方声明的顺序" in html


def test_gt21_page_uses_scenario_first_narrative_and_bounds_conflict_strategies() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8")

    assert "遥测显示延误60秒，运行审核记录显示55秒，AI应该相信哪一个？" in html
    assert "为什么必须把冲突显式暴露出来？" in html
    assert "直接覆盖的后果" in html
    assert "AI常见的“合理化”错误" in html
    assert "先由业务方说明规则，系统再执行" in html
    assert "技术实现：GeoTask如何记录这两种处理" in html
    assert "require_equal" in html
    assert "explicit_precedence" in html
    assert "applied + consolidated" in html
    assert "applied + superseded" in html
    assert "不证明该来源天然更真实或更权威" in html


def test_gt21_page_recomputes_complete_precedence_locally() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8")

    assert "function hasCompletePrecedence" in html
    assert "function resolveExplicitPrecedence" in html
    assert 'state:"blocked"' in html
    assert 'state:"completed"' in html
    assert 'local.value===55' in html
    assert '"applied":"superseded"' in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt21_page_exposes_three_candidate_actions() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-last"' in html
    assert 'id="btn-average"' in html
    assert 'id="btn-policy"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "last_arrival_wins" in html
    assert "average_conflicting_values" in html
    assert "apply_complete_explicit_precedence" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt21_page_is_static_and_secret_free() -> None:
    html = GT21_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt20_catalog_readme_and_sitemap_include_gt21() -> None:
    gt20_html = GT20_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt21/"' in gt20_html
    assert "GT21" in readme
    assert "https://stpku.github.io/GeoTask/gt21/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt21/" in readme
    assert "https://stpku.github.io/GeoTask/gt21/" in sitemap
    assert "gt21" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
