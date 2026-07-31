"""Tests for the public-safe external HTTP Runtime Adapter example."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator

import pytest

from geotask_core import (
    FailClosedMockRuntime,
    RuntimeAdapter,
    RuntimeInterfaceFormatError,
    load_runtime_request,
    reference_runtime_descriptor,
    submit_runtime_request,
)


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "examples" / "adapters" / "http_json_runtime_adapter.py"
REQUEST_PATH = ROOT / "examples" / "core" / "runtime_validate_artifact_request.json"


def _load_adapter_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "geotask_http_json_runtime_adapter_example",
        ADAPTER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER_MODULE = _load_adapter_module()
HttpJsonRuntimeAdapter = ADAPTER_MODULE.HttpJsonRuntimeAdapter
RuntimeTransportError = ADAPTER_MODULE.RuntimeTransportError


def _request_payload() -> dict[str, object]:
    return json.loads(REQUEST_PATH.read_text(encoding="utf-8"))


def _valid_response(body: bytes) -> tuple[int, str, bytes]:
    payload = json.loads(body.decode("utf-8"))
    request = load_runtime_request(payload)
    response = FailClosedMockRuntime().submit(request).to_dict()
    return 200, "application/json; charset=utf-8", json.dumps(response).encode("utf-8")


@contextmanager
def _runtime_server(
    responder: Callable[[bytes], tuple[int, str, bytes]],
) -> Iterator[tuple[str, dict[str, object]]]:
    state: dict[str, object] = {
        "calls": 0,
        "bodies": [],
        "headers": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            state["calls"] = int(state["calls"]) + 1
            state["bodies"].append(body)
            state["headers"].append(dict(self.headers.items()))
            status, content_type, response_body = responder(body)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if status in {301, 302, 303, 307, 308}:
                self.send_header("Location", self.path)
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, format: str, *args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/runtime", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_adapter_is_external_protocol_implementation_with_offline_describe() -> None:
    with _runtime_server(_valid_response) as (endpoint, state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )

        assert isinstance(adapter, RuntimeAdapter)
        assert adapter.describe().runtime_id == "geotask.reference.fail-closed"
        assert state["calls"] == 0


def test_http_adapter_submits_one_json_request_and_core_validates_exchange() -> None:
    with _runtime_server(_valid_response) as (endpoint, state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )
        payload = _request_payload()

        response = submit_runtime_request(adapter, payload)

        assert response.state == "completed"
        assert response.side_effects_executed is False
        assert [item.artifact_id for item in response.output_artifacts] == [
            "geotask.artifact-validation-report"
        ]
        assert state["calls"] == 1
        submitted = json.loads(state["bodies"][0].decode("utf-8"))
        assert submitted == payload
        headers = {key.lower(): value for key, value in state["headers"][0].items()}
        assert headers["accept"] == "application/json"
        assert headers["content-type"] == "application/json; charset=utf-8"
        assert "authorization" not in headers


def test_http_adapter_does_not_hide_malicious_runtime_response() -> None:
    def malicious(body: bytes) -> tuple[int, str, bytes]:
        request = load_runtime_request(json.loads(body.decode("utf-8")))
        response = FailClosedMockRuntime().submit(request).to_dict()
        response["runtime_response"]["output_artifacts"] = []
        return 200, "application/json", json.dumps(response).encode("utf-8")

    with _runtime_server(malicious) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )

        with pytest.raises(RuntimeInterfaceFormatError, match="exactly match"):
            submit_runtime_request(adapter, _request_payload())


def test_http_adapter_keeps_transport_failure_separate_from_runtime_state() -> None:
    def unavailable(_body: bytes) -> tuple[int, str, bytes]:
        return 503, "application/json", b'{"runtime_response": {}}'

    with _runtime_server(unavailable) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )

        with pytest.raises(RuntimeTransportError, match="HTTP 503"):
            adapter.submit(load_runtime_request(_request_payload()))


def test_http_adapter_rejects_redirects_nonfinite_and_duplicate_json() -> None:
    def redirect(_body: bytes) -> tuple[int, str, bytes]:
        return 307, "application/json", b"{}"

    with _runtime_server(redirect) as (endpoint, state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )
        with pytest.raises(RuntimeTransportError, match="HTTP 307"):
            adapter.submit(load_runtime_request(_request_payload()))
        assert state["calls"] == 1

    def nonfinite(_body: bytes) -> tuple[int, str, bytes]:
        return 200, "application/json", b'{"runtime_response": NaN}'

    with _runtime_server(nonfinite) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )
        with pytest.raises(RuntimeTransportError, match="non-finite JSON"):
            adapter.submit(load_runtime_request(_request_payload()))

    def duplicate(_body: bytes) -> tuple[int, str, bytes]:
        return 200, "application/json", b'{"runtime_response": {}, "runtime_response": {}}'

    with _runtime_server(duplicate) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )
        with pytest.raises(RuntimeTransportError, match="duplicate JSON object key"):
            adapter.submit(load_runtime_request(_request_payload()))


def test_http_adapter_rejects_non_json_and_oversized_responses() -> None:
    def plain_text(_body: bytes) -> tuple[int, str, bytes]:
        return 200, "text/plain", b"not-json"

    with _runtime_server(plain_text) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )
        with pytest.raises(RuntimeTransportError, match="application/json"):
            adapter.submit(load_runtime_request(_request_payload()))

    def oversized(_body: bytes) -> tuple[int, str, bytes]:
        return 200, "application/json", b"{}" * 20

    with _runtime_server(oversized) as (endpoint, _state):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
            max_response_bytes=8,
        )
        with pytest.raises(RuntimeTransportError, match="max_response_bytes"):
            adapter.submit(load_runtime_request(_request_payload()))


def test_http_adapter_rejects_credential_bearing_or_non_http_endpoints() -> None:
    descriptor = reference_runtime_descriptor()

    with pytest.raises(ValueError, match="scheme must be http or https"):
        HttpJsonRuntimeAdapter(descriptor=descriptor, endpoint="file:///tmp/runtime")
    with pytest.raises(ValueError, match="must not embed credentials"):
        HttpJsonRuntimeAdapter(
            descriptor=descriptor,
            endpoint="https://user:secret@example.test/runtime",
        )
    with pytest.raises(ValueError, match="positive finite"):
        HttpJsonRuntimeAdapter(
            descriptor=descriptor,
            endpoint="https://example.test/runtime",
            timeout_seconds=float("inf"),
        )
    with pytest.raises(ValueError, match="positive integer"):
        HttpJsonRuntimeAdapter(
            descriptor=descriptor,
            endpoint="https://example.test/runtime",
            max_response_bytes=True,
        )
