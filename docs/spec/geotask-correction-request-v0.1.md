# GeoTask Correction Request v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

A Correction Request is an immutable, bounded instruction for producing a **successor World State** from one already published base snapshot. It binds exact Discrepancy Report artifacts, identifies the discrepancies being addressed, declares allowed changes, requires preservation of immutable paths, defines machine-readable acceptance criteria, and keeps affected outputs and actions blocked until an explicit resume condition is satisfied.

A valid Correction Request does **not** modify the base snapshot. Validation does not compare sources, prove a discrepancy, apply a change, materialize a successor World State, evaluate acceptance criteria, resolve a discrepancy, rerun a task, release an output, or authorize an action.

## 1. Stable identity

- Artifact ID: `geotask.correction-request`
- Wrapper: `correction_request`
- Schema version: `0.1`
- JSON Schema: [`schemas/geotask-correction-request-v0.1.schema.json`](../../schemas/geotask-correction-request-v0.1.schema.json)
- Python loader: `load_correction_request(payload)`
- Binding validator: `validate_correction_request_bindings(request, base_world_state, discrepancy_reports, artifact_contents)`
- Unified validation: `geotask artifact validate geotask.correction-request <correction-request.json>`

The Registry descriptor intentionally has no generation command. An Agent or Runtime may author or materialize a request only after a Discrepancy Report exists. Core validates the declared request and explicit bindings; it does not decide which real-world correction is appropriate.

## 2. Successor-state semantics

Correction Request v0.1 never edits a published World State in place. The request binds one immutable base snapshot and requires a later output with:

- Artifact ID `geotask.world-state`;
- Schema version `0.1`;
- the same `world_state_id`;
- a revision greater than the base revision;
- preserved immutable paths;
- a deterministic semantic fingerprint.

The base snapshot remains an audit record even when the request is later completed.

## 3. Request states

v0.1 supports three states:

| State | Meaning | Required next action |
|---|---|---|
| `required` | concrete bounded changes may proceed | `materialize_successor_state` |
| `need_review` | correction scope requires an authorized human decision | `human_review` |
| `blocked` | the referenced discrepancy cannot be corrected through the declared scope | `none` |

State shape is fail-closed:

- `required` requires one or more changes, forbids review requirements, and requires at least one change for every referenced discrepancy;
- `need_review` forbids executable changes, requires review requirements and a `human_reviewed` acceptance criterion;
- `blocked` forbids changes, review requirements, and acceptance criteria.

Evidence acquisition remains a separate Evidence Request concern. A Correction Request is not used to conceal missing evidence.

## 4. Exact base and Artifact bindings

The base World State reference records:

```json
{
  "ref_id": "base-world-state",
  "artifact_id": "geotask.world-state",
  "schema_version": "0.1",
  "world_state_id": "fictional-uav-separation-state",
  "revision": 2,
  "as_of": "2026-07-16T10:01:00+08:00",
  "semantic_fingerprint": "...",
  "content_sha256": "..."
}
```

Each Discrepancy Report and supporting Artifact reference records a stable `ref_id`, Artifact ID, Schema version, instance identity, and exact raw-byte SHA-256 digest.

`validate_correction_request_bindings()` verifies:

1. base World State identity, revision, snapshot time, and semantic fingerprint;
2. exact bytes for the base state, every Discrepancy Report, and every supporting Artifact;
3. each Discrepancy Report instance identity;
4. each report's World State binding to the same base snapshot;
5. request creation time not preceding any bound report;
6. Observation and Evidence references declared by the bound reports;
7. every change's Observation and Evidence references against its exact discrepancy finding;
8. every non-`add` change's `before` value against the value actually present at its identity path in the base World State;
9. `add` targets are absent from the base World State;
10. review requirements are bound to the referenced report and remain inside the finding's declared correction scope.

Exact-byte binding identifies the serialized inputs. It does not validate every supporting Artifact's own semantics; each Artifact must still pass its registered validator.

## 5. Referenced discrepancies

A request declares local discrepancy references:

```json
{
  "id": "separation-mismatch",
  "report_ref": "discrepancy-uav-recheck",
  "discrepancy_id": "temporal-separation-value-mismatch"
}
```

The local `id` is used by changes, review requirements, and acceptance criteria. Binding validation resolves the pair against the loaded Discrepancy Report.

For a `required` request, each referenced finding must be `detected` or `confirmed` and must declare `correction_scope.state=allowed`.

For `need_review`, each referenced finding must declare `correction_scope.state=need_review`.

For `blocked`, each referenced finding must declare `blocked` or `not_applicable` correction scope.

## 6. Identity-based correction paths

v0.1 successor-state changes target only World State object, attribute, or relation paths:

| Subject kind | Required path form |
|---|---|
| `object` | `/objects/<object-id>/...` |
| `attribute` | `/objects/<object-id>/attributes/<name>/...` |
| `relation` | `/relations/<relation-id>/...` |

Paths are identity-based JSON Pointers rather than array indices. Empty segments, root paths, trailing slashes, and invalid JSON Pointer escapes are rejected.

During binding validation, every target path must equal or descend from a mutable path declared by its bound discrepancy. It must not equal, contain, or descend from any immutable path. Change targets must also be mutually non-overlapping, so two requested edits cannot independently claim the same subtree.

Whole-object, whole-attribute, and whole-relation replacement is forbidden. Intrinsic identity and provenance fields are immutable even when a malformed upstream report were to declare them mutable: object `id` and `type`, attribute `name`, relation `id`, `subject_ref`, `predicate`, and `object_ref`, plus all Observation and Evidence reference arrays.

## 7. Change operations

Each change records its discrepancy reference, subject kind, target path, operation, reason, source bindings, Observation/Evidence references, required input fields, and acceptance-criterion references.

| Operation | Value rule |
|---|---|
| `add` | requires `after`; forbids `before` and `input_fields` |
| `replace` | requires different `before` and `after`; forbids `input_fields` |
| `remove` | requires `before`; forbids `after` and `input_fields` |
| `recompute` | requires `before` and non-empty `input_fields`; forbids `after` |

`recompute` is important when Core must not invent a corrected value. It requests a later authorized materializer to derive the successor value from named inputs.

When a change targets the exact discrepancy subject path and the discrepancy records an observed value, `replace`, `remove`, and `recompute` must anchor `before` to that observed value. Binding validation additionally resolves every change target against the actual base World State: `replace`, `remove`, and `recompute` require the path to exist and require `before` to equal its current value; `add` requires the path to be absent. This prevents a scope-valid request from carrying a false base value.

## 8. Acceptance criteria

v0.1 defines seven criterion kinds:

| Kind | Required declaration |
|---|---|
| `path_equals` | target path and expected value |
| `path_absent` | target path |
| `path_recomputed` | target path |
| `artifact_valid` | Artifact ID |
| `discrepancy_resolved` | local discrepancy reference |
| `recheck_completed` | one or more affected output references |
| `human_reviewed` | reviewer role |

Operation-specific criteria are mandatory:

- `add` and `replace` require a matching `path_equals` criterion whose expected value equals `after`;
- `remove` requires a matching `path_absent` criterion;
- `recompute` requires a matching `path_recomputed` criterion.

A `required` request additionally requires:

- one `discrepancy_resolved` criterion for every referenced discrepancy;
- one `artifact_valid` criterion for `geotask.world-state`;
- `recheck_completed` coverage for every blocked output.

A `need_review` request requires review coverage for every referenced discrepancy and a matching `human_reviewed` criterion for every required reviewer role.

These criteria are declarations. Loading the request does not evaluate them. A later Reevaluation Result or authorized Runtime must record whether they were satisfied.

## 9. Output and action gates

Every request must block at least one output or action. The fields:

- `blocked_outputs`;
- `blocked_actions`;
- `resume_when`;
- `next_action`;

make the operational boundary explicit.

A valid request does not release anything when `resume_when` is merely written in the Artifact. The condition must be evaluated through a later explicit workflow, and action authorization remains external.

## 10. Deterministic semantic fingerprint

`CorrectionRequest.semantic_fingerprint()` canonicalizes:

- Artifact references by `ref_id`;
- discrepancy references by local `id`;
- changes, review requirements, and acceptance criteria by `id`;
- nested reference and input arrays;
- blocked output/action arrays;
- JSON object keys.

Equivalent requests with different collection ordering produce the same lowercase SHA-256 fingerprint. The fingerprint is not a digital signature, publisher identity, proof of authority, or proof that a correction was performed.

## 11. Validation layers

Correction Request v0.1 separates:

1. **Request structure valid** — strict loading or unified Artifact validation succeeded.
2. **Bindings and correction scope verified** — the base World State, Discrepancy Reports, raw bytes, and mutable/immutable paths matched.
3. **Supporting Artifact semantics verified** — each linked Artifact passed its own registered validator.
4. **Changes applied and successor state materialized** — an authorized materializer produced a new World State.
5. **Acceptance criteria and rechecks completed** — the successor state and affected outputs were independently reevaluated.
6. **outputs released or actions authorized** — an external control and authorization layer permitted use.

Success at one layer never implies success at a later layer. Generic unified validation receives only the request payload and therefore explicitly reports false for base/report/artifact binding verification, correction-scope verification, change application, successor-state materialization, acceptance evaluation, discrepancy resolution, recheck execution, output release, external truth, and action authorization.

## 12. Fictional example

[`examples/core/correction_request_uav_recheck.json`](../../examples/core/correction_request_uav_recheck.json) binds:

- World State revision 2;
- the corresponding Discrepancy Report;
- the GT16 task document.

It requests two bounded recomputations in a successor World State:

1. UAV-B's telemetry-derived delay;
2. the dependent temporal-separation relation.

The request preserves route identities and route geometry, requires a valid successor World State with revision at least 3, requires the temporal discrepancy to be resolved and the affected continuation output to be rechecked, and keeps automatic continuation blocked until those conditions are satisfied.

The example is fictional. It does not contain live telemetry, a production correction, a real successor state, a completed recheck, flight authorization, or a real-world action.
