# CLI Snapshot

Generated for patent evidence archival.

## Available Commands

```bash
# Validate a GeoTask document
geotask validate examples/geotask_core_lite.yaml

# Run a GeoTask document (validate + execute)
geotask run examples/geotask_core_lite.yaml

# Normalize LLM output (extraction only)
geotask normalize examples/deepseek_output_sample.txt

# Normalize + verify against GeoTask ground truth
geotask normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml

# Evaluate LLM output against Core ground truth
geotask eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt

# Python module equivalents
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
python -m geotask_core.cli run examples/geotask_core_lite.yaml
python -m geotask_core.cli normalize examples/deepseek_output_sample.txt
python -m geotask_core.cli normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml
python -m geotask_core.cli eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt
```

## Example: `geotask run geotask_core_lite.yaml`

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

## Example: Normalize with verification

```bash
geotask normalize examples/model_outputs/deepseek_cn.md --geotask examples/geotask_core_lite.yaml
```

Output includes `status: verified` / `status: contradicted` / `status: need_review` for each measurement, plus `expected_value` and `difference` fields for numeric checks.
