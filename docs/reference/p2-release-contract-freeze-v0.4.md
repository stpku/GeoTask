# GeoTask 0.4.0 Release-Scope Contract Freeze

**Status:** P2 release-scope freeze; 0.4.0 is not released  
**Date:** 2026-08-07  
**Machine snapshot:** `docs/reference/p2-release-contract-freeze-v0.4.json`

## Purpose

This document freezes the **public names expected to survive into the 0.4.0 release scope** so product hardening can proceed without accidental renaming. It is not a claim that every future 0.4.0 behavior is finalized and it does not change the currently published package version.

The machine-readable snapshot is tested against the live registries and CLI. A public rename that makes the test fail is treated as an intentional compatibility event and must be accompanied by migration documentation rather than silently updating the snapshot.

## Frozen product names

```text
PyPI package: geotask-core
Python import: geotask_core
primary CLI: geotask
legacy/deprecated CLI alias: stir
Python support: 3.10, 3.11, 3.12, 3.13
```

`stir` compatibility remains deprecated; this freeze does not restore the old `stir_core` Python package.

## Frozen registry surface

For this release scope the snapshot binds:

```text
14 deterministic operator IDs
32 registered Artifact IDs
33 bundled Schemas
Artifact Registry version 1.0
18 top-level CLI commands
```

The exact IDs live in the JSON snapshot and are mechanically checked against:

- `geotask_core.operator_registry.operator_names()`;
- `geotask_core.v1.artifact_registry.list_artifact_descriptors()`;
- `geotask_core.v1.schema_bundle.list_bundled_schema_ids()`;
- the current `geotask --help` top-level command list.

## What is frozen

- spelling of the package/import/primary CLI names;
- current operator IDs;
- current Artifact IDs;
- top-level CLI command names;
- the declared Python minor-version support matrix;
- the count boundary of the current Schema Bundle unless this snapshot is explicitly reviewed and updated before release.

## What is not frozen by this document

- implementation internals;
- private Runtime behavior;
- domain-pack business semantics;
- Lowa-GT integration payload details beyond its separate versioned contract;
- automatic dependency discovery, which is not currently claimed;
- the future existence of additional backward-compatible Artifacts, provided the release-scope snapshot is explicitly updated and reviewed;
- the 0.4.0 publication date.

## Compatibility rule

A breaking rename is not accepted as an incidental cleanup. Before release it requires all of:

1. explicit rationale;
2. old → new mapping in `MIGRATION.md` or the 0.4 migration matrix;
3. compatibility/deprecation decision;
4. updated tests and release-scope snapshot;
5. review that Reference Agent and public examples still replay.

This converts “naming freeze” from a prose intention into a testable release gate.
