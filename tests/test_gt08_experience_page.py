from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT07_PAGE = ROOT / "site" / "gt07" / "index.html"
GT08_PAGE = ROOT / "site" / "gt08" / "index.html"
README = ROOT / "site" / "README.md"
DEPLOY_SCRIPT = ROOT / "site" / "deploy-nginx.sh"


def test_gt08_page_contains_evidence_request_plan() -> None:
    html = GT08_PAGE.read_text(encoding="utf-8")

    required_fragments = (
        'id: "gt08-evidence-request-plan"',
        'id: "verify-restricted-schedule"',
        'trigger: "temporal_conflict"',
        'reason: "restricted_schedule_not_verified"',
        'next_action: "request_evidence"',
        'resume_when: "restricted_schedule_verified == true"',
        '"issuing_authority"',
        '"effective_date"',
        '"document_version"',
        '"source_reference"',
        '"verified_at"',
        '"full_conflict"',
        '"automatic_approval"',
    )
    for fragment in required_fragments:
        assert fragment in html


def test_gt08_page_visualizes_unknown_to_action_flow() -> None:
    html = GT08_PAGE.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "发现 unknown" in html
    assert "定位证据缺口" in html
    assert "生成补证据任务" in html
    assert "暂停危险输出" in html
    assert "证据补齐后恢复" in html
    assert "request_evidence" in html


def test_gt08_page_generates_request_from_local_status() -> None:
    html = GT08_PAGE.read_text(encoding="utf-8")

    assert "function evaluateEvidenceCondition" in html
    assert "function buildEvidenceRequest" in html
    assert "function determineNextAction" in html
    assert 'conditionStatus === "unverifiable"' in html
    assert 'return "request_evidence"' in html
    assert "blocked_outputs" in html
    assert "required_fields" in html
    assert "local_deterministic" in html
    assert "model_generated" in html


def test_gt08_page_exposes_three_candidate_actions() -> None:
    html = GT08_PAGE.read_text(encoding="utf-8")

    assert 'id="btn-true"' in html
    assert 'id="btn-false"' in html
    assert 'id="btn-request"' in html
    assert 'id="verify"' in html
    assert 'id="copy-open"' in html
    assert 'id="copy-only"' in html
    assert "verified" in html
    assert "contradicted" in html
    assert "https://chat.deepseek.com/" in html
    assert "navigator.clipboard.writeText" in html
    assert 'document.execCommand("copy")' in html


def test_gt08_page_is_static_and_secret_free() -> None:
    html = GT08_PAGE.read_text(encoding="utf-8").lower()

    assert "fetch(" not in html
    assert "xmlhttprequest" not in html
    assert "api_key" not in html
    assert "authorization:" not in html
    assert "analytics" not in html
    assert "cookie" not in html


def test_gt07_readme_and_deploy_script_include_gt08() -> None:
    gt07_html = GT07_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'href="../gt08/"' in gt07_html
    assert "GT08" in readme
    assert "https://skyswind.tailf4fad8.ts.net/geotask/gt08/" in readme
