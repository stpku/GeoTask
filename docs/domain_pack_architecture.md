# GeoTask Domain Pack Architecture

## What Is a Domain Pack

A Domain Pack is a **pluggable industry-specific extension** that runs on top of GeoTask Runtime. It provides the domain objects, rules, templates, scoring models, data connectors, and workflow definitions required to deploy GeoTask in a specific industry vertical.

A Domain Pack does **not** interact with Core directly. It communicates through the Runtime, which handles model orchestration, verification, governance, and audit.

Domain Pack 是运行在 GeoTask Runtime 之上的可插拔行业扩展包，提供特定行业部署所需的领域对象、规则、模板、评分模型、数据连接器和工作流定义。Domain Pack 不直接与 Core 交互，而是通过 Runtime 通信。

---

## Domain Pack Interface Contract

A Domain Pack must implement the `DomainPackProtocol`:

```python
from typing import Protocol, Any

class DomainPackProtocol(Protocol):
    """Interface contract for GeoTask Domain Packs."""

    @property
    def pack_id(self) -> str:
        """Unique identifier for this Domain Pack."""
        ...

    @property
    def version(self) -> str:
        """Semantic version string."""
        ...

    def get_object_models(self) -> dict[str, Any]:
        """Return industry-specific object type definitions.

        Each object model defines fields, validation rules,
        and mapping to Core object types.
        """
        ...

    def get_operator_mapping(self) -> dict[str, str]:
        """Return mapping from domain concepts to Core operators.

        Keys are domain-specific operation names.
        Values are Core operator names or extended operator references.
        """
        ...

    def get_rules(self) -> list[dict[str, Any]]:
        """Return industry rules and constraints.

        Each rule defines conditions, thresholds, and actions.
        """
        ...

    def get_task_templates(self) -> list[dict[str, Any]]:
        """Return pre-built task templates for common workflows.

        Each template is a parameterized GeoTask YAML skeleton.
        """
        ...

    def get_scoring_model(self) -> dict[str, Any]:
        """Return domain-specific scoring configuration.

        Defines weights, thresholds, and aggregation methods.
        """
        ...

    def get_workflow_templates(self) -> list[dict[str, Any]]:
        """Return multi-step workflow definitions.

        Each workflow defines steps, dependencies, approval gates,
        and escalation rules.
        """
        ...

    def get_data_connector_configs(self) -> list[dict[str, Any]]:
        """Return data connector interface configurations.

        Each config defines the data source type, connection parameters,
        and field mapping. Credentials are managed by Runtime.
        """
        ...

    def get_report_templates(self) -> list[dict[str, Any]]:
        """Return output report format templates."""
        ...

    def get_human_review_rules(self) -> list[dict[str, Any]]:
        """Return rules for human review escalation.

        Defines when automated results require manual verification.
        """
        ...
```

---

## How a Domain Pack Extends Runtime

```
┌──────────────────────────────────────────────────┐
│                  Domain Application               │
│         (user-facing interface)                   │
├──────────────────────────────────────────────────┤
│               Domain Pack                         │
│  ┌───────────┬──────────┬───────────────────┐    │
│  │ Object    │ Rules &  │ Task & Workflow    │    │
│  │ Models    │ Scoring  │ Templates          │    │
│  ├───────────┼──────────┼───────────────────┤    │
│  │ Data      │ Report   │ Human Review      │    │
│  │ Connectors│ Templates│ Rules             │    │
│  └───────────┴──────────┴───────────────────┘    │
├──────────────────────────────────────────────────┤
│                    Runtime                        │
│  (orchestration, model adapter, governance)       │
├──────────────────────────────────────────────────┤
│                     Core                          │
│  (format, operators, normalizer, verifier)        │
└──────────────────────────────────────────────────┘
```

**Interaction flow:**

1. Domain Application receives a user request
2. Domain Pack selects the appropriate task template and fills in parameters
3. Domain Pack submits the task to Runtime via the Runtime SDK
4. Runtime orchestrates model calls, verification, and governance
5. Runtime returns verified results to Domain Pack
6. Domain Pack applies scoring model, checks rules, evaluates review escalation
7. Domain Pack formats the report and returns it to the Domain Application

---

## Example Domain Packs

### LowAlt Site Precheck Pack

| Aspect | Detail |
|--------|--------|
| Industry | Low-altitude economy, UAV operations |
| Object models | Takeoff sites, landing zones, flight corridors, restricted airspace, obstacles, weather zones |
| Core operator mapping | `distance_2d` → site-to-obstacle distance; `line_intersects_rect` → route-to-restricted-zone intersection; `rect_contains_point` → site within controlled zone; `altitude_overlap` → flight altitude vs. restricted altitude band |
| Key rules | Minimum distance to obstacles; airspace authorization requirements; weather minimums; no-fly zone avoidance |
| Task templates | Site precheck report; route clearance check; multi-site comparison |
| Data connectors | Airspace database adapter; obstacle database adapter; weather service adapter |

### Facility Siting Pack

| Aspect | Detail |
|--------|--------|
| Industry | Infrastructure planning, real estate, logistics |
| Object models | Candidate sites, existing facilities, population centers, environmental zones, transportation nodes |
| Core operator mapping | `distance_2d` → facility-to-demand distance; `rect_contains_point` → site within restricted zone; `point_to_line_distance_2d` → site-to-road distance |
| Key rules | Minimum separation between facilities; maximum distance to demand centers; environmental exclusion zones; zoning compliance |
| Task templates | Multi-criteria site ranking; constraint satisfaction check; comparative site analysis |
| Data connectors | GIS database adapter; zoning registry adapter; transportation network adapter |

### Network Spatial Optimization Pack

| Aspect | Detail |
|--------|--------|
| Industry | Telecommunications, logistics networks |
| Object models | Base stations, coverage areas, demand points, backbone nodes, cable routes |
| Core operator mapping | `distance_2d` → station-to-demand distance; `line_intersects_rect` → cable route through restricted zone; `rect_contains_point` → demand point within coverage |
| Key rules | Maximum coverage distance; minimum signal overlap; redundancy requirements; cost-per-distance thresholds |
| Task templates | Coverage gap analysis; new station placement evaluation; route optimization check |
| Data connectors | Network inventory adapter; terrain database adapter; demand forecast adapter |

### Urban Space Risk Pack

| Aspect | Detail |
|--------|--------|
| Industry | Urban planning, public safety, emergency management |
| Object models | Risk sources, population zones, evacuation routes, emergency facilities, critical infrastructure |
| Core operator mapping | `distance_2d` → risk source to population distance; `line_intersects_rect` → evacuation route through hazard zone; `rect_contains_point` → critical facility within risk area; `time_overlap` → event timing conflict |
| Key rules | Minimum safety buffer distances; evacuation route clearance; emergency response time limits; concurrent event capacity |
| Task templates | Risk proximity assessment; evacuation feasibility check; emergency coverage analysis |
| Data connectors | Urban planning database adapter; emergency service registry adapter; hazard map adapter |

---

## Domain Pack Lifecycle

### 1. Define

- Identify industry requirements and spatial reasoning use cases
- Define domain object models with field specifications
- Map domain concepts to Core operators
- Design industry rules, scoring models, and workflow templates
- Specify data connector interfaces
- Create acceptance test cases

### 2. Test

- Unit tests for object model validation
- Integration tests with Mock Runtime (using Domain Pack protocol)
- Rule evaluation tests with synthetic data
- Workflow tests covering multi-step processes and approval gates
- Data connector tests with mock data sources
- End-to-end tests: user request → Domain Application → Domain Pack → Runtime → Core → verified result

### 3. Deploy

- Register Domain Pack with Runtime via pack registry
- Configure data connector credentials in Runtime (credentials never stored in Domain Pack)
- Set per-pack resource limits and quota allocations
- Enable audit logging for domain-specific operations
- Activate human review rules and escalation channels

### 4. Update

- Domain Pack versioning follows semantic versioning
- Runtime supports multiple concurrent Domain Pack versions for migration
- Rule updates can be deployed without full pack redeployment (hot reload for rule changes)
- Object model changes require version bump and migration validation
- All updates produce audit records

---

## Versioning

| Component | Versioning Strategy |
|-----------|-------------------|
| Domain Pack protocol | Semantic versioning; breaking changes require major version bump |
| Individual Domain Packs | Independent semantic versioning per pack |
| Object models within a pack | Versioned with the pack; backward-compatible additions are minor versions |
| Rules within a pack | Rules carry individual version tags; can be updated independently |
| Runtime compatibility | Each Domain Pack declares minimum Runtime version in its manifest |

**Pack manifest example:**

```yaml
pack:
  id: "lowalt-site-precheck"
  version: "1.0.0"
  runtime_min_version: "2.0.0"
  core_min_version: "0.3.0"
  author: "GeoTask Team"
  license: "proprietary"
  description: "Low-altitude site precheck for UAV operations"
```

---

## Relationship to Patent Portfolio

| Domain Pack Capability | Patent Relevance |
|----------------------|-----------------|
| Industry object model definitions | Not patentable (data schema) |
| Operator mapping from domain to Core | Method patent: domain-specific spatial task decomposition |
| Industry rule evaluation | Method patent: automated compliance verification |
| Task template instantiation | Method patent: parameterized spatial task generation |
| Scoring model execution | Method patent: domain-specific spatial quality scoring |
| Workflow orchestration with approval gates | Method patent: governed spatial task workflow |
| Data connector integration | Not patentable individually; covered by system patents |

Domain Pack implementations contain patent-sensitive methods. The Domain Pack protocol and generic examples are public; all real industry implementations are private.

---

## Separation of Generic Examples from Commercial Packs

| Category | Public (Generic Example) | Private (Commercial Pack) |
|----------|-------------------------|--------------------------|
| Object models | `ExamplePoint`, `ExampleLine`, `ExampleRect` with trivial fields | Industry-specific objects with regulatory field requirements |
| Rules | "distance must be > 100 meters" | Regulatory thresholds, safety margins, compliance logic |
| Task templates | Basic distance check template | Multi-step industry workflow templates |
| Scoring | Simple pass/fail threshold | Weighted multi-criteria scoring with domain expertise |
| Data connectors | Mock connector returning static data | Real database/API adapters with authentication |
| Workflows | Single-step validate-and-return | Multi-step with approval gates, escalation, and audit |

---

*Document version: v0.1 | Date: 2025-06-18 | Status: Initial architecture definition*
