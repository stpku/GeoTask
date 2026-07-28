from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT04_PAGE = ROOT / "site" / "gt04" / "index.html"
GT05_PAGE = ROOT / "site" / "gt05" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt05_page_contains_temporal_conflict_task() -> None:
    html = GT05_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt05-space-overlap-time-separation"',
        'type: "time_interval"',
        'start_time: "08:00"',
        'end_time: "09:00"',
        'start_time: "15:00"',
        'end_time: "17:00"',
        'operator: "time_overlap"',
        'object_refs: ["flight_time", "restricted_time"]',
        'temporal_conflict = false',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt05_page_visualizes_space_and_time_dimensions() -> None:
    html = GT05_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "位置重叠" in html
    assert "高度重叠" in html
    assert "时间错开" in html
    assert "08:00–09:00" in html or "08:00-09:00" in html
    assert "15:00–17:00" in html or "15:00-17:00" in html
    assert "相隔 6 小时" in html


def test_gt05_page_runs_local_time_overlap() -> None:
    html = GT05_PAGE.read_text(encoding="utf-8")

    assert "function timeToMinutes" in html
    assert "function timeOverlap" in html
    assert "aStart <= bEnd && bStart <= aEnd" in html
    assert "const localDeterministic = timeOverlap" in html
    assert "verified" in html
    assert "contradicted" in html
    assert "model_generated" in html
    assert "local_deterministic" in html


def test_gt05_page_exposes_copy_and_boolean_verification() -> None:
    html = GT05_PAGE.read_text(encoding="utf-8")

    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert 'id="btn-true"' in html
    assert 'id="btn-false"' in html
    assert 'id="verify"' in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt05_page_is_static_and_secret_free() -> None:
    html = GT05_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html
    assert '<script src=' not in html


def test_gt04_readme_and_deploy_script_include_gt05() -> None:
    gt04_html = GT04_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt05/"' in gt04_html
    assert "GT05" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt05/" in readme
