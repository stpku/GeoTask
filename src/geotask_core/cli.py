"""GeoTask Core CLI.

Usage:
    geotask validate <file.yaml>
    geotask run <file.yaml>
    geotask normalize <file.txt> [--geotask <file.yaml>]
    geotask eval <file.yaml> <model_output.txt>
    python -m geotask_core.cli validate <file.yaml>
    python -m geotask_core.cli run <file.yaml>
    python -m geotask_core.cli normalize <file.txt> [--geotask <file.yaml>]
    python -m geotask_core.cli eval <file.yaml> <model_output.txt>

The old `stir` CLI command is deprecated but still works as an alias.
"""

import sys
import json
from pathlib import Path

from geotask_core.parser import (
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


def cmd_run(path: str):
    """Run a GeoTask document."""
    print(f"[run] {path}")
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

    result = run_geotask(data)
    print_result(result)
    return result


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


def cmd_inspect(args: list[str]):
    """Inspect public-safe Core metadata."""
    if not args or args[0] in ("--help", "-h"):
        print("Usage: geotask inspect <operators|schema|examples> [operator_name]")
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

    if subject == "examples":
        result = _example_index()
        print_result(result)
        return result

    print(f"Unknown inspect target: {subject}", file=sys.stderr)
    print("Available inspect targets: operators, schema, examples", file=sys.stderr)
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

    if len(sys.argv) >= 2 and sys.argv[1] in ("--help", "-h"):
        print(f"Usage: {cmd_name} <command> <file> [<file2>] [--geotask <file.yaml>]")
        print("Commands: validate, run, explain, inspect, report, normalize, eval")
        sys.exit(0)

    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <command> <file> [<file2>] [--geotask <file.yaml>]")
        print("Commands: validate, run, explain, inspect, report, normalize, eval")
        print()
        print("Examples:")
        print(f"  {cmd_name} validate examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} run examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} normalize examples/deepseek_output_sample.txt")
        print(f"  {cmd_name} normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt")
        print(f"  {cmd_name} inspect operators")
        print(f"  {cmd_name} explain examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} report examples/geotask_core_lite.yaml --format json")
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

    if command == "inspect":
        cmd_inspect(sys.argv[2:])
        return

    if command == "explain":
        cmd_explain(sys.argv[2])
        return

    if command == "report":
        cmd_report(sys.argv[2], sys.argv[3:])
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
        "run": cmd_run,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available commands: validate, run, explain, inspect, report, normalize, eval")
        sys.exit(1)

    commands[command](path)


if __name__ == "__main__":
    main()
