#!/usr/bin/env python3
"""Standalone entrypoint for GeoTask Verification Quality Benchmark v0.2.

The canonical perturbation benchmark implementation lives in the installed
``geotask_core`` package. This wrapper keeps the Reference Agent teaching
workspace self-contained while preserving one implementation of the benchmark.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SRC_ROOT = next(
    (
        parent / "src"
        for parent in Path(__file__).resolve().parents
        if (parent / "src" / "geotask_core").is_dir()
    ),
    None,
)
if _SRC_ROOT is not None and str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from geotask_core.verification_quality_benchmark import (  # noqa: E402
    run_verification_quality_benchmark_command,
)


def main() -> int:
    args = ["--suite", "perturbation", *sys.argv[1:]]
    if "--format" not in args:
        args = ["--format", "text", *args]
    _, exit_code = run_verification_quality_benchmark_command(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
