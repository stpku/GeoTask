"""Public-safe HTTP endpoint for the GeoTask fail-closed reference Runtime.

This example is an independently hosted transport service, not part of
``geotask_core`` and not a production Runtime. It accepts one strict Runtime
Request JSON document, dispatches only to ``FailClosedMockRuntime``, and returns
one validated Runtime Response JSON document.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final

from geotask_core import (
    FailClosedMockRuntime,
    RuntimeInterfaceFormatError,
    submit_runtime_request,
)


SERVICE_ID: Final = "geotask.example.reference-http-endpoint"
SERVICE_VERSION: Final = "0.1"
DEFAULT_HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8765
DEFAULT_MAX_REQUEST_BYTES: Final = 1024 * 1024
_RUNTIME_PATH: Final = "/runtime"
_CREDENTIAL_HEADERS: Final = (
    "Authorization",
    "Proxy-Authorization",
    "Cookie",
    "X-API-Key",
)


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in pairs:
        if key in normalized:
            raise ValueError(f"duplicate JSON object key {key!r} is not allowed")
        normalized[key] = value
    return normalized


def _validate_loopback_host(host: object) -> str:
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host must be a non-empty loopback hostname or address")
    normalized = host.strip().lower()
    if normalized not in {"127.0.0.1", "localhost"}:
        raise ValueError(
            "the public reference endpoint may bind only to 127.0.0.1 or localhost"
        )
    return host.strip()


def _validate_port(port: object) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    return port


def _validate_positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _problem_payload(status: int, title: str, detail: str) -> dict[str, object]:
    return {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "service_id": SERVICE_ID,
        "service_version": SERVICE_VERSION,
    }


class ReferenceRuntimeHttpServer(ThreadingHTTPServer):
    """Loopback-only HTTP server carrying the public fail-closed Runtime."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
    ) -> None:
        host, port = server_address
        self.max_request_bytes = _validate_positive_integer(
            max_request_bytes,
            "max_request_bytes",
        )
        self.runtime_request_count = 0
        super().__init__(
            (_validate_loopback_host(host), _validate_port(port)),
            ReferenceRuntimeRequestHandler,
        )


class ReferenceRuntimeRequestHandler(BaseHTTPRequestHandler):
    """Strict transport envelope for one Runtime Request per HTTP POST."""

    protocol_version = "HTTP/1.1"
    server_version = f"GeoTaskReferenceRuntime/{SERVICE_VERSION}"
    sys_version = ""

    @property
    def runtime_server(self) -> ReferenceRuntimeHttpServer:
        server = self.server
        if not isinstance(server, ReferenceRuntimeHttpServer):
            raise TypeError("handler requires ReferenceRuntimeHttpServer")
        return server

    def log_message(self, format: str, *args: object) -> None:
        """Suppress request-line logging so Runtime metadata is not echoed."""

        return None

    def _send_json(
        self,
        status: int,
        payload: Mapping[str, object],
        *,
        content_type: str,
        extra_headers: Mapping[str, str] | None = None,
        send_body: bool = True,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        if extra_headers is not None:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()
        if send_body:
            self.wfile.write(body)
        self.close_connection = True

    def _send_problem(self, status: int, title: str, detail: str) -> None:
        self._send_json(
            status,
            _problem_payload(status, title, detail),
            content_type="application/problem+json",
        )

    def _method_not_allowed(self, *, send_body: bool = True) -> None:
        self._send_json(
            405,
            _problem_payload(
                405,
                "Method Not Allowed",
                "The reference Runtime endpoint accepts only POST /runtime.",
            ),
            content_type="application/problem+json",
            extra_headers={"Allow": "POST"},
            send_body=send_body,
        )

    def do_GET(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_HEAD(self) -> None:  # noqa: N802
        self._method_not_allowed(send_body=False)

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != _RUNTIME_PATH:
            self._send_problem(
                404,
                "Not Found",
                "The reference Runtime endpoint is available only at /runtime.",
            )
            return

        if self.headers.get("Transfer-Encoding") is not None:
            self._send_problem(
                400,
                "Unsupported Transfer Encoding",
                "Use a fixed Content-Length; chunked Runtime Requests are not accepted.",
            )
            return

        credential_headers = [
            name for name in _CREDENTIAL_HEADERS if self.headers.get(name) is not None
        ]
        if credential_headers:
            self._send_problem(
                400,
                "Credential Headers Not Accepted",
                "The public reference endpoint does not accept credential-bearing headers.",
            )
            return

        content_type = self.headers.get("Content-Type")
        media_type = "" if content_type is None else content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json" and not media_type.endswith("+json"):
            self._send_problem(
                415,
                "Unsupported Media Type",
                "Runtime Requests must use application/json or a +json media type.",
            )
            return

        content_length_value = self.headers.get("Content-Length")
        if content_length_value is None:
            self._send_problem(
                411,
                "Length Required",
                "Runtime Requests require an explicit Content-Length.",
            )
            return
        try:
            content_length = int(content_length_value)
        except ValueError:
            self._send_problem(
                400,
                "Invalid Content Length",
                "Content-Length must be a decimal integer.",
            )
            return
        if content_length <= 0:
            self._send_problem(
                400,
                "Empty Runtime Request",
                "Runtime Request bodies must not be empty.",
            )
            return
        if content_length > self.runtime_server.max_request_bytes:
            self._send_problem(
                413,
                "Runtime Request Too Large",
                "Runtime Request exceeded the configured request-size limit.",
            )
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self._send_problem(
                400,
                "Incomplete Runtime Request",
                "The received body length did not match Content-Length.",
            )
            return
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            self._send_problem(
                400,
                "Invalid Runtime Request Encoding",
                "Runtime Requests must be UTF-8 encoded JSON.",
            )
            return
        try:
            payload = json.loads(
                text,
                parse_constant=_reject_nonfinite_json,
                object_pairs_hook=_reject_duplicate_object_keys,
            )
        except (json.JSONDecodeError, ValueError):
            self._send_problem(
                400,
                "Invalid Runtime Request JSON",
                "The body must contain one strict JSON document with no non-finite numbers.",
            )
            return
        if not isinstance(payload, Mapping):
            self._send_problem(
                400,
                "Invalid Runtime Request Root",
                "Runtime Request JSON must have an object root.",
            )
            return

        try:
            response = submit_runtime_request(FailClosedMockRuntime(), payload)
        except (RuntimeInterfaceFormatError, TypeError, ValueError):
            self._send_problem(
                400,
                "Invalid Runtime Request Artifact",
                "The JSON document does not satisfy the Runtime Request v0.1 contract.",
            )
            return
        except Exception:
            self._send_problem(
                500,
                "Reference Runtime Failure",
                "The reference Runtime could not process the valid Request Artifact.",
            )
            return

        self.runtime_server.runtime_request_count += 1
        self._send_json(
            200,
            response.to_dict(),
            content_type="application/json",
        )


def build_reference_runtime_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
) -> ReferenceRuntimeHttpServer:
    """Build a loopback-only server without starting its request loop."""

    return ReferenceRuntimeHttpServer(
        (host, port),
        max_request_bytes=max_request_bytes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the public fail-closed GeoTask Runtime endpoint on a loopback address. "
            "The service performs read-only Artifact validation only."
        )
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=DEFAULT_MAX_REQUEST_BYTES,
    )
    args = parser.parse_args(argv)

    try:
        server = build_reference_runtime_server(
            host=args.host,
            port=args.port,
            max_request_bytes=args.max_request_bytes,
        )
    except ValueError as exc:
        parser.error(str(exc))
    host, port = server.server_address
    print(
        f"{SERVICE_ID}/{SERVICE_VERSION} listening on http://{host}:{port}{_RUNTIME_PATH}",
        flush=True,
    )
    print(
        "Reference service only: no credentials, model calls, external evidence, or actions.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SERVICE_ID",
    "SERVICE_VERSION",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_MAX_REQUEST_BYTES",
    "ReferenceRuntimeHttpServer",
    "ReferenceRuntimeRequestHandler",
    "build_reference_runtime_server",
    "main",
]
