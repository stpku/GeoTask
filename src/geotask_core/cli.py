"""GeoTask Core CLI.

Usage:
    geotask validate <file.yaml>
    geotask run <file.yaml> [--format yaml|v1-json] [--output <file>|-]
    geotask result validate <execution-result.json> [--format text|json]
    geotask normalize <file.txt> [--geotask <file.yaml>]
    geotask eval <file.yaml> <model_output.txt>
    geotask control evaluate <file.yaml> --result <result.json> [--state <state.yaml>]
    geotask control validate <control-evaluation.json> [--format text|json]
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


def _print_inspect_schemas_usage(stream=None) -> None:
    out = stream or sys.stdout
    print("Usage: geotask inspect schemas [--format yaml|json]", file=out)
    print(
        "Lists the stable public artifact registry, including schema IDs, "
        "versions, generation guidance, and validation commands.",
        file=out,
    )


def _parse_inspect_schemas_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {"help": False, "format": "yaml"}
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
        except ValueError as exc:
            print(f"inspect_schemas_failed: {exc}", file=sys.stderr)
            sys.exit(1)

        result = artifact_registry_payload()
        if parsed["format"] == "json":
            sys.stdout.write(_render_json(result, compact=False))
        else:
            print_result(result)
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
        print("Commands: validate, run, result, explain, inspect, report, control, normalize, eval, version")
        sys.exit(0)

    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <command> <file> [<file2>] [--geotask <file.yaml>]")
        print("Commands: validate, run, result, explain, inspect, report, control, normalize, eval, version")
        print()
        print("Examples:")
        print(f"  {cmd_name} validate examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} run examples/geotask_core_lite.yaml")
        print(
            f"  {cmd_name} run examples/core/uav_arrival_ground_clearance_release.yaml "
            "--format v1-json --output execution-result.json"
        )
        print(f"  {cmd_name} result validate execution-result.json")
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

    if command == "result":
        cmd_result(sys.argv[2:])
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
        print(f"Available commands: validate, run, result, explain, inspect, report, control, normalize, eval, version")
        sys.exit(1)

    commands[command](path)


if __name__ == "__main__":
    main()
