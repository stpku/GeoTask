"""Run the repository-local GeoTask TC1 proof benchmark.

Usage:
    python -m benchmarks.run_task_context_v0_1

All fixtures are synthetic. The printed numbers demonstrate deterministic
context/cost trade-offs only and must not be reported as real-world accuracy.
"""

from __future__ import annotations

from benchmarks.task_context_cases_v0_1 import tc1_cases
from benchmarks.task_context_v0_1 import format_results, run_case


def main() -> int:
    all_results = []
    for case in tc1_cases():
        all_results.extend(run_case(case))

    print("GeoTask TC1 Task Context Proof Benchmark")
    print("synthetic_fixture=true")
    print("task_outcome_regret=not_available")
    print()
    print(format_results(all_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
