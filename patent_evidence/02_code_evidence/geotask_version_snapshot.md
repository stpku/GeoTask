# GeoTask Version Snapshot

Generated for patent evidence archival.

## Repository State

| Item | Value |
|------|-------|
| Git branch | `evidence/encoding-benchmark-v0.1` |
| Base branch | `feature/normalizer-v0.2` |
| Latest commit | `9b9e1c1` — feat: GeoTask Normalizer v0.2 with verifier |
| Latest tag | `v0.1.0` (GeoTask Core) |
| pyproject version | `0.1.0` |
| Python requirement | `>=3.10` |

## Core Capabilities

| Module | Description |
|--------|-------------|
| `geotask_core` | Package init |
| `models.py` | Dataclasses: PointObject, LineObject, RectObject, StirDocument |
| `parser.py` | YAML loader + validator (`load_geotask`, `validate_geotask`) |
| `ops.py` | Deterministic operators: `distance_2d`, `line_intersects_rect` |
| `runner.py` | Auto-detection runner: `run_geotask(data) -> dict` |
| `normalizer.py` | Extract + normalize model output (`normalize_model_output`) |
| `verifier.py` | Verify normalized results against local ops (`verify_normalized_result`) |
| `evaluator.py` | Compare Core results with LLM outputs |
| `result_schema.py` | Status constants + builder functions |
| `cli.py` | CLI: validate, run, normalize, eval |

## Dependencies

- Runtime: `pyyaml>=6.0`
- Dev: `pytest>=7.0`
- Benchmark (optional): `matplotlib` (for charts)

## Supported Object Types (v0.1-lite)

- `point`: `xy: [x, y]`
- `line`: `points: [[x1,y1], [x2,y2], ...]`
- `rect`: `bbox: [min_x, min_y, max_x, max_y]`

## Supported Operators (v0.1-lite)

- `distance_2d`: 2D Euclidean distance between two points
- `line_intersects_rect`: Whether line segment intersects axis-aligned rectangle
