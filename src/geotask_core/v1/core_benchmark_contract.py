"""Stable identifiers and defaults for the public Core benchmark."""

from __future__ import annotations


CORE_BENCHMARK_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-core-benchmark-v0.1.schema.json"
)
CORE_BENCHMARK_SCHEMA_VERSION = "0.1"
CORE_BENCHMARK_REPORT_VERSION = "0.1"
CORE_BENCHMARK_ID = "geotask.core-conformance-performance"
CORE_BENCHMARK_VERSION = "0.1"
DEFAULT_BENCHMARK_ITERATIONS = 30
DEFAULT_BENCHMARK_WARMUP_ITERATIONS = 3
DEFAULT_MAX_PIPELINE_P95_MS = 100.0
CORE_BENCHMARK_STAGE_NAMES = (
    "decode",
    "canonicalize",
    "validate",
    "execute",
    "serialize",
    "pipeline",
)


class CoreBenchmarkFormatError(ValueError):
    """Raised when a serialized Core benchmark report is inconsistent."""


__all__ = [
    "CORE_BENCHMARK_ID",
    "CORE_BENCHMARK_REPORT_VERSION",
    "CORE_BENCHMARK_SCHEMA_ID",
    "CORE_BENCHMARK_SCHEMA_VERSION",
    "CORE_BENCHMARK_STAGE_NAMES",
    "CORE_BENCHMARK_VERSION",
    "CoreBenchmarkFormatError",
    "DEFAULT_BENCHMARK_ITERATIONS",
    "DEFAULT_BENCHMARK_WARMUP_ITERATIONS",
    "DEFAULT_MAX_PIPELINE_P95_MS",
]
