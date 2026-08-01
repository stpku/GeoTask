"""Compatibility re-exports for opaque OpenAI client resolution.

The public provider package never resolves or stores a raw credential. Private
startup code constructs an authenticated official SDK client and binds it to an
opaque Runtime authorization reference through ``StaticOpenAIClientResolver``.
"""

from .client import (
    OpenAIClientResolutionError,
    OpenAIClientResolver,
    StaticOpenAIClientResolver,
)

__all__ = [
    "OpenAIClientResolutionError",
    "OpenAIClientResolver",
    "StaticOpenAIClientResolver",
]
