from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT16_PAGE = ROOT / "site" / "gt16" / "index.html"
GT17_PAGE = ROOT / "site" / "gt17" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"
SITEMAP = ROOT / "site" / "sitemap.xml"


def test_gt17_page_contains_event_deduplication_task() -> None:
    html = GT17_PAGE.read_text(encoding="utf-8")

    required = (
        'id: "gt17-city-event-report-deduplication"',
        "report_count: 10",
        'event_type: "road_waterlogging"',
        "same_semantic_signature: true",
        "spatial_threshold_m: 30",
        "maximum_report_distance_m: 18.97",
        "all_reports_within_spatial_threshold: true",
        'dedup_window: "08:00-08:10"',
        "all_reports_within_temporal_window: true",
        "evidence_source_count: 10",
        'selected_action: "merge_reports_and_create_one_task"',
        "task_count: 1",
        "preserve_source_evidence: true",
        'expected_status: "verified_deduplication"',
    )
    for fragment in required:
        assert fragment in html


def test_gt17_page_visualizes_ten_reports_one_task_and_evidence() -> None:
    html = GT17_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "十个上报点" in html
    assert "最大偏移18.97米" in html
    assert "10</strong><span>来源上报" in html
    assert "1</strong><span>处置任务" in html
    assert "evidence_source_count = 10" in html
    assert "true AND true AND true" in html


def test_gt17_page_calculates_spatial_and_temporal_cluster_locally() -> None:
    html = GT17_PAGE.read_text(encoding="utf-8")

    assert "function distance" in html
    assert "function overlap" in html
    assert "distances=reports.map" in html
    assert "maxDistance=Math.max" in html
    assert "allSpatial" in html
    assert "allTemporal" in html
    assert "sameSemanticSignature" in html
    assert "local_deterministic" in html
    assert "application_verified" in html
    assert "model_generated" in html


def test_gt17_page_exposes_three_candidate_actions() -> None:
    html = GT17_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-ten"' in html
    assert 'id="btn-discard"' in html
    assert 'id="btn-merge"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "create_ten_dispatch_tasks" in html
    assert "discard_repeated_reports" in html
    assert "merge_reports_and_create_one_task" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html


def test_gt17_page_is_static_and_secret_free() -> None:
    html = GT17_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt16_readme_deploy_and_sitemap_include_gt17() -> None:
    gt16_html = GT16_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert 'href="../gt17/"' in gt16_html
    assert "GT17" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt17/" in readme
    assert "https://stpku.github.io/GeoTask/gt17/" in sitemap
