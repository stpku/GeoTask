"""v1.0 Output contract enforcement.

Validates that execution results satisfy the output contract defined
in the CanonicalDocument (required fields, additional fields policy,
numeric precision, ordering constraints).
"""

from __future__ import annotations

from geotask_core.v1.enums import (
    AssuranceLevel,
    ClaimStatus,
    ExecutionStatus,
)
from geotask_core.v1.ir import CanonicalDocument
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.assurance import _is_success


def _enforce_output_contract(
    result: GeotaskResult, doc: CanonicalDocument
) -> None:
    """Populate ``result.outputs`` and validate against ``doc.output_contract``.

    Violations are recorded in ``result.errors``.  If ``allow_additional_fields``
    is ``False``, only fields listed in ``required_fields`` may appear in
    outputs.  ``numeric_precision.decimal_places`` is applied to float values.
    ``ordering.by`` must reference a field in ``required_fields`` and
    ``ordering.direction`` must be ``"ascending"`` or ``"descending"``.
    """
    oc = doc.output_contract

    # ── Populate outputs from successful checks ───────────────────────────
    for check in result.checks:
        if _is_success(check.status):
            result.outputs[check.assertion_id] = check.value

    required = set(oc.required_fields)
    present = set(result.outputs.keys())

    # ── Required fields must exist ────────────────────────────────────────
    missing = required - present
    if missing:
        for field in sorted(missing):
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Required field '{field}' not found in outputs."
                    ),
                    "path": "output_contract.required_fields",
                }
            )

    # ── Additional fields check ───────────────────────────────────────────
    if not oc.allow_additional_fields:
        extra = present - required
        if extra:
            for field in sorted(extra):
                result.errors.append(
                    {
                        "code": "output_contract_violation",
                        "message": (
                            f"Additional field '{field}' not allowed "
                            f"(allow_additional_fields=false)."
                        ),
                        "path": "output_contract.allow_additional_fields",
                    }
                )

    # ── Apply numeric precision ───────────────────────────────────────────
    np_dict = oc.numeric_precision
    if isinstance(np_dict, dict):
        dp = np_dict.get("decimal_places")
        if dp is not None and isinstance(dp, int) and not isinstance(dp, bool) and dp >= 0:
            for key, val in result.outputs.items():
                if isinstance(val, float):
                    result.outputs[key] = round(val, dp)

    # ── Validate ordering ─────────────────────────────────────────────────
    ordering = oc.ordering
    if isinstance(ordering, dict) and ordering:
        by_field = ordering.get("by", "")
        direction = ordering.get("direction", "")
        if by_field and by_field not in required:
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Ordering 'by' field '{by_field}' not in "
                        f"required_fields."
                    ),
                    "path": "output_contract.ordering.by",
                }
            )
        if direction and direction not in ("ascending", "descending"):
            result.errors.append(
                {
                    "code": "output_contract_violation",
                    "message": (
                        f"Ordering direction must be 'ascending' or "
                        f"'descending', got '{direction}'."
                    ),
                    "path": "output_contract.ordering.direction",
                }
            )

    # ── Adjust execution status and overall on contract violation ─────────
    if result.errors:
        current = result.execution.status
        if current == ExecutionStatus.completed.value:
            result.execution.status = ExecutionStatus.partial.value
        result.overall.status = ClaimStatus.invalid_input.value
        result.overall.assurance_level = AssuranceLevel.unverified.name
