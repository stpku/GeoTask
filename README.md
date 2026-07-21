# GeoTask Core

**Lightweight spatial task representation for LLMs with deterministic verification.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

GeoTask Core lets you describe spatial objects, operations, and tasks in a YAML format that LLMs can read and reason about. It then verifies every computed result using local deterministic operators. No network calls, no model dependencies, no ambiguity. If an LLM claims a distance is 144.22 meters, GeoTask Core computes it locally and confirms or contradicts the claim.

**Why agents need GeoTask.** LLMs are fluent but unreliable with spatial reasoning. They can hallucinate distances, flip coordinates, or misinterpret geometric relationships. GeoTask Core gives agent frameworks a verifiable spatial layer: define the objects, state the assertions, run the operators, and inspect the assurance level. Every result carries a provenance chain from object references through operator contracts to deterministic computation.

## Quickstart

```bash
git clone https://github.com/GeoTask/geotask-core.git
cd geotask-core
pip install -e .
pip install pytest

geotask validate examples/core/v1_minimal_distance.yaml
geotask run examples/core/v1_minimal_distance.yaml
pytest
```

## Minimal Example

```yaml
geotask:
  id: "example"
  schema_version: "1.0"

objects:
  a: {type: "point", coordinates: [0, 0]}
  b: {type: "point", coordinates: [3, 4]}

operator_set: [distance_2d]

tasks:
  - id: "calc"
    assertions:
      - id: "ab"
        operator: "distance_2d"
        object_refs: ["a", "b"]
```

This produces a verified result: `ab = 5.0 meter` with `assurance_level: local_deterministic`.

## Core Concepts

```
objects => assertions => execution => result => assurance
```

1. **Objects.** Declare spatial primitives: `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`.
2. **Assertions.** Bind objects to operators with explicit references. `{operator: "distance_2d", object_refs: ["a", "b"]}`.
3. **Execution.** Dispatch assertions through the local executor. Each assertion becomes a `CheckResult` with a value, unit, and status.
4. **Result.** A `GeotaskResult` aggregates all checks, summary counts, and derivation metadata.
5. **Assurance.** Every result carries an `AssuranceLevel` from `unverified` (0) to `local_deterministic` (3) and beyond, letting callers decide when a result is trustworthy.

## Main Chain

```
parse YAML => canonicalize (v1 IR) => validate => execute => GeotaskResult
```

The canonical IR (`CanonicalDocument`) is the single source of truth between all stages. Validation produces structured diagnostics. Execution dispatches assertions through the operator registry and collects results with assurance metadata.

## Current Capabilities

**Operators** (6, all deterministic):

| Operator | Input | Output |
|---|---|---|
| `distance_2d` | point, point | number |
| `line_intersects_rect` | polyline, rect | boolean |
| `point_to_line_distance_2d` | point, polyline | number |
| `rect_contains_point` | rect, point | boolean |
| `time_overlap` | time_interval, time_interval | boolean |
| `altitude_overlap` | altitude_interval, altitude_interval | boolean |

**Object types** (5): `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`.

**Dependencies:** Python 3.10+ and PyYAML. Zero GIS libraries.

## What's Not Here

- **No model executor.** GeoTask Core only runs local deterministic operators. It does not call any LLM.
- **No orchestrator.** Task routing, model selection, and pipeline orchestration live in the private GeoTask Runtime.
- **No domain packs.** Industry-specific rules, data connectors, and scoring logic are separate.
- **No benchmarks.** Encoding benchmarks and evaluation suites are internal tooling.
- **No network I/O.** Core is entirely offline and deterministic.

## CLI

```bash
geotask validate <file.yaml>     # check document structure
geotask run <file.yaml>          # validate + execute
geotask normalize <output.txt>   # extract structured results from LLM output
geotask eval <file.yaml> <txt>   # compare LLM output against ground truth
```

## License

MIT. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, code style, and PR process. Architecture details are in [docs/architecture.md](docs/architecture.md). Operator extension guide is in [docs/operator-guide.md](docs/operator-guide.md).
