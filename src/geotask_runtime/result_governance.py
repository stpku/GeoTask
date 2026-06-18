"""GeoTask Runtime Result Governance v0.1 — MOCK/SKELETON.

THIS IS A MOCK IMPLEMENTATION for future development.
Uses existing Core normalizer and verifier for deterministic governance.
A real implementation would add provenance tracking, audit trails,
confidence scoring, and multi-model consensus.

Status hierarchy (production):
  invalid_operator > invalid_reference > contradicted > need_review > verified

Planned / future statuses (not yet active):
  model_inferred — model produced a value without operator verification
  need_data — verification requires external data not yet available
"""

from typing import Protocol

from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
    STATUS_INVALID_OPERATOR,
    STATUS_INVALID_REFERENCE,
    compute_overall_status,
)
from geotask_core.normalizer import normalize_model_output
from geotask_core.verifier import verify_normalized_result

from geotask_runtime.contracts import (
    GovernedTaskResult,
    ModelResponse,
    RuntimeEvent,
    TaskRequest,
    TaskStatus,
    VerificationPlan,
)


_TASK_STATUS_TO_CORE = {
    TaskStatus.VERIFIED: STATUS_VERIFIED,
    TaskStatus.CONTRADICTED: STATUS_CONTRADICTED,
    TaskStatus.NEED_REVIEW: STATUS_NEED_REVIEW,
    TaskStatus.INVALID_OPERATOR: STATUS_INVALID_OPERATOR,
    TaskStatus.INVALID_REFERENCE: STATUS_INVALID_REFERENCE,
}

_CORE_TO_TASK_STATUS = {v: k for k, v in _TASK_STATUS_TO_CORE.items()}


class ResultGovernor(Protocol):
    """Contract for result governors.

    A ResultGovernor takes model output through normalization, verification,
    and status adjudication to produce a GovernedTaskResult.
    """

    def govern(
        self,
        request: TaskRequest,
        response: ModelResponse,
        verification_plan: VerificationPlan,
        geotask_data: dict,
    ) -> GovernedTaskResult:
        """Govern a model response through normalization and verification."""
        ...


class DeterministicResultGovernor:
    """MOCK deterministic result governor.

    Delegates to Core normalizer and verifier. Produces GovernedTaskResult
    with statuses derived from the Core status hierarchy.

    This is a mock. A real implementation would add:
      - Provenance and audit trail recording
      - Multi-model consensus checks
      - Confidence scoring and threshold gates
      - Domain-specific status overrides
    """

    def govern(
        self,
        request: TaskRequest,
        response: ModelResponse,
        verification_plan: VerificationPlan,
        geotask_data: dict,
    ) -> GovernedTaskResult:
        events: list[RuntimeEvent] = []

        events.append(RuntimeEvent(
            event_type="normalize_start",
            detail={"raw_text_length": len(response.raw_text)},
        ))

        # Pass geotask_data to normalizer so it can enrich measurements
        # with expected values from deterministic operators
        normalized = normalize_model_output(response.raw_text, geotask_data=geotask_data)

        events.append(RuntimeEvent(
            event_type="normalize_complete",
            detail={
                "measurement_count": len(normalized.get("measurements", [])),
            },
        ))

        events.append(RuntimeEvent(
            event_type="verify_start",
            detail={"verifiable_claims": verification_plan.verifiable_claims},
        ))

        verified = verify_normalized_result(normalized, geotask_data)

        events.append(RuntimeEvent(
            event_type="verify_complete",
            detail={
                "overall_status": verified.get("conclusion", {}).get(
                    "overall_status", STATUS_NEED_REVIEW
                ),
            },
        ))

        core_status = verified.get("conclusion", {}).get(
            "overall_status", STATUS_NEED_REVIEW
        )
        review_reasons = list(
            verified.get("conclusion", {}).get("review_reasons", [])
        )

        # If verifier found no issues but we expected more measurements,
        # add unverified_claim markers (lenient: claims are question text,
        # not measurement names, so we flag gaps rather than exact matches)
        measurements = verified.get("measurements", [])
        if verification_plan.verifiable_claims and not measurements:
            review_reasons.append("no_measurements_found")
            if core_status == STATUS_VERIFIED:
                core_status = STATUS_NEED_REVIEW

        return GovernedTaskResult(
            task_id=request.task_id,
            normalized_result=normalized,
            verification_result=verified,
            overall_status=core_status,
            review_reasons=review_reasons,
            runtime_events=events,
        )
