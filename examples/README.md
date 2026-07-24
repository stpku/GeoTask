# GeoTask Examples

This directory contains public-safe Core examples and separate domain-pack
examples. Core examples use fictional local coordinates and generic intervals.
They do not encode domain-specific approval logic, regulatory thresholds, or
patent-sensitive workflows.

## Public-Safe Core Examples

- `examples/core/minimal_valid.yaml`: minimal point distance example.
- `examples/core/time_altitude_overlap.yaml`: generic time and altitude interval
  overlap example.
- `examples/core/assertions_expected_results.yaml`: schema example for optional
  `assertions` and `expected_results` sections.
- `examples/core/multi_constraint_conflict.yaml`: three deterministic assertions
  combined by an explicit public-safe `AND` decision rule.
- `examples/core/unverifiable_constraint.yaml`: two verified assertions and one
  unverifiable required condition combined with three-valued unknown propagation.
- `examples/core/evidence_request_plan.yaml`: an unverifiable required condition
  converted into a structured evidence request with blocked outputs and a resume condition.
- `examples/geotask_core_lite.yaml`: legacy Core lite example used by tests.
- `examples/basic_distance.yaml`: basic distance example.
- `examples/route_zone_intersection.yaml`: line and rectangle intersection
  example.

## Domain-Pack Examples

Files under `examples/domain_packs/` are not public-safe Core examples. They are
kept separate to avoid mixing Core documentation with domain-specific material.
