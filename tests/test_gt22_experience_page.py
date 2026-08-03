from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT21_PAGE = ROOT / "site" / "gt21" / "index.html"
GT22_PAGE = ROOT / "site" / "gt22" / "index.html"
README = ROOT / "site" / "README.md"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt22_page_contains_initial_snapshot_scenario() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt22-initial-world-state-snapshot"',
        'observation_id: "obs-uav-alpha-position-gt22"',
        'observation_id: "obs-uav-alpha-battery-gt22"',
        'object_id: "uav-alpha"',
        'world_state_id: "fictional-uav-alpha-initial-state"',
        "revision: 1",
        "exact_claim_coverage: true",
        "object_count: 1",
        "attribute_count: 2",
        "observation_ref_count: 2",
        "evidence_ref_count: 2",
        'semantic_fingerprint: "bb57804b830e08dc361bc04e3ca96f4530ea525c198857492dcb6c304dbe540f"',
        "core_ingests_observations_automatically: false",
        "object_identity_inferred: false",
        "observation_bytes_bound_by_world_state: false",
        "external_truth_verified: false",
        "state_transition_computed: false",
        "action_authorized: false",
    )
    for fragment in required:
        assert fragment in html


def test_gt22_page_visualizes_explicit_mapping_to_revision_one() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "Position Observation" in html
    assert "Battery Observation" in html
    assert "显式object_plan" in html
    assert "全部claim恰好映射一次" in html
    assert "revision 1" in html
    assert "1 object · 2 attrs" in html
    assert "referenceable" in html


def test_gt22_page_explains_referenceable_snapshot_boundaries() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8")

    assert "可引用不等于已经证明真实" in html
    assert "bb57804b…dbe540f" in html
    assert "asserted ≠ externally verified" in html
    assert "没有绑定原始文件字节" in html
    assert "空白字符" in html
    assert "规范化世界语义与引用" in html


def test_gt22_page_recomputes_claim_coverage_and_fingerprint_locally() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8")

    assert "function exactCoverage" in html
    assert "async function sha256" in html
    assert 'crypto.subtle.digest("SHA-256"' in html
    assert "digest===expected" in html
    assert "local_deterministic" in html
    assert "model_generated" in html
    assert "bb57804b830e08dc361bc04e3ca96f4530ea525c198857492dcb6c304dbe540f" in html


def test_gt22_page_exposes_three_candidate_actions() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-direct"' in html
    assert 'id="btn-infer"' in html
    assert 'id="btn-explicit"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "treat_observations_as_world_state" in html
    assert "infer_object_identity_and_merge" in html
    assert "build_revision_1_with_explicit_mapping" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt22_page_is_static_and_secret_free() -> None:
    html = GT22_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt21_catalog_readme_and_sitemap_include_gt22() -> None:
    gt21_html = GT21_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt22/"' in gt21_html
    assert "GT22" in readme
    assert "https://stpku.github.io/GeoTask/gt22/" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt22/" in readme
    assert "https://stpku.github.io/GeoTask/gt22/" in sitemap
    assert "gt22" in (ROOT / "site" / "cases.txt").read_text(encoding="utf-8").splitlines()
