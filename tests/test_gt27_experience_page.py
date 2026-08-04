from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT26_PAGE = ROOT / "site" / "gt26" / "index.html"
GT27_PAGE = ROOT / "site" / "gt27" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt27_page_contains_concrete_weather_and_mission_scenario() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8")
    for fragment in (
        'id: "gt27-weather-incremental-reevaluation"',
        "old_wind_mps: 6",
        "new_wind_mps: 12",
        'id: mission-a-delivery',
        'id: mission-b-inspection',
        'id: mission-c-survey',
        'id: mission-d-emergency',
        "12 ≤ 10 → false",
        "12 ≤ 15 → true",
        "f229b9b3f6d6b0bf358c15b19cb563f11c3d8930d948681b69fd02bcbbef2899",
        "58b48884c3d70a2cd565e2791acdc121207b28fce4e66aff8ec68c9ccc3df4c6",
        "0e20bf36957b46ea1739b280faec424b4c23314f411346322bdc8439af82002f",
    ):
        assert fragment in html


def test_gt27_page_is_scenario_first_and_explains_necessity() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8")
    assert "一条气象数据更新后，如何只复核受影响的飞行任务？" in html
    assert "四项任务，只有两项进入复核" in html
    assert "普通AI容易犯什么错误？" in html
    assert "把四项任务全部重算" in html
    assert "只复核结果会变化的任务" in html
    assert "结果仍为true ≠ 无需复核" in html
    assert "技术实现：Incremental Reevaluation记录了什么？" in html


def test_gt27_page_shows_two_rechecks_two_reuses_and_two_outcomes() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8")
    assert "任务A · 东区配送" in html
    assert "任务B · 西区巡检" in html
    assert "任务C · 东区测绘" in html
    assert "任务D · 东区应急" in html
    assert "2</b><span>复核任务" in html
    assert "2</b><span>复用任务" in html
    assert "1</b><span>结果改变" in html
    assert "1</b><span>复核后不变" in html
    assert "任务B、C不进入图，也不发生状态修改" in html


def test_gt27_page_exposes_three_actions_and_local_check() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8")
    assert 'id="btn-all"' in html
    assert 'id="btn-changed"' in html
    assert 'id="btn-bounded"' in html
    assert "reevaluate_all_missions" in html
    assert "reevaluate_only_changed_outcome" in html
    assert "reevaluate_declared_region_time_scope" in html
    assert "function localCheck" in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "https://chat.deepseek.com/" in html


def test_gt27_page_preserves_incremental_reevaluation_boundaries() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8")
    for fragment in (
        "scope_discovered_by_core: false",
        "reevaluation_executed_by_generic_core: false",
        "unaffected_tasks_proven_permanently_safe: false",
        "artifact_output_gates_recorded_released: true",
        "production_outputs_released: false",
        "action_authorized: false",
        "action_executed: false",
        "Core不主动发现这份依赖关系",
        "不代表生产系统已经发布结果",
    ):
        assert fragment in html


def test_gt27_page_is_static_and_secret_free() -> None:
    html = GT27_PAGE.read_text(encoding="utf-8").lower()
    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt26_navigation_readme_and_sitemap_include_gt27() -> None:
    assert 'href="../gt27/"' in GT26_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert "GT27" in readme
    assert "https://stpku.github.io/GeoTask/gt27/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt27/" in readme
    assert "https://stpku.github.io/GeoTask/gt27/" in sitemap
    assert "gt27" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
