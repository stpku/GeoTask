# GeoTask Agent Integration Profile v0.1

Status: implemented public preview

Profile ID: `geotask.agent-integration`

Profile version: `0.1`

## 1. Purpose

This profile defines how an AI Agent uses GeoTask Core as a verifiable spatial-task protocol layer. It composes existing public Artifact, execution, and control contracts. It does not turn GeoTask Core into a hosted-model client, general Agent framework, approval system, or autonomous action runner.

The central responsibility split is:

```text
Agent: understand intent, generate or route artifacts, request missing evidence
GeoTask Core: validate contracts, execute deterministic operators, evaluate controls
Domain Pack / Runtime: provide private data, connectors, policies, and production actions
```

## 2. Required Tool Surface

A conforming integration exposes these four model-neutral tools in this order.

### 2.1 `inspect_artifacts`

Purpose: discover stable Artifact IDs and their Schemas.

```bash
geotask inspect schemas --format json
```

Python API: `geotask_core.artifact_registry_payload`

This operation does not execute a task or scan arbitrary files.

### 2.2 `validate_artifact`

Purpose: validate one registered artifact before it is trusted.

```bash
geotask artifact validate <artifact-id> <file> --format json
```

Python API: `geotask_core.validate_artifact_file`

Validation is read-only. Validating an execution result does not rerun the task, and validating an Artifact Validation Report does not repeat the original validation target.

### 2.3 `execute_task`

Purpose: execute a validated GeoTask document with deterministic Core operators.

```bash
geotask run <task.yaml> --format v1-json
```

Python API: `geotask_core.execute_canonical`

Core executes declared operators only. It does not call a hosted model or infer missing evidence.

### 2.4 `evaluate_control`

Purpose: evaluate evidence, blocking, and resume conditions.

```bash
geotask control evaluate <task.yaml> \
  --result <execution-result.json> \
  --state <state.yaml>
```

Python API: `geotask_core.evaluate_control_profile`

Control evaluation is observational. It never executes `next_action` or releases outputs.

The machine-readable catalog is available through:

```bash
geotask agent inspect --format json
```

or:

```python
from geotask_core import agent_integration_profile_payload
```

## 3. Normative Agent Rules

A conforming Agent MUST:

1. inspect the Artifact Registry rather than inventing Artifact IDs or Schema paths;
2. validate generated or received artifacts before using them;
3. preserve `unverifiable`, `need_data`, and unknown values instead of coercing them to booleans;
4. keep every declared `blocked_output` unavailable until its resume condition is satisfied;
5. rerun affected deterministic assertions after evidence recovery;
6. treat `next_action` as a routing instruction unless a separate authorized Runtime executes it;
7. preserve source references, versions, authorities, and verification times supplied by evidence;
8. distinguish model-generated summaries from original evidence.

A conforming Agent MUST NOT:

- fabricate a schedule, authority, version, source reference, or verification time;
- replace a deterministic operator result with model judgment;
- treat an Artifact Validation Report as proof that the underlying real-world evidence is authentic;
- release a blocked output through prose, fallback fields, or a second tool path;
- execute production actions merely because a control block names `next_action`.

## 4. Outcome Handling

| GeoTask outcome | Agent behavior |
|---|---|
| `verified` | Use the value subject to the output and control contracts. |
| `contradicted` | Preserve the contradiction and report the failed expectation. |
| `unverifiable` | Do not guess; evaluate the control profile and request evidence when declared. |
| `need_data` | Request the named data or route to a data connector. |
| `execution_error` | Report the execution failure; do not reinterpret it as a domain answer. |
| blocked control | Keep outputs blocked and surface the declared recovery path. |

`unknown` is a control-evaluation value, not a third business answer.

## 5. Generated Document Preparation

The preview provides a deterministic helper for Agent-generated native v1 drafts:

```bash
geotask agent prepare examples/core/agent_generated_distance_draft.yaml \
  --repaired-output prepared.yaml \
  --output preparation-report.json
```

Python API:

```python
from geotask_core import prepare_generated_document

report = prepare_generated_document(generated_document)
```

The helper declares `repair_policy=mechanical_only`, `model_called=false`, and `domain_inference_used=false`.

The helper follows this sequence:

```text
generated draft
→ strict initial validation
→ mechanical protocol repairs
→ strict revalidation
→ deterministic local execution
```

Safe repairs are limited to information already determined by document structure:

- add v1 `schema_version` to a native v1 shape;
- copy an explicit `geotask.id` into a missing display `name`;
- add stable task and assertion IDs from list position;
- synchronize `operator_set` from explicitly named assertion operators;
- add `local_only` execution defaults;
- add structured output defaults with `allow_model_inference: false`.

The helper MUST NOT:

- alter coordinates, geometry, intervals, altitude values, or evidence;
- choose, replace, or correct an operator;
- infer `object_refs`;
- invent task identity when both name and id are absent;
- infer domain policy or approval logic;
- execute `model_only`, `hybrid`, `shadow_compare`, or a private Runtime.

A result state of `valid` or `repaired` means final validation passed and local execution ran. `blocked` means residual errors remain and execution did not run. The CLI still emits a machine-readable report but exits with code `2`, enabling the calling Agent to revise the draft. A repaired document is written only after final validation succeeds.

Every report also contains `revision_request/0.1`. When no residual error remains, its state is `not_required`. A blocked report contains one `required_change` per unresolved diagnostic, including an action type, path, instruction, and optional `candidate_values`. Candidate values are inventories derived from public contracts or the document itself; `selected_value` remains `null`, `automatic_change_allowed` remains `false`, and Core does not edit the document. Non-local execution requirements produce `route_to_authorized_runtime` rather than a silent mode rewrite.

The Agent SHOULD revise the returned `prepared_document`, preserve its `revision_base_sha256`, and submit both the blocked report and revised document through the guarded retry path:

```bash
geotask agent retry blocked-preparation.json revised.yaml \
  --verification-output revision-verification.json \
  --prepared-output prepared.yaml \
  --output retry-report.json
```

Python API:

```python
from geotask_core import retry_generated_document

retry = retry_generated_document(blocked_report, revised_document)
```

Before any validation or execution, `agent retry` recomputes the revision request from the blocked document diagnostics and verifies its base SHA-256. It then computes a deterministic changed-path set. Only requested paths named by `required_changes` may change. A revised operator may also update the derived `operator_set`, but that inventory must exactly equal operators used by revised assertions. Coordinates, evidence, task goals, metadata, control policy, task ordering, and all other fields remain immutable unless a revision item explicitly names them.

Each requested path must change, and any selected value must belong to the declared candidate inventory. A candidate inventory is not a recommendation and does not establish semantic correctness. After the diff is accepted, the revised document still passes through strict preparation, validation, and deterministic execution. A rejected diff returns `agent_revision_retry/0.1`, exits with code `2`, sets `task_executed=false`, and does not write `--prepared-output`.

The public retry example starts with `examples/core/agent_generated_distance_blocked.yaml`, which contains an unregistered operator and unknown object binding. After the Agent explicitly selects a registered operator and existing object IDs, `examples/core/agent_generated_distance_revised.yaml` passes revision verification and returns the deterministic five-meter result.

The `agent_generation_preparation/0.1`, `agent_revision_verification/0.1`, and `agent_revision_retry/0.1` reports record the preparation, diff decision, and guarded retry trace. They are registered public Artifacts with offline Draft 2020-12 Schemas:

| Artifact ID | Schema |
|---|---|
| `geotask.agent-generation-preparation` | `schemas/geotask-agent-generation-preparation-v0.1.schema.json` |
| `geotask.agent-revision-verification` | `schemas/geotask-agent-revision-verification-v0.1.schema.json` |
| `geotask.agent-revision-retry` | `schemas/geotask-agent-revision-retry-v0.1.schema.json` |

Validate them without repeating preparation, diff verification, or execution:

```bash
geotask artifact validate geotask.agent-generation-preparation preparation-report.json
geotask artifact validate geotask.agent-revision-verification revision-verification.json
geotask artifact validate geotask.agent-revision-retry retry-report.json
```

A report with business state `blocked` or `rejected` can still be a valid Artifact when its serialized structure and cross-field invariants are correct.

## 6. Evidence Recovery Contract

The public preview implements a narrow, fail-closed recovery function:

```python
from geotask_core import recover_evidence_request

report = recover_evidence_request(document, evidence_state)
```

CLI:

```bash
geotask agent recover examples/core/evidence_request_plan.yaml \
  --evidence examples/core/evidence_request_verified_state.yaml \
  --output recovery-report.json
```

Recovery is supported only when:

1. the document declares `extensions.evidence_request` under `geotask.control/1.0`;
2. `evidence_request.trigger` resolves to exactly one assertion;
3. the trigger assertion is initially in its declared `trigger_status`;
4. the trigger assertion condition is a single named boolean condition represented by one plain identifier, such as `restricted_schedule_verified`;
5. every item in `required_fields` has a non-empty value in the evidence state;
6. the evidence state sets the named condition to boolean `true`;
7. `resume_when` evaluates to `true`.

Only after all checks pass does Core create an in-memory copy of the document, replace that one condition with literal `true`, and rerun the task. The caller's input document is not mutated.

Missing evidence and an unsatisfied resume condition produce a valid `blocked` report and a successful command exit. Malformed documents, ambiguous trigger references, and unsupported condition shapes fail with a non-zero exit code.

## 7. Recovery Report

`recover_evidence_request` returns an `agent_integration/0.1` report containing:

- profile identity;
- task and evidence-request identity;
- required and missing evidence fields;
- initial execution result;
- initial control evaluation without evidence;
- resume control evaluation with supplied evidence;
- resumed execution result when recovery succeeds;
- final control evaluation;
- blocked and eligible outputs;
- explicit flags showing whether the task was rerun, whether `next_action` was executed, and whether a model guess was used.

The report is registered as `geotask.agent-evidence-recovery` and is backed by the offline Draft 2020-12 Schema `schemas/geotask-agent-integration-v0.1.schema.json`. Validate a retained trace without reacquiring evidence or repeating recovery:

```bash
geotask artifact validate \
  geotask.agent-evidence-recovery \
  recovery-report.json \
  --format json
```

A report with `state=blocked` can still be a valid Artifact when its nested execution results, control evaluations, evidence-completeness decision, output gates, and safety flags are structurally consistent. Artifact validity does not mean the recovery condition was satisfied.

## 8. GT08 End-to-End Example

Initial document:

```text
route_intersects_zone = true
altitude_conflict = true
temporal_conflict = unverifiable
full_conflict = unknown
next_action = request_evidence
```

Evidence request:

```yaml
evidence_request:
  id: verify-restricted-schedule
  trigger: temporal_conflict
  required_fields:
    - issuing_authority
    - effective_date
    - start_time
    - end_time
    - document_version
    - source_reference
    - verified_at
  blocked_outputs:
    - full_conflict
    - automatic_approval
  resume_when: restricted_schedule_verified == true
  next_action: request_evidence
```

Verified fictional state:

```yaml
restricted_schedule_verified: true
issuing_authority: Fictional Airspace Coordination Office
effective_date: "2026-08-01"
start_time: "08:30"
end_time: "10:00"
document_version: "2026-08-01-r1"
source_reference: fictional://restricted-schedule/2026-08-01-r1
verified_at: "2026-07-30T06:30:00Z"
```

Recovery result:

```text
evidence complete = true
resume_when = true
temporal_conflict rerun = true
full_conflict = true
task_reexecuted = true
next_action_executed = false
model_guess_used = false
```

## 9. Security and Public Boundary

The public profile may demonstrate fictional evidence and deterministic recovery. It does not include:

- real regulatory notices or customer data;
- private source-ranking rules;
- production approval matrices;
- credentials or connector configuration;
- automatic action execution;
- patent-sensitive private Runtime or Domain Pack logic.

Production integrations should keep private retrieval, authority selection, approval, and action execution outside the MIT-licensed Core.

## 10. Related Files

- `src/geotask_core/v1/agent_integration.py`
- `src/geotask_core/v1/agent_generation.py`
- `skills/geotask-core/SKILL.md`
- `examples/core/agent_generated_distance_draft.yaml`
- `examples/core/evidence_request_plan.yaml`
- `examples/core/evidence_request_verified_state.yaml`
- `tests/test_agent_integration_profile.py`
- `tests/test_agent_generated_document_preparation.py`
- `tests/test_agent_generated_document_revision.py`
- [Control Extension Profile v1.0](geotask-control-extension-profile-v1.0.md)
- [Control Evaluation v1.0](geotask-control-evaluation-v1.0.md)
- [Evidence and Recovery](../reference/evidence-and-recovery.md)
