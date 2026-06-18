"""Metrics computation for GeoTask Encoding Benchmark v0.1.

Computes per-case and aggregate metrics comparing three encoding formats:
  - natural_language
  - geotask_yaml
  - compact_dsl
"""

import sys
from pathlib import Path

# Ensure geotask_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
)


def compute_case_metrics(
    case: dict,
    encoding_type: str,
    input_text: str,
    model_output_text: str,
    geotask_result: dict,
    all_token_costs: dict[str, dict[str, int]],
) -> dict:
    """Compute metrics for a single benchmark case.

    Args:
        case: Case definition dict from cases.yaml.
        encoding_type: One of 'natural_language', 'geotask_yaml', 'compact_dsl'.
        input_text: The input prompt text for this encoding.
        model_output_text: The simulated model output text.
        geotask_result: The normalized + verified GeoTask Result dict.
        all_token_costs: Dict mapping encoding_type -> total_tokens for this case
                         (used to compute token_efficiency_score).

    Returns:
        Dict of metrics for this case.
    """
    from benchmarks.encoding_v0_1.token_counter import estimate_tokens

    case_id = case["case_id"]
    expected = case.get("expected", {})

    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(model_output_text)
    total_tokens = input_tokens + output_tokens

    # Store for later token_efficiency computation
    all_token_costs.setdefault(case_id, {})[encoding_type] = total_tokens

    # Normalization success
    measurements = geotask_result.get("measurements", [])
    conclusion = geotask_result.get("conclusion", {})
    normalized_success = len(measurements) >= 2  # we expect at least distance + intersection

    # Overall status
    overall_status = conclusion.get("overall_status", STATUS_NEED_REVIEW)
    expected_overall_status = expected.get("expected_overall_status", "verified")

    # Status match
    status_matched = (overall_status == expected_overall_status)

    # Verification counts
    verified_count = sum(1 for m in measurements if m.get("status") == STATUS_VERIFIED)
    contradicted_count = sum(1 for m in measurements if m.get("status") == STATUS_CONTRADICTED)
    need_review_count = sum(1 for m in measurements if m.get("status") == STATUS_NEED_REVIEW)

    # Review reasons
    review_reasons = conclusion.get("review_reasons", [])

    # Verification success rate
    total_meas = len(measurements)
    verification_success_rate = verified_count / total_meas if total_meas > 0 else 0.0

    # Token efficiency: min tokens across encodings for this case / current tokens
    # Will be recomputed after all encodings are processed
    token_efficiency_score = 1.0  # placeholder

    # Benchmark score (0–100)
    benchmark_score = _compute_benchmark_score(
        status_matched=status_matched,
        normalized_success=normalized_success,
        verification_success_rate=verification_success_rate,
        token_efficiency_score=token_efficiency_score,
    )

    return {
        "case_id": case_id,
        "encoding_type": encoding_type,
        "input_token_estimate": input_tokens,
        "output_token_estimate": output_tokens,
        "total_token_estimate": total_tokens,
        "normalized_success": normalized_success,
        "overall_status": overall_status,
        "expected_overall_status": expected_overall_status,
        "status_matched": status_matched,
        "measurements_count": total_meas,
        "verified_count": verified_count,
        "contradicted_count": contradicted_count,
        "need_review_count": need_review_count,
        "review_reasons": review_reasons,
        "benchmark_score": benchmark_score,
    }


def finalize_token_efficiency(rows: list[dict]) -> list[dict]:
    """Recompute benchmark_score with actual token_efficiency_score.

    Must be called after all encodings for a case have been processed.
    """
    # Group rows by case_id
    case_groups: dict[str, list[dict]] = {}
    for row in rows:
        case_groups.setdefault(row["case_id"], []).append(row)

    for case_id, case_rows in case_groups.items():
        # Find min total_token for this case
        min_tokens = min(r["total_token_estimate"] for r in case_rows)

        for row in case_rows:
            if min_tokens > 0:
                token_efficiency = min_tokens / row["total_token_estimate"]
            else:
                token_efficiency = 1.0

            row["token_efficiency_score"] = round(token_efficiency, 3)
            row["benchmark_score"] = _compute_benchmark_score(
                status_matched=row["status_matched"],
                normalized_success=row["normalized_success"],
                verification_success_rate=(
                    row["verified_count"] / row["measurements_count"]
                    if row["measurements_count"] > 0
                    else 0.0
                ),
                token_efficiency_score=token_efficiency,
            )

    return rows


def aggregate_metrics(rows: list[dict]) -> dict:
    """Compute aggregate metrics across all cases, grouped by encoding_type.

    Args:
        rows: List of per-case metric dicts.

    Returns:
        Dict with per-encoding and overall aggregates.
    """
    encodings = ["natural_language", "geotask_yaml", "compact_dsl"]

    result = {"by_encoding": {}, "overall": {}}

    for enc in encodings:
        enc_rows = [r for r in rows if r["encoding_type"] == enc]
        if not enc_rows:
            continue

        n = len(enc_rows)
        result["by_encoding"][enc] = {
            "case_count": n,
            "avg_input_tokens": round(sum(r["input_token_estimate"] for r in enc_rows) / n, 1),
            "avg_output_tokens": round(sum(r["output_token_estimate"] for r in enc_rows) / n, 1),
            "avg_total_tokens": round(sum(r["total_token_estimate"] for r in enc_rows) / n, 1),
            "normalization_success_rate": round(
                sum(1 for r in enc_rows if r["normalized_success"]) / n, 2
            ),
            "status_match_rate": round(
                sum(1 for r in enc_rows if r["status_matched"]) / n, 2
            ),
            "avg_verified_count": round(sum(r["verified_count"] for r in enc_rows) / n, 2),
            "avg_contradicted_count": round(sum(r["contradicted_count"] for r in enc_rows) / n, 2),
            "avg_need_review_count": round(sum(r["need_review_count"] for r in enc_rows) / n, 2),
            "avg_benchmark_score": round(sum(r["benchmark_score"] for r in enc_rows) / n, 1),
            "avg_token_efficiency": round(
                sum(r.get("token_efficiency_score", 0) for r in enc_rows) / n, 3
            ),
        }

    # Overall
    all_n = len(rows)
    result["overall"] = {
        "total_cases": all_n,
        "total_encoding_types": len(encodings),
        "avg_benchmark_score": round(sum(r["benchmark_score"] for r in rows) / all_n, 1),
    }

    return result


def _compute_benchmark_score(
    status_matched: bool,
    normalized_success: bool,
    verification_success_rate: float,
    token_efficiency_score: float,
) -> float:
    """Compute benchmark score (0–100).

    Components:
      - 40 points: status_matched
      - 20 points: normalized_success
      - 20 points: verification_success_rate (scaled)
      - 20 points: token_efficiency_score (scaled)
    """
    score = 0.0
    if status_matched:
        score += 40.0
    if normalized_success:
        score += 20.0
    score += 20.0 * verification_success_rate
    score += 20.0 * token_efficiency_score
    return round(score, 1)
