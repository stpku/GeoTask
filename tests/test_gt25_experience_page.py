from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT24_PAGE = ROOT / "site" / "gt24" / "index.html"
GT25_PAGE = ROOT / "site" / "gt25" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt25_page_contains_concrete_corridor_scenario() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8")
    required = (
        'id: "gt25-corridor-safety-recompute"',
        "old_uav_position_m: 100",
        "current_uav_position_m: 130",
        "crane_position_m: 150",
        "communication_tower_position_m: 260",
        "uav_crane_distance_m: 20",
        "uav_tower_distance_m: 130",
        "crane_tower_distance_m: 110",
        "battery_percent: 48",
        'world_state_semantic_fingerprint: "1f472e30422fdc1d2c56e88876157affd06b3de7aefb6b900e657aa4910067c1"',
        'discrepancy_semantic_fingerprint: "a1a4c1dea91ec81ac4c5e492e93cde6b4725852354ae3218eebadf0e14d9cec1"',
        'correction_semantic_fingerprint: "8cb25a65a4a22aaf887181c62ce89595171816ffb026f40452c02adb0b3f851b"',
        'derivation_semantic_fingerprint: "60c5bd7849bf2c2b5d37f4cbe46564dbff86e6ba197f6e4f5ec1bf471d196784"',
    )
    for fragment in required:
        assert fragment in html


def test_gt25_page_is_scenario_first_and_explains_necessity() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8")
    assert "无人机位置更新后，哪些安全距离需要重算，哪些结果可以继续沿用？" in html
    assert "为什么不能把全部结果一起推翻？" in html
    assert "全部重算" in html
    assert "只改位置" in html
    assert "普通AI容易犯什么错误？" in html
    assert "沿用不等于永久有效" in html
    assert "技术实现：受限重算推导记录了什么？" in html


def test_gt25_page_visualizes_recompute_and_reuse_results() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8")
    assert "<svg" in html
    assert "旧位置 100m" in html
    assert "新位置 130m" in html
    assert "起重机 150m" in html
    assert "通信塔 260m" in html
    assert "50 → 20m" in html
    assert "160 → 130m" in html
    assert "110m" in html
    assert "48%" in html
    assert "重算两项受影响距离，保留两项无关结果" in html


def test_gt25_page_exposes_three_candidate_actions_and_local_check() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8")
    assert 'id="btn-all"' in html
    assert 'id="btn-nearest"' in html
    assert 'id="btn-bounded"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "recompute_everything" in html
    assert "recompute_nearest_only" in html
    assert "validate_bounded_recompute_scope" in html
    assert "function localCheck" in html
    assert "values.crane===20" in html
    assert "values.tower===130" in html
    assert "local_deterministic" in html
    assert "https://chat.deepseek.com/" in html


def test_gt25_page_preserves_recompute_safety_boundary() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8")
    for fragment in (
        "dependency_scope_discovered_by_core: false",
        "declared_scope_validated: true",
        "arbitrary_code_executed: false",
        "successor_materialized: false",
        "reevaluation_executed: false",
        "outputs_released: false",
        "external_truth_verified: false",
        "action_authorized: false",
        "action_executed: false",
        "不证明Core自动发现了全部依赖",
        "不会执行任意代码",
    ):
        assert fragment in html


def test_gt25_page_is_static_and_secret_free() -> None:
    html = GT25_PAGE.read_text(encoding="utf-8").lower()
    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt24_catalog_readme_and_sitemap_include_gt25() -> None:
    gt24_html = GT24_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert 'href="../gt25/"' in gt24_html
    assert "GT25" in readme
    assert "https://stpku.github.io/GeoTask/gt25/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt25/" in readme
    assert "https://stpku.github.io/GeoTask/gt25/" in sitemap
    assert "gt25" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
