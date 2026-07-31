"""Official SDK serialization test using an offline mock transport."""

from __future__ import annotations

import json
import sys

import pytest


def test_official_sdk_mock_transport_serializes_one_strict_response_call(
    live_smoke,
) -> None:
    openai = pytest.importorskip("openai", minversion="2.46.0")
    httpx = pytest.importorskip("httpx")

    neutral_src = live_smoke.root / "examples/model_adapters/provider_neutral/src"
    openai_src = live_smoke.root / "examples/model_adapters/openai_responses/src"
    for package_src in (neutral_src, openai_src):
        if str(package_src) not in sys.path:
            sys.path.insert(0, str(package_src))

    from geotask_core import submit_runtime_request
    from geotask_openai_responses_adapter import (
        OPENAI_AUTHORIZATION_REF,
        OpenAIResponsesConfig,
        StaticOpenAIClientResolver,
        build_openai_responses_runtime_adapter,
    )

    request_payload = json.loads(
        (
            live_smoke.root
            / "examples/model_adapters/openai_responses/examples/"
            "openai_runtime_request.json"
        ).read_text(encoding="utf-8")
    )
    output_payload = json.loads(
        (
            live_smoke.root
            / "examples/model_adapters/provider_neutral/examples/"
            "mock_model_execution_result.json"
        ).read_text(encoding="utf-8")
    )
    envelope = json.dumps(
        {
            "artifact_json": json.dumps(
                output_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        },
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    captured: dict[str, object] = {}

    def handler(request: object):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"x-request-id": "req_sdk_mock_001"},
            json={
                "id": "resp_sdk_mock_001",
                "object": "response",
                "created_at": 1785488400,
                "status": "completed",
                "model": "gpt-4.1-mini-2025-04-14",
                "output": [
                    {
                        "id": "msg_sdk_mock_001",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": envelope,
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = openai.OpenAI(
        api_key="[REDACTED_SECRET]",
        max_retries=0,
        timeout=60.0,
        http_client=http_client,
    )
    try:
        adapter = build_openai_responses_runtime_adapter(
            OpenAIResponsesConfig(
                model="gpt-4.1-mini-2025-04-14",
                max_output_tokens=2048,
            ),
            StaticOpenAIClientResolver(OPENAI_AUTHORIZATION_REF, client),
        )
        response = submit_runtime_request(adapter, request_payload)
    finally:
        client.close()

    assert response.state == "completed"
    assert response.side_effects_executed is True
    assert response.audit_ref == (
        "openai://responses/req_sdk_mock_001/resp_sdk_mock_001"
    )
    assert [item.artifact_id for item in response.output_artifacts] == [
        "geotask.execution-result"
    ]
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    body = captured["body"]
    assert body["model"] == "gpt-4.1-mini-2025-04-14"
    assert body["store"] is False
    assert body["truncation"] == "disabled"
    assert body["max_output_tokens"] == 2048
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "tools" not in body
    assert client.max_retries == 0
