from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT08_PAGE = ROOT / "site" / "gt08" / "index.html"
GT09_PAGE = ROOT / "site" / "gt09" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt09_page_contains_conflicting_verified_sources() -> None:
    html = GT09_PAGE.read_text(encoding="utf-8")

    assert "两张临时禁飞通知时间不一样，无人机还能起飞吗" in html
    assert "uav_temporary_no_fly_notice_conflict" in html
    assert 'planned_flight_window: "08:00-09:00"' in html
    required_fragments = (
        'id: "gt09-evidence-conflict-review"',
        'id: "resolve-restricted-schedule-conflict"',
        'conflict_type: "incompatible_verified_sources"',
        'next_action: "request_conflict_review"',
        'expected_status: "conflicted"',
        'resume_when: "evidence_conflict_resolved == true"',
        '"authoritative_source"',
        '"superseded_version"',
        '"effective_schedule"',
        '"resolution_basis"',
        '"resolved_by"',
        '"resolved_at"',
        '08:30',
        '09:30',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt09_page_visualizes_source_conflict_and_review_flow() -> None:
    html = GT09_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "来源 A" in html
    assert "来源 B" in html
    assert "时间重叠 true" in html
    assert "时间重叠 false" in html
    assert "证据冲突" in html
    assert "冲突复核任务" in html
    assert "暂停危险输出" in html
    assert "解决后恢复" in html


def test_gt09_page_detects_conflict_locally() -> None:
    html = GT09_PAGE.read_text(encoding="utf-8")

    assert "function timeToMinutes" in html
    assert "function timeOverlap" in html
    assert "function detectEvidenceConflict" in html
    assert "function buildConflictReview" in html
    assert "function determineNextAction" in html
    assert 'values.includes(true) && values.includes(false)' in html
    assert 'return "request_conflict_review"' in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt09_page_exposes_three_candidate_actions() -> None:
    html = GT09_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-source-a"' in html
    assert 'id="btn-source-b"' in html
    assert 'id="btn-review"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt09_page_is_static_and_secret_free() -> None:
    html = GT09_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt08_readme_and_deploy_script_include_gt09() -> None:
    gt08_html = GT08_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt09/"' in gt08_html
    assert "GT09" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt09/" in readme
    assert '"$SOURCE/gt09/index.html"' in script
    assert 'test -f "$TARGET/gt09/index.html"' in script
