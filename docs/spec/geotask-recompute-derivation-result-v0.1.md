# GeoTask Recompute Derivation Result v0.1

## 1. Purpose

`geotask.recompute-derivation-result` records how every `recompute` change in one bound Correction Request obtains a deterministic value from exact source Artifact paths. It closes the gap between a bounded correction request and World State materialization without allowing a caller, model, or provider to inject unexplained values.

The Artifact is an immutable result contract. It is not an arbitrary expression language and it is not a general workflow engine.

## 2. Binding model

One result binds:

- one immutable base `geotask.world-state` by ID, revision, time, semantic fingerprint, and raw-byte SHA-256;
- one exact `geotask.correction-request` by instance ID and raw-byte SHA-256;
- one or more exact source Artifacts, currently `geotask.observation` and `geotask.document`;
- one derivation for every Correction Request change whose operation is `recompute`;
- one complete `recompute_values` map suitable for bounded successor materialization.

Binding validation requires the supplied parsed objects to match the exact declared bytes. Observation identities and source references must already be declared by the Correction Request. Every GeoTask Document source must appear in the Correction Request `supporting_artifact_refs` with the same Artifact ID, version, instance ID, and content SHA-256.

## 3. Input contract

Each derivation declares named inputs. The names must exactly equal the corresponding Correction Request change's `input_fields`.

An input is either:

- `artifact_path`: a value copied from an exact JSON or YAML Artifact through a non-root JSON Pointer; or
- `literal`: explicit control metadata such as the allowlisted calculation method or a bounded verification timestamp.

For `artifact_path`, binding validation resolves the pointer against the exact source bytes and requires the declared value to match. Missing paths, stale values, undeclared sources, or hash drift fail closed.

## 4. Allowlisted methods

v0.1 supports only three deterministic methods:

| Method | Contract |
|---|---|
| `copy_input` | Copies one named operand exactly. |
| `subtract` | Subtracts the second finite numeric operand from the first. |
| `interval_gap_minus_delay_seconds` | Converts two same-day `HH:MM[:SS]` intervals to seconds, computes the gap from the first interval end to the second interval start, then subtracts a finite delay in seconds. |

Operand order is the declared `input_refs` order. Arbitrary Python, JavaScript, templates, shell commands, dynamic imports, network calls, model calls, provider calls, and unregistered expressions are forbidden.

## 5. Derivation and aggregate states

Each derivation is `completed`, `blocked`, `failed`, or `unknown`. A completed derivation must declare a result; all other states forbid a result.

The aggregate state is derived from its members:

- `completed`: all derivations completed;
- `partial`: completed and unknown derivations coexist;
- `blocked`: at least one derivation is blocked;
- `failed`: at least one derivation failed;
- `unknown`: no derivation completed and at least one is unknown.

For a completed Artifact, `recompute_values` must exactly equal the completed derivation results and `next_action` must be `materialize_successor_state`.

## 6. Correction Request coverage

Explicit binding validation requires:

- every request change with operation `recompute` is represented exactly once;
- no derivation targets a non-recompute or unknown change;
- each derivation target path equals the Correction Request change path;
- each derivation's basis includes the Correction Request and every source Artifact used by an input;
- `calculation_method`, when required by the request, equals the allowlisted derivation method;
- `verified_at`, when required, falls between the base World State `as_of` and the derivation result creation time.

The evaluated value map can be passed to `materialize_successor_world_state(..., recomputed_values=...)`. Materialization remains a separate operation and produces a separate immutable result.

## 7. Validation levels

Generic Artifact validation proves only:

- JSON Schema validity;
- strict loader validity;
- aggregate state and value-map closure;
- deterministic semantic fingerprinting.

It deliberately reports source bindings and derivation evaluation as false. Explicit `validate_recompute_derivation_bindings` additionally verifies exact bytes, source paths, request coverage, and deterministic values.

## 8. Safety boundary

Even after explicit binding and evaluation, the Artifact does not:

- fetch or verify external evidence;
- merge Observations;
- call a model or Provider;
- materialize or mutate a World State;
- execute reevaluation or propagation;
- release outputs;
- verify external truth;
- authorize or execute actions.

All boundary booleans in v0.1 are therefore required to remain `false`: `successor_materialized`, `reevaluation_executed`, `outputs_released`, `external_truth_verified`, `action_authorized`, and `action_executed`.

## 9. Reference example

`examples/core/recompute_derivation_result_uav_recheck.json` binds a telemetry Observation and a GeoTask Document. It copies a 60-second UAV delay and derives temporal separation as a 120-second planned interval gap minus the 60-second delay, yielding a complete materializer map with both values equal to 60.
