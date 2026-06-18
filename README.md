# GeoTask Core

**Lightweight spatial task representation for LLMs.**

GeoTask Core 是一种面向大模型的轻量级空间任务表达格式，让大模型能够理解空间对象、
空间关系和计算任务，并能被本地确定性算子验证。

> **GeoTask Core only defines a lightweight spatial task representation.**
> Heavy audit, domain-specific rule packs, data connectors, and business
> workflows should live outside the Core.

> **GeoTask Core 只定义轻量空间任务表达。审计、行业规则包、数据连接器和业务流程不属于 Core。**

> **Migration note**: STIR was the original prototype name. The project has been
> renamed to GeoTask to better communicate its purpose: representing spatial
> tasks for LLMs. Old `stir` CLI and `stir:` YAML field are temporarily
> supported but deprecated. See [MIGRATION.md](MIGRATION.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

## What GeoTask Core Is

- A **human-readable and LLM-readable YAML format** for describing spatial objects,
  spatial operations, and spatial tasks.
- A **minimal deterministic runtime** that verifies LLM spatial reasoning outputs.
- A **lightweight normalizer** that extracts structured results from unstructured
  LLM text output.

## What GeoTask Core Is NOT

- ❌ **Not a GeoJSON replacement.** GeoJSON is a data interchange format for
  geographic features. GeoTask Core is a task representation format that includes
  operations, questions, and verification.
- ❌ **Not a drone / UAV system.** GeoTask UAV is a separate domain-specific rule
  pack built on top of GeoTask Core.
- ❌ **Not a heavy audit platform.** GeoTask Audit is a separate component for
  provenance tracking and compliance verification.
- ❌ **Not a GIS library.** No PostGIS, GDAL, Shapely, or GeoPandas. The only
  dependency beyond stdlib is PyYAML.

## Relationship to Other GeoTask Components

```
┌──────────────────────────────────────────┐
│              GeoTask Audit                │  ← Provenance, compliance, heavy audit
├──────────────────────────────────────────┤
│  GeoTask UAV   │  GeoTask Eval           │  ← Domain rule packs, evaluation
├───────────────┴──────────────────────────┤
│          GeoTask Core (this repo)        │  ← Format + minimal runtime
└──────────────────────────────────────────┘
```

- **GeoTask Core**: The format. Self-contained, minimal, verifiable.
- **GeoTask Eval**: Evaluates LLM outputs against Core ground truth.
- **GeoTask UAV**: Domain-specific rule packs and object libraries for UAV operations.
- **GeoTask Audit**: Provenance tracking, audit trails, output contracts.

## Quick Start

```bash
# Clone
git clone https://gitee.com/stpku/GeoTask.git
cd geotask

# Install in development mode
pip install -e .
pip install pytest  # for tests

# Run tests
pytest

# CLI examples
geotask validate examples/geotask_core_lite.yaml
geotask run examples/geotask_core_lite.yaml
geotask normalize examples/deepseek_output_sample.txt
```

## Example Input

```yaml
# examples/geotask_core_lite.yaml
geotask:
  version: "0.1-lite"
  name: "GeoTask Core"
  goal: "LLM-readable spatial task representation"

space:
  crs: "local_xy_m"
  unit: "meter"
  axes:
    x: "east"
    y: "north"

objects:
  takeoff:
    type: "point"
    xy: [0, 0]
  school:
    type: "point"
    xy: [120, 80]
  route:
    type: "line"
    points:
      - [-200, 0]
      - [400, 0]
  zone:
    type: "rect"
    bbox: [250, -100, 350, 100]

ops:
  distance_2d: "sqrt((x1 - x2)^2 + (y1 - y2)^2)"
  line_intersects_rect: "true if any part of a line segment crosses or touches the rectangle"

task:
  questions:
    - "Calculate the 2D distance from takeoff to school."
    - "Determine whether route intersects zone."
```

## Example Output

```bash
$ geotask run examples/geotask_core_lite.yaml
```

```yaml
measurements:
  - name: takeoff_to_school_distance
    value: 144.22
    unit: meter
    object_refs: [takeoff, school]
    verified_by: distance_2d
  - name: route_intersects_zone
    value: true
    unit: null
    object_refs: [route, zone]
    verified_by: line_intersects_rect

conclusion:
  summary: "takeoff_to_school_distance=144.22 meter; route_intersects_zone=true"
  external_data_used: false

verified_by:
  - operation: distance_2d
    result: "144.22 meter"
  - operation: line_intersects_rect
    result: "true"
```

## CLI Usage

```bash
# Validate a GeoTask document
geotask validate examples/geotask_core_lite.yaml

# Run a GeoTask document (validate + execute)
geotask run examples/geotask_core_lite.yaml

# Normalize LLM output into structured format
geotask normalize examples/deepseek_output_sample.txt

# Also works with python -m
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
python -m geotask_core.cli run examples/geotask_core_lite.yaml
python -m geotask_core.cli normalize examples/deepseek_output_sample.txt
```

## GeoTask Normalizer

GeoTask Normalizer converts model outputs (natural language, YAML-like, Markdown)
into structured GeoTask Results and verifies them against local deterministic operators.

```bash
# Extract only (without verification)
geotask normalize examples/deepseek_output_sample.txt

# Extract + verify against GeoTask Core ground truth
geotask normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml
```

Output includes `verified` / `contradicted` / `need_review` status for each measurement,
along with expected values and differences for numeric checks.

> GeoTask Normalizer 将模型输出归一化为统一 GeoTask Result，并用本地确定性算子验证。

## GeoTask Eval Lite

GeoTask Eval Lite compares deterministic GeoTask Core results with normalized LLM outputs.

> GeoTask Eval Lite 用于比较 GeoTask Core 本地确定性结果与大模型输出归一化结果是否一致。

```bash
# Evaluate LLM output against Core ground truth
geotask eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt
python -m geotask_core.cli eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt
```

**Scoring rubric** (100 points total):

| Check              | Points | What it verifies                                     |
|--------------------|--------|------------------------------------------------------|
| Distance match     | 40     | `takeoff_to_school_distance` within tolerance        |
| Intersection match | 40     | `route_intersects_zone` boolean matches              |
| Operator match     | 15     | All expected operators present in model output       |
| External data      | 5      | `external_data_used` flag matches                    |

**Example eval output**:

```yaml
score:
  total: 100
  distance_match: true
  intersection_match: true
  operator_match: true
  external_data_used_match: true

details:
  expected_distance: 144.22
  actual_distance: 144.22
  expected_intersection: true
  actual_intersection: true
  expected_operations:
    - distance_2d
    - line_intersects_rect
  actual_operations:
    - distance_2d
    - line_intersects_rect

warnings: []
errors: []
```

See [`docs/eval_spec.md`](docs/eval_spec.md) for the full evaluation specification.

## GeoTask Encoding Benchmark

GeoTask Encoding Benchmark compares natural language, GeoTask YAML, and compact DSL encodings for spatial tasks. It evaluates approximate token cost, normalization success, verification success, and benchmark score.

The current benchmark uses **deterministic simulated outputs** and does not claim live LLM accuracy. It is intended to evaluate token cost, normalization behavior, verification behavior, and patent evidence reproducibility.

```bash
python benchmarks/encoding_v0_1/run_benchmark.py
```

Results are output to `benchmarks/encoding_v0_1/outputs/` and copied to `patent_evidence/03_benchmark/`.

See [`docs/encoding_benchmark_v0_1.md`](docs/encoding_benchmark_v0_1.md) for the full benchmark report,
and [`docs/patent_evidence_guide.md`](docs/patent_evidence_guide.md) for patent evidence usage.

### Benchmark v0.2 (Expanded)

The v0.2 benchmark extends to **24 cases** across **6 operators**, **5 case groups**, and **8 error types** — a 6× expansion over v0.1.

```bash
python benchmarks/encoding_v0_2/run_benchmark.py
```

**Results**: natural_language 96% | geotask_yaml 100% | compact_dsl 100% status match.
Compact DSL uses 35% fewer tokens than natural language while achieving perfect verification.

New in v0.2: `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, `altitude_overlap` operators; unit mismatch, Chinese negation, Markdown/YAML extraction robustness tests.

See `benchmarks/encoding_v0_2/` and `patent_evidence/07_benchmark_v0_2/` for details.

### Core Normalizer / Verifier v0.3

v0.3 is the **production Core backfill** of stable v0.2 capabilities. The Core Normalizer and Verifier now support all 6 operators, unified status hierarchy (`invalid_operator` > `invalid_reference` > `contradicted` > `need_review` > `verified`), invalid operator/reference detection, unit mismatch detection, and Chinese negation for all boolean operators.

```bash
# Run production end-to-end tests
pytest tests/test_core_normalizer_verifier_v0_3.py tests/test_ops_v0_3.py
```

See [`docs/core_normalizer_verifier_v0_3.md`](docs/core_normalizer_verifier_v0_3.md) and `patent_evidence/08_core_v0_3/` for details.

## Supported Object Types (v0.1-lite)

| Type  | Fields               | Description                         |
|-------|----------------------|-------------------------------------|
| point | `xy: [x, y]`         | A 2D point                          |
| line  | `points: [[x,y],...]`| A line segment (2+ points)          |
| rect  | `bbox: [min_x, min_y, max_x, max_y]` | Axis-aligned rectangle |

## Supported Operators (v0.1-lite)

| Operator               | Input                        | Output | Description                              |
|------------------------|------------------------------|--------|------------------------------------------|
| `distance_2d`          | two points                   | float  | 2D Euclidean distance                    |
| `line_intersects_rect` | line segment + rect bbox     | bool   | Whether line touches or crosses rectangle |
| `point_to_line_distance_2d` | point + line           | float  | Point-to-line-segment distance (v0.3+)   |
| `rect_contains_point` | rect + point                  | bool   | Rectangle containment (v0.3+)            |
| `time_overlap`       | two time intervals            | bool   | Time interval overlap (v0.3+)            |
| `altitude_overlap`   | two altitude ranges           | bool   | Altitude range overlap (v0.3+)           |

## Architecture

```
src/geotask_core/
├── __init__.py        # Package init
├── models.py          # Dataclasses: PointObject, LineObject, RectObject, StirDocument
├── parser.py          # YAML loader + validator
├── ops.py             # Deterministic 6 operators
├── runner.py          # Generic type-based auto-detection runner
├── normalizer.py      # Multi-operator normalizer with error detection
├── verifier.py        # Verifier with unified status hierarchy
├── result_schema.py   # Status/reason constants + overall_status computation
├── evaluator.py       # Compare Core results with normalized LLM outputs
└── cli.py             # CLI: validate, run, normalize, eval
```

## Design Principles

See [`docs/design_principles.md`](docs/design_principles.md):

1. **Core Must Be Light** — No heavy dependencies, no platform features.
2. **Format and Evaluation Are Separate** — Core is the format; evaluation is external.
3. **General-Purpose First** — Universal object types and operators only.
4. **LLM-Friendly First** — Format designed for LLM readability.
5. **Incrementally Enhanceable** — Start small, grow intentionally.

## Open Source Boundary

See [`docs/open_source_boundary.md`](docs/open_source_boundary.md).

**Open Source (this repo)**:
- GeoTask Core format spec and examples
- Core parser, operators, runner, lite normalizer
- Simple evaluator

**Not Open Source**:
- Full GeoTask Runtime
- UAV Rule Pack
- Real-world data connectors
- Audit / review backend
- Customer case studies
- Failure sample library

## From STIR to GeoTask

STIR was the original prototype name. The project has been renamed to GeoTask
to better communicate its purpose: representing spatial tasks for LLMs.

Old `stir` CLI and `stir:` YAML top-level field are temporarily supported
but deprecated. See [MIGRATION.md](MIGRATION.md) for migration guidance.

## License

MIT License — see [`LICENSE`](LICENSE).

Patents covering the underlying **system and method** (spatial task representation,
object–operator–proposition binding, agent orchestration, deterministic verification)
are retained separately. The MIT License covers the software code and documentation,
not patent rights. See [`docs/patent_boundary.md`](docs/patent_boundary.md).

## Repository

- **Gitee (Primary)**: [https://gitee.com/stpku/GeoTask](https://gitee.com/stpku/GeoTask)
