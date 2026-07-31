"""Structural guard for the split private OpenAI live-smoke test suite."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_SUITE = ROOT / "tests" / "private_openai_live_smoke"
EXPECTED_FILES = {
    "conftest.py",
    "test_boundaries.py",
    "test_closure_verify.py",
    "test_closure_write.py",
    "test_evidence.py",
    "test_readiness.py",
    "test_sdk_transport.py",
}
EXPECTED_TESTS = {
    "test_readiness_is_read_only_and_can_reach_ready_state",
    "test_readiness_reports_all_blockers_without_claiming_ticket",
    "test_readiness_rejects_expired_or_claimed_ticket",
    "test_cli_readiness_is_read_only",
    "test_verified_evidence_bundle_closes_gate_and_emits_hashes",
    "test_evidence_mismatch_or_unknown_audit_cannot_close_gate",
    "test_evidence_rechecks_pinned_model_and_hard_limits",
    "test_evidence_inside_repository_or_path_collision_is_rejected",
    "test_cli_evidence_verification_is_read_only",
    "test_verified_evidence_can_be_recorded_as_write_once_closure",
    "test_invalid_evidence_or_unsafe_output_cannot_record_closure",
    "test_post_publish_permission_failure_rolls_back_new_closure",
    "test_cli_write_closure_records_once_without_exposing_paths",
    "test_closure_verification_reanchors_digest_and_source_evidence",
    "test_closure_verification_rejects_wrong_or_malformed_digest",
    "test_rehashed_closure_tampering_still_fails_evidence_and_time_binding",
    "test_closure_verification_rejects_non_strict_json",
    "test_closure_verification_detects_changed_source_evidence",
    "test_closure_verification_detects_midflight_source_evidence_change",
    "test_closure_verification_rejects_repository_path_or_open_permissions",
    "test_cli_verify_closure_is_read_only_and_path_redacted",
    "test_official_sdk_mock_transport_serializes_one_strict_response_call",
    "test_private_live_smoke_assets_are_excluded_from_public_export",
}


def test_private_live_smoke_suite_is_split_by_responsibility() -> None:
    actual_files = {path.name for path in PRIVATE_SUITE.glob("*.py")}
    assert actual_files == EXPECTED_FILES
    assert all(
        len((PRIVATE_SUITE / name).read_text(encoding="utf-8").splitlines()) < 500
        for name in EXPECTED_FILES
    )

    actual_tests: set[str] = set()
    for path in PRIVATE_SUITE.glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        actual_tests.update(
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
    assert actual_tests == EXPECTED_TESTS
