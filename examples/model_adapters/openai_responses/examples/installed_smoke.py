"""Offline installed-wheel smoke test for the GeoTask OpenAI Adapter stack.

Run this script with a Python environment where the GeoTask Core,
provider-neutral Adapter, and OpenAI Responses Adapter wheels are installed.
It uses an SDK-shaped fake client and never performs a network request.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from geotask_core import submit_runtime_request
from geotask_openai_responses_adapter import (
    OPENAI_AUTHORIZATION_REF,
    OpenAIResponsesConfig,
    StaticOpenAIClientResolver,
    build_openai_responses_runtime_adapter,
)


class _FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        return SimpleNamespace(
            status="completed",
            output_text=self.output_text,
            id="resp_installed_smoke",
            _request_id="req_installed_smoke",
        )


class _FakeClient:
    def __init__(self, output_text: str):
        self.responses = _FakeResponses(output_text)
        self.option_calls: list[dict[str, object]] = []

    def with_options(self, **kwargs: object) -> "_FakeClient":
        self.option_calls.append(dict(kwargs))
        return self


def _repository_root(value: str | None) -> Path:
    if value is not None:
        return Path(value).resolve()
    return Path(__file__).resolve().parents[4]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the installed GeoTask OpenAI Adapter stack without a live call."
    )
    parser.add_argument("--repository-root")
    args = parser.parse_args(argv)
    root = _repository_root(args.repository_root)

    request_payload = json.loads(
        (
            root
            / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
        ).read_text(encoding="utf-8")
    )
    output_payload = json.loads(
        (
            root
            / "examples/model_adapters/provider_neutral/examples/mock_model_execution_result.json"
        ).read_text(encoding="utf-8")
    )
    output_text = json.dumps(
        {
            "artifact_json": json.dumps(
                output_payload,
                ensure_ascii=False,
                allow_nan=False,
            )
        },
        ensure_ascii=False,
        allow_nan=False,
    )

    client = _FakeClient(output_text)
    adapter = build_openai_responses_runtime_adapter(
        OpenAIResponsesConfig(model="gpt-test-2026-07-01"),
        StaticOpenAIClientResolver(OPENAI_AUTHORIZATION_REF, client),
    )
    response = submit_runtime_request(adapter, request_payload)

    if response.state != "completed":
        raise RuntimeError(f"installed smoke returned {response.state!r}")
    if response.audit_ref != (
        "openai://responses/req_installed_smoke/resp_installed_smoke"
    ):
        raise RuntimeError("installed smoke audit reference mismatch")
    if len(client.responses.calls) != 1:
        raise RuntimeError("installed smoke must perform exactly one fake call")
    if client.responses.calls[0].get("store") is not False:
        raise RuntimeError("installed smoke expected store=false")
    if client.option_calls != [{"max_retries": 0, "timeout": 60.0}]:
        raise RuntimeError("installed smoke expected no-retry client options")

    print(
        json.dumps(
            {
                "installed_smoke": {
                    "valid": True,
                    "runtime_state": response.state,
                    "side_effects_executed": response.side_effects_executed,
                    "audit_ref": response.audit_ref,
                    "provider_calls": len(client.responses.calls),
                    "live_request_executed": False,
                }
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
