"""Provider-neutral GeoTask Runtime Adapter reference implementation."""

from __future__ import annotations

from dataclasses import dataclass

from geotask_core import (
    EXECUTE_NONLOCAL_OPERATION_ID,
    RuntimeArtifact,
    RuntimeDescriptor,
    RuntimeDiagnostic,
    RuntimeInterfaceFormatError,
    RuntimeOperationDescriptor,
    RuntimeRequest,
    RuntimeResponse,
    load_runtime_descriptor,
    validate_artifact_payload,
    validate_runtime_request_contract,
)

from .contracts import (
    ModelAdapterConfig,
    ModelAdapterContractError,
    ProviderDiagnostic,
    StructuredModelInvocation,
    StructuredModelProvider,
    StructuredModelResult,
)


_ALLOWED_MODEL_ASSURANCE = {
    "unverified",
    "model_generated",
    "model_self_checked",
}
_SENSITIVE_METADATA_KEYS = {
    "api_" + "key",
    "access_" + "token",
    "bearer_" + "token",
    "pass" + "word",
    "client_" + "secret",
    "sec" + "ret",
    "credential",
    "credentials",
}


def _runtime_diagnostic(item: ProviderDiagnostic) -> RuntimeDiagnostic:
    return RuntimeDiagnostic(
        code=item.code,
        path=item.path,
        message=item.message,
        severity=item.severity,
        suggested_fix=item.suggested_fix,
    )


def _single_error(
    *,
    code: str,
    path: str,
    message: str,
    suggested_fix: str,
) -> tuple[RuntimeDiagnostic, ...]:
    return (
        RuntimeDiagnostic(
            code=code,
            path=path,
            message=message,
            severity="error",
            suggested_fix=suggested_fix,
        ),
    )


def _sensitive_metadata_path(value: object, path: str = "metadata") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.strip().lower().replace("-", "_")
            item_path = f"{path}.{key}"
            if normalized in _SENSITIVE_METADATA_KEYS:
                return item_path
            nested = _sensitive_metadata_path(item, item_path)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested = _sensitive_metadata_path(item, f"{path}[{index}]")
            if nested is not None:
                return nested
    return None


def _model_input_truthfulness_error(input_payload: dict[str, object]) -> str | None:
    execution = input_payload.get("execution")
    if not isinstance(execution, dict) or execution.get("mode") != "model_only":
        return "model Adapter input execution.mode must be 'model_only'"
    steps = execution.get("steps")
    if not isinstance(steps, list) or not steps:
        return "model Adapter input execution.steps must be a non-empty array"
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or step.get("executor") != "model":
            return f"model Adapter input execution.steps[{index}].executor must be 'model'"
    return None


def _model_output_truthfulness_error(
    input_payload: dict[str, object],
    output_payload: dict[str, object],
) -> str | None:
    input_body = input_payload.get("geotask")
    output_body = output_payload.get("geotask_result")
    if not isinstance(input_body, dict) or not isinstance(output_body, dict):
        return "input and output wrappers must be objects"
    if output_body.get("task_id") != input_body.get("id"):
        return "model output task_id must match the submitted GeoTask document id"
    execution = output_body.get("execution")
    if not isinstance(execution, dict) or execution.get("mode") != "model_only":
        return "model Adapter output execution.mode must be 'model_only'"
    checks = output_body.get("checks")
    if not isinstance(checks, list):
        return "model Adapter output checks must be an array"
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            return f"model Adapter output checks[{index}] must be an object"
        if check.get("executor") != "model":
            return f"model Adapter output checks[{index}].executor must be 'model'"
        if check.get("deterministic") is not False:
            return f"model Adapter output checks[{index}].deterministic must be false"
        if check.get("assurance_level") not in _ALLOWED_MODEL_ASSURANCE:
            return (
                f"model Adapter output checks[{index}].assurance_level must remain "
                "model-scoped or unverified"
            )
        if check.get("status") == "verified":
            return f"model Adapter output checks[{index}].status must not claim verified"
    summary = output_body.get("summary")
    if not isinstance(summary, dict) or summary.get("verified") != 0:
        return "model Adapter output summary.verified must be zero"
    overall = output_body.get("overall")
    if not isinstance(overall, dict):
        return "model Adapter output overall must be an object"
    if overall.get("assurance_level") not in _ALLOWED_MODEL_ASSURANCE:
        return "model Adapter output overall assurance must remain model-scoped or unverified"
    if overall.get("status") == "verified":
        return "model Adapter output overall.status must not claim verified"
    return None


@dataclass(frozen=True)
class ProviderNeutralModelRuntimeAdapter:
    """Map one public Runtime Request to one provider-neutral model invocation.

    The Adapter validates the Runtime contract and input Artifact before invoking
    the provider. It validates the returned output Artifact and model-truthfulness
    claims before returning ``completed``. Provider-native exceptions are not
    exposed as Runtime diagnostics because their execution outcome is unknown.
    """

    provider: StructuredModelProvider
    config: ModelAdapterConfig = ModelAdapterConfig()

    def __post_init__(self) -> None:
        if not isinstance(self.config, ModelAdapterConfig):
            raise TypeError("config must be a ModelAdapterConfig")
        for field_name in (
            "provider_id",
            "external_call",
            "requires_authorization",
            "audit_supported",
        ):
            if not hasattr(self.provider, field_name):
                raise ModelAdapterContractError(
                    f"provider is missing required attribute {field_name!r}"
                )
        if not isinstance(self.provider.provider_id, str) or not self.provider.provider_id.strip():
            raise ModelAdapterContractError("provider_id must be a non-empty string")
        for field_name in (
            "external_call",
            "requires_authorization",
            "audit_supported",
        ):
            if not isinstance(getattr(self.provider, field_name), bool):
                raise ModelAdapterContractError(f"provider.{field_name} must be boolean")
        if self.provider.external_call and not self.provider.audit_supported:
            raise ModelAdapterContractError(
                "external providers must support audit references for executed calls"
            )
        if not callable(getattr(self.provider, "invoke", None)):
            raise ModelAdapterContractError("provider.invoke must be callable")
        self.describe()

    def describe(self) -> RuntimeDescriptor:
        side_effect = "external_read" if self.provider.external_call else "none"
        implementation_kind = "external" if self.provider.external_call else "mock"
        descriptor = RuntimeDescriptor(
            runtime_id=self.config.runtime_id,
            runtime_version=self.config.runtime_version,
            title=self.config.title,
            implementation_kind=implementation_kind,
            production_ready=False,
            capabilities=(
                "provider_neutral_model_adapter",
                "structured_artifact_output",
                f"provider:{self.provider.provider_id.strip()}",
            ),
            operations=(
                RuntimeOperationDescriptor(
                    operation_id=EXECUTE_NONLOCAL_OPERATION_ID,
                    title="Execute a GeoTask document through a structured model provider",
                    description=(
                        "Submit one valid GeoTask document to an independently implemented "
                        "provider and return one strictly validated execution-result Artifact."
                    ),
                    input_artifact_ids=(self.config.input_artifact_id,),
                    accepts_any_registered_artifact=False,
                    min_input_artifacts=1,
                    max_input_artifacts=1,
                    output_artifact_ids=(self.config.output_artifact_id,),
                    side_effect=side_effect,
                    requires_authorization=self.provider.requires_authorization,
                    synchronous=True,
                ),
            ),
            audit_supported=self.provider.audit_supported,
            credentials_managed_externally=True,
            external_side_effects_allowed=self.provider.external_call,
        )
        return load_runtime_descriptor(descriptor.to_dict())

    def _response(
        self,
        request: RuntimeRequest,
        *,
        state: str,
        output_artifacts: tuple[RuntimeArtifact, ...] = (),
        diagnostics: tuple[RuntimeDiagnostic, ...] = (),
        audit_ref: str | None = None,
        side_effects_executed: bool = False,
        retryable: bool = False,
    ) -> RuntimeResponse:
        return RuntimeResponse(
            request_id=request.request_id,
            runtime_id=self.config.runtime_id,
            operation_id=request.operation_id,
            state=state,
            output_artifacts=output_artifacts,
            diagnostics=diagnostics,
            audit_ref=audit_ref,
            side_effects_executed=side_effects_executed,
            retryable=retryable,
            next_poll_after_ms=None,
        )

    def submit(self, request: RuntimeRequest) -> RuntimeResponse:
        if not isinstance(request, RuntimeRequest):
            raise TypeError("request must be a RuntimeRequest")
        descriptor = self.describe()
        try:
            validate_runtime_request_contract(descriptor, request)
        except RuntimeInterfaceFormatError as exc:
            return self._response(
                request,
                state="rejected",
                diagnostics=_single_error(
                    code="model_runtime_request_contract_mismatch",
                    path="runtime_request",
                    message=str(exc),
                    suggested_fix=(
                        "Rebuild the Request from the inspected model Runtime Descriptor "
                        "before submission."
                    ),
                ),
            )

        input_artifact = request.input_artifacts[0]
        input_report = validate_artifact_payload(
            self.config.input_artifact_id,
            input_artifact.payload,
        )
        if not input_report.valid:
            return self._response(
                request,
                state="rejected",
                diagnostics=_single_error(
                    code="invalid_model_input_artifact",
                    path="runtime_request.input_artifacts[0].payload",
                    message=(
                        "The submitted input Artifact did not pass registered GeoTask "
                        "validation; the model provider was not invoked."
                    ),
                    suggested_fix=(
                        f"Validate the input with geotask artifact validate "
                        f"{self.config.input_artifact_id} before submission."
                    ),
                ),
            )
        input_payload = dict(input_artifact.payload)
        input_truthfulness_error = _model_input_truthfulness_error(input_payload)
        if input_truthfulness_error is not None:
            return self._response(
                request,
                state="rejected",
                diagnostics=_single_error(
                    code="unsupported_model_input_execution",
                    path="runtime_request.input_artifacts[0].payload.execution",
                    message=input_truthfulness_error,
                    suggested_fix=(
                        "Use a model_only document whose execution steps explicitly use "
                        "executor=model, or route the document to another Runtime operation."
                    ),
                ),
            )
        sensitive_path = _sensitive_metadata_path(dict(request.metadata))
        if sensitive_path is not None:
            return self._response(
                request,
                state="rejected",
                diagnostics=_single_error(
                    code="credential_bearing_model_metadata",
                    path=f"runtime_request.{sensitive_path}",
                    message=(
                        "Runtime Request metadata contains a credential-like key; the "
                        "model provider was not invoked."
                    ),
                    suggested_fix=(
                        "Remove credentials from metadata and use only an opaque "
                        "authorization_ref resolved outside Core."
                    ),
                ),
            )

        invocation = StructuredModelInvocation(
            request_id=request.request_id,
            model_ref=self.config.model_ref,
            input_artifact_id=input_artifact.artifact_id,
            input_payload=input_artifact.payload,
            expected_output_artifact_id=self.config.output_artifact_id,
            authorization_ref=request.authorization_ref,
            idempotency_key=request.idempotency_key,
            metadata=request.metadata,
        )
        try:
            result = self.provider.invoke(invocation)
        except Exception:
            raise ModelAdapterContractError(
                "model provider failed without returning a structured result"
            ) from None
        if not isinstance(result, StructuredModelResult):
            raise ModelAdapterContractError(
                "model provider must return StructuredModelResult"
            )
        if result.external_call_executed and not self.provider.external_call:
            raise ModelAdapterContractError(
                "a non-external provider cannot claim an external call executed"
            )
        if result.audit_ref is not None and not self.provider.audit_supported:
            raise ModelAdapterContractError(
                "provider returned audit_ref but declared audit_supported=false"
            )

        diagnostics = tuple(_runtime_diagnostic(item) for item in result.diagnostics)
        if result.state != "completed":
            return self._response(
                request,
                state=result.state,
                diagnostics=diagnostics,
                audit_ref=result.audit_ref,
                side_effects_executed=result.external_call_executed,
                retryable=result.retryable,
            )

        assert result.output_payload is not None
        output_payload = dict(result.output_payload)
        output_report = validate_artifact_payload(
            self.config.output_artifact_id,
            output_payload,
        )
        if not output_report.valid:
            return self._response(
                request,
                state="failed",
                diagnostics=_single_error(
                    code="invalid_model_output_artifact",
                    path="provider_result.output_payload",
                    message=(
                        "The provider returned an output that did not pass registered "
                        "GeoTask Artifact validation."
                    ),
                    suggested_fix=(
                        "Make the provider return the exact registered output Artifact "
                        "schema declared by the Runtime Descriptor."
                    ),
                ),
                audit_ref=result.audit_ref,
                side_effects_executed=result.external_call_executed,
                retryable=False,
            )
        truthfulness_error = _model_output_truthfulness_error(
            dict(input_artifact.payload),
            output_payload,
        )
        if truthfulness_error is not None:
            return self._response(
                request,
                state="failed",
                diagnostics=_single_error(
                    code="untruthful_model_output_claim",
                    path="provider_result.output_payload.geotask_result",
                    message=truthfulness_error,
                    suggested_fix=(
                        "Return model_only, model-executed, non-deterministic, "
                        "model-scoped output and leave verification to Core or another verifier."
                    ),
                ),
                audit_ref=result.audit_ref,
                side_effects_executed=result.external_call_executed,
                retryable=False,
            )
        return self._response(
            request,
            state="completed",
            output_artifacts=(
                RuntimeArtifact(
                    artifact_id=self.config.output_artifact_id,
                    payload=output_payload,
                ),
            ),
            diagnostics=diagnostics,
            audit_ref=result.audit_ref,
            side_effects_executed=result.external_call_executed,
            retryable=False,
        )


__all__ = ["ProviderNeutralModelRuntimeAdapter"]
