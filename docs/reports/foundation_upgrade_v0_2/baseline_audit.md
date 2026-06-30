# Foundation Upgrade v0.2 Baseline Audit

Date: 2026-06-30

## Module Structure

Core modules under `src/geotask_core/`:

- `parser.py`: YAML loading and string-list validation.
- `ops.py`: deterministic spatial operators.
- `runner.py`: operation auto-detection and deterministic execution.
- `normalizer.py`: LLM-output normalization and review reason extraction.
- `verifier.py`: normalized-output verification against Core runner output.
- `result_schema.py`: status and reason constants plus result builders.
- `evaluator.py`: simple scoring against Core ground truth.
- `cli.py`: command-line entry point.
- `models.py`: lightweight dataclasses retained for simple Core structures.

Domain pack modules under `src/geotask_domain_packs/` currently include a mock
LowAlt site precheck pack. This audit treats that pack as boundary-sensitive and
does not expand its rules.

## Current CLI Commands

Available:

- `validate`
- `run`
- `normalize`
- `eval`

Missing from the requested foundation target:

- `explain`
- `inspect operators`
- `inspect schema`
- `inspect examples`
- `report --format json`
- `report --format markdown`

## Current Operators

Production Core currently implements six deterministic operators:

- `distance_2d`
- `line_intersects_rect`
- `point_to_line_distance_2d`
- `rect_contains_point`
- `time_overlap`
- `altitude_overlap`

The verifier previously had a hard-coded supported operator list matching those
six operators. Loop A added a central public registry with input shape, output
type, supported geometry, error codes, and examples.

## Current Schema Capability

`parser.validate_geotask()` checks top-level structure and the `point`, `line`,
and `rect` object shapes. Validation currently returns plain strings. It does
not yet provide structured diagnostics with `path`, `code`, `message`, and
`suggested_fix`.

## Current Normalizer Capability

The production normalizer extracts distance and line/rect intersection evidence
from model text, detects missing operators, invalid operator references,
invalid references, unit mismatches, and selected Chinese negation patterns.

## Current Verifier Capability

The verifier compares normalized measurements against deterministic Core runner
output and produces statuses including `verified`, `contradicted`,
`need_review`, `invalid_operator`, and `invalid_reference`. Result summaries are
still lightweight and do not yet expose a formal report model or CLI report
command.

## Current Examples

Existing examples include:

- `examples/geotask_core_lite.yaml`
- `examples/basic_distance.yaml`
- `examples/route_zone_intersection.yaml`
- runtime examples under `examples/runtime/`
- model output samples under `examples/model_outputs/`
- boundary-sensitive mock domain pack examples under `examples/domain_packs/`

There is not yet a dedicated `examples/core/` public-safe golden example set.

## Current Benchmarks

Existing benchmark directories:

- `benchmarks/encoding_v0_1/`
- `benchmarks/encoding_v0_2/`

Both contain inputs, simulated model outputs, generated outputs, and runner
scripts. v0.2 includes an explicit benchmark-local verifier boundary.

## Current Tests

After baseline repairs, `pytest` reports `476 passed`.

## Documentation Gaps

- `docs/operator_registry.md`
- `docs/geotask_yaml_schema.md`
- `docs/verification_result_model.md`
- `docs/cli_usage.md`
- `docs/benchmark_usage.md`
- `docs/domain_pack_interface.md`
- `docs/ci_quality_gates.md`

## Public-Safe Risks

- Existing patent evidence and LowAlt files must remain read-only unless only
  boundary issues are being recorded.
- Public docs must not describe unfiled P2/P5 implementation details.
- Mock domain-pack wording should not imply real approval, regulatory, or
  flight-permission conclusions.

## Public-Safe Upgrade Backlog

1. Improve schema diagnostics without adding domain-specific fields.
2. Add report/explain CLI surfaces for deterministic Core results.
3. Add `inspect schema` and `inspect examples`.
4. Add public-safe `examples/core/` with golden tests.
5. Stabilize benchmark usage docs and smoke tests.
6. Define a generic domain-pack interface without expanding LowAlt content.
7. Add quality-gate docs and scoped type/lint guidance.
