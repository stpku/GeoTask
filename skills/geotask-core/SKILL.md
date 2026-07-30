---
name: geotask-core
description: Generate, validate, execute, and recover verifiable spatial tasks with GeoTask Core without inventing missing evidence.
---

# GeoTask Core Agent Skill

Use this skill when a request contains spatial objects, routes, zones, time windows, altitude intervals, distances, containment, intersections, or evidence-gated operational decisions.

## Boundary

GeoTask Core is the deterministic protocol and validation layer. You are responsible for understanding intent and requesting evidence. Do not pretend GeoTask Core is a hosted-model client, a source of real-world facts, or an authorization system.

Never:

- invent coordinates, schedules, authorities, document versions, source references, or verification times;
- convert `unverifiable`, `need_data`, or unknown into `true` or `false`;
- bypass `blocked_outputs` in prose or another tool call;
- execute `next_action` unless a separate authorized Runtime explicitly supports it;
- replace deterministic operator output with model judgment.

## Required Workflow

1. Discover contracts:

   ```bash
   geotask agent inspect --format json
   geotask inspect schemas --format json
   ```

2. Create or receive a native GeoTask v1 document.

3. Prepare Agent-generated drafts before trusting them:

   ```bash
   geotask agent prepare <generated.yaml> \
     --repaired-output prepared.yaml \
     --output preparation-report.json
   ```

   Accept only `valid` or `repaired`. When the report is `blocked`, use `revision_request.required_changes` to revise the returned `prepared_document`, then run:

   ```bash
   geotask agent retry preparation-report.json revised.yaml \
     --verification-output revision-verification.json \
     --prepared-output prepared.yaml \
     --output retry-report.json
   ```

   `candidate_values` are inventories only: never treat them as selected answers. `agent retry` must accept the revision before execution. Do not bypass its changed-path check, revision-base fingerprint, or reconstructed revision request. Never change coordinates, evidence, task goals, domain policy, or other fields unless the request explicitly names them.

   Treat preparation and retry traces as registered Artifacts. Validate the report you retain for audit:

   ```bash
   geotask artifact validate geotask.agent-generation-preparation preparation-report.json --format json
   geotask artifact validate geotask.agent-revision-retry retry-report.json --format json
   ```

   A structurally valid report may still record `blocked` or `rejected`; do not reinterpret Artifact validity as workflow acceptance.

4. Validate the prepared document:

   ```bash
   geotask artifact validate geotask.document prepared.yaml --format json
   ```

5. Execute deterministic assertions:

   ```bash
   geotask run prepared.yaml --format v1-json --output execution-result.json
   ```

6. Validate the execution result:

   ```bash
   geotask artifact validate geotask.execution-result execution-result.json --format json
   ```

7. When the document declares `geotask.control/1.0`, evaluate controls with explicit state:

   ```bash
   geotask control evaluate <task.yaml> \
     --result execution-result.json \
     --state state.yaml \
     --output control-evaluation.json
   ```

8. If a required assertion is `unverifiable`, surface the declared evidence request exactly. Ask for every item in `required_fields`; do not ask vaguely for “more information.”

9. After evidence arrives, use fail-closed recovery:

   ```bash
   geotask agent recover <task.yaml> \
     --evidence <verified-state.yaml> \
     --output recovery-report.json

   geotask artifact validate \
     geotask.agent-evidence-recovery \
     recovery-report.json \
     --format json
   ```

   A structurally valid recovery Artifact may still record `state=blocked`; do not treat Artifact validity as proof that recovery succeeded.

10. Use the final decision only after the affected assertion has been rerun and the control evaluation no longer blocks the output.

## Status Handling

- `verified`: use the computed value subject to control gates.
- `contradicted`: preserve the contradiction and explain which expectation failed.
- `unverifiable`: request declared evidence; do not guess.
- `need_data`: request or route the named data dependency.
- `execution_error`: report the failure; do not reinterpret it as a domain answer.
- blocked control: keep outputs blocked and state the exact `resume_when` condition.

## GT08 Recovery Example

Initial result:

```text
route_intersects_zone = true
altitude_conflict = true
temporal_conflict = unverifiable
```

Required response:

```text
state = blocked
next_action = request_evidence
blocked_outputs = full_conflict, automatic_approval
```

Do not answer `full_conflict=true` merely because the two known conditions are true.

After all required schedule evidence is present and `restricted_schedule_verified == true`, run:

```bash
geotask agent recover examples/core/evidence_request_plan.yaml \
  --evidence examples/core/evidence_request_verified_state.yaml \
  --output recovery-report.json
```

A successful report must show:

```text
state = recovered
task_reexecuted = true
next_action_executed = false
model_guess_used = false
```

## Public and Private Boundary

Keep real regulatory sources, customer data, connector credentials, source-ranking policies, approvals, and production actions in a private Runtime or Domain Pack. Public Core examples must use fictional evidence.
