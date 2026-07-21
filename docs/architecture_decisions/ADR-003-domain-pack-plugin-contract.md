# ADR-003: Domain Pack Plugin Contract

**Date:** 2025-06-18
**Status:** Accepted
**Deciders:** GeoTask maintainers

---

## Context

Domain Packs extend GeoTask Runtime with industry-specific capabilities. We need a plugin contract that:

1. Enables independent development and deployment of Domain Packs
2. Supports diverse industries with different object models, rules, and workflows
3. Maintains clear separation between generic examples (public) and commercial packs (private)
4. Allows Runtime to discover, load, validate, and manage Domain Packs at runtime

We evaluated three contract approaches:

- **Inheritance-based**: Domain Packs extend a base class provided by Runtime
- **Protocol-based**: Domain Packs implement a structural interface (Python Protocol)
- **Configuration-based**: Domain Packs are pure YAML/JSON configuration with no code

---

## Decision

Domain Packs implement a **Protocol-based contract** (`DomainPackProtocol`).

---

## Contract Definition

The `DomainPackProtocol` is a Python `Protocol` class that defines the structural interface every Domain Pack must satisfy. Runtime uses structural subtyping — any class that implements the required methods is a valid Domain Pack, regardless of inheritance.

Core contract methods:

| Method | Returns | Purpose |
|--------|---------|---------|
| `pack_id` (property) | `str` | Unique identifier |
| `version` (property) | `str` | Semantic version |
| `get_object_models()` | `dict[str, Any]` | Industry object type definitions |
| `get_operator_mapping()` | `dict[str, str]` | Domain concept → Core operator mapping |
| `get_rules()` | `list[dict[str, Any]]` | Industry rules and constraints |
| `get_task_templates()` | `list[dict[str, Any]]` | Parameterized task skeletons |
| `get_scoring_model()` | `dict[str, Any]` | Scoring configuration |
| `get_workflow_templates()` | `list[dict[str, Any]]` | Multi-step workflow definitions |
| `get_data_connector_configs()` | `list[dict[str, Any]]` | Data source configurations |
| `get_report_templates()` | `list[dict[str, Any]]` | Output format templates |
| `get_human_review_rules()` | `list[dict[str, Any]]` | Review escalation rules |

See [`domain_pack_architecture.md`](../domain_pack_architecture.md) for the full Protocol definition.

---

## Lifecycle

### Registration

1. Domain Pack implementation is packaged as a Python module
2. Runtime discovers packs via entry points or explicit registration
3. Runtime validates the pack against `DomainPackProtocol` structural checks
4. Runtime loads pack metadata (id, version, compatibility requirements)
5. Pack is added to the runtime pack registry

### Execution

1. Incoming request is routed to the appropriate Domain Pack based on task type
2. Domain Pack selects task template and fills parameters
3. Runtime orchestrates the task (model calls, Core verification, governance)
4. Domain Pack applies scoring, rules, and formatting to the result
5. Result is returned through the Domain Application

### Update

1. New pack version is deployed alongside the existing version
2. Runtime supports concurrent versions during migration windows
3. Traffic is gradually shifted to the new version
4. Old version is deregistered after migration completes

### Deregistration

1. Pack is marked as deprecated in the registry
2. Active tasks using the pack are allowed to complete
3. Pack is removed from the registry after drain period

---

## Versioning

| Rule | Description |
|------|-------------|
| Pack versions are independent | Each Domain Pack follows its own semantic versioning |
| Protocol version compatibility | Each pack declares its minimum Runtime version in the pack manifest |
| Backward compatibility | Minor version changes must not break existing task templates or workflows |
| Breaking changes | Major version bumps require migration documentation and a concurrent deployment window |
| Core version dependency | Packs declare minimum Core version for operator availability |

**Pack manifest schema:**

```yaml
pack:
  id: string        # unique pack identifier
  version: string   # semantic version (e.g., "1.2.0")
  runtime_min_version: string  # minimum Runtime version
  core_min_version: string     # minimum Core version for required operators
  author: string
  license: string   # "proprietary" for commercial packs
  description: string
```

---

## Testing Strategy

| Test Level | Scope | Environment |
|------------|-------|-------------|
| Unit | Object model validation, rule evaluation, template rendering | Pack code only |
| Integration | Pack ↔ Mock Runtime interaction | Mock Runtime from public SDK |
| Contract | Pack satisfies `DomainPackProtocol` structural checks | Automated protocol validation |
| End-to-end | Full request flow through Domain Application → Pack → Runtime → Core | Staging environment with real Runtime |
| Regression | Existing tasks produce consistent results after pack update | CI/CD pipeline |

**Contract testing example:**

```python
from typing import runtime_checkable
from domain_pack_protocol import DomainPackProtocol

@runtime_checkable
class DomainPackProtocol(Protocol):
    ...

def validate_pack(pack: object) -> bool:
    return isinstance(pack, DomainPackProtocol)
```

---

## Separation of Generic Examples from Commercial Packs

### Public (Generic Examples)

- Skeleton pack implementing `DomainPackProtocol` with trivial logic
- Example object models using Core's `point`, `line`, `rect` types
- Simple rules (e.g., "distance must exceed threshold")
- Single-step task templates
- Mock data connector returning static data
- Intended for: developer onboarding, protocol understanding, testing

### Private (Commercial Packs)

- Full industry object models with regulatory field requirements
- Production rules with real safety margins and compliance thresholds
- Multi-step workflow templates with approval gates
- Real data connectors with authentication and error handling
- Domain scoring models calibrated to industry standards
- Intended for: customer deployments, revenue generation

---

## Consequences

### Positive

- Protocol-based contract enables structural subtyping without requiring inheritance
- Independent versioning allows industries to evolve at their own pace
- Clear separation between public examples and commercial packs protects IP
- Mock Runtime enables Domain Pack development without Runtime access

### Negative

- Protocol evolution must be managed carefully to avoid breaking existing packs
- Structural typing may miss errors that inheritance-based typing would catch at import time
- Domain Pack developers must test against Mock Runtime, which may not perfectly replicate production behavior

### Mitigations

- Contract validation tool provided as part of the public SDK
- Mock Runtime is maintained in sync with production Runtime's external behavior
- Protocol changes follow deprecation cycles with at least one version of backward compatibility

---

## References

- [`docs/domain_pack_architecture.md`](../domain_pack_architecture.md)
- [`docs/product_architecture_v0_1.md`](../product_architecture_v0_1.md)
- [ADR-001: Three-Layer Architecture](ADR-001-core-runtime-domain-pack.md)
- [ADR-002: Private Runtime Boundary](ADR-002-private-runtime-boundary.md)
