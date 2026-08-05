# GeoTask Core Conformance and Performance Benchmark v0.1

## 1. Purpose

The public Core benchmark provides one reproducible, offline release gate for the implemented GeoTask Core pipeline. It measures two different properties:

1. **Conformance** — fixed fictional tasks continue to validate, execute, serialize, deserialize, and replay with the expected semantics.
2. **Local performance regression** — the production pipeline remains below a configurable latency guardrail on the machine running the benchmark.

The benchmark does not evaluate a language model, compare providers, access a network, fetch evidence, execute production actions, or establish cross-hardware performance claims.

## 2. Public Artifact

```text
Artifact ID: geotask.core-benchmark-report
Schema: schemas/geotask-core-benchmark-v0.1.schema.json
Schema version: 0.1
Wrapper: core_benchmark
```

Generate a report:

```bash
geotask benchmark core \
  --iterations 30 \
  --warmup 3 \
  --max-p95-ms 100 \
  --enforce-performance \
  --format json \
  --output core-benchmark.json
```

Validate the retained report without rerunning the benchmark:

```bash
geotask artifact validate \
  geotask.core-benchmark-report \
  core-benchmark.json \
  --format json
```

Artifact validation checks the registered JSON Schema and strict report cross-field invariants. It does not repeat timing measurements or deterministic execution.

## 3. Fixed Conformance Cases

The v0.1 case set contains nine fictional documents and covers all thirteen public deterministic operators:

| Case | Operators and contracts |
|---|---|
| `distance_2d` | Point-to-point distance and horizontal-unit inheritance |
| `planar_topology` | Point-to-line distance, line/rectangle intersection, rectangle containment |
| `polygon_multi_polyline` | Point-in-polygon and grouped-route/rectangle intersection |
| `time_altitude` | Closed time-window and altitude-interval overlap |
| `provenance_evidence` | Distance execution plus validated assertion evidence propagation |
| `trajectory_duration` | Moving-object binding plus strictly ordered discrete trajectory duration |
| `trajectory_segments` | Adjacent-sample binding plus per-segment duration, planar distance, and average speed |
| `trajectory_classifications` | Caller-declared stationary and observation-gap thresholds plus closed stop/move/gap/unverifiable classification |
| `trajectory_acceleration` | Segment-midpoint representative times, adjacent segment-average speed changes, scalar acceleration estimates, and gap-driven unverifiable transitions |

Each case uses only local fictional coordinates and metadata. No benchmark case represents real operational, regulatory, customer, or external evidence.

For every case, the runner requires:

- canonical validation without blocking errors;
- expected outputs exactly matching the fixed contract;
- expected `evidence_refs` exactly matching the declared fictional provenance;
- `overall.status=verified`;
- result serialization and strict deserialization round trip;
- a second execution with the same semantic SHA-256 after execution timestamps are removed.

The benchmark imports production `geotask_core` Parser/Canonical/Validator/Executor/Result code. It does not contain or call a benchmark-local verifier.

## 4. Performance Pipeline

Each measured sample executes this pipeline:

```text
JSON decode
→ Canonical IR construction
→ Canonical validation
→ deterministic execution
→ Result serialization
```

The execution phase intentionally calls the normal fail-closed public executor, which validates the Canonical document again before dispatching operators. The measurement therefore represents the supported production path rather than an optimized internal shortcut.

Metrics are reported for:

```text
decode
canonicalize
validate
execute
serialize
pipeline
```

For each stage and case, the report records:

```text
sample_count
min_ms
median_ms
p95_ms
max_ms
```

`p95_ms` uses the nearest-rank method over the recorded samples. Throughput is the number of completed cases divided by the sum of measured full-pipeline durations.

## 5. Guardrail Semantics

The default guardrail is:

```text
pipeline_p95_ms <= 100.0
```

Without `--enforce-performance`, a failed performance guardrail remains visible in the report but does not make the overall benchmark fail when conformance passes. With `--enforce-performance`, both conformance and the performance guardrail must pass.

This threshold is deliberately broad and is intended to detect severe local regressions or accidental external work. It is not a hardware benchmark, service-level objective, capacity estimate, or guarantee of production latency.

Comparisons are meaningful only when the environment, Python implementation, GeoTask version, configuration, machine load, and hardware are controlled. The report therefore records environment metadata and explicitly sets:

```text
cross_hardware_comparison_supported = false
```

## 6. Exit Codes

```text
0  report generated and overall benchmark passed
1  invalid command, configuration, output path, or benchmark execution failure
2  benchmark report generated but overall benchmark failed
```

Exit code `2` is primarily used when `--enforce-performance` is enabled and the configured p95 threshold is exceeded, or when a conformance case fails.

## 7. Report Trust Boundary

A valid report proves only that:

- its structure matches the registered Schema;
- strict internal counts, states, metrics, case ordering, and guardrail relationships are self-consistent;
- the report declares the mandatory public boundaries;
- the generating benchmark recorded successful production-Core conformance when `conformance.valid=true`.

A retained report does not prove that its timing measurements were produced on a trusted machine. For release evidence, retain the report together with the Git commit, package version, CI job identity, and an external file digest or signed build provenance.

The benchmark never claims:

- live LLM accuracy or superiority;
- provider availability, account access, quota, billing, or model compatibility;
- production Runtime readiness;
- external evidence authenticity;
- regulatory or domain approval;
- comparable performance across different machines.
