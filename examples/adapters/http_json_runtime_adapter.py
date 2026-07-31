"""Public-safe HTTP JSON transport adapter for the GeoTask Runtime Interface.

This example intentionally lives outside ``geotask_core``. It demonstrates how a
caller can bind the public RuntimeAdapter Protocol to an independently hosted
Runtime without adding networking, credentials, model calls, or production
actions to Core.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from geotask_core import (
    RuntimeAdapter,
    RuntimeDescriptor,
    RuntimeRequest,
    RuntimeResponse,
    load_runtime_response,
)


ADAPTER_ID: Final = "geotask.example.http-json-adapter"
ADAPTER_VERSION: Final = "0.1"
_DEFAULT_TIMEOUT_SECONDS: Final = 10.0
_DEFAULT_MAX_RESPONSE_BYTES: Final = 1024 * 1024


class RuntimeTransportError(RuntimeError):
    """Raised when an HTTP exchange cannot yield a Runtime Response Artifact."""


class _RejectRedirects(HTTPRedirectHandler):
    """Prevent Runtime requests from being replayed to an uninspected endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _validate_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("endpoint must be a non-empty HTTP or HTTPS URL")
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("endpoint scheme must be http or https")
    if not parsed.hostname:
        raise ValueError("endpoint must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("endpoint must not embed credentials")
    if parsed.fragment:
        raise ValueError("endpoint must not contain a fragment")
    return endpoint


def _validate_positive_finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive finite number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return normalized


def _validate_positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _is_json_content_type(value: str | None) -> bool:
    if value is None:
        return False
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


@dataclass(frozen=True)
class HttpJsonRuntimeAdapter(RuntimeAdapter):
    """Bind one inspected Runtime Descriptor to one HTTP JSON endpoint.

    ``describe()`` is deliberately offline: it returns the descriptor supplied by
    the caller and never contacts the endpoint. ``submit()`` performs exactly one
    HTTP POST and strictly loads the returned Runtime Response Artifact. The
    caller should use ``submit_runtime_request()`` so Core also performs the
    Descriptor/Request/Response three-way contract validation.

    The reference adapter has no credential or retry API. Production adapters
    should add authentication, policy, observability, and retry behavior outside
    ``geotask_core`` without changing the public message contracts.
    """

    descriptor: RuntimeDescriptor
    endpoint: str
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, RuntimeDescriptor):
            raise TypeError("descriptor must be a RuntimeDescriptor")
        object.__setattr__(self, "endpoint", _validate_endpoint(self.endpoint))
        object.__setattr__(
            self,
            "timeout_seconds",
            _validate_positive_finite_number(
                self.timeout_seconds,
                "timeout_seconds",
            ),
        )
        object.__setattr__(
            self,
            "max_response_bytes",
            _validate_positive_integer(
                self.max_response_bytes,
                "max_response_bytes",
            ),
        )

    def describe(self) -> RuntimeDescriptor:
        """Return the caller-inspected descriptor without network activity."""

        return self.descriptor

    def submit(self, request: RuntimeRequest) -> RuntimeResponse:
        """POST one Runtime Request and strictly load one Runtime Response."""

        if not isinstance(request, RuntimeRequest):
            raise TypeError("request must be a RuntimeRequest")
        try:
            request_bytes = json.dumps(
                request.to_dict(),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise RuntimeTransportError(
                f"Runtime Request could not be serialized as strict JSON: {exc}"
            ) from exc

        http_request = Request(
            self.endpoint,
            data=request_bytes,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"{ADAPTER_ID}/{ADAPTER_VERSION}",
            },
        )
        opener = build_opener(_RejectRedirects())
        try:
            with opener.open(http_request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", response.getcode())
                content_type = response.headers.get("Content-Type")
                response_bytes = response.read(self.max_response_bytes + 1)
        except HTTPError as exc:
            raise RuntimeTransportError(
                f"Runtime endpoint returned HTTP {exc.code}; transport failures must "
                "not be reinterpreted as Runtime Response states"
            ) from exc
        except URLError as exc:
            raise RuntimeTransportError(
                f"Runtime endpoint could not be reached: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeTransportError("Runtime endpoint timed out") from exc
        except OSError as exc:
            raise RuntimeTransportError(f"Runtime transport failed: {exc}") from exc

        if not 200 <= int(status) <= 299:
            raise RuntimeTransportError(
                f"Runtime endpoint returned HTTP {status}; expected a 2xx transport status"
            )
        if not _is_json_content_type(content_type):
            raise RuntimeTransportError(
                "Runtime endpoint must return application/json or a +json media type"
            )
        if len(response_bytes) > self.max_response_bytes:
            raise RuntimeTransportError(
                "Runtime Response exceeded max_response_bytes before validation"
            )
        try:
            response_text = response_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeTransportError(
                "Runtime Response must be UTF-8 encoded JSON"
            ) from exc
        try:
            payload = json.loads(response_text, parse_constant=_reject_nonfinite_json)
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeTransportError(
                f"Runtime endpoint returned invalid strict JSON: {exc}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise RuntimeTransportError("Runtime Response JSON root must be an object")
        return load_runtime_response(payload)


__all__ = [
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "RuntimeTransportError",
    "HttpJsonRuntimeAdapter",
]
