"""GeoTask Core CLI.

Usage:
    geotask validate <file.yaml>
    geotask run <file.yaml> [--format yaml|v1-json] [--output <file>|-]
    geotask result validate <execution-result.json> [--format text|json]
    geotask artifact validate <artifact-id> <file> [--format text|json]
    geotask schema export <artifact-id> [--output <file>|-] [--compact]
    geotask schema verify [artifact-id] [--format text|json]
    geotask normalize <file.txt> [--geotask <file.yaml>]
    geotask eval <file.yaml> <model_output.txt>
    geotask control evaluate <file.yaml> --result <result.json> [--state <state.yaml>]
    geotask control validate <control-evaluation.json> [--format text|json]
    geotask agent inspect [--format text|json]
    geotask agent prepare <generated.yaml> [--format text|json]
    geotask agent retry <blocked-report.json> <revised.yaml> [--format text|json]
    geotask agent recover <task.yaml> --evidence <state.yaml> [--format text|json]
    geotask runtime inspect [runtime-descriptor.json] [--profile] [--format text|json]
    geotask runtime check <runtime-descriptor.json> <runtime-request.json> [--format text|json]
    geotask runtime mock <runtime-request.json> [--format text|json]
    python -m geotask_core.cli validate <file.yaml>
    python -m geotask_core.cli run <file.yaml>
    python -m geotask_core.cli normalize <file.txt> [--geotask <file.yaml>]
    python -m geotask_core.cli eval <file.yaml> <model_output.txt>

The old `stir` CLI command is deprecated but still works as an alias.
"""

import sys
import json
from collections.abc import Mapping
from pathlib import Path

import yaml

from geotask_core._version import __version__
from geotask_core.parser import (
    _UniqueKeyLoader,
    load_geotask,
    validate_document,
)
from geotask_core.runner import run_geotask
from geotask_core.normalizer import normalize_model_output
from geotask_core.evaluator import evaluate_model_output
from geotask_core.operator_registry import (
    get_operator_metadata,
    list_operator_metadata,
)
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.control_evaluation import (
    ControlContextError,
    evaluate_control_profile,
)
from geotask_core.v1.result import GeotaskResult, ResultFormatError
from geotask_core.v1.serialized_validation import (
    CONTROL_EVALUATION_VALIDATION_CONTRACT,
    EXECUTION_RESULT_VALIDATION_CONTRACT,
    VersionedPayloadContract,
    invalid_versioned_payload_report,
    validate_versioned_payload,
)
from geotask_core.v1.artifact_registry import artifact_registry_payload
from geotask_core.v1.schema_bundle import (
    load_artifact_schema,
    verify_schema_bundle,
)
from geotask_core.v1.artifact_validation import validate_artifact_file
from geotask_core.v1.agent_integration import (
    AgentIntegrationError,
    agent_integration_profile_payload,
    recover_evidence_request,
)
from geotask_core.v1.agent_generation import (
    AgentGenerationError,
    prepare_generated_document,
    retry_generated_document,
)
from geotask_core.v1.runtime_interface import (
    FailClosedMockRuntime,
    RuntimeInterfaceFormatError,
    load_runtime_descriptor,
    load_runtime_request,
    reference_runtime_descriptor,
    runtime_interface_profile_payload,
    submit_runtime_request,
    validate_runtime_request_contract,
)


def _get_command_name() -> str:
    """Detect which command name was used (geotask or deprecated stir)."""
    return Path(sys.argv[0]).stem


def cmd_validate(path: str):
    """Validate a GeoTask YAML file."""
    print(f"[validate] {path}")
    data = load_geotask(path)
    diagnostics = validate_document(data)
    if data.get("_deprecated_stir_field"):
        print("  Warning: Using deprecated 'stir' top-level field. Please migrate to 'geotask'.", file=sys.stderr)
    errors = [d for d in diagnostics if d.get("severity", "error") == "error"]
    warnings_only = [d for d in diagnostics if d.get("severity") == "warning"]
    if warnings_only:
        _print_validation_diagnostics(warnings_only, prefix="  ", label="Warnings")
    if errors:
        _print_validation_diagnostics(errors, prefix="  ")
        sys.exit(1)
    if not diagnostics:
        print("  Validation OK")
    return data


def _print_run_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask run <geotask.yaml> "
        "[--format yaml|v1-json] [--output <file>|-] [--compact]",
        file=out,
    )
    print(
        "Default format is compatibility YAML. v1-json emits the canonical "
        "GeotaskResult.to_dict() shape for control evaluation.",
        file=out,
    )


def _parse_run_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "format": "yaml",
        "output_path": None,
        "compact": False,
    }
    seen_value_flags: set[str] = set()
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_run_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in ("--format", "--output"):
            if arg in seen_value_flags:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a value")
            seen_value_flags.add(arg)
            target = "format" if arg == "--format" else "output_path"
            parsed[target] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown run option: {arg}")

    output_format = str(parsed["format"])
    if output_format not in {"yaml", "v1-json"}:
        raise ValueError(
            f"unsupported_run_format: {output_format}. Supported formats: yaml, v1-json"
        )
    if parsed["compact"] and output_format != "v1-json":
        raise ValueError("--compact is supported only with --format v1-json")
    return parsed


def _write_or_print_output(
    rendered: str,
    *,
    output_path: object,
    input_paths: list[Path],
) -> None:
    if output_path is None or output_path == "-":
        sys.stdout.write(rendered)
        return

    resolved_output = Path(str(output_path)).resolve()
    if resolved_output in [path.resolve() for path in input_paths]:
        raise ValueError("--output must not overwrite an input file")
    try:
        resolved_output.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"cannot write output file {str(output_path)!r}: {exc}"
        ) from exc


def cmd_run(path: str, args: list[str] | None = None):
    """Run a GeoTask document in compatibility YAML or canonical v1 JSON."""
    if path in ("--help", "-h"):
        _print_run_usage()
        return None

    try:
        parsed = _parse_run_args(list(args or []))
        if parsed.get("help"):
            return None

        data = load_geotask(path)
        diagnostics = validate_document(data)
        if data.get("_deprecated_stir_field"):
            print(
                "Warning: Using deprecated 'stir' top-level field. "
                "Please migrate to 'geotask'.",
                file=sys.stderr,
            )
        errors = [
            d for d in diagnostics if d.get("severity", "error") == "error"
        ]
        warnings_only = [d for d in diagnostics if d.get("severity") == "warning"]
        if warnings_only:
            _print_validation_diagnostics(
                warnings_only,
                label="Warnings",
                stream=sys.stderr,
            )
        if errors:
            _print_validation_diagnostics(errors, stream=sys.stderr)
            sys.exit(1)

        output_format = str(parsed["format"])
        if output_format == "v1-json":
            result = execute_canonical(canonicalize(data))
            rendered = _render_json(
                result.to_dict(),
                compact=bool(parsed["compact"]),
            )
        else:
            result = run_geotask(data)
            rendered = yaml.dump(
                result,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
            if not rendered.endswith("\n"):
                rendered += "\n"

        if output_format == "yaml" and parsed["output_path"] is None:
            print(f"[run] {path}")
        _write_or_print_output(
            rendered,
            output_path=parsed["output_path"],
            input_paths=[Path(path)],
        )
        return result
    except SystemExit:
        raise
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"run_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _print_result_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask result validate <execution-result.json> "
        "[--format text|json]",
        file=out,
    )
    print(
        "Validates the canonical geotask_result v1.0 payload without "
        "executing a GeoTask document.",
        file=out,
    )


def _print_control_validate_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask control validate <control-evaluation.json> "
        "[--format text|json]",
        file=out,
    )
    print(
        "Validates a Control Evaluation Result v1.0 payload without "
        "evaluating expressions or executing actions.",
        file=out,
    )


def _parse_serialized_validate_args(
    args: list[str],
    *,
    command_label: str,
    file_description: str,
    usage_printer,
) -> dict[str, object]:
    if not args:
        raise ValueError(f"{command_label} requires {file_description}")
    if args[0] in ("--help", "-h"):
        usage_printer()
        return {"help": True}
    if args[0].startswith("-"):
        raise ValueError(f"{command_label} requires {file_description}")

    parsed: dict[str, object] = {
        "help": False,
        "path": args[0],
        "format": "text",
    }
    seen_format = False
    index = 1
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            usage_printer()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown {command_label} option: {arg}")

    output_format = str(parsed["format"])
    if output_format not in {"text", "json"}:
        raise ValueError(
            f"unsupported_validation_format: {output_format}. "
            "Supported formats: text, json"
        )
    return parsed


def _validate_serialized_artifact(
    *,
    path: str,
    file_label: str,
    output_format: str,
    contract: VersionedPayloadContract,
) -> dict:
    try:
        payload = _load_json_mapping(path, file_label)
    except (ValueError, OSError) as exc:
        report = invalid_versioned_payload_report(
            contract,
            file=path,
            message=str(exc),
        )
        loaded = None
    else:
        report, loaded = validate_versioned_payload(
            payload,
            contract,
            file=path,
        )

    rendered_report = report.to_dict()
    if output_format == "json":
        sys.stdout.write(_render_json(rendered_report, compact=False))
    elif report.valid:
        print(f"{contract.artifact_name} valid: {path}")
        print(f"  Schema: {contract.schema_id}")
        print(f"  Task: {report.task_id}")
        print(f"  {contract.count_label}: {report.item_count}")
    else:
        message = report.diagnostics[0]["message"]
        print(f"{contract.artifact_name} INVALID: {path}", file=sys.stderr)
        print(f"  {message}", file=sys.stderr)
        print(f"  Schema: {contract.schema_id}", file=sys.stderr)

    if not report.valid:
        sys.exit(1)
    assert loaded is not None
    return rendered_report


def _parse_result_validate_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in ("--help", "-h"):
        _print_result_usage()
        return {"help": True}
    if args[0] != "validate":
        raise ValueError(
            f"unknown result command {args[0]!r}; available command: validate"
        )
    return _parse_serialized_validate_args(
        args[1:],
        command_label="result validate",
        file_description="an execution-result JSON file",
        usage_printer=_print_result_usage,
    )


def cmd_result(args: list[str]):
    """Validate canonical GeoTask execution-result JSON without execution."""

    try:
        parsed = _parse_result_validate_args(args)
        if parsed.get("help"):
            return None
        return _validate_serialized_artifact(
            path=str(parsed["path"]),
            file_label="execution result",
            output_format=str(parsed["format"]),
            contract=EXECUTION_RESULT_VALIDATION_CONTRACT,
        )
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"result_validate_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_normalize(path: str, geotask_path: str | None = None):
    """Normalize an LLM output file, optionally verifying against a GeoTask document."""
    if geotask_path:
        print(f"[normalize + verify] model={path}  geotask={geotask_path}")
        geotask_data = load_geotask(geotask_path)
        diagnostics = validate_document(geotask_data)
        errors = [d for d in diagnostics if d.get("severity", "error") == "error"]
        warnings_only = [d for d in diagnostics if d.get("severity") == "warning"]
        if warnings_only:
            _print_validation_diagnostics(warnings_only, prefix="  ", label="GeoTask Warnings")
        if errors:
            _print_validation_diagnostics(errors, prefix="  ", label="GeoTask")
            sys.exit(1)
    else:
        print(f"[normalize] {path}")
        geotask_data = None

    text = Path(path).read_text(encoding="utf-8")
    result = normalize_model_output(text, geotask_data=geotask_data)
    print_result(result)
    return result


def cmd_eval(geotask_path: str, model_path: str):
    """Evaluate model output against GeoTask Core ground truth."""
    print(f"[eval] core={geotask_path}  model={model_path}")

    # Run Core for ground truth
    data = load_geotask(geotask_path)
    diagnostics = validate_document(data)
    if data.get("_deprecated_stir_field"):
        print("  Warning: Using deprecated 'stir' top-level field. Please migrate to 'geotask'.", file=sys.stderr)
    errors = [d for d in diagnostics if d.get("severity", "error") == "error"]
    warnings_only = [d for d in diagnostics if d.get("severity") == "warning"]
    if warnings_only:
        _print_validation_diagnostics(warnings_only, prefix="  ", label="Core Warnings")
    if errors:
        _print_validation_diagnostics(errors, prefix="  ", label="Core")
        sys.exit(1)

    core_result = run_geotask(data)

    # Normalize model output
    text = Path(model_path).read_text(encoding="utf-8")
    normalized = normalize_model_output(text)

    # Evaluate
    score = evaluate_model_output(core_result, normalized)
    print_result(score)
    return score


def _load_valid_geotask(path: str, label: str = "GeoTask") -> dict:
    """Load and validate a GeoTask document for non-interactive CLI commands."""
    data = load_geotask(path)
    diagnostics = validate_document(data)
    errors = [d for d in diagnostics if d.get("severity", "error") == "error"]
    if errors:
        _print_validation_diagnostics(errors, label=label, stream=sys.stderr)
        sys.exit(1)
    return data


def _print_validation_diagnostics(
    diagnostics: list[dict],
    prefix: str = "",
    label: str = "Validation",
    stream=None,
):
    """Print structured validation diagnostics without a traceback."""
    out = stream or sys.stdout
    error_count = sum(1 for d in diagnostics if d.get("severity", "error") != "warning")
    warning_count = sum(1 for d in diagnostics if d.get("severity") == "warning")
    total = len(diagnostics)
    if error_count and warning_count:
        print(f"{prefix}{label} FAILED ({error_count} error(s), {warning_count} warning(s)):", file=out)
    elif error_count:
        print(f"{prefix}{label} FAILED ({error_count} error(s)):", file=out)
    else:
        print(f"{prefix}{label} ({warning_count} warning(s)):", file=out)
    for diagnostic in diagnostics:
        sev = diagnostic.get("severity", "error")
        print(f"{prefix}  - [{sev.upper()}] path: {diagnostic['path']}", file=out)
        print(f"{prefix}    code: {diagnostic['code']}", file=out)
        print(f"{prefix}    message: {diagnostic['message']}", file=out)
        print(f"{prefix}    Suggested fix: {diagnostic['suggested_fix']}", file=out)


def _print_artifact_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask artifact validate <artifact-id> <file> "
        "[--format text|json]",
        file=out,
    )
    print(
        "Validates a registered public artifact without executing operators, "
        "control actions, or output releases.",
        file=out,
    )


def _parse_artifact_validate_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in ("--help", "-h"):
        _print_artifact_usage()
        return {"help": True}
    if args[0] != "validate":
        raise ValueError(
            f"unknown artifact command {args[0]!r}; available command: validate"
        )
    if len(args) >= 2 and args[1] in ("--help", "-h"):
        _print_artifact_usage()
        return {"help": True}
    if len(args) < 2 or args[1].startswith("-"):
        raise ValueError("artifact validate requires an Artifact ID")
    if len(args) < 3 or args[2].startswith("-"):
        raise ValueError("artifact validate requires an artifact file")

    parsed: dict[str, object] = {
        "artifact_id": args[1],
        "path": args[2],
        "format": "text",
    }
    seen_format = False
    index = 3
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_artifact_usage()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown artifact validate option: {arg}")

    if parsed["format"] not in {"text", "json"}:
        raise ValueError(
            f"unsupported artifact validation format: {parsed['format']}. "
            "Supported formats: text, json"
        )
    return parsed


def cmd_artifact(args: list[str]):
    """Validate any registered public artifact through one stable command."""

    try:
        parsed = _parse_artifact_validate_args(args)
        if parsed.get("help"):
            return None
        report = validate_artifact_file(
            str(parsed["artifact_id"]),
            str(parsed["path"]),
        )
        rendered = report.to_dict()
        body = rendered["artifact_validation"]
        if parsed["format"] == "json":
            sys.stdout.write(_render_json(rendered, compact=False))
        elif report.valid:
            print(f"Artifact valid: {body['file']}")
            print(f"  Artifact: {body['artifact_id']}")
            print(f"  Schema: {body['schema_id']}")
            print(f"  Schema verified: {str(body['schema_verified']).lower()}")
            for key, value in body["summary"].items():
                print(f"  {key}: {value}")
        else:
            print(f"Artifact INVALID: {body['file']}", file=sys.stderr)
            print(f"  Artifact: {body['artifact_id']}", file=sys.stderr)
            print(f"  Schema: {body['schema_id']}", file=sys.stderr)
            for diagnostic in body["diagnostics"]:
                path = diagnostic["path"] or "<root>"
                print(
                    f"  {diagnostic['code']} at {path}: {diagnostic['message']}",
                    file=sys.stderr,
                )

        if not report.valid:
            sys.exit(1)
        return rendered
    except SystemExit:
        raise
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"artifact_validate_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _print_schema_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask schema export <artifact-id> "
        "[--output <file>|-] [--compact]",
        file=out,
    )
    print(
        "       geotask schema verify [artifact-id] [--format text|json]",
        file=out,
    )
    print(
        "Exports or verifies installed public JSON Schemas without network access.",
        file=out,
    )


def _parse_schema_export_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "artifact_id": None,
        "output_path": None,
        "compact": False,
    }
    seen_output = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_schema_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg == "--output":
            if seen_output:
                raise ValueError("--output may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--output requires a value")
            seen_output = True
            parsed["output_path"] = args[index + 1]
            index += 2
            continue
        if not arg.startswith("--"):
            if parsed["artifact_id"] is not None:
                raise ValueError("only one artifact ID may be provided")
            parsed["artifact_id"] = arg
            index += 1
            continue
        raise ValueError(f"unknown schema export option: {arg}")

    if parsed["artifact_id"] is None:
        raise ValueError("schema export requires an artifact ID")
    return parsed


def _parse_schema_verify_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "artifact_id": None,
        "format": "text",
    }
    seen_format = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_schema_usage()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        if not arg.startswith("--"):
            if parsed["artifact_id"] is not None:
                raise ValueError("only one artifact ID may be provided")
            parsed["artifact_id"] = arg
            index += 1
            continue
        raise ValueError(f"unknown schema verify option: {arg}")

    if parsed["format"] not in {"text", "json"}:
        raise ValueError(
            f"unsupported schema verify format: {parsed['format']}. "
            "Supported formats: text, json"
        )
    return parsed


def _cmd_schema_export(args: list[str]):
    parsed = _parse_schema_export_args(args)
    if parsed.get("help"):
        return None
    schema = load_artifact_schema(str(parsed["artifact_id"]))
    rendered = _render_json(schema, compact=bool(parsed["compact"]))
    _write_or_print_output(
        rendered,
        output_path=parsed["output_path"],
        input_paths=[],
    )
    return schema


def _cmd_schema_verify(args: list[str]):
    parsed = _parse_schema_verify_args(args)
    if parsed.get("help"):
        return None
    artifact_id = (
        str(parsed["artifact_id"])
        if parsed["artifact_id"] is not None
        else None
    )
    report = verify_schema_bundle(artifact_id)
    verification = report["schema_bundle_verification"]
    if parsed["format"] == "json":
        sys.stdout.write(_render_json(report, compact=False))
    elif verification["valid"]:
        print(
            "Schema Bundle valid: "
            f"{verification['checked_count']} schema(s), "
            f"version {verification['bundle_version']}"
        )
        for schema in verification["schemas"]:
            print(f"  OK {schema['schema_id']}  sha256={schema['actual_sha256']}")
    else:
        print("Schema Bundle INVALID", file=sys.stderr)
        for diagnostic in verification["diagnostics"]:
            print(
                f"  {diagnostic['code']}: {diagnostic['message']}",
                file=sys.stderr,
            )

    if not verification["valid"]:
        sys.exit(1)
    return report


def cmd_schema(args: list[str]):
    """Export or verify installed public JSON Schemas without network access."""

    if not args or args[0] in ("--help", "-h"):
        _print_schema_usage()
        return None
    if args[0] == "export":
        try:
            return _cmd_schema_export(args[1:])
        except SystemExit:
            raise
        except (KeyError, OSError, TypeError, ValueError) as exc:
            print(f"schema_export_failed: {exc}", file=sys.stderr)
            sys.exit(1)
    if args[0] == "verify":
        try:
            return _cmd_schema_verify(args[1:])
        except SystemExit:
            raise
        except (KeyError, OSError, TypeError, ValueError) as exc:
            print(f"schema_verify_failed: {exc}", file=sys.stderr)
            sys.exit(1)
    print(
        f"schema_failed: unknown schema command {args[0]!r}; "
        "available commands: export, verify",
        file=sys.stderr,
    )
    sys.exit(1)


def _print_inspect_schemas_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask inspect schemas [artifact-id] "
        "[--format yaml|json] [--verify]",
        file=out,
    )
    print(
        "Lists the stable public artifact registry, including schema IDs, "
        "versions, IDE file patterns, generation guidance, and validation commands. --verify "
        "adds local Schema Bundle integrity results.",
        file=out,
    )


def _parse_inspect_schemas_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "help": False,
        "format": "yaml",
        "artifact_id": None,
        "verify": False,
    }
    seen_format = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_inspect_schemas_usage()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        if arg == "--verify":
            if parsed["verify"]:
                raise ValueError("--verify may be provided only once")
            parsed["verify"] = True
            index += 1
            continue
        if not arg.startswith("--"):
            if parsed["artifact_id"] is not None:
                raise ValueError("only one artifact ID may be provided")
            parsed["artifact_id"] = arg
            index += 1
            continue
        raise ValueError(f"unknown inspect schemas option: {arg}")

    output_format = str(parsed["format"])
    if output_format not in {"yaml", "json"}:
        raise ValueError(
            f"unsupported_inspect_schemas_format: {output_format}. "
            "Supported formats: yaml, json"
        )
    return parsed


def cmd_inspect(args: list[str]):
    """Inspect public-safe Core metadata."""
    if not args or args[0] in ("--help", "-h"):
        print(
            "Usage: geotask inspect "
            "<operators|schema|schemas|examples> [options]"
        )
        return None

    subject = args[0]
    if subject == "operators":
        try:
            if len(args) >= 2:
                result = {"operator": get_operator_metadata(args[1])}
            else:
                result = {"operators": list_operator_metadata()}
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        print_result(result)
        return result

    if subject == "schema":
        result = _schema_description()
        print_result(result)
        return result

    if subject == "schemas":
        try:
            parsed = _parse_inspect_schemas_args(args[1:])
            if parsed.get("help"):
                return None
            artifact_id = (
                str(parsed["artifact_id"])
                if parsed["artifact_id"] is not None
                else None
            )
            result = artifact_registry_payload(artifact_id=artifact_id)
            verification_valid = True
            if parsed["verify"]:
                verification = verify_schema_bundle(artifact_id)
                result.update(verification)
                verification_valid = bool(
                    verification["schema_bundle_verification"]["valid"]
                )
        except (KeyError, ValueError) as exc:
            print(f"inspect_schemas_failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if parsed["format"] == "json":
            sys.stdout.write(_render_json(result, compact=False))
        else:
            print_result(result)
        if not verification_valid:
            sys.exit(1)
        return result

    if subject == "examples":
        result = _example_index()
        print_result(result)
        return result

    print(f"Unknown inspect target: {subject}", file=sys.stderr)
    print(
        "Available inspect targets: operators, schema, schemas, examples",
        file=sys.stderr,
    )
    sys.exit(1)


def _schema_description() -> dict:
    """Return a compact public-safe schema description for CLI inspection."""
    return {
        "schema": {
            "required_top_level_keys": ["geotask", "space", "objects", "ops", "task"],
            "optional_top_level_keys": ["assertions", "expected_results"],
            "geotask": {
                "required_fields": ["version", "name", "goal"],
                "description": "Document metadata.",
            },
            "space": {
                "common_fields": ["crs", "unit", "axes"],
                "description": "Coordinate reference and unit metadata.",
            },
            "objects": {
                "point": {"required_fields": ["type", "xy"]},
                "line": {"required_fields": ["type", "points"]},
                "rect": {"required_fields": ["type", "bbox"]},
                "time": {"required_fields": ["type", "interval"]},
                "altitude": {"required_fields": ["type", "range"]},
            },
            "ops": {
                "description": "Mapping of requested deterministic Core operator names.",
                "supported": [op["name"] for op in list_operator_metadata()],
            },
            "task": {
                "common_fields": ["questions"],
                "description": "Human-readable task prompts and requested checks.",
            },
            "assertions": {
                "description": "Optional declarative validation checks.",
                "entry_required_fields": ["id", "operator", "object_refs"],
            },
            "expected_results": {
                "description": "Optional expected output fixtures.",
                "entry_required_fields": ["name", "value"],
                "entry_optional_fields": ["unit"],
            },
            "extension_boundary": (
                "Domain-specific extensions should be handled by domain packs "
                "without changing Core operator semantics."
            ),
        }
    }


def _example_index() -> dict:
    """List examples and mark public-safe Core examples."""
    examples_root = Path("examples")
    examples = []
    if examples_root.exists():
        for path in sorted(examples_root.rglob("*.yaml")):
            examples.append({
                "path": path.as_posix(),
                "public_safe": "domain_packs" not in path.parts,
            })
    return {"examples": examples}


def cmd_explain(path: str):
    """Explain how a GeoTask document resolves requested operators."""
    data = _load_valid_geotask(path, label="GeoTask")
    explanations = []
    for op_name in data.get("ops", {}):
        try:
            metadata = get_operator_metadata(str(op_name))
            explanations.append({
                "operator": metadata["name"],
                "registered": True,
                "deterministic": metadata["deterministic"],
                "input_shape": metadata["input_shape"],
                "output_type": metadata["output_type"],
                "supported_geometry": metadata["supported_geometry"],
            })
        except KeyError as exc:
            explanations.append({
                "operator": str(op_name),
                "registered": False,
                "error_code": "unsupported_operator",
                "message": str(exc),
            })

    result = {
        "file": path,
        "object_count": len(data.get("objects", {})),
        "operators": explanations,
    }
    print_result(result)
    return result


def cmd_report(path: str, args: list[str]):
    """Run a deterministic Core report in JSON or Markdown format."""
    report_format = _parse_report_format(args)
    data = _load_valid_geotask(path, label="GeoTask")
    result = run_geotask(data)
    payload = {
        "file": path,
        "summary": _result_summary(result),
        "result": result,
    }

    if report_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif report_format == "markdown":
        print(_format_markdown_report(payload))
    else:
        print(
            f"unsupported_report_format: {report_format}. "
            "Supported formats: json, markdown",
            file=sys.stderr,
        )
        sys.exit(1)

    return payload


def _parse_report_format(args: list[str]) -> str:
    """Parse report format from CLI args."""
    if not args:
        return "json"
    for i, arg in enumerate(args):
        if arg == "--format" and i + 1 < len(args):
            return args[i + 1]
    return "json"


def _result_summary(result: dict) -> dict:
    """Build a compact summary for deterministic Core runner output."""
    measurements = result.get("measurements", [])
    return {
        "total_checks": len(measurements),
        "verified_count": len(measurements),
        "contradicted_count": 0,
        "need_review_count": 0,
        "invalid_count": 0,
    }


def _format_markdown_report(payload: dict) -> str:
    """Render a compact Markdown report for deterministic Core output."""
    result = payload["result"]
    summary = payload["summary"]
    lines = [
        "# GeoTask Report",
        "",
        f"Source: `{payload['file']}`",
        "",
        "## Summary",
        "",
        f"- Total checks: {summary['total_checks']}",
        f"- Verified: {summary['verified_count']}",
        f"- Contradicted: {summary['contradicted_count']}",
        f"- Need review: {summary['need_review_count']}",
        f"- Invalid: {summary['invalid_count']}",
        "",
        "## Measurements",
        "",
        "| Measurement | Value | Unit | Operator |",
        "|-------------|-------|------|----------|",
    ]
    for measurement in result.get("measurements", []):
        value = measurement.get("value")
        if isinstance(value, bool):
            value = str(value).lower()
        unit = measurement.get("unit") or ""
        lines.append(
            f"| `{measurement.get('name', '')}` | `{value}` | `{unit}` | "
            f"`{measurement.get('verified_by', '')}` |"
        )

    lines.extend([
        "",
        "## Conclusion",
        "",
        result.get("conclusion", {}).get("summary", ""),
    ])
    return "\n".join(lines)


def _print_control_usage(stream=None) -> None:
    out = stream or sys.stdout
    print("Usage: geotask control <evaluate|validate> ...", file=out)
    print(
        "  geotask control evaluate <geotask.yaml> --result <result.json> "
        "[--state <state.json|state.yaml>] [--output <file>] [--compact]",
        file=out,
    )
    print(
        "  geotask control validate <control-evaluation.json>",
        file=out,
    )
    print("  Validates Control Evaluation Result v1.0.", file=out)
    print(
        "The CLI never executes next_action or releases outputs.",
        file=out,
    )


def _print_control_evaluate_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask control evaluate <geotask.yaml> "
        "--result <geotask-result.json> "
        "[--state <state.json|state.yaml>] "
        "[--output <control-evaluation.json>] [--compact]",
        file=out,
    )
    print(
        "Evaluates geotask.control/1.0 conditions only; it never executes "
        "next_action or releases outputs.",
        file=out,
    )


def _parse_control_evaluate_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in ("--help", "-h"):
        _print_control_evaluate_usage()
        return {"help": True}
    if args[0] != "evaluate":
        raise ValueError(
            f"unknown control command {args[0]!r}; available command: evaluate"
        )
    if len(args) >= 2 and args[1] in ("--help", "-h"):
        _print_control_evaluate_usage()
        return {"help": True}
    if len(args) < 2 or args[1].startswith("-"):
        raise ValueError("control evaluate requires a GeoTask YAML file")

    parsed: dict[str, object] = {
        "help": False,
        "geotask_path": args[1],
        "result_path": None,
        "state_path": None,
        "output_path": None,
        "compact": False,
    }
    value_flags = {
        "--result": "result_path",
        "--state": "state_path",
        "--output": "output_path",
    }
    index = 2
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_control_evaluate_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in value_flags:
            target = value_flags[arg]
            if parsed[target] is not None:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a file path")
            parsed[target] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown control evaluate option: {arg}")

    if parsed["result_path"] is None:
        raise ValueError("control evaluate requires --result <geotask-result.json>")
    return parsed


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_mapping(path: str, label: str) -> dict:
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite_json,
            object_pairs_hook=_unique_json_object,
        )
    except OSError as exc:
        raise ValueError(f"cannot read {label} file {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {label} file {path!r} at "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise ValueError(f"invalid JSON in {label} file {path!r}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} file {path!r} must contain a JSON object")
    return dict(payload)


def _load_state_mapping(path: str | None) -> dict:
    if path is None:
        return {}
    state_path = Path(path)
    try:
        text = state_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read state file {path!r}: {exc}") from exc

    try:
        if state_path.suffix.lower() == ".json":
            payload = json.loads(
                text,
                parse_constant=_reject_nonfinite_json,
                object_pairs_hook=_unique_json_object,
            )
        else:
            payload = yaml.load(text, Loader=_UniqueKeyLoader)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in state file {path!r} at "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise ValueError(f"invalid JSON in state file {path!r}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in state file {path!r}: {exc}") from exc

    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"state file {path!r} must contain an object or mapping")
    return dict(payload)


def _render_json(payload: dict, *, compact: bool) -> str:
    if compact:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        ) + "\n"
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=False,
    ) + "\n"


def _cmd_control_evaluate(args: list[str]):
    """Evaluate a versioned control profile without executing actions."""

    try:
        parsed = _parse_control_evaluate_args(args)
        if parsed.get("help"):
            return None

        geotask_path = str(parsed["geotask_path"])
        data = _load_valid_geotask(geotask_path, label="GeoTask")
        document = canonicalize(data)
        result_payload = _load_json_mapping(
            str(parsed["result_path"]),
            "execution result",
        )
        execution_result = GeotaskResult.from_dict(result_payload)
        domain_state = _load_state_mapping(
            None if parsed["state_path"] is None else str(parsed["state_path"])
        )
        payload = evaluate_control_profile(
            document,
            execution_result,
            domain_state,
        ).to_dict()
        rendered = _render_json(payload, compact=bool(parsed["compact"]))

        input_paths = [
            Path(geotask_path),
            Path(str(parsed["result_path"])),
        ]
        if parsed["state_path"] is not None:
            input_paths.append(Path(str(parsed["state_path"])))
        _write_or_print_output(
            rendered,
            output_path=parsed["output_path"],
            input_paths=input_paths,
        )
        return payload
    except SystemExit:
        raise
    except (
        ControlContextError,
        ResultFormatError,
        ValueError,
        TypeError,
        OSError,
        yaml.YAMLError,
    ) as exc:
        print(f"control_evaluate_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_control_validate(args: list[str]):
    """Validate a serialized Control Evaluation Result without evaluation."""

    try:
        parsed = _parse_serialized_validate_args(
            args,
            command_label="control validate",
            file_description="a control-evaluation JSON file",
            usage_printer=_print_control_validate_usage,
        )
        if parsed.get("help"):
            return None
        return _validate_serialized_artifact(
            path=str(parsed["path"]),
            file_label="control evaluation",
            output_format=str(parsed["format"]),
            contract=CONTROL_EVALUATION_VALIDATION_CONTRACT,
        )
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"control_validate_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_control(args: list[str]):
    """Evaluate or validate versioned control artifacts without actions."""

    if not args or args[0] in ("--help", "-h"):
        _print_control_usage()
        return None
    if args[0] == "evaluate":
        return _cmd_control_evaluate(args)
    if args[0] == "validate":
        return _cmd_control_validate(args[1:])
    print(
        f"control_failed: unknown control command {args[0]!r}; "
        "available commands: evaluate, validate",
        file=sys.stderr,
    )
    sys.exit(1)


def _print_agent_usage(stream=None) -> None:
    out = stream or sys.stdout
    print("Usage: geotask agent inspect [--format text|json]", file=out)
    print(
        "       geotask agent prepare <generated.yaml> "
        "[--format text|json] [--output <report.json>|-] "
        "[--repaired-output <task.yaml>] [--compact]",
        file=out,
    )
    print(
        "       geotask agent retry <blocked-report.json> <revised.yaml> "
        "[--format text|json] [--output <report.json>|-] "
        "[--verification-output <report.json>] "
        "[--prepared-output <task.yaml>] [--compact]",
        file=out,
    )
    print(
        "       geotask agent recover <task.yaml> --evidence <state.yaml> "
        "[--format text|json] [--output <file>|-] [--compact]",
        file=out,
    )
    print(
        "The preview Agent profile composes existing Artifact, execution, and "
        "control contracts without calling a model or executing next_action.",
        file=out,
    )


def _parse_agent_inspect_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {"format": "text"}
    index = 0
    seen_format = False
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_agent_usage()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown agent inspect option: {arg}")
    if parsed["format"] not in {"text", "json"}:
        raise ValueError("agent inspect --format must be text or json")
    return parsed


def _parse_agent_prepare_args(args: list[str]) -> dict[str, object]:
    if not args:
        raise ValueError("agent prepare requires a generated GeoTask YAML file")
    if args[0] in ("--help", "-h"):
        _print_agent_usage()
        return {"help": True}
    if args[0].startswith("-"):
        raise ValueError("agent prepare requires a generated GeoTask YAML file")

    parsed: dict[str, object] = {
        "task_path": args[0],
        "format": "json",
        "output_path": None,
        "repaired_output_path": None,
        "compact": False,
    }
    seen: set[str] = set()
    index = 1
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_agent_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in {"--format", "--output", "--repaired-output"}:
            if arg in seen:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a value")
            seen.add(arg)
            target = {
                "--format": "format",
                "--output": "output_path",
                "--repaired-output": "repaired_output_path",
            }[arg]
            parsed[target] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown agent prepare option: {arg}")

    if parsed["format"] not in {"text", "json"}:
        raise ValueError("agent prepare --format must be text or json")
    if parsed["compact"] and parsed["format"] != "json":
        raise ValueError("--compact is supported only with --format json")
    if parsed["format"] == "text" and parsed["output_path"] is not None:
        raise ValueError("--output is supported only with --format json")
    return parsed


def _parse_agent_retry_args(args: list[str]) -> dict[str, object]:
    if len(args) < 2:
        raise ValueError(
            "agent retry requires a blocked preparation report and revised GeoTask YAML"
        )
    if args[0] in ("--help", "-h"):
        _print_agent_usage()
        return {"help": True}
    if args[0].startswith("-") or args[1].startswith("-"):
        raise ValueError(
            "agent retry requires a blocked preparation report and revised GeoTask YAML"
        )

    parsed: dict[str, object] = {
        "report_path": args[0],
        "revised_path": args[1],
        "format": "json",
        "output_path": None,
        "verification_output_path": None,
        "prepared_output_path": None,
        "compact": False,
    }
    seen: set[str] = set()
    index = 2
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_agent_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in {
            "--format",
            "--output",
            "--verification-output",
            "--prepared-output",
        }:
            if arg in seen:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a value")
            seen.add(arg)
            target = {
                "--format": "format",
                "--output": "output_path",
                "--verification-output": "verification_output_path",
                "--prepared-output": "prepared_output_path",
            }[arg]
            parsed[target] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown agent retry option: {arg}")

    if parsed["format"] not in {"text", "json"}:
        raise ValueError("agent retry --format must be text or json")
    if parsed["compact"] and parsed["format"] != "json":
        raise ValueError("--compact is supported only with --format json")
    if parsed["format"] == "text" and parsed["output_path"] is not None:
        raise ValueError("--output is supported only with --format json")
    if parsed["verification_output_path"] == "-":
        raise ValueError("--verification-output requires a file path, not stdout")
    return parsed


def _parse_agent_recover_args(args: list[str]) -> dict[str, object]:
    if not args:
        raise ValueError("agent recover requires a GeoTask YAML file")
    if args[0] in ("--help", "-h"):
        _print_agent_usage()
        return {"help": True}
    if args[0].startswith("-"):
        raise ValueError("agent recover requires a GeoTask YAML file")

    parsed: dict[str, object] = {
        "task_path": args[0],
        "evidence_path": None,
        "format": "json",
        "output_path": None,
        "compact": False,
    }
    seen: set[str] = set()
    index = 1
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_agent_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in {"--evidence", "--format", "--output"}:
            if arg in seen:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a value")
            seen.add(arg)
            target = {
                "--evidence": "evidence_path",
                "--format": "format",
                "--output": "output_path",
            }[arg]
            parsed[target] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown agent recover option: {arg}")

    if parsed["evidence_path"] is None:
        raise ValueError("agent recover requires --evidence <state.yaml>")
    if parsed["format"] not in {"text", "json"}:
        raise ValueError("agent recover --format must be text or json")
    if parsed["compact"] and parsed["format"] != "json":
        raise ValueError("--compact is supported only with --format json")
    if parsed["format"] == "text" and parsed["output_path"] is not None:
        raise ValueError("--output is supported only with --format json")
    return parsed


def _cmd_agent_inspect(args: list[str]):
    parsed = _parse_agent_inspect_args(args)
    if parsed.get("help"):
        return None
    payload = agent_integration_profile_payload()
    if parsed["format"] == "json":
        sys.stdout.write(_render_json(payload, compact=False))
    else:
        profile = payload["agent_integration_profile"]
        print(
            "GeoTask Agent Integration Profile "
            f"{profile['id']}/{profile['version']} ({profile['status']})"
        )
        for tool in profile["tools"]:
            print(f"  {tool['name']}: {tool['purpose']}")
            print(f"    CLI: {tool['cli']}")
    return payload


def _cmd_agent_prepare(args: list[str]):
    parsed = _parse_agent_prepare_args(args)
    if parsed.get("help"):
        return None

    task_path = str(parsed["task_path"])
    document = load_geotask(task_path)
    result = prepare_generated_document(document)
    payload = result.to_dict()
    body = payload["agent_generation_preparation"]

    repaired_output = parsed["repaired_output_path"]
    report_output = parsed["output_path"]
    input_path = Path(task_path).resolve()
    if repaired_output is not None:
        repaired_path = Path(str(repaired_output)).resolve()
        if repaired_path == input_path:
            raise ValueError("--repaired-output must not overwrite the generated input")
        if report_output is not None and report_output != "-":
            if repaired_path == Path(str(report_output)).resolve():
                raise ValueError("--output and --repaired-output must be different files")
        if body["final_validation"]["valid"]:
            if repaired_path.suffix.lower() == ".json":
                rendered_document = _render_json(
                    body["prepared_document"],
                    compact=False,
                )
            else:
                rendered_document = yaml.safe_dump(
                    body["prepared_document"],
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            repaired_path.write_text(rendered_document, encoding="utf-8")

    if parsed["format"] == "json":
        rendered = _render_json(payload, compact=bool(parsed["compact"]))
        _write_or_print_output(
            rendered,
            output_path=report_output,
            input_paths=[Path(task_path)],
        )
    else:
        print(f"Agent generated-document preparation {body['state']}: {task_path}")
        print(f"  Initial errors: {body['summary']['initial_error_count']}")
        print(f"  Mechanical repairs: {body['summary']['repair_count']}")
        print(f"  Residual errors: {body['summary']['residual_error_count']}")
        print(f"  Task executed: {str(body['summary']['task_executed']).lower()}")
        print(f"  Overall status: {body['summary']['overall_status'] or 'not_executed'}")
        if body["repairs"]:
            print("  Repair codes: " + ", ".join(item["code"] for item in body["repairs"]))
        if body["final_validation"]["diagnostics"]:
            print(
                "  Blocking diagnostics: "
                + ", ".join(
                    item["code"]
                    for item in body["final_validation"]["diagnostics"]
                    if item.get("severity", "error") == "error"
                )
            )

    if body["state"] == "blocked":
        sys.exit(2)
    return payload


def _cmd_agent_retry(args: list[str]):
    parsed = _parse_agent_retry_args(args)
    if parsed.get("help"):
        return None

    report_path = str(parsed["report_path"])
    revised_path = str(parsed["revised_path"])
    preparation_report = _load_json_mapping(
        report_path,
        "Agent blocked preparation report",
    )
    revised_document = load_geotask(revised_path)
    result = retry_generated_document(preparation_report, revised_document)
    payload = result.to_dict()
    body = payload["agent_revision_retry"]

    prepared_output = parsed["prepared_output_path"]
    verification_output = parsed["verification_output_path"]
    output_path = parsed["output_path"]
    input_paths = [Path(report_path).resolve(), Path(revised_path).resolve()]
    resolved_outputs: dict[str, Path] = {}
    for label, raw_path in (
        ("--output", output_path),
        ("--verification-output", verification_output),
        ("--prepared-output", prepared_output),
    ):
        if raw_path is None or raw_path == "-":
            continue
        resolved_path = Path(str(raw_path)).resolve()
        if resolved_path in input_paths:
            raise ValueError(
                f"{label} must not overwrite the blocked report or revised input"
            )
        if resolved_path in resolved_outputs.values():
            raise ValueError(
                "--output, --verification-output, and --prepared-output "
                "must be different files"
            )
        resolved_outputs[label] = resolved_path

    verification_path = resolved_outputs.get("--verification-output")
    if verification_path is not None:
        verification_payload = {
            "agent_revision_verification": body["revision_verification"]
        }
        verification_path.write_text(
            _render_json(verification_payload, compact=False),
            encoding="utf-8",
        )

    prepared_path = resolved_outputs.get("--prepared-output")
    if prepared_path is not None:
        preparation = body.get("preparation")
        if body["state"] == "accepted" and isinstance(preparation, Mapping):
            prepared_document = preparation.get("prepared_document")
            if isinstance(prepared_document, Mapping):
                if prepared_path.suffix.lower() == ".json":
                    rendered_document = _render_json(
                        dict(prepared_document),
                        compact=False,
                    )
                else:
                    rendered_document = yaml.safe_dump(
                        dict(prepared_document),
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                prepared_path.write_text(rendered_document, encoding="utf-8")

    if parsed["format"] == "json":
        rendered = _render_json(payload, compact=bool(parsed["compact"]))
        _write_or_print_output(
            rendered,
            output_path=output_path,
            input_paths=input_paths,
        )
    else:
        verification = body["revision_verification"]
        print(f"Agent generated-document retry {body['state']}: {revised_path}")
        print(f"  Revision verification: {verification['state']}")
        print(
            f"  Changed paths: {verification['summary']['changed_path_count']}"
        )
        print(f"  Violations: {verification['summary']['violation_count']}")
        print(f"  Task executed: {str(body['summary']['task_executed']).lower()}")
        print(
            f"  Overall status: {body['summary']['overall_status'] or 'not_executed'}"
        )
        for violation in verification["violations"]:
            print(
                f"  {violation['code']} at {violation['path']}: "
                f"{violation['message']}"
            )

    if body["state"] != "accepted":
        sys.exit(2)
    return payload


def _cmd_agent_recover(args: list[str]):
    parsed = _parse_agent_recover_args(args)
    if parsed.get("help"):
        return None

    task_path = str(parsed["task_path"])
    evidence_path = str(parsed["evidence_path"])
    document = _load_valid_geotask(task_path, label="Agent recovery GeoTask")
    evidence_state = _load_state_mapping(evidence_path)
    result = recover_evidence_request(document, evidence_state)
    payload = result.to_dict()
    body = payload["agent_integration"]

    if parsed["format"] == "json":
        rendered = _render_json(payload, compact=bool(parsed["compact"]))
        _write_or_print_output(
            rendered,
            output_path=parsed["output_path"],
            input_paths=[Path(task_path), Path(evidence_path)],
        )
    else:
        print(f"Agent evidence recovery {body['state']}: {body['task_id']}")
        print(f"  Request: {body['request']['id']}")
        print(f"  Trigger: {body['request']['trigger']}")
        missing = body["request"]["missing_fields"]
        print(f"  Missing evidence: {', '.join(missing) if missing else 'none'}")
        print(f"  Task reexecuted: {str(body['materialization']['task_reexecuted']).lower()}")
        print(f"  Decision value: {body['summary']['decision_value']}")
        print(
            "  Blocked outputs: "
            + (", ".join(body["summary"]["blocked_outputs"]) or "none")
        )
        print(
            "  Eligible outputs: "
            + (", ".join(body["summary"]["eligible_outputs"]) or "none")
        )
    return payload


def cmd_agent(args: list[str]):
    """Inspect, prepare, retry guarded revisions, or recover blocked evidence."""

    try:
        if not args or args[0] in ("--help", "-h"):
            _print_agent_usage()
            return None
        if args[0] == "inspect":
            return _cmd_agent_inspect(args[1:])
        if args[0] == "prepare":
            return _cmd_agent_prepare(args[1:])
        if args[0] == "retry":
            return _cmd_agent_retry(args[1:])
        if args[0] == "recover":
            return _cmd_agent_recover(args[1:])
        raise ValueError(
            f"unknown agent command {args[0]!r}; "
            "available commands: inspect, prepare, retry, recover"
        )
    except SystemExit:
        raise
    except (
        AgentIntegrationError,
        AgentGenerationError,
        ControlContextError,
        ValueError,
        TypeError,
        OSError,
        yaml.YAMLError,
    ) as exc:
        print(f"agent_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _print_runtime_usage(stream=None) -> None:
    out = stream or sys.stdout
    print(
        "Usage: geotask runtime inspect [runtime-descriptor.json] "
        "[--profile] [--format text|json]",
        file=out,
    )
    print(
        "       geotask runtime check <runtime-descriptor.json> "
        "<runtime-request.json> [--format text|json]",
        file=out,
    )
    print(
        "       geotask runtime mock <runtime-request.json> "
        "[--format text|json] [--output <runtime-response.json>|-] [--compact]",
        file=out,
    )
    print(
        "The public reference Runtime performs read-only Artifact validation only. "
        "It never calls a model, resolves external evidence, or executes actions.",
        file=out,
    )


def _parse_runtime_inspect_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "format": "text",
        "profile": False,
        "descriptor_path": None,
    }
    seen_format = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_runtime_usage()
            return {"help": True}
        if arg == "--profile":
            if parsed["profile"]:
                raise ValueError("--profile may be provided only once")
            parsed["profile"] = True
            index += 1
            continue
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        if not arg.startswith("-"):
            if parsed["descriptor_path"] is not None:
                raise ValueError("runtime inspect accepts at most one descriptor file")
            parsed["descriptor_path"] = arg
            index += 1
            continue
        raise ValueError(f"unknown runtime inspect option: {arg}")
    if parsed["format"] not in {"text", "json"}:
        raise ValueError("runtime inspect --format must be text or json")
    if parsed["profile"] and parsed["descriptor_path"] is not None:
        raise ValueError("runtime inspect --profile cannot be combined with a descriptor file")
    return parsed


def _parse_runtime_check_args(args: list[str]) -> dict[str, object]:
    if len(args) < 2 or args[0].startswith("-") or args[1].startswith("-"):
        raise ValueError(
            "runtime check requires a Runtime Descriptor JSON file and Runtime Request JSON file"
        )
    parsed: dict[str, object] = {
        "descriptor_path": args[0],
        "request_path": args[1],
        "format": "text",
    }
    seen_format = False
    index = 2
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_runtime_usage()
            return {"help": True}
        if arg == "--format":
            if seen_format:
                raise ValueError("--format may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError("--format requires a value")
            seen_format = True
            parsed["format"] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown runtime check option: {arg}")
    if parsed["format"] not in {"text", "json"}:
        raise ValueError("runtime check --format must be text or json")
    return parsed


def _parse_runtime_mock_args(args: list[str]) -> dict[str, object]:
    if not args or args[0].startswith("-"):
        raise ValueError("runtime mock requires a Runtime Request JSON file")
    parsed: dict[str, object] = {
        "request_path": args[0],
        "format": "json",
        "output_path": None,
        "compact": False,
    }
    seen: set[str] = set()
    index = 1
    while index < len(args):
        arg = args[index]
        if arg in ("--help", "-h"):
            _print_runtime_usage()
            return {"help": True}
        if arg == "--compact":
            if parsed["compact"]:
                raise ValueError("--compact may be provided only once")
            parsed["compact"] = True
            index += 1
            continue
        if arg in {"--format", "--output"}:
            if arg in seen:
                raise ValueError(f"{arg} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{arg} requires a value")
            seen.add(arg)
            parsed["format" if arg == "--format" else "output_path"] = args[index + 1]
            index += 2
            continue
        raise ValueError(f"unknown runtime mock option: {arg}")
    if parsed["format"] not in {"text", "json"}:
        raise ValueError("runtime mock --format must be text or json")
    if parsed["compact"] and parsed["format"] != "json":
        raise ValueError("--compact is supported only with --format json")
    if parsed["format"] == "text" and parsed["output_path"] is not None:
        raise ValueError("--output is supported only with --format json")
    return parsed


def _cmd_runtime_inspect(args: list[str]):
    parsed = _parse_runtime_inspect_args(args)
    if parsed.get("help"):
        return None
    if parsed["profile"]:
        payload = runtime_interface_profile_payload()
        body = payload["runtime_interface_profile"]
        if parsed["format"] == "text":
            print(
                f"GeoTask Runtime Interface Profile "
                f"{body['profile_id']}/{body['profile_version']}"
            )
            print(f"  Reference Runtime: {body['reference_runtime_id']}")
            print("  Standard operations:")
            for operation_id in body["standard_operation_ids"]:
                print(f"    {operation_id}")
            print("  Private implementation excluded: true")
        else:
            sys.stdout.write(_render_json(payload, compact=False))
        return payload

    descriptor_path = parsed["descriptor_path"]
    if descriptor_path is None:
        payload = reference_runtime_descriptor().to_dict()
    else:
        payload = load_runtime_descriptor(
            _load_json_mapping(str(descriptor_path), "Runtime Descriptor")
        ).to_dict()
    body = payload["runtime_descriptor"]
    if parsed["format"] == "json":
        sys.stdout.write(_render_json(payload, compact=False))
    else:
        print(f"Runtime {body['runtime_id']} v{body['runtime_version']}")
        print(f"  Interface: {body['interface_version']}")
        print(f"  Kind: {body['implementation_kind']}")
        print(f"  Production ready: {str(body['production_ready']).lower()}")
        print(
            "  External side effects allowed: "
            f"{str(body['external_side_effects_allowed']).lower()}"
        )
        print("  Operations:")
        for operation in body["operations"]:
            print(f"    {operation['operation_id']} ({operation['side_effect']})")
    return payload


def _cmd_runtime_check(args: list[str]):
    parsed = _parse_runtime_check_args(args)
    if parsed.get("help"):
        return None
    descriptor_path = str(parsed["descriptor_path"])
    request_path = str(parsed["request_path"])
    descriptor = load_runtime_descriptor(
        _load_json_mapping(descriptor_path, "Runtime Descriptor")
    )
    request = load_runtime_request(_load_json_mapping(request_path, "Runtime Request"))
    operation = validate_runtime_request_contract(descriptor, request)
    payload = {
        "runtime_contract_check": {
            "valid": True,
            "runtime_id": descriptor.runtime_id,
            "runtime_version": descriptor.runtime_version,
            "request_id": request.request_id,
            "operation_id": operation.operation_id,
            "input_artifact_ids": [
                artifact.artifact_id for artifact in request.input_artifacts
            ],
            "expected_output_artifact_ids": list(
                request.expected_output_artifact_ids
            ),
            "requires_authorization": operation.requires_authorization,
            "authorization_supplied": request.authorization_ref is not None,
            "side_effect": operation.side_effect,
            "submitted": False,
            "side_effects_executed": False,
        }
    }
    if parsed["format"] == "json":
        sys.stdout.write(_render_json(payload, compact=False))
    else:
        body = payload["runtime_contract_check"]
        print(f"Runtime contract valid: {body['request_id']}")
        print(f"  Runtime: {body['runtime_id']} v{body['runtime_version']}")
        print(f"  Operation: {body['operation_id']}")
        print(f"  Side effect: {body['side_effect']}")
        print("  Submitted: false")
        print("  Side effects executed: false")
    return payload


def _cmd_runtime_mock(args: list[str]):
    parsed = _parse_runtime_mock_args(args)
    if parsed.get("help"):
        return None
    request_path = str(parsed["request_path"])
    request_payload = _load_json_mapping(request_path, "Runtime Request")
    response = submit_runtime_request(FailClosedMockRuntime(), request_payload)
    payload = response.to_dict()
    body = payload["runtime_response"]
    if parsed["format"] == "json":
        _write_or_print_output(
            _render_json(payload, compact=bool(parsed["compact"])),
            output_path=parsed["output_path"],
            input_paths=[Path(request_path)],
        )
    else:
        print(f"Runtime request {body['request_id']}: {body['state']}")
        print(f"  Runtime: {body['runtime_id']}")
        print(f"  Operation: {body['operation_id']}")
        print(f"  Output Artifacts: {len(body['output_artifacts'])}")
        print(
            "  Side effects executed: "
            f"{str(body['side_effects_executed']).lower()}"
        )
        for diagnostic in body["diagnostics"]:
            print(
                f"  {diagnostic['severity']} {diagnostic['code']}: "
                f"{diagnostic['message']}"
            )
    if body["state"] in {"blocked", "rejected", "failed"}:
        sys.exit(2)
    return payload


def cmd_runtime(args: list[str]):
    """Inspect the public Runtime SDK or invoke the fail-closed reference adapter."""

    try:
        if not args or args[0] in ("--help", "-h"):
            _print_runtime_usage()
            return None
        if args[0] == "inspect":
            return _cmd_runtime_inspect(args[1:])
        if args[0] == "check":
            return _cmd_runtime_check(args[1:])
        if args[0] == "mock":
            return _cmd_runtime_mock(args[1:])
        raise ValueError(
            f"unknown runtime command {args[0]!r}; "
            "available commands: inspect, check, mock"
        )
    except SystemExit:
        raise
    except (RuntimeInterfaceFormatError, ValueError, TypeError, OSError) as exc:
        print(f"runtime_failed: {exc}", file=sys.stderr)
        sys.exit(1)


def print_result(result: dict):
    """Print a result dict as YAML."""
    import yaml
    print(yaml.dump(result, allow_unicode=True, default_flow_style=False, sort_keys=False))


def _parse_geotask_flag(args: list[str]) -> tuple[str | None, int]:
    """Parse --geotask <path> from args. Returns (path, consumed_count)."""
    for i, arg in enumerate(args):
        if arg == "--geotask" and i + 1 < len(args):
            return args[i + 1], 2
    return None, 0


def main():
    cmd_name = _get_command_name()
    if cmd_name == "stir":
        print("Warning: 'stir' command is deprecated. Please use 'geotask' instead.", file=sys.stderr)

    if len(sys.argv) >= 2 and sys.argv[1] in ("--version", "-V", "version"):
        print(f"geotask-core {__version__}")
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] in ("--help", "-h"):
        print(f"Usage: {cmd_name} <command> <file> [<file2>] [--geotask <file.yaml>]")
        print("Commands: validate, run, result, artifact, schema, explain, inspect, report, control, agent, runtime, normalize, eval, version")
        sys.exit(0)

    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <command> <file> [<file2>] [--geotask <file.yaml>]")
        print("Commands: validate, run, result, artifact, schema, explain, inspect, report, control, agent, runtime, normalize, eval, version")
        print()
        print("Examples:")
        print(f"  {cmd_name} validate examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} run examples/geotask_core_lite.yaml")
        print(
            f"  {cmd_name} run examples/core/uav_arrival_ground_clearance_release.yaml "
            "--format v1-json --output execution-result.json"
        )
        print(f"  {cmd_name} result validate execution-result.json")
        print(
            f"  {cmd_name} schema export geotask.execution-result "
            "--output geotask-result.schema.json"
        )
        print(f"  {cmd_name} normalize examples/deepseek_output_sample.txt")
        print(f"  {cmd_name} normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt")
        print(f"  {cmd_name} inspect operators")
        print(f"  {cmd_name} explain examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} report examples/geotask_core_lite.yaml --format json")
        print(
            f"  {cmd_name} control evaluate examples/core/uav_arrival_ground_clearance_release.yaml "
            "--result execution-result.json --state control-state.yaml"
        )
        print(f"  {cmd_name} agent inspect --format json")
        print(
            f"  {cmd_name} agent prepare examples/core/agent_generated_distance_draft.yaml "
            "--repaired-output prepared.yaml"
        )
        print(
            f"  {cmd_name} agent retry blocked-preparation.json "
            "examples/core/agent_generated_distance_revised.yaml "
            "--prepared-output prepared.yaml"
        )
        print(
            f"  {cmd_name} agent recover examples/core/evidence_request_plan.yaml "
            "--evidence examples/core/evidence_request_verified_state.yaml"
        )
        print(f"  {cmd_name} runtime inspect --profile --format json")
        print(
            f"  {cmd_name} runtime mock "
            "examples/core/runtime_validate_artifact_request.json"
        )
        print()
        print(f"  python -m geotask_core.cli validate examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli run examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli normalize examples/deepseek_output_sample.txt")
        print(f"  python -m geotask_core.cli normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt")
        print(f"  python -m geotask_core.cli inspect operators")
        print(f"  python -m geotask_core.cli explain examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli report examples/geotask_core_lite.yaml --format json")
        print(f"")
        print(f"Backward compatibility: the old 'stir' YAML field and 'stir' CLI are accepted but deprecated.")
        sys.exit(1)

    command = sys.argv[1]

    if command == "control":
        cmd_control(sys.argv[2:])
        return

    if command == "agent":
        cmd_agent(sys.argv[2:])
        return

    if command == "runtime":
        cmd_runtime(sys.argv[2:])
        return

    if command == "result":
        cmd_result(sys.argv[2:])
        return

    if command == "artifact":
        cmd_artifact(sys.argv[2:])
        return

    if command == "schema":
        cmd_schema(sys.argv[2:])
        return

    if command == "inspect":
        cmd_inspect(sys.argv[2:])
        return

    if command == "explain":
        cmd_explain(sys.argv[2])
        return

    if command == "report":
        cmd_report(sys.argv[2], sys.argv[3:])
        return

    if command == "run":
        cmd_run(sys.argv[2], sys.argv[3:])
        return

    # eval takes two file arguments
    if command == "eval":
        if len(sys.argv) < 4:
            print(f"Usage: {cmd_name} eval <geotask.yaml> <model_output.txt>")
            sys.exit(1)
        cmd_eval(sys.argv[2], sys.argv[3])
        return

    path = sys.argv[2]

    # normalize supports optional --geotask flag
    if command == "normalize":
        remaining = sys.argv[3:]
        geotask_path, consumed = _parse_geotask_flag(remaining)
        cmd_normalize(path, geotask_path=geotask_path)
        return

    commands = {
        "validate": cmd_validate,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available commands: validate, run, result, artifact, schema, explain, inspect, report, control, agent, runtime, normalize, eval, version")
        sys.exit(1)

    commands[command](path)


if __name__ == "__main__":
    main()
