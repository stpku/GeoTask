"""GeoTask Core CLI.

Usage:
    geotask validate <file.yaml>
    geotask run <file.yaml>
    geotask normalize <file.txt>
    geotask eval <file.yaml> <model_output.txt>
    python -m geotask_core.cli validate <file.yaml>
    python -m geotask_core.cli run <file.yaml>
    python -m geotask_core.cli normalize <file.txt>
    python -m geotask_core.cli eval <file.yaml> <model_output.txt>

The old `stir` CLI command is deprecated but still works as an alias.
"""

import sys
from pathlib import Path

from geotask_core.parser import load_geotask, validate_geotask
from geotask_core.runner import run_geotask
from geotask_core.normalizer import normalize_model_output
from geotask_core.evaluator import evaluate_model_output


def _get_command_name() -> str:
    """Detect which command name was used (geotask or deprecated stir)."""
    return Path(sys.argv[0]).stem


def cmd_validate(path: str):
    """Validate a GeoTask YAML file."""
    print(f"[validate] {path}")
    data = load_geotask(path)
    errors = validate_geotask(data)
    if data.get("_deprecated_stir_field"):
        print("  Warning: Using deprecated 'stir' top-level field. Please migrate to 'geotask'.", file=sys.stderr)
    if errors:
        print(f"  Validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  Validation OK")
    return data


def cmd_run(path: str):
    """Run a GeoTask document."""
    print(f"[run] {path}")
    data = load_geotask(path)
    errors = validate_geotask(data)
    if data.get("_deprecated_stir_field"):
        print("  Warning: Using deprecated 'stir' top-level field. Please migrate to 'geotask'.", file=sys.stderr)
    if errors:
        print(f"  Validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    result = run_geotask(data)
    print_result(result)
    return result


def cmd_normalize(path: str):
    """Normalize an LLM output file."""
    print(f"[normalize] {path}")
    text = Path(path).read_text(encoding="utf-8")
    result = normalize_model_output(text)
    print_result(result)
    return result


def cmd_eval(geotask_path: str, model_path: str):
    """Evaluate model output against GeoTask Core ground truth."""
    print(f"[eval] core={geotask_path}  model={model_path}")

    # Run Core for ground truth
    data = load_geotask(geotask_path)
    errors = validate_geotask(data)
    if data.get("_deprecated_stir_field"):
        print("  Warning: Using deprecated 'stir' top-level field. Please migrate to 'geotask'.", file=sys.stderr)
    if errors:
        print(f"  Core validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    core_result = run_geotask(data)

    # Normalize model output
    text = Path(model_path).read_text(encoding="utf-8")
    normalized = normalize_model_output(text)

    # Evaluate
    score = evaluate_model_output(core_result, normalized)
    print_result(score)
    return score


def print_result(result: dict):
    """Print a result dict as YAML."""
    import yaml
    print(yaml.dump(result, allow_unicode=True, default_flow_style=False, sort_keys=False))


def main():
    cmd_name = _get_command_name()
    if cmd_name == "stir":
        print("Warning: 'stir' command is deprecated. Please use 'geotask' instead.", file=sys.stderr)

    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <command> <file> [<file2>]")
        print("Commands: validate, run, normalize, eval")
        print()
        print("Examples:")
        print(f"  {cmd_name} validate examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} run examples/geotask_core_lite.yaml")
        print(f"  {cmd_name} normalize examples/deepseek_output_sample.txt")
        print(f"  {cmd_name} eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt")
        print()
        print(f"  python -m geotask_core.cli validate examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli run examples/geotask_core_lite.yaml")
        print(f"  python -m geotask_core.cli normalize examples/deepseek_output_sample.txt")
        print(f"  python -m geotask_core.cli eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt")
        print(f"")
        print(f"Backward compatibility: the old 'stir' YAML field and 'stir' CLI are accepted but deprecated.")
        sys.exit(1)

    command = sys.argv[1]

    # eval takes two file arguments
    if command == "eval":
        if len(sys.argv) < 4:
            print(f"Usage: {cmd_name} eval <geotask.yaml> <model_output.txt>")
            sys.exit(1)
        cmd_eval(sys.argv[2], sys.argv[3])
        return

    path = sys.argv[2]

    commands = {
        "validate": cmd_validate,
        "run": cmd_run,
        "normalize": cmd_normalize,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available commands: validate, run, normalize, eval")
        sys.exit(1)

    commands[command](path)


if __name__ == "__main__":
    main()
