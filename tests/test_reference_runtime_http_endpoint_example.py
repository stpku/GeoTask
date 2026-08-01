"""End-to-end tests for the public-safe reference Runtime HTTP endpoint."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from geotask_core import (
    EXECUTE_ACTION_OPERATION_ID,
    REFERENCE_RUNTIME_ID,
    VALIDATE_ARTIFACT_OPERATION_ID,
    reference_runtime_descriptor,
    submit_runtime_request,
)


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT_PATH = ROOT / "examples" / "endpoints" / "reference_runtime_http_server.py"
ADAPTER_PATH = ROOT / "examples" / "adapters" / "http_json_runtime_adapter.py"
REQUEST_PATH = ROOT / "examples" / "core" / "runtime_validate_artifact_request.json"


def _load_example_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ENDPOINT_MODULE = _load_example_module(
    "geotask_reference_runtime_http_endpoint_example",
    ENDPOINT_PATH,
)
ADAPTER_MODULE = _load_example_module(
    "geotask_http_json_runtime_adapter_endpoint_test",
    ADAPTER_PATH,
)

build_reference_runtime_server = ENDPOINT_MODULE.build_reference_runtime_server
HttpJsonRuntimeAdapter = ADAPTER_MODULE.HttpJsonRuntimeAdapter


def _request_payload() -> dict[str, object]:
    return json.loads(REQUEST_PATH.read_text(encoding="utf-8"))


@contextmanager
def _reference_endpoint(
    *,
    max_request_bytes: int = 1024 * 1024,
) -> Iterator[tuple[str, object]]:
    server = build_reference_runtime_server(
        host="127.0.0.1",
        port=0,
        max_request_bytes=max_request_bytes,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/runtime", server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _http_exchange(
    url: str,
    *,
    method: str = "POST",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    request = Request(
        url,
        data=body,
        method=method,
        headers=headers or {},
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def test_reference_endpoint_and_http_adapter_complete_valid_exchange() -> None:
    with _reference_endpoint() as (endpoint, server):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )

        response = submit_runtime_request(adapter, _request_payload())

        assert response.state == "completed"
        assert response.runtime_id == REFERENCE_RUNTIME_ID
        assert response.operation_id == VALIDATE_ARTIFACT_OPERATION_ID
        assert response.side_effects_executed is False
        assert [item.artifact_id for item in response.output_artifacts] == [
            "geotask.artifact-validation-report"
        ]
        assert server.runtime_request_count == 1


def test_reference_endpoint_returns_structured_rejection_for_valid_but_unsupported_request() -> None:
    payload = _request_payload()
    payload["runtime_request"]["operation_id"] = EXECUTE_ACTION_OPERATION_ID

    with _reference_endpoint() as (endpoint, server):
        adapter = HttpJsonRuntimeAdapter(
            descriptor=reference_runtime_descriptor(),
            endpoint=endpoint,
        )

        response = submit_runtime_request(adapter, payload)

        assert response.state == "rejected"
        assert response.output_artifacts == ()
        assert response.side_effects_executed is False
        assert response.diagnostics[0].code == "unsupported_runtime_operation"
        assert server.runtime_request_count == 1


def test_reference_endpoint_uses_problem_json_for_malformed_transport_payloads() -> None:
    with _reference_endpoint() as (endpoint, server):
        status, headers, body = _http_exchange(
            endpoint,
            body=b'{"runtime_request": NaN}',
            headers={"Content-Type": "application/json"},
        )
        problem = json.loads(body.decode("utf-8"))

        assert status == 400
        assert headers["Content-Type"].startswith("application/problem+json")
        assert problem["title"] == "Invalid Runtime Request JSON"
        assert problem["status"] == 400
        assert problem["service_id"] == ENDPOINT_MODULE.SERVICE_ID
        assert "NaN" not in problem["detail"]
        assert server.runtime_request_count == 0

        status, _headers, body = _http_exchange(
            endpoint,
            body=b'{"runtime_request": {}, "runtime_request": {}}',
            headers={"Content-Type": "application/json"},
        )
        problem = json.loads(body.decode("utf-8"))
        assert status == 400
        assert problem["title"] == "Invalid Runtime Request JSON"
        assert server.runtime_request_count == 0

        status, _headers, body = _http_exchange(
            endpoint,
            body=b'{"runtime_request": {}}',
            headers={"Content-Type": "application/json"},
        )
        problem = json.loads(body.decode("utf-8"))
        assert status == 400
        assert problem["title"] == "Invalid Runtime Request Artifact"
        assert server.runtime_request_count == 0


def test_reference_endpoint_rejects_wrong_media_credentials_and_oversize() -> None:
    body = json.dumps(_request_payload()).encode("utf-8")

    with _reference_endpoint() as (endpoint, server):
        status, _headers, problem_body = _http_exchange(
            endpoint,
            body=body,
            headers={"Content-Type": "text/plain"},
        )
        assert status == 415
        assert json.loads(problem_body)["title"] == "Unsupported Media Type"

        status, _headers, problem_body = _http_exchange(
            endpoint,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer do-not-log-this-secret",
            },
        )
        assert status == 400
        problem_text = problem_body.decode("utf-8")
        assert json.loads(problem_text)["title"] == "Credential Headers Not Accepted"
        assert "do-not-log-this-secret" not in problem_text
        assert server.runtime_request_count == 0

    with _reference_endpoint(max_request_bytes=8) as (endpoint, server):
        status, _headers, problem_body = _http_exchange(
            endpoint,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        assert status == 413
        assert json.loads(problem_body)["title"] == "Runtime Request Too Large"
        assert server.runtime_request_count == 0


def test_reference_endpoint_rejects_wrong_method_and_path() -> None:
    with _reference_endpoint() as (endpoint, server):
        status, headers, body = _http_exchange(endpoint, method="GET")
        assert status == 405
        assert headers["Allow"] == "POST"
        assert json.loads(body)["title"] == "Method Not Allowed"

        wrong_path = endpoint.removesuffix("/runtime") + "/descriptor"
        status, _headers, body = _http_exchange(
            wrong_path,
            body=json.dumps(_request_payload()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        assert status == 404
        assert json.loads(body)["title"] == "Not Found"
        assert server.runtime_request_count == 0


def test_reference_endpoint_response_headers_are_non_cacheable_and_do_not_expose_python() -> None:
    with _reference_endpoint() as (endpoint, _server):
        status, headers, body = _http_exchange(
            endpoint,
            body=json.dumps(_request_payload()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        assert status == 200
        assert json.loads(body)["runtime_response"]["state"] == "completed"
        assert headers["Cache-Control"] == "no-store"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "GeoTaskReferenceRuntime/0.1" in headers["Server"]
        assert "Python" not in headers["Server"]


def test_reference_endpoint_hides_unexpected_internal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_without_leaking(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("sensitive internal failure detail")

    monkeypatch.setattr(
        ENDPOINT_MODULE,
        "submit_runtime_request",
        fail_without_leaking,
    )
    with _reference_endpoint() as (endpoint, server):
        status, headers, body = _http_exchange(
            endpoint,
            body=json.dumps(_request_payload()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        problem_text = body.decode("utf-8")

        assert status == 500
        assert headers["Content-Type"].startswith("application/problem+json")
        assert json.loads(problem_text)["title"] == "Reference Runtime Failure"
        assert "sensitive internal failure detail" not in problem_text
        assert server.runtime_request_count == 0


def test_reference_endpoint_cli_rejects_remote_binding_without_traceback() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")

    help_result = subprocess.run(
        [sys.executable, str(ENDPOINT_PATH), "--help"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "loopback" in help_result.stdout

    invalid_result = subprocess.run(
        [sys.executable, str(ENDPOINT_PATH), "--host", "0.0.0.0"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert invalid_result.returncode == 2
    assert "may bind only" in invalid_result.stderr
    assert "Traceback" not in invalid_result.stderr


def test_reference_endpoint_is_loopback_only_and_excludes_noncore_implementation() -> None:
    with pytest.raises(ValueError, match="may bind only"):
        build_reference_runtime_server(host="0.0.0.0", port=0)
    with pytest.raises(ValueError, match="may bind only"):
        build_reference_runtime_server(host="example.test", port=0)
    with pytest.raises(ValueError, match="positive integer"):
        build_reference_runtime_server(
            host="127.0.0.1",
            port=0,
            max_request_bytes=True,
        )

    text = ENDPOINT_PATH.read_text(encoding="utf-8")
    assert "from geotask_runtime" not in text
    assert "import geotask_runtime" not in text
    assert "geotask_domain_packs" not in text
    assert "model_router" not in text
    assert "connector_credentials" not in text
    assert "FailClosedMockRuntime" in text
