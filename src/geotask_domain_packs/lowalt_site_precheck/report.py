"""Report builder for LowAlt Site Precheck results."""

from .models import LowAltPrecheckResult


def build_lowalt_precheck_report(result: LowAltPrecheckResult) -> dict:
    """Build a structured report from a LowAltPrecheckResult."""
    return {
        "domain_pack": result.domain_pack,
        "version": result.version,
        "request_id": result.request_id,
        "overall_status": result.overall_status,
        "risk_items": result.risk_items,
        "verified_items": result.verified_items,
        "contradicted_items": result.contradicted_items,
        "review_items": result.review_items,
        "planned_data_gaps": result.planned_data_gaps,
        "planned_model_inferred_items": result.planned_model_inferred_items,
        "summary": result.summary,
        "disclaimer": result.disclaimer,
    }
