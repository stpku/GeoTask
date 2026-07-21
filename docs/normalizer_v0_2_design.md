# GeoTask Normalizer v0.2 Design

## Why Normalizer Is Needed

LLMs (GPT, DeepSeek, etc.) can produce correct spatial reasoning results when
given a GeoTask Core document, but their output is **unstructured**:

- Natural language (Chinese / English)
- YAML-like fragments
- Markdown lists or tables
- Mixed formats within the same response

Business systems cannot stably consume this unstructured output. The Normalizer
bridges this gap by:

1. **Extracting** structured measurements from unstructured text
2. **Verifying** claims against local deterministic GeoTask operators
3. **Producing** a unified GeoTask Result with verification status

> **GeoTask Normalizer does not replace deterministic computation. It extracts
> model claims and verifies them against local GeoTask operators.**

> GeoTask Normalizer 不替代确定性计算，它负责抽取模型声明，并用本地 GeoTask 算子
> 验证这些声明。

## Supported Input Types (v0.2)

| Format | Example | Extraction |
|--------|---------|------------|
| Chinese natural language | "距离为 144.22 米" | `re.search` patterns |
| English natural language | "distance is 144.22 meter" | `re.search` patterns |
| YAML-like | `value: 144.22` | regex value matching |
| Markdown | `- distance: 144.22 meter` | regex value matching |

## Extraction Pipeline

```
Raw LLM text
    │
    ├─ 1. Distance extraction
    │     ├─ Chinese: 距离/米 patterns
    │     ├─ English: distance/meter patterns
    │     ├─ YAML/Markdown: value: NNN
    │     └─ sqrt() ≈ value
    │
    ├─ 2. Intersection extraction
    │     ├─ Chinese negation FIRST: 不相交, 不存在相交
    │     ├─ Chinese affirmation: 相交, 存在相交
    │     ├─ English negation: does not intersect
    │     └─ English affirmation: intersects, cross
    │
    ├─ 3. Operator detection
    │     ├─ distance_2d / sqrt((x1
    │     └─ line_intersects_rect
    │
    └─ 4. If geotask_data provided:
          Invoke Verifier → add status / expected_value / difference
```

## Verification Pipeline

```
Normalized model claims  +  GeoTask Core data
    │
    ├─ 1. Run local deterministic operators (run_geotask)
    │
    ├─ 2. Per-measurement comparison
    │     ├─ Numeric: abs(model - expected) ≤ tolerance → verified
    │     ├─ Numeric: abs(model - expected) > tolerance → contradicted
    │     ├─ Boolean: model == expected → verified
    │     ├─ Boolean: model != expected → contradicted
    │     └─ Missing value → need_review
    │
    └─ 3. Aggregate overall_status
          ├─ Any contradicted → contradicted
          ├─ Any need_review → need_review
          └─ Otherwise → verified
```

## Status Definitions

| Status | Meaning |
|--------|---------|
| `verified` | Model output matches local deterministic result |
| `contradicted` | Model output conflicts with local deterministic result |
| `need_review` | Missing fields, unrecognized objects/operators, or extraction failure |
| `extracted` | Value was extracted but not yet verified (no geotask_data provided) |

## Current Limitations (v0.2)

1. **Two measurements only**: `takeoff_to_school_distance` and `route_intersects_zone`
2. **Chinese object mapping**: Simple CN→EN mapping; no NLP
3. **Single value per measurement**: Cannot handle multiple distance values
4. **Fixed operators**: Only `distance_2d` and `line_intersects_rect`
5. **No confidence scores**: All extractions are binary (found / not found)
6. **No context window**: Extraction is regex-based, not semantic

## Future Directions (v0.3+)

- Dynamic measurement names (not hardcoded)
- Multi-value measurements
- Operator dispatch from geotask_data
- Confidence scoring
- Support for additional object types (polygon, multi-segment)
- JSON output mode
- Batch processing
