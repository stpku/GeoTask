# GeoTask Discrepancy Report v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

A Discrepancy Report is an immutable audit record describing explicit differences relative to one World State snapshot. It binds exact serialized source artifacts, identifies the affected object, attribute, relation, claim, artifact, or action-eligibility path, records expected and observed values when applicable, declares downstream impact, and constrains what a later correction may or may not change.

A valid report does **not** prove that its discrepancy is externally true. Validation does not compare source contents, discover differences, propagate impact, create a Correction Request, apply a correction, materialize a World State, execute a recheck, or authorize an action.

## 1. Stable identity

- Artifact ID: `geotask.discrepancy-report`
- Wrapper: `discrepancy_report`
- Schema version: `0.1`
- JSON Schema: [`schemas/geotask-discrepancy-report-v0.1.schema.json`](../../schemas/geotask-discrepancy-report-v0.1.schema.json)
- Python loader: `load_discrepancy_report(payload)`
- Binding validator: `validate_discrepancy_report_bindings(report, world_state, artifact_contents)`
- Unified validation: `geotask artifact validate geotask.discrepancy-report <discrepancy-report.json>`

The Registry descriptor has no generation command. An Agent or Runtime may author or materialize the report only after explicit source comparison has occurred outside this loader. Core validates the declared report and explicit bindings; it does not perform the comparison.

## 2. Report envelope

Each report contains:

| Field | Meaning |
|---|---|
| `report_id` | Stable identity of the report |
| `recorded_at` | Time the report was recorded |
| `state` | Aggregate discrepancy state |
| `severity` | Maximum discrepancy severity |
| `reason` | Human-readable report rationale |
| `world_state` | Bound World State identity and semantic fingerprint |
| `observation_refs` | Observation inventory used by findings |
| `evidence_refs` | Evidence inventory used by findings |
| `artifact_refs` | Exact-byte source Artifact inventory |
| `discrepancies` | One or more explicit findings |

`recorded_at` must include a timezone offset and must not precede the bound World State `as_of` time.

## 3. World State and source bindings

The World State reference contains:

```json
{
  "world_state_id": "fictional-uav-separation-state",
  "revision": 2,
  "as_of": "2026-07-16T10:01:00+08:00",
  "semantic_fingerprint": "..."
}
```

`validate_discrepancy_report_bindings()` verifies all four fields against one already loaded `WorldState`. It also requires every report-level Observation and Evidence reference to be declared by that state.

Each source Artifact reference contains:

```json
{
  "ref_id": "result-gt16-initial",
  "artifact_id": "geotask.execution-result",
  "schema_version": "1.0",
  "instance_id": "gt16-uav-route-crossing-temporal-separation-result",
  "content_sha256": "..."
}
```

The binding validator accepts a mapping from `ref_id` to raw `bytes`. It rejects missing files, undeclared extras, non-byte values, and SHA-256 mismatches. Exact-byte binding answers which serialized file the report refers to; it does not validate that file's own semantics. Each linked Artifact must still pass its own registered validator.

## 4. Discrepancy states and severity

Finding and report states are:

- `detected`
- `confirmed`
- `need_review`
- `unknown`

The aggregate report state is deterministic:

1. any `confirmed` finding → report `confirmed`;
2. otherwise any `need_review` finding → report `need_review`;
3. otherwise any `detected` finding → report `detected`;
4. otherwise report `unknown`.

Severity values are `low`, `medium`, `high`, and `critical`. Report severity must equal the maximum finding severity.

These rules make the report internally consistent. They do not independently establish that a finding was correctly detected or confirmed.

## 5. Discrepancy kinds

v0.1 supports:

| Kind | Value rule |
|---|---|
| `value_mismatch` | requires different `expected` and `observed` values |
| `missing_claim` | requires `expected`; forbids `observed` |
| `unexpected_claim` | requires `observed`; forbids `expected` |
| `stale_claim` | requires `observed` |
| `source_conflict` | requires different `expected` and `observed` values |
| `validity_conflict` | requires different `expected` and `observed` values |
| `uncertainty_conflict` | requires different `expected` and `observed` values |
| `unsupported_claim` | requires `observed` |

Expected and observed values may contain any finite JSON-compatible structure. Non-finite numbers and mappings with non-string keys are rejected.

## 6. Subject identity paths

Every finding identifies one subject kind and an identity-based JSON Pointer:

| Subject kind | Required path prefix |
|---|---|
| `object` | `/objects/<object-id>/...` |
| `attribute` | `/objects/<object-id>/attributes/<name>/...` |
| `relation` | `/relations/<relation-id>/...` |
| `action_eligibility` | `/action_eligibility/<output-ref>/...` |
| `claim` | `/claims/<claim-id>/...` |
| `artifact` | `/artifacts/<artifact-ref>/...` |

Paths must be non-root pointers with valid JSON Pointer escapes and no empty segments. Identity-based paths are used instead of array indices so order changes do not silently retarget a finding.

## 7. Reference closure

Each finding contains:

- non-empty `basis_refs` resolving to report-level source Artifacts;
- optional `observation_refs` resolving to the report-level Observation inventory;
- optional `evidence_refs` resolving to the report-level Evidence inventory.

Top-level Artifact reference IDs and instance IDs are unique. Finding IDs are unique. Closure proves internal connectivity only; it does not fetch, authenticate, or verify any source.

## 8. Impact declaration

Every finding contains an `impact` object with:

- state: `none`, `potential`, `confirmed`, or `unknown`;
- reason;
- affected world-state paths;
- affected assertion references;
- affected output references;
- affected action references.

`none` requires all affected-reference arrays to be empty. `potential` and `confirmed` require at least one affected reference. Core validates this declaration but does not traverse an Impact Graph, invalidate outputs, execute a recheck, or change action eligibility.

## 9. Bounded correction scope

Every finding contains a `correction_scope`:

| State | Required semantics |
|---|---|
| `allowed` | at least one mutable path |
| `blocked` | no mutable paths and at least one immutable path |
| `need_review` | at least one mutable or immutable path |
| `not_applicable` | both path arrays empty |

Mutable and immutable paths must not overlap by equality, ancestor, or descendant relationship. This prevents a report from simultaneously allowing and forbidding changes to the same subtree.

The scope is a declaration for a later Correction Request. Loading the report does not create that request, edit a document, patch a World State, or rerun a task.

## 10. Deterministic semantic fingerprint

`DiscrepancyReport.semantic_fingerprint()` canonicalizes:

- report Observation and Evidence inventories;
- source Artifact references by `ref_id`;
- findings by `id`;
- nested reference arrays;
- impact paths and references;
- mutable and immutable path arrays;
- JSON object keys.

Equivalent reports with different collection ordering produce the same lowercase SHA-256 fingerprint. The fingerprint is not a digital signature, publisher identity, or external attestation.

## 11. Five distinct validation layers

Discrepancy Report v0.1 deliberately separates:

1. **Report structure valid** — strict loader or unified Artifact validation succeeded.
2. **Bindings verified** — the World State and exact source bytes matched.
3. **Source Artifact semantics verified** — every source passed its own validator.
4. **Discrepancy and impact computed** — an authorized comparison/impact process actually produced and confirmed the finding.
5. **Correction and operational work executed** — a Correction Request, bounded edit, state materialization, recheck, or action was actually performed.

Success at one layer never implies success at a later layer. Generic unified validation receives only the report payload and therefore explicitly returns false for binding verification, source semantic verification, discrepancy computation, impact propagation, correction creation/application, state materialization, recheck execution, external truth, and action authorization.

## 12. Fictional example

[`examples/core/discrepancy_report_uav_recheck.json`](../../examples/core/discrepancy_report_uav_recheck.json) binds World State revision 2 and four exact source Artifacts. It records:

- a confirmed high-severity mismatch between the original 120-second temporal-separation assumption and the later 60-second state;
- a confirmed medium-severity stale initial execution result;
- confirmed impact on the temporal assertion, route-continuation output, and automatic-continuation action;
- mutable telemetry-derived state paths;
- immutable route identity, route geometry relation, and historical execution-result paths.

The example is fictional. It contains no live telemetry, regulatory decision, production correction, real recheck, flight authorization, or real-world action.
