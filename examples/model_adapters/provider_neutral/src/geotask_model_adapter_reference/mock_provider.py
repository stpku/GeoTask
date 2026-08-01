"""Deterministic no-network model provider used by the public Adapter skeleton."""

from __future__ import annotations

from collections.abc import Mapping

from .contracts import StructuredModelInvocation, StructuredModelResult


class MockStructuredModelProvider:
    """Return one preconfigured structured result without an external model call."""

    provider_id = "geotask.mock.structured-model"
    external_call = False
    requires_authorization = False
    audit_supported = False

    def __init__(self, result: StructuredModelResult):
        if not isinstance(result, StructuredModelResult):
            raise TypeError("result must be a StructuredModelResult")
        self._result = result
        self.invocations: list[StructuredModelInvocation] = []

    @classmethod
    def completed(
        cls,
        output_payload: Mapping[str, object],
    ) -> "MockStructuredModelProvider":
        return cls(StructuredModelResult.completed(output_payload))

    def invoke(self, invocation: StructuredModelInvocation) -> StructuredModelResult:
        if not isinstance(invocation, StructuredModelInvocation):
            raise TypeError("invocation must be a StructuredModelInvocation")
        self.invocations.append(invocation)
        return self._result


__all__ = ["MockStructuredModelProvider"]
