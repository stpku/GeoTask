# Run the GeoTask Reference Agent End to End

**English** | [简体中文](reference-agent.zh-CN.md)

This tutorial is for developers who want to understand the complete GeoTask lifecycle without reading GT01–GT42 first. A fictional low-altitude facility receives new obstacle evidence. The workflow shows how that evidence moves through World State, Discrepancy, Correction, Impact, and Control until the report becomes eligible for refresh—without pretending that the report was actually published.

> **Boundary:** all data is fictional. The tutorial uses the public Core and local reference code only. It does not read a Lowa-GT production database, fetch live regulatory data, write production state, publish a report, or execute a real-world action.

## 1. Prepare a source checkout

The fixed scenarios and replay script are public repository examples, so run this tutorial from a source checkout:

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m pip install -e .
```

If you are already inside the GeoTask repository, continue directly. `replay.py` also supports an installed `geotask-core` package while keeping the example files in the checkout.

## 2. Replay the success scenario

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario success \
  --check-expected
```

The fixed success scenario contains:

- fictional facility `FAC-001`;
- previous obstacle distance: 80 m;
- minimum obstacle-distance threshold: 50 m;
- a fresh map Observation moving the obstacle to 70 m from the facility;
- evidence inside its declared validity interval;
- explicit human-review approval.

Do not read only the final `satisfied` state. The important part is why the state advances through three revisions.

## 3. Understand rev1 → rev2 → rev3

### rev1: baseline World State

`world_state_before.json` contains the previous business state:

```text
obstacle_distance_m = 80
obstacle_clearance_pass = true
accessibility_score = 84
service_capability_score = 78
report_version = report-v4
```

This is an immutable baseline. The replay records its `semantic_fingerprint` and never edits it in place.

### rev2: apply only the new Observation

After the map evidence is accepted, the Reference Agent first creates an observation-state snapshot:

```text
mapped-obstacle-01.position_xy: 80m → 70m
obstacle_distance_m: still 80
obstacle_clearance_pass: still true
```

The old assessment is intentionally left unchanged. Otherwise the system would lose the distinction between **a changed real-world input** and **a conclusion that has not yet been recomputed**.

Inspect:

```text
reference_agent.world_state_update.observation_state_revision = 2
```

## 4. Discrepancy: state what is currently inconsistent

The registered `geotask.discrepancy-report` represents:

```text
current observed value = 80m
expected recomputed value = 70m
```

`observed` is the stale value that actually exists in revision 2. `expected` is the deterministic target derived after the new evidence. GeoTask does not describe a future recomputed value as though it were already present in the current state.

Inspect:

```text
reference_agent.registered_impact_bundle.discrepancy_report
```

## 5. Correction: allow only two paths to change

The registered `geotask.correction-request` permits only:

```text
recompute obstacle_distance_m
recompute obstacle_clearance_pass
```

It explicitly protects unrelated assessment paths such as:

```text
accessibility_score
service_capability_score
```

One obstacle update therefore does not silently become a full-site rescore.

Inspect:

```text
reference_agent.registered_impact_bundle.correction_request
```

## 6. Impact: propagate through an explicit finite dependency graph

The registered `geotask.impact-graph` represents the bounded dependency chain:

```text
Discrepancy
  → recompute obstacle distance
  → obstacle_distance_m path
  → distance_2d assertion recheck
  → obstacle clearance path
  → assessment_refresh
  → report_refresh
```

The Core does not discover every dependency in the world or expand the reevaluation to unrelated facilities and report sections.

Inspect:

```text
reference_agent.registered_impact_bundle.impact_graph
```

`reference_agent.impact_scope` is the developer-facing business summary. The registered artifact in `registered_impact_bundle` is the Core-validated representation of the correction chain.

## 7. rev3: materialize only the affected assessment values

After deterministic `distance_2d` execution, revision 3 contains:

```text
obstacle_distance_m = 70
obstacle_clearance_pass = true
accessibility_score = 84       # reused
service_capability_score = 78  # reused
```

Inspect:

```text
reference_agent.world_state_update.successor_revision = 3
```

## 8. Control: eligibility is not execution

The report-refresh gate requires:

```text
obstacle_distance_m >= min_obstacle_distance_m
AND evidence_verified == true
AND human_review_approved == true
```

The success scenario satisfies the gate, so:

```text
assessment_refresh_eligible = true
report_update_eligible = true
```

But the same result must also say:

```text
production_write_performed = false
production_report_refreshed = false
action_authorized = false
action_executed = false
```

GeoTask establishes that an external business workflow may now take the next explicitly authorized step. Lowa-GT or another industry system still owns the real write, approval, publication, and new authoritative business record.

## 9. Replay the fail-closed scenarios

Missing evidence:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario missing_evidence \
  --check-expected
```

The result remains `unverifiable` and emits an Evidence Request.

Fresh conflicting evidence:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario conflicting_evidence \
  --check-expected
```

Two fresh independent observations report 70 m and 30 m. No precedence or adjudication rule is declared, so the result remains `conflicted` rather than inventing authority or majority voting.

Stale evidence:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario stale_evidence \
  --check-expected
```

Existing data is not automatically current evidence; the result remains `unverifiable`.

Explicit contradiction:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario contradicted \
  --check-expected
```

The fresh obstacle position produces a deterministic distance of 30 m. That fact can enter the successor World State, but `obstacle_clearance_pass=false` and the report refresh remains blocked.

## 10. Modify one input yourself

Copy the success scenario without changing Core code:

```bash
cp examples/reference_agent/facility_assessment_update/scenarios/success.json /tmp/geotask-reference-60m.json
```

In the copied file change only:

```text
scenario.id: success → developer-60m
coordinates: [70, 0] → [60, 0]
```

You may remove the fixed `expected` block because it belongs to the built-in acceptance fixture. Keep the original source, time, producer, version, and validity fields.

Run the custom scenario:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario-file /tmp/geotask-reference-60m.json
```

You should observe:

```text
distance_m = 60.0
observation_state_revision = 2
successor_revision = 3
report_update_eligible = true
production_report_refreshed = false
```

This is a Product Track requirement: a developer can modify an actual input state and see the lifecycle change, rather than only watching a fixed demonstration.

## 11. Check deterministic replay

Running the same fixed input twice should preserve the same `replay_fingerprint`:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario success
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario success
```

The automated tests enforce this property as well.

## 12. Run the focused Reference Agent tests

```bash
python3 -m pytest \
  tests/test_reference_agent_facility_assessment_update.py \
  tests/test_reference_agent_experience_page.py
```

The focused suite covers:

- all five fixed scenarios;
- fail-closed unknown/conflict semantics;
- rev1 / rev2 / rev3 separation;
- registered Discrepancy / Correction / Impact artifacts and SHA-256 bindings;
- bounded impact and reuse of unrelated results;
- developer-supplied scenario files;
- deterministic replay;
- `eligible != executed`;
- the public experience page and project entry point.

## 13. Next: map the pattern into Lowa-GT without copying its database

The public Reference Agent proves the generic mechanism only. The first real industry validation follows `GeoTask ↔ Lowa-GT Integration Contract v0.1` in read-only/shadow mode:

```text
Lowa-GT authoritative facility/evidence/assessment/report state
→ bounded Trusted State Snapshot
→ GeoTask Verification / Impact / Control
→ human-readable recommendation
→ Lowa-GT decides whether to rescore or refresh
```

GeoTask does not become a second low-altitude System of Record and does not directly write the Lowa-GT production database.
