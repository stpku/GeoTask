# GeoTask repository benchmarks

## TC1 — Task Context Proof Benchmark v0.1

Run:

```bash
python -m benchmarks.run_task_context_v0_1
```

The benchmark currently contains two **synthetic, deterministic** physical-world task fixtures:

1. **low-altitude mission preparation** — weather, airspace, obstacle resolution, and optional POI context;
2. **multi-scale spatial planning** — district demand/capacity at coarse scale plus local hotspot refinement.

Each case compares the same three strategies:

- **B0 / full_context** — load every candidate item;
- **B1 / manual_template** — use a fixed human-authored checklist;
- **G0 / declared_min_cost_v0** — select one lowest-cost candidate for every critical requirement only when explicit scope and declared resolution checks pass.

G0 deliberately lives in `benchmarks/`, not `geotask_core`. It is an experimental selection policy, not a public GeoTask semantic contract.

The benchmark reports:

- Critical Context Miss Rate (CCMR);
- Context Preparation Cost (CPC), using the synthetic `fixture_cost_point` unit;
- item-count Context Reduction Ratio (CRR);
- concrete context gaps;
- refinement requirements;
- context status.

`Task Outcome Regret` is intentionally reported as unavailable because these fixtures do not contain an independently validated downstream flight or planning outcome model. Reporting zero regret would falsely imply real-world decision accuracy.

### What TC1 can prove

TC1 can prove that the current contracts and a named deterministic policy can distinguish these three failure/cost patterns:

```text
full context      -> critical coverage can be complete but unnecessarily expensive
fixed template    -> can be cheaper but miss a task-specific critical condition
G0 task context   -> can select a smaller set while preserving declared critical coverage
```

### What TC1 cannot prove

TC1 does **not** prove that GeoTask automatically discovers the right requirements, that its synthetic costs match operational cost, or that a reduced context produces a correct real-world decision.

Those claims require later real or independently labelled domain evidence. The synthetic benchmark is a contract/proof harness, not a product accuracy benchmark.
