from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "site" / "index.html"
EN_PORTAL = ROOT / "site" / "en" / "index.html"


def test_portal_composes_worldstate_and_geotask_without_merging_ownership() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    required = (
        "WorldState + GeoTask",
        "从现实状态",
        "Reality → WorldState → GeoTask → Agent",
        "WorldState 不知道当前任务",
        "GeoTask 不拥有世界真值",
        "一个故事 ≠ 一个仓库",
        "https://github.com/stpku/WorldState",
        "https://github.com/stpku/GeoTask",
    )
    for fragment in required:
        assert fragment in html


def test_portal_keeps_geotask_task_context_identity() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    for fragment in (
        "时空任务上下文引擎",
        "Task → Context",
        "Task Sufficiency at Minimum Context Cost",
        "相关 ≠ 适用",
        "Context Sufficient ≠ Domain Decision ≠ Action Authorization",
    ):
        assert fragment in html


def test_portal_keeps_worldstate_truth_identity_without_overclaiming_truth() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    for fragment in (
        "世界现在是什么？",
        "Truth Fidelity",
        "StateAssertion / Relation / Validity",
        "Unknown / Conflict / History / StateDelta",
        "带证据、有效期、未知与冲突",
    ):
        assert fragment in html

    assert "负责把现实状态表达得可信" not in html


def test_portal_exposes_github_star_call_to_action() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    assert 'class="star-link"' in html
    assert "★ GitHub" in html
    assert "★ Star GeoTask" in html
    assert 'aria-label="在 GitHub 上为 GeoTask 点 Star"' in html
    assert "查看 WorldState" in html


def test_legacy_cases_are_archive_not_current_positioning() -> None:
    html = PORTAL.read_text(encoding="utf-8")

    assert "GT01—GT42 继续保留" in html
    assert "不做“整包迁移到 WorldState”" in html
    assert "展开全部 42 个原始案例与七阶段目录" in html
    assert "<!-- CASE_CATALOG:START -->" in html
    assert "<!-- CASE_CATALOG:END -->" in html
    assert 'id="reference-agent"' in html
    assert "P1 Reference Agent" in html
    for number in range(1, 43):
        assert f'href="gt{number:02d}/"' in html


def test_english_portal_matches_combined_foundation_story() -> None:
    html = EN_PORTAL.read_text(encoding="utf-8")

    required = (
        "WorldState + GeoTask",
        "From world state",
        "Reality → WorldState → GeoTask → Agent",
        "One public story does not mean one repository",
        "WorldState does not know the task",
        "GeoTask does not own world truth",
        "Spatiotemporal Task Context Engine for AI agents",
        "Truth Fidelity",
        "Task Sufficiency at Minimum Context Cost",
        "★ GitHub",
        "★ Star GeoTask",
        "https://github.com/stpku/WorldState",
        "https://github.com/stpku/GeoTask",
    )
    for fragment in required:
        assert fragment in html
