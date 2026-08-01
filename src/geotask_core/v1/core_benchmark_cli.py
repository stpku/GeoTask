"""CLI parsing and rendering for the public Core benchmark command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

import yaml

from geotask_core.v1.core_benchmark import run_core_benchmark
from geotask_core.v1.core_benchmark_contract import (
    CoreBenchmarkFormatError,
    DEFAULT_BENCHMARK_ITERATIONS,
    DEFAULT_BENCHMARK_WARMUP_ITERATIONS,
    DEFAULT_MAX_PIPELINE_P95_MS,
)


def print_core_benchmark_usage(stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    print(
        "Usage: geotask benchmark core [--iterations N] [--warmup N] "
        "[--max-p95-ms N] [--enforce-performance] "
        "[--format json|yaml] [--output <file>|-] [--compact]",
        file=output,
    )
    print(
        "Runs fixed fictional cases through production Core only. The default "
        "performance threshold is observational unless --enforce-performance is set.",
        file=output,
    )


def _positive_integer(value: str, flag: str, *, allow_zero: bool = False) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{flag} requires an integer") from exc
    minimum = 0 if allow_zero else 1
    if parsed < minimum:
        raise ValueError(f"{flag} must be >= {minimum}")
    return parsed


def _positive_number(value: str, flag: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{flag} requires a number") from exc
    if not parsed > 0 or parsed == float("inf") or parsed != parsed:
        raise ValueError(f"{flag} must be a finite positive number")
    return parsed


def parse_core_benchmark_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "help": False,
        "iterations": DEFAULT_BENCHMARK_ITERATIONS,
        "warmup_iterations": DEFAULT_BENCHMARK_WARMUP_ITERATIONS,
        "max_pipeline_p95_ms": DEFAULT_MAX_PIPELINE_P95_MS,
        "enforce_performance": False,
        "format": "json",
        "output_path": None,
        "compact": False,
    }
    value_flags = {
        "--iterations": "iterations",
        "--warmup": "warmup_iterations",
        "--max-p95-ms": "max_pipeline_p95_ms",
        "--format": "format",
        "--output": "output_path",
    }
    seen: set[str] = set()
    index = 0
    while index < len(args):
        argument = args[index]
        if argument in {"--help", "-h"}:
            parsed["help"] = True
            index += 1
            continue
        if argument == "--enforce-performance":
            if argument in seen:
                raise ValueError("--enforce-performance may be provided only once")
            seen.add(argument)
            parsed["enforce_performance"] = True
            index += 1
            continue
        if argument == "--compact":
            if argument in seen:
                raise ValueError("--compact may be provided only once")
            seen.add(argument)
            parsed["compact"] = True
            index += 1
            continue
        if argument in value_flags:
            if argument in seen:
                raise ValueError(f"{argument} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise ValueError(f"{argument} requires a value")
            seen.add(argument)
            raw_value = args[index + 1]
            target = value_flags[argument]
            if argument == "--iterations":
                parsed[target] = _positive_integer(raw_value, argument)
            elif argument == "--warmup":
                parsed[target] = _positive_integer(raw_value, argument, allow_zero=True)
            elif argument == "--max-p95-ms":
                parsed[target] = _positive_number(raw_value, argument)
            else:
                parsed[target] = raw_value
            index += 2
            continue
        raise ValueError(f"unknown benchmark option: {argument}")

    output_format = str(parsed["format"])
    if output_format not in {"json", "yaml"}:
        raise ValueError(
            f"unsupported_benchmark_format: {output_format}. Supported formats: json, yaml"
        )
    if parsed["compact"] and output_format != "json":
        raise ValueError("--compact is supported only with --format json")
    return parsed


def _render_report(report: dict[str, object], *, output_format: str, compact: bool) -> str:
    if output_format == "json":
        if compact:
            return json.dumps(
                report,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ) + "\n"
        return json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
    return yaml.safe_dump(report, allow_unicode=True, sort_keys=False)


def _write_report(rendered: str, output_path: object, stdout: TextIO) -> None:
    if output_path is None or output_path == "-":
        stdout.write(rendered)
        return
    target = Path(str(output_path)).resolve()
    if target.exists() and not target.is_file():
        raise ValueError("--output must identify a file")
    try:
        target.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot write benchmark output {str(output_path)!r}: {exc}") from exc


def run_core_benchmark_command(
    args: list[str],
    *,
    stdout: TextIO | None = None,
) -> tuple[dict[str, object] | None, int]:
    """Run the Core benchmark command and return ``(report, exit_code)``."""
    output = stdout or sys.stdout
    parsed = parse_core_benchmark_args(args)
    if parsed["help"]:
        print_core_benchmark_usage(output)
        return None, 0

    report = run_core_benchmark(
        iterations=int(parsed["iterations"]),
        warmup_iterations=int(parsed["warmup_iterations"]),
        max_pipeline_p95_ms=float(parsed["max_pipeline_p95_ms"]),
        enforce_performance=bool(parsed["enforce_performance"]),
    )
    rendered = _render_report(
        report,
        output_format=str(parsed["format"]),
        compact=bool(parsed["compact"]),
    )
    _write_report(rendered, parsed["output_path"], output)
    valid = bool(report["core_benchmark"]["overall"]["valid"])
    return report, 0 if valid else 2


__all__ = [
    "CoreBenchmarkFormatError",
    "parse_core_benchmark_args",
    "print_core_benchmark_usage",
    "run_core_benchmark_command",
]
