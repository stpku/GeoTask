# GeoTask Core Architecture

## Main Chain

Every GeoTask document flows through a single linear pipeline:

```
parse => canonicalize => validate => execute => result
```

### 1. Parse

Raw YAML input is loaded into a Python dictionary. Structural checks catch missing sections, duplicate keys, and unknown top-level fields. Version detection distinguishes legacy (v0.x) documents from v1.0 native documents.

Module: `geotask_core.parser`

### 2. Canonicalize

The parsed dictionary is converted into a `CanonicalDocument` dataclass. This step normalizes legacy field names (`xy` to `coordinates`, `line` to `polyline`), auto-generates assertions from legacy question-style tasks, and produces the single canonical representation used by every downstream stage.

Module: `geotask_core.v1.canonicalizer`  
Canonical types: `geotask_core.v1.ir`

### 3. Validate

The `CanonicalDocument` is validated against the v1.0 specification. Checks include:

- ID format and uniqueness
- Object type validity and geometry constraints
- Operator registration and arity matching
- Object reference resolution
- Execution mode support
- Output contract consistency
- Dependency cycle detection

Validation produces structured diagnostics. An empty diagnostic list means the document is fully valid.

Module: `geotask_core.v1.validator`

### 4. Execute

Valid assertions are dispatched through the `AssertionDispatcher` against the operator registry. Each assertion resolves its `object_refs` to concrete `GeoObject` instances, extracts geometry data by type, and calls the bound implementation function. The result is captured as a `CheckResult` with value, unit, status, and assurance metadata.

Pre-execution validation filters out assertions with structural errors (unknown operators, bad references, type mismatches) before dispatching. Condition and dependency ordering are enforced per the execution plan.

Module: `geotask_core.v1.executor`

### 5. Result

All `CheckResult` instances are aggregated into a `GeotaskResult`. Summary counts, overall status derivation, and assurance level synthesis are computed from the check collection. The result can be serialized to dict, YAML, or JSON for consumption by downstream systems.

Legacy output projections (`measurements`, `conclusion`, `verified_by`) are computed as `@property` on `GeotaskResult`, not stored separately.

Module: `geotask_core.v1.executor` (GeotaskResult dataclass)

## Module Map

Public modules in `src/geotask_core/`:

```
geotask_core/
├── ops.py                  # 6 deterministic operator implementations
├── parser.py               # YAML loading and structural validation
├── runner.py               # Public entry: run_geotask()
├── normalizer.py           # LLM output extraction and structuring
├── verifier.py             # Measurement verification with status hierarchy
├── evaluator.py            # Compare Core results with normalized LLM output
├── result_schema.py        # Status constants and overall_status computation
├── cli.py                  # CLI: validate, run, normalize, eval
├── models.py               # Legacy v0.x dataclasses (compat)
├── operator_registry.py    # Legacy v0.x operator registry (compat)
│
└── v1/
    ├── ir.py               # Canonical IR dataclasses (pure data, zero logic)
    ├── enums.py            # All v1.0 enums, error codes, ID validation
    ├── canonicalizer.py    # Raw dict to CanonicalDocument conversion
    ├── validator.py        # CanonicalDocument validation
    ├── operator_contracts.py  # Operator contracts, registry, dispatcher
    └── executor.py         # Execution engine and GeotaskResult
```

The `geotask_runtime/` directory contains private interfaces and mock implementations. These are published as reference contracts only. The mock pipeline, planner, and router are not part of Core.

## Dependency Direction

Dependencies flow from high-level orchestration down to pure data types. No cycles exist.

```
runner.py / cli.py
  => parser.py, canonicalizer, validator, executor

executor => validator, dispatcher, ir, enums
validator => ir, enums, operator_contracts (for operator lookup)
canonicalizer => ir, enums
dispatcher => ir, operator implementations (ops.py)

ir.py => nothing (leaf)
enums.py => nothing (leaf)
ops.py => nothing (leaf, stdlib math only)
```

The rule: `ir.py` and `enums.py` import nothing from Core. `ops.py` is a pure math module. Everything else depends inward toward these leaves.

## Operator Contract Structure

Each operator is defined by an `OperatorContract` dataclass in `v1/operator_contracts.py`:

| Field | Purpose |
|---|---|
| `name` | Unique operator identifier |
| `family` | Category: `measurement`, `topology`, `interval` |
| `arity` | Number of input objects |
| `input_types` | Ordered list of expected `GeoObject` types |
| `output` | Result type (`number`, `boolean`) and unit behavior |
| `deterministic` | Always `True` for Core operators |
| `semantics` | Formula description and boundary rules |
| `invariants` | Properties that must hold (e.g., `result >= 0`) |
| `error_codes` | Diagnostic codes this operator may surface |
| `implementation` | Module path to the bound function (e.g., `geotask_core.ops.distance_2d`) |

The `OperatorRegistry` loads all 6 built-in contracts at construction time. External packages can register additional contracts via `registry.register(contract)`.

## Assurance Level System

Every result carries an `AssuranceLevel`, an integer from 0 to 6:

| Level | Value | Meaning |
|---|---|---|
| `unverified` | 0 | No verification performed |
| `model_generated` | 1 | Produced by a model, unchecked |
| `model_self_checked` | 2 | Model checked its own output |
| `local_deterministic` | 3 | Verified by Core local operator |
| `model_local_agreement` | 4 | Model and Core agree |
| `independent_cross_verified` | 5 | Verified by an independent system |
| `human_reviewed` | 6 | Reviewed by a human |

Core always produces at least `local_deterministic` (3) for successful executions. Higher levels require the Runtime layer or external systems. Callers can set a `required_assurance` threshold and reject results below it.
