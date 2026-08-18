# Low-altitude mission Task Context demo

This fictional, offline example is the first task-first slice of the GeoTask Task Context Engine direction.

It intentionally starts from a **task**, not from a pre-built World State:

> Prepare context for a fictional low-altitude delivery mission from A to B in a declared time window.

The task declares four context requirements:

1. weather — critical;
2. applicable airspace restrictions — critical;
3. obstacle context — critical, with a required spatial resolution of 10 m or finer;
4. POI labels — non-critical, explanation only.

The selected candidate context contains:

- a 500 m weather grid that satisfies the declared weather requirement;
- an airspace notice bound to the same corridor/time scope;
- a 100 m obstacle grid, which is relevant and spatially applicable but too coarse;
- no POI labels.

Spatial resolution units are explicit. The demo also uses a fictional `credits` unit for context-acquisition cost so that cost is never silently compared across incompatible units.

Running:

```bash
python examples/task_context/low_altitude_mission/demo.py
```

should produce a result equivalent to:

```text
task_id=delivery-a-b-1500
status=insufficient
gaps=obstacles,poi_labels
refinement_needed=obstacles
context_cost=4.0 credits
budget_exceeded=false
```

The important behavior is not that GeoTask knows the full world. It knows that:

- weather is already good enough for this declared task requirement;
- airspace context is already present for the declared scope;
- obstacle context needs finer detail;
- POI labels may remain absent because they are non-critical;
- therefore the next useful information action is to refine **obstacle context**, not to collect everything.

## What this demo proves

This v0.1 slice proves only deterministic contract behavior:

```text
TaskFrame
  → ContextRequirement
  → ContextCandidate
  → explicit relevance binding
  → explicit scope applicability
  → explicit resolution-unit compatibility
  → declared resolution check
  → sufficiency / gap result
```

## What it does not prove

It does not:

- discover the requirements automatically;
- search maps, weather, or airspace services;
- infer that one geometry contains another;
- decide the globally cheapest set of context candidates;
- calculate a real route or risk score;
- authorize a real flight;
- claim that 10 m is a generally correct obstacle resolution.

The 10 m requirement is deliberately caller-declared so the first slice can test the contract before GeoTask attempts decision-sensitive automatic resolution selection.
