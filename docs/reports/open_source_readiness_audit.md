# GeoTask Open Source Readiness Audit

**Date**: 2026-07-20
**Status**: Pre-refactoring assessment

---

## 1. Current Module Tree

```
src/
├── geotask_core/              ← Open source Core
│   ├── __init__.py            (69 lines)
│   ├── models.py              (36 lines) - legacy dataclasses
│   ├── parser.py              (671 lines) - legacy + v1 validation mixing
│   ├── ops.py                 (132 lines) - operator implementations
│   ├── runner.py              (256 lines) - legacy + v1 execution mixing
│   ├── cli.py                 (406 lines) - CLI
│   ├── operator_registry.py   (131 lines) - v0.x registry (old)
│   ├── normalizer.py          (270 lines) - LLM output normalizer
│   ├── verifier.py            (168 lines) - v0.3 verifier
│   ├── evaluator.py           (167 lines) - legacy evaluator
│   ├── result_schema.py       (100 lines) - v0.3 status constants
│   │
│   └── v1/                    ← v1.0 core (new)
│       ├── __init__.py        (35 lines)
│       ├── ir.py              (160 lines) - Canonical IR ★
│       ├── enums.py           (159 lines) - Enums ★
│       ├── canonicalizer.py   (718 lines) - Legacy→v1 conversion ⚠
│       ├── validator.py       (1093 lines) - Validation ⚠⚠
│       ├── operator_contracts.py (548 lines) - Operators ⚠
│       └── executor.py        (1242 lines) - Execution ⚠⚠⚠
│
├── geotask_runtime/           ← Private/commercial Runtime
│   ├── contracts.py           (106 lines)
│   ├── planner.py             (87 lines) - mock
│   ├── router.py              (81 lines) - mock
│   ├── mock_runtime.py        (210 lines) - mock
│   ├── domain_pack.py         (122 lines) - demo
│   └── result_governance.py   (118 lines) - mock
│
└── geotask_domain_packs/      ← Private domain packs
    └── lowalt_site_precheck/
        ├── models.py          (69 lines)
        ├── rules.py           (142 lines)
        ├── mock_data.py       (77 lines)
        ├── pack.py            (113 lines)
        └── report.py          (18 lines)
```

**Key**: ★ = canonical, ⚠ = borderline size, ⚠⚠ = needs split, ⚠⚠⚠ = urgent split

---

## 2. Core Execution Main Chain

```
load/parse → canonicalize → validate → dispatch → GeotaskResult
```

**Current problems in main chain:**

| Step | Current State | Issue |
|------|--------------|-------|
| load/parse | `parser.py` 671 lines | Mixes legacy v0.x + v1 detection, raw validation, duplicate key detection |
| canonicalize | `canonicalizer.py` 718 lines | Mixes legacy conversion, v1 parsing, auto-assertion generation, execution step generation |
| validate | `validator.py` 1093 lines | Single giant file with all 12 check categories + raw validation split across parser.py |
| dispatch | `executor.py` 1242 lines | Contains: dispatch, condition, on_error, depends_on, output_contract, assurance aggregation, status derivation, result serialization, legacy projection — everything in one file |
| Result | `executor.py` + properties | `GeotaskResult.to_dict()` + legacy `@property` projections in same class — legitimate but in wrong module |

---

## 3. v0 vs v1 Relationship

```
v0.x layer:
  parser.py (validate_geotask_diagnostics) ← still used as raw validation
  runner.py (_run_legacy)                   ← still main execution path for legacy docs
  operator_registry.py                      ← v0.x registry (superseded by v1 OperatorRegistry)
  models.py                                 ← v0.x dataclasses (StirDocument etc.)
  result_schema.py                          ← v0.3 status constants

v1.x layer:
  v1/ir.py, enums.py                        ← Canonical types
  v1/canonicalizer.py                       ← Bridges v0→v1
  v1/validator.py                           ← Canonical validation
  v1/operator_contracts.py                  ← v1 OperatorRegistry + Dispatcher
  v1/executor.py                            ← Execution engine

Mixed:
  cli.py                                    ← Uses both legacy + v1
  runner.py (_run_v1)                       ← Bridges v1 to legacy output
  parser.py (validate_document)             ← Unified entry
```

**Critical finding**: v0 and v1 logic is NOT cleanly separated. `runner.py` has both `_run_legacy` and `_run_v1` as top-level branches. `parser.py` has both v0 and v1 raw validation in the same function. `cli.py` must handle both output formats.

---

## 4. Dependency Direction

### ✅ Correct directions:
- `v1/ir.py` → nothing (leaf)
- `v1/enums.py` → nothing (leaf)
- `v1/validator.py` → `v1/ir.py`, `v1/enums.py`, `v1/operator_contracts.py` ✓
- `v1/operator_contracts.py` → `v1/ir.py`, `geotask_core.ops` ✓

### ⚠ Problematic directions:
- `v1/executor.py` → `v1/validator.py` (at runtime, via `execute_canonical`) — executor calling validator is fine architecturally
- `runner.py` → `v1/canonicalizer.py`, `v1/validator.py`, `v1/executor.py`, `parser.py` — runner depends on everything
- `parser.py` → `v1/canonicalizer.py`, `v1/validator.py` (in `validate_document`) — parser depending on v1 is a layering violation
- `cli.py` → everything — unavoidable for CLI, but should be thin

---

## 5. Files >500 Lines

### Must-split (>>500):
| File | Lines | Must-do? |
|------|-------|----------|
| `v1/executor.py` | 1242 | **MUST split** into executor + policy + assurance + output_contract + result |
| `v1/validator.py` | 1093 | **MUST split** or accept as single validation module |
| `v1/canonicalizer.py` | 718 | Borderline — consider splitting legacy_input into compat/ |
| `parser.py` | 671 | Should split raw v0 validation from unified entry |
| `v1/operator_contracts.py` | 548 | Borderline — could split dispatcher from contracts |
| `cli.py` | 406 | Acceptable for CLI |

---

## 6. Function Count Per Module (est.)

| Module | Approx functions | Rating |
|--------|-----------------|--------|
| executor.py | ~35 | ⚠⚠⚠ Way too many |
| validator.py | ~25 | ⚠⚠ |
| canonicalizer.py | ~15 | ⚠ |
| parser.py | ~15 | ⚠ |
| cli.py | ~20 | Acceptable (CLI) |

---

## 7. Circular Dependencies

No true circular imports found, but:

- `v1/executor.py` imports `v1/validator.py` at runtime inside `execute_canonical()` — lazy import to avoid cycle
- `runner.py` has function-internal imports for `canonicalize`, `validate_canonical`, `execute_canonical` — lazy import pattern

These are symptoms of poor layering, not actual cycles.

---

## 8. Enum vs Raw String Mixing

**Confirmation**: Code mixes:
- `ExecutionStatus.failed.value` ("failed") + raw `"failed"` strings
- `AssuranceLevel.unverified.name` ("unverified") + raw `"unverified"` strings
- `ClaimStatus.verified.value` ("verified") + raw `"verified"` strings

Found in: `executor.py`, `runner.py`, `result_schema.py`

**Must fix**: Use Enum members internally, convert only at `to_dict()`, CLI output, and compat boundaries.

---

## 9. Legacy Logic Distribution

| Location | Legacy Content | Severity |
|----------|---------------|----------|
| `runner.py` `_run_legacy()` | Full v0.x auto-detection runner | Must isolate |
| `runner.py` `_v1_result_to_legacy()` | v1→v0 result conversion | Should move to compat |
| `parser.py` v0 field checks | `geotask.version/goal`, old object types | Should move to compat |
| `models.py` `StirDocument`, `PointObject` | v0.x dataclasses | Can keep (used by tests) |
| `operator_registry.py` | v0.x operator registry | Can keep (used by CLI inspect) |
| `result_schema.py` | v0.3 status constants | Can keep (used by normalizer/verifier) |
| `evaluator.py` | v0.1 evaluator | Can keep |
| `normalizer.py`, `verifier.py` | v0.3 normalizer/verifier | Can keep |

---

## 10. Skeleton / Experimental Interfaces

| Location | What | Verdict |
|----------|------|---------|
| `geotask_runtime/contracts.py` | TaskRequest, EncodingPlan, GovernedTaskResult | Keep as interface definition |
| `geotask_runtime/planner.py` | RuleBasedEncodingPlanner (mock) | **Move to experimental** |
| `geotask_runtime/router.py` | MockModelRouter | **Move to experimental** |
| `geotask_runtime/mock_runtime.py` | End-to-end mock pipeline | **Move to experimental** |
| `geotask_runtime/domain_pack.py` | GenericSpatialDomainPack (demo) | **Move to experimental** |
| `geotask_runtime/result_governance.py` | DeterministicResultGovernor (mock) | **Move to experimental** |
| `geotask_domain_packs/lowalt_site_precheck/` | Domain pack example | Keep but exclude from public |
| `v1/executor.py` model_only path | Skeleton execution | Keep as skeleton (returns proposed) |

---

## 11. AI Coding Traces

| Category | Count | Severity |
|----------|-------|----------|
| Visual separator lines (`# ═══`) | ~50+ across v1 files | Medium |
| Redundant docstrings (paraphrase code) | ~20+ | Low |
| Function-internal imports | ~5 across runner.py, parser.py, executor.py | Should fix |
| "pragma: no cover" comments | ~3 | Acceptable |
| "defence in depth" comments | 2 | Remove |
| "Hardened flow" / "Hardening Gate" comments | ~5 | Remove |

---

## 12. Duplicate Validation Logic

- Raw schema validation: `parser.py` (v0) + `validator.py` (v1 canonical) — some overlap on object types
- Object type validation: parser.py + validator.py both check object types
- Operator validation: parser.py + validator.py both check operator registration
- Reference validation: parser.py + validator.py both check object references

**Must fix**: Raw validation should only check structure. Canonical validation should check semantics. Remove overlap.

---

## 13. Duplicate Result Conversion

- `executor.py`: `GeotaskResult` has `@property measurements`, `@property conclusion`, `@property verified_by`
- `runner.py`: `_v1_result_to_legacy()` duplicates the above logic
- `executor.py`: `_build_legacy()` still exists as function (called in _finalize but no-op since properties)

**Must fix**: Single source of truth for legacy projection.

---

## 14. Oversized Test Files

| File | Lines | Action |
|------|-------|--------|
| `test_v1_hardening.py` | 1356 | **MUST split** into v1/ subdirectory |
| `test_v1_foundation.py` | 707 | **SHOULD split** into v1/ subdirectory |

---

## 15. File Classification for Public Export

### Public Core (include):
```
src/geotask_core/__init__.py
src/geotask_core/models.py
src/geotask_core/ops.py
src/geotask_core/parser.py
src/geotask_core/runner.py
src/geotask_core/cli.py
src/geotask_core/normalizer.py
src/geotask_core/verifier.py
src/geotask_core/evaluator.py
src/geotask_core/result_schema.py
src/geotask_core/operator_registry.py
src/geotask_core/v1/*.py
src/geotask_core/compat/*.py (new)
```

### Careful public (needs review):
```
src/geotask_runtime/contracts.py     ← Interface only, keep
```

### Internal only (exclude):
```
src/geotask_runtime/planner.py       ← mock
src/geotask_runtime/router.py        ← mock
src/geotask_runtime/mock_runtime.py  ← mock
src/geotask_runtime/domain_pack.py   ← demo
src/geotask_runtime/result_governance.py ← mock
src/geotask_domain_packs/**          ← private domain packs
```

### Public documents:
```
README.md (rewrite needed)
LICENSE
CHANGELOG.md
docs/specification.md (new, from format_spec + v1 spec)
docs/architecture.md (new)
docs/operator-guide.md (new)
docs/cli.md (from cli_usage.md)
docs/contributing.md (new)
SECURITY.md (new)
CONTRIBUTING.md (new)
```

### Forbidden for public:
```
patent_evidence/**
docs/reports/**
docs/superpowers/**
.ai-bridge/**
.omx/**
benchmarks/**
scripts/**
docs/GeoTask Specification v1.0.md (internal draft)
```

---

## Audit Conclusions

### 必须整改 (MUST fix before public):
1. ✅ Split `executor.py` (1242 lines) — too many responsibilities
2. ✅ Isolate legacy compat into dedicated module
3. ✅ Unify Enum usage internally
4. ✅ Remove AI coding style artifacts
5. ✅ Add architecture boundary tests
6. ✅ Fix `validate_document` to live outside parser.py

### 建议整改 (SHOULD fix):
7. Split `validator.py` (1093 lines) — acceptable as single validation module
8. Cut `canonicalizer.py` legacy conversion into compat/
9. Split oversized test files
10. Clean up duplicate validation between parser and validator

### 允许保留 (OK to keep):
11. `operator_registry.py` as v0.x compat
12. `models.py` legacy dataclasses
13. `result_schema.py` v0.3 constants
14. `normalizer.py`, `verifier.py`, `evaluator.py` as mature v0.3 modules

### 内部专用 (Internal only):
15. `geotask_runtime/` — mock implementations
16. `geotask_domain_packs/` — private domain packs
17. `patent_evidence/` — patent documentation
18. `benchmarks/` — internal benchmarks
19. `.ai-bridge/`, `.omx/` — agent scaffolding

### 公开禁止 (Never public):
20. API keys, tokens, passwords
21. Internal paths, customer names
22. Commercial routing logic
23. Unpublished patent details
