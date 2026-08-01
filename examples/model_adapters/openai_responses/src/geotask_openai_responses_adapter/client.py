"""Authenticated OpenAI client resolution kept outside GeoTask Core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class OpenAIClientResolutionError(ValueError):
    """Raised when an opaque authorization reference cannot resolve a client."""


@runtime_checkable
class OpenAIClientResolver(Protocol):
    """Resolve an already authenticated official SDK client by opaque reference."""

    def resolve(self, authorization_ref: str) -> object:
        """Return a client exposing ``responses.create`` without exposing secrets."""


@dataclass(frozen=True)
class StaticOpenAIClientResolver:
    """Bind one opaque reference to one externally constructed client object."""

    authorization_ref: str
    client: object

    def __post_init__(self) -> None:
        if not isinstance(self.authorization_ref, str) or not self.authorization_ref.strip():
            raise OpenAIClientResolutionError(
                "authorization_ref must be a non-empty string"
            )
        responses = getattr(self.client, "responses", None)
        if not callable(getattr(responses, "create", None)):
            raise OpenAIClientResolutionError(
                "client must expose responses.create"
            )

    def resolve(self, authorization_ref: str) -> object:
        if authorization_ref != self.authorization_ref:
            raise OpenAIClientResolutionError(
                "authorization_ref is not accepted by this client resolver"
            )
        return self.client


__all__ = [
    "OpenAIClientResolutionError",
    "OpenAIClientResolver",
    "StaticOpenAIClientResolver",
]
