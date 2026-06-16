"""STIR-Core CLI.

Usage:
    stir validate <file.yaml>
    stir run <file.yaml>
    stir normalize <file.txt>
    stir eval <file.yaml> <model_output.txt>
    python -m stir_core.cli validate <file.yaml>
    python -m stir_core.cli run <file.yaml>
    python -m stir_core.cli normalize <file.txt>
    python -m stir_core.cli eval <file.yaml> <model_output.txt>
"""

import sys
from pathlib import Path

from stir_core.parser import load_stir, validate_stir
from stir_core.runner import run_stir
from stir_core.normalizer import normalize_model_output
from stir_core.evaluator import evaluate_model_output


def cmd_validate(path: str):
    """Validate a STIR YAML file."""
    print(f"[validate] {path}")
    data = load_stir(path)
    errors = validate_stir(data)
    if errors:
        print(f"  Validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  Validation OK")
    return data


def cmd_run(path: str):
    """Run a STIR document."""
    print(f"[run] {path}")
    data = load_stir(path)
    errors = validate_stir(data)
    if errors:
        print(f"  Validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    result = run_stir(data)
    print_result(result)
    return result


def cmd_normalize(path: str):
    """Normalize an LLM output file."""
    print(f"[normalize] {path}")
    text = Path(path).read_text(encoding="utf-8")
    result = normalize_model_output(text)
    print_result(result)
    return result


def cmd_eval(stir_path: str, model_path: str):
    """Evaluate model output against STIR-Core ground truth."""
    print(f"[eval] core={stir_path}  model={model_path}")

    # Run Core for ground truth
    data = load_stir(stir_path)
    errors = validate_stir(data)
    if errors:
        print(f"  Core validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    core_result = run_stir(data)

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
    if len(sys.argv) < 3:
        print("Usage: stir <command> <file> [<file2>]")
        print("Commands: validate, run, normalize, eval")
        print()
        print("Examples:")
        print("  stir validate examples/stir_core_lite.yaml")
        print("  stir run examples/stir_core_lite.yaml")
        print("  stir normalize examples/deepseek_output_sample.txt")
        print("  stir eval examples/stir_core_lite.yaml examples/deepseek_output_sample.txt")
        print()
        print("  python -m stir_core.cli validate examples/stir_core_lite.yaml")
        print("  python -m stir_core.cli run examples/stir_core_lite.yaml")
        print("  python -m stir_core.cli normalize examples/deepseek_output_sample.txt")
        print("  python -m stir_core.cli eval examples/stir_core_lite.yaml examples/deepseek_output_sample.txt")
        sys.exit(1)

    command = sys.argv[1]

    # eval takes two file arguments
    if command == "eval":
        if len(sys.argv) < 4:
            print("Usage: stir eval <stir.yaml> <model_output.txt>")
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
