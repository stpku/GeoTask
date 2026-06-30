# Foundation Upgrade v0.2 Task State

Date: 2026-06-30

## Goal

Upgrade GeoTask's public-safe foundation without publishing, pushing, releasing,
or expanding P2/P5 or LowAlt-sensitive material.

## Current Branch

`foundation/geotask-upgrade-marathon-v0.2`

## Starting Point

- Start branch: `product/patent-and-lowalt-mvp-v0.1`
- Start HEAD: `18a75559c1084a12a4299a7970ebd5a9a2df4d72`
- Initial untracked files observed and left untouched:
  - `.omx/state/session.json`
  - `.omx/logs/omx-2026-06-30.jsonl`

## Safety Boundary

- No push.
- No release.
- No package upload.
- No P2/P5 expansion.
- No LowAlt industry-rule expansion.
- Patent evidence is read-only unless explicitly required for boundary checks.

## Completed Loops

- Baseline repair: restored benchmark test import path consistency.
- Baseline repair: restored public-safe local verifier boundary wording in
  `docs/encoding_benchmark_v0_2.md`.
- Loop A: added public-safe Core operator registry metadata and CLI inspection.
- Loop B: added CLI `explain`, `inspect schema`, `inspect examples`, and
  `report --format json|markdown`.
- Loop C: added public-safe Core examples and generic time/altitude validation.
- Loop D: added structured parser diagnostics and CLI validation output.
- Loop E: broadened diagnostics to unknown fields and unsupported operators,
  and aligned `inspect schema` with optional reserved sections.
- Loop F: turned `assertions` and `expected_results` into minimally validated
  public-safe schema sections with examples.

## In Progress

- Loop F verification and local commit.
