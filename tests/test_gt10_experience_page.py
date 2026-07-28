from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT09_PAGE = ROOT / "site" / "gt09" / "index.html"
GT10_PAGE = ROOT / "site" / "gt10" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt10_page_contains_robot_corridor_task_and_policy() -> None:
    html = GT10_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt10-robot-corridor-coordination"',
        'scenario: "warehouse_robot_single_capacity_corridor"',
        'resource_capacity: 1',
        'mission: "urgent_outbound_order"',
        'mission: "empty_return"',
        'task_priority: 90',
        'task_priority: 40',
        'priority_rule: "higher_task_priority_first"',
        'clearance_buffer_minutes: 1',
        'selected_action: "robot_b_wait"',
        'revised_entry_time: "08:36"',
        'wait_duration_minutes: 4',
        'next_action: "coordinate_passage"',
        'expected_status: "coordinated"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt10_page_visualizes_route_time_and_capacity_conflict() -> None:
    html = GT10_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "机器人 A" in html
    assert "机器人 B" in html
    assert "紧急出库" in html
    assert "空载返程" in html
    assert "单向窄通道" in html
    assert "容量 = 1" in html
    assert "08:30–08:35" in html
    assert "08:32–08:37" in html
    assert "B 等待至 08:36" in html


def test_gt10_page_calculates_coordination_locally() -> None:
    html = GT10_PAGE.read_text(encoding="utf-8")

    assert "function pointInRect" in html
    assert "function lineIntersectsRect" in html
    assert "function timeToMinutes" in html
    assert "function timeOverlap" in html
    assert "function detectCorridorConflict" in html
    assert "function selectYieldAction" in html
    assert "function buildCoordinationPlan" in html
    assert 'return "robot_b_wait"' in html
    assert "clearanceBufferMinutes" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt10_page_exposes_three_candidate_actions() -> None:
    html = GT10_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-a-wait"' in html
    assert 'id="btn-b-wait"' in html
    assert 'id="btn-replan"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt10_page_is_static_and_secret_free() -> None:
    html = GT10_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt09_readme_and_deploy_script_include_gt10() -> None:
    gt09_html = GT09_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt10/"' in gt09_html
    assert "GT10" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt10/" in readme
