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

## Architecture

```
src/geotask_core/
├── __init__.py      # Package init
├── models.py        # Dataclasses: PointObject, LineObject, RectObject, StirDocument
├── parser.py        # YAML loader + validator
├── ops.py           # Deterministic operators: distance_2d, line_intersects_rect
├── runner.py        # Auto-detection runner for spatial tasks
├── normalizer.py    # Extract structured results from LLM text output
├── evaluator.py     # Compare Core results with normalized LLM outputs
└── cli.py           # CLI: validate, run, normalize, eval
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
