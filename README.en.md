# GeoTask

[简体中文](README.md) | **English**

> **GeoTask is a spatiotemporal Task Context Engine for AI agents.**
>
> It does not try to put “the whole world” into an agent context. It constructs the **minimum context that the current task actually needs, that is applicable, resolution-adequate, and explicitly sufficient**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![CI](https://github.com/stpku/GeoTask/actions/workflows/ci.yml/badge.svg)](https://github.com/stpku/GeoTask/actions/workflows/ci.yml)
[![Pages](https://github.com/stpku/GeoTask/actions/workflows/pages.yml/badge.svg)](https://stpku.github.io/GeoTask/)
[![Release](https://img.shields.io/github/v/release/stpku/GeoTask?include_prereleases&label=release)](https://github.com/stpku/GeoTask/releases)
[![PyPI](https://img.shields.io/pypi/v/geotask-core)](https://pypi.org/project/geotask-core/)

## Why Task Context instead of more context?

For an agent working on a real task, the hard questions are usually not “do we have data?” but:

- **What does this task actually need to know?**
- A fact may be relevant, but is it applicable to this object, place, time, and condition?
- Is its spatial, temporal, or semantic resolution adequate for the task?
- Is the resulting context sufficient, or is a critical gap still open?
- Can irrelevant context be removed without increasing critical misses?
- When reality changes, which requirements must be reassessed and which context can be reused?

GeoTask turns these questions into explicit, composable, testable Task Context contracts and methods.

```text
Task
  ↓
derive requirements
  ↓
discover candidates
  ↓
Relevance
  ↓
Applicability
  ↓
Resolution Adequacy
  ↓
Sufficiency
  ↓
Minimum Sufficient TaskContext
  ↓
Explicit Gaps / Trace / Cost
```

## Core semantics

The current public Core exposes task-context primitives and composition seams including:

- `TaskFrame`
- `ContextRequirement`
- `ContextCandidate`
- `RelevanceResult`
- `ApplicabilityResult`
- `ResolutionRequirement` / `ResolutionAdequacyResult`
- `ContextAssessment`
- `ContextGap`
- `SufficiencyAssessment`
- `TaskContext`
- `ContextConstructionTrace`
- `ContextMinimalityAssessment`
- `MinimumSufficientTaskContext`
- temporal reassessment / continuity contracts

The contracts deliberately preserve these distinctions:

```text
Context ≠ World State
Relevant ≠ Applicable
Applicable ≠ Sufficient
Candidate exists ≠ Requirement satisfied
Large payload ≠ Sufficient context
Provider returned a value ≠ Valid task context
Context sufficient ≠ Domain decision
Context sufficient ≠ Action authorization
```

## What GeoTask owns

GeoTask owns **task-relative context**:

1. frame the task, goal, and scope with `TaskFrame`;
2. derive or receive `ContextRequirement` objects;
3. acquire `ContextCandidate` objects from GIS, API, sensor, database, WorldState, or other providers;
4. assess relevance, applicability, and resolution adequacy separately;
5. keep requirement-level assessments and gaps explicit;
6. compose `SufficiencyAssessment` through an explicit method;
7. construct `TaskContext` and seek a minimum sufficient context without increasing critical misses;
8. when a provider or reality changes, reassess only affected requirements and reuse unaffected context where valid.

GeoTask **does not own world truth** and does not replace an agent harness, GIS, database, knowledge graph, RAG system, or domain decision system.

```text
World / Data Providers
WorldState · GIS · API · Sensor · Database · Other Provider
                    │
                    ▼
              ┌─────────┐
              │ GeoTask │
              │  Task   │
              │ Context │
              └────┬────┘
                   │
                   ▼
             Agent / Harness
                   │
                   ▼
           Domain Decision / Action
```

**A provider can tell GeoTask what candidate information exists. GeoTask evaluates whether that information is needed, applicable, and sufficient for the current task.**

## North Star: sufficiency, not accumulation

GeoTask's long-term North Star is:

> **Task Sufficiency at Minimum Context Cost**

The goal is to support the task with the smallest useful context while keeping critical requirement misses visible.

Positive metrics should be paired with counter-metrics:

| Goal | Counter-metric |
|---|---|
| Critical Requirement Coverage ↑ | **Critical Context Miss Rate** |
| Sufficiency Accuracy ↑ | **False Sufficiency Rate** |
| Context Reduction ↑ | **Critical Context Miss Rate** |
| Applicability Accuracy ↑ | **Irrelevant / Inapplicable Context Rate** |
| Local Rebuild ↑ | **Unnecessary Context Rebuild** |

Context cost can include acquisition cost, carried bytes, token cost, provider latency, and human recovery cost.

## Public independent consumer: Warehouse Robot Picking

GeoTask includes an independent public consumer that does **not** require the official WorldState implementation and does not depend on the low-altitude domain:

```text
Indoor GIS / topology
Inventory API
Aisle-clearance sensor
        ↓
TaskFrame
        ↓
ContextRequirement[]
        ↓
ContextCandidate[]
        ↓
Relevance / Applicability / Resolution Adequacy
        ↓
SufficiencyAssessment
        ↓
Minimum Sufficient TaskContext
        ↓
Sensor change
        ↓
Bounded Temporal Reassessment
```

The example preserves an important boundary: if an aisle is measured narrower than the robot, GeoTask may still conclude that **the context is sufficient** when that measurement is relevant, applicable, fresh, and resolution-adequate. It does **not** conclude that the robot may traverse the aisle. Domain safety and action authorization remain downstream.

- [Warehouse Robot Picking example](examples/independent_consumers/warehouse_robot_picking/README.md)

## Install and inspect

```bash
pip install geotask-core
geotask inspect capabilities
geotask inspect health
```

The public package also retains previously released deterministic operators, Artifacts, Verification, Runtime/Provider, Reference Agent, and benchmark capabilities. They remain supported public compatibility assets from GeoTask's earlier evolution; **the long-term semantic direction is now Task Context Engine**.

To inspect the Task Context Engine composition directly, start with the independent consumer:

```bash
python - <<'PY'
from examples.independent_consumers.warehouse_robot_picking.consumer import (
    build_warehouse_pick_context,
)

run = build_warehouse_pick_context()
print(run.construction.sufficiency.status)
print(len(run.construction.context.values), len(run.minimum.context.values))
PY
```

Expected high-level output:

```text
sufficient
4 3
```

This is a deterministic reference example, not a live warehouse integration or robot-safety certification.

## Reality change is a context problem too

Task Context is not one-shot prompt assembly. During long-running work, reality changes: state expires, providers update, conflicts appear, and unknowns are resolved.

GeoTask's change-response boundary is:

```text
Changed facts / provider state
        ↓
Affected ContextRequirements
        ↓
Reassess Applicability / Resolution / Sufficiency
        ↓
ContextGap delta
        ↓
Minimal rebuild only when needed
```

The objective is not to rebuild everything after every change, but to make **context rebuild locality** explicit and measurable.

## Public research direction

The current Task Context line advances through these problems:

- **Requirement Derivation** — stable Task → Requirement methods;
- **Relevance / Applicability Separation** — the same fact can have different applicability for different tasks;
- **Resolution Adequacy & Sufficiency** — data availability is not the same as task adequacy;
- **Minimum Context Cost** — reduce context cost without increasing critical misses;
- **Temporal Reassessment** — bounded reassessment and minimal rebuild after change;
- **Independent Consumers** — validate the Core in additional domains so one product cannot shape the semantics.

These are research and public capability directions, not delivery-date commitments.

## Legacy / compatibility

Earlier public GeoTask releases centered on a verifiable spatiotemporal task protocol, World-State Cycle, Verification, and related Artifacts. Those assets remain for compatibility, traceability, and maintenance of released capabilities, but they **no longer define GeoTask's long-term product positioning**.

### Released v0.4.1 compatibility surface

These capabilities remain real public compatibility commitments. Earlier v0.4.x release material described GeoTask as an **“Open verifiable spatiotemporal task protocol and deterministic Core”** and discussed a **“trusted world-state runtime”**; those phrases are retained here only as historical release context.

| Release item | Version | Notes |
|---|---:|---|
| GeoTask Core package | `0.4.1` | [v0.4.1 release notes](docs/release_v0_4_1.md) |

Released deterministic operators include `distance_2d`, `line_intersects_rect`, `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, and `altitude_overlap`. Base object types include `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`, and `feature_collection`.

Existing Agent / Runtime / Provider tooling remains compatible:

```bash
geotask agent prepare
geotask agent retry
geotask runtime inspect
geotask runtime check
geotask runtime mock
geotask provider inspect
geotask provider check
geotask provider validate
```

The existing Runtime Interface Profile and Verification Provider Descriptor remain bounded compatibility contracts: the Core does not **invent undeclared source precedence**, and provider validation does not turn an external response into world truth.

Useful legacy entry points:

- [GeoTask Architecture Series v0.1](docs/articles/architecture-series/README.zh-CN.md)
- [Documentation index](docs/README.en.md)
- [GT01–GT20 Cookbook](docs/cookbook/gt01-gt20.md)
- [GT21–GT28 World-State Cycle](docs/cookbook/gt21-gt28.md)
- [Reference Agent](docs/reference/reference-agent-v0.1.md)
- [Verification Quality Benchmark](docs/reference/verification-quality-benchmark-v0.2.md)
- [Historical White Paper v0.1](docs/whitepaper/GeoTask_White_Paper_v0.1.md)
- [Historical White Paper English Abstract](docs/whitepaper/GeoTask_White_Paper_v0.1.md#english-abstract)

> Historical documents that describe “GeoTask = World-State Runtime / Verifiable World Model” should be read in their release-era context. The current positioning is **Task Context Engine**.

## Start here

- [GeoTask project homepage](https://stpku.github.io/GeoTask/)
- [Warehouse Robot Picking independent consumer](examples/independent_consumers/warehouse_robot_picking/README.md)
- [Quickstart](docs/tutorials/quickstart.md)
- [Public API](src/geotask_core/v1/)
- [Examples](examples/)
- [Issues](https://github.com/stpku/GeoTask/issues)
- [Releases](https://github.com/stpku/GeoTask/releases)

## License

GeoTask Core is released under the [MIT License](LICENSE).

---

**In one sentence: GeoTask does not try to know the whole world; it helps an agent obtain only the spatiotemporal context that the current task actually needs, that applies, and that is sufficient.**
