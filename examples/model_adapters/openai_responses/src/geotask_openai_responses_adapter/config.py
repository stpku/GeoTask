"""Configuration contracts for the GeoTask OpenAI Responses provider."""

from __future__ import annotations

import re
from dataclasses import dataclass


OPENAI_RESPONSES_ADAPTER_VERSION = "0.1.0"
OPENAI_RUNTIME_ID = "geotask.openai.responses"
OPENAI_RUNTIME_VERSION = "0.1"
OPENAI_AUTHORIZATION_REF = "env://OPENAI_API_KEY"

_PINNED_MODEL_PATTERN = re.compile(r"^.+-\d{4}-\d{2}-\d{2}$")


class OpenAIProviderConfigurationError(ValueError):
    """Raised when public provider configuration is unsafe or incomplete."""


def _non_empty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenAIProviderConfigurationError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class OpenAIResponsesConfig:
    """Non-secret configuration for one synchronous Responses API provider."""

    model: str
    instructions: str = (
        "Return exactly one JSON object matching the supplied response schema. "
        "Its artifact_json field must contain a complete serialized "
        "geotask.execution-result/1.0 object for the submitted GeoTask document. "
        "The result is model-generated: use execution.mode=model_only, "
        "executor=model, deterministic=false, summary.verified=0, and do not "
        "claim verified, local_deterministic, independent verification, or human review."
    )
    max_output_tokens: int = 4096
    timeout_seconds: float = 60.0
    require_pinned_model: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "model", _non_empty(self.model, "model"))
        object.__setattr__(
            self,
            "instructions",
            _non_empty(self.instructions, "instructions"),
        )
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens <= 0
        ):
            raise OpenAIProviderConfigurationError(
                "max_output_tokens must be a positive integer"
            )
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise OpenAIProviderConfigurationError(
                "timeout_seconds must be a positive number"
            )
        if not isinstance(self.require_pinned_model, bool):
            raise OpenAIProviderConfigurationError(
                "require_pinned_model must be boolean"
            )
        if self.require_pinned_model and not _PINNED_MODEL_PATTERN.fullmatch(self.model):
            raise OpenAIProviderConfigurationError(
                "model must be a pinned snapshot ending in YYYY-MM-DD; set "
                "require_pinned_model=false only after an explicit compatibility decision"
            )
        lowered = self.model.lower()
        markers = ("api_" + "key=", "to" + "ken=", "pass" + "word=")
        if any(marker in lowered for marker in markers):
            raise OpenAIProviderConfigurationError(
                "model must not contain embedded credentials"
            )


__all__ = [
    "OPENAI_RESPONSES_ADAPTER_VERSION",
    "OPENAI_RUNTIME_ID",
    "OPENAI_RUNTIME_VERSION",
    "OPENAI_AUTHORIZATION_REF",
    "OpenAIProviderConfigurationError",
    "OpenAIResponsesConfig",
]
