# GeoTask Observation v0.1

## 1. Purpose

`geotask.observation` is the first public world-model Artifact above the existing task and result contracts. It records what one producer claims to have observed or inferred about the world at a particular time.

An Observation is **not** a verified fact and is **not** a WorldState update by itself. Validation proves only that the payload is structurally complete, internally consistent, JSON-safe, and traceable to a declared source and producer.

## 2. Artifact identity

- Artifact ID: `geotask.observation`
- Schema version: `0.1`
- Wrapper key: `observation`
- JSON Schema: `schemas/geotask-observation-v0.1.schema.json`
- Validation command:

```bash
geotask artifact validate geotask.observation <observation.json> --format json
```

## 3. Top-level contract

```json
{
  "observation": {
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-observation-v0.1.schema.json",
    "schema_version": "0.1",
    "observation_id": "obs-uav-a-delay-001",
    "observed_at": "2026-08-01T08:30:05+08:00",
    "received_at": "2026-08-01T08:30:06+08:00",
    "source": {},
    "producer": {},
    "claims": []
  }
}
```

`received_at` must not be earlier than `observed_at`. Both timestamps must include a timezone offset.

## 4. Source and producer

`source` identifies the material or channel from which the Observation originated:

```json
{
  "kind": "sensor",
  "reference": "telemetry://fictional-uav-a/sample-4402",
  "artifact_id": "optional-source-artifact-id",
  "sha256": "optional-lowercase-sha256"
}
```

Supported source kinds:

- `multimodal_model`
- `sensor`
- `map`
- `authoritative_data`
- `human`
- `external_system`
- `simulation`

`producer` identifies the system or person that materialized the Observation payload:

```json
{
  "id": "fictional-telemetry-adapter",
  "kind": "software",
  "version": "0.1.0"
}
```

Supported producer kinds:

- `ai_model`
- `sensor`
- `human`
- `software`
- `organization`

A valid source or producer declaration does not authenticate either party and does not prove that referenced content exists.

## 5. World claims

Each Observation contains at least one claim:

```json
{
  "id": "uav-a-delay-seconds",
  "subject_ref": "uav-a",
  "predicate": "delay_seconds",
  "basis": "direct_observation",
  "value": 40,
  "uncertainty": {
    "kind": "standard_deviation",
    "value": 0.5,
    "unit": "second"
  },
  "evidence_refs": ["telemetry-sample-4402"]
}
```

`subject_ref` is a stable external reference intended to bind to a future or existing world object. `predicate` is an explicit property or relation name. `value` may be any finite JSON-compatible value. A relation may additionally use `object_ref`.

Supported claim bases:

- `direct_observation`
- `model_inference`
- `derived`
- `external_assertion`
- `human_judgment`

Claim IDs must be unique within one Observation. Evidence references must be non-empty and unique.

A claim may override the parent `observed_at` and may declare `valid_until`. A claim observation time must not be later than the parent `received_at`, and `valid_until` must not be earlier than the effective claim observation time.

## 6. Uncertainty

Supported uncertainty forms:

- `probability_of_error`: number from 0 to 1;
- `confidence`: number from 0 to 1;
- `standard_deviation`: non-negative number, optional unit;
- `interval_width`: non-negative number, optional unit;
- `qualitative`: `low`, `medium`, `high`, or `unknown`.

The contract records declared uncertainty. It does not calibrate, normalize, compare, or independently validate that uncertainty.

## 7. Supersession

An Observation may list earlier Observation IDs in `supersedes`. This records an author-declared replacement relationship. The current Observation cannot supersede itself, and duplicate IDs are rejected.

Supersession does not delete prior evidence, merge claims, or update a World State. The published Observation Merge Result v0.1 can apply complete explicit claim mappings to existing attributes or relations and emit a bound successor revision. When multiple claims target one path, it accepts only caller-declared `require_equal` consolidation or complete `explicit_precedence`; it does not infer identity, create missing state, invent precedence, rank sources, resolve an undeclared ambiguous conflict, or calculate a State Transition. State Transition v0.1 can then record an explicit change between already materialized snapshots.

## 8. Trust and execution boundary

Observation validation does not:

- verify that a world claim is true;
- fetch or authenticate the declared source;
- recompute a source SHA-256;
- resolve `subject_ref`, `object_ref`, or `evidence_refs` against a World State;
- infer omitted objects, predicates, units, or uncertainty;
- merge the Observation into a World State;
- execute a model, Provider, Runtime, or real-world action;
- increase an assurance level.

The published snapshot contract and next intended processing layers are:

```text
Observation
→ World State v0.1 snapshot
→ State Transition v0.1 audit record
→ future automatic materialization / VerificationSession / recheck
→ action eligibility
```

A valid Observation v0.1 payload does not imply that a World State snapshot has been materialized or that any later transition, verification, recheck, or eligibility decision exists.
