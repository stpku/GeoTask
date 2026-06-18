# GeoTask Encoding Benchmark v0.2 — Normalizer Boundary

> **Evidence boundary document.** Not a functional specification.
> 本文档是证据边界说明，不是功能规格。

---

## 1. Purpose

This document defines the **evidence boundary** between:

- **v0.1.1**: End-to-end GeoTask Core Normalizer + Verifier loop (4 cases, 2 operators);
- **v0.2**: Multi-case, multi-operator encoding robustness evidence (24 cases, 6 operators).

Its purpose is to **prevent misunderstandings** in patent prosecution or attorney review where v0.2's 100% status match might be incorrectly interpreted as proof that the production GeoTask Core Normalizer fully supports all six operators.

---

## 2. Why v0.2 Uses a Benchmark Local Verifier

### 2.1 Design rationale

v0.2 was designed to rapidly expand case coverage and operator variety:

- 24 cases across 5 case groups;
- 6 operators (distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap);
- 8 error/robustness types (wrong values, missing operators, invalid references, unit mismatch, Chinese negation, Markdown extraction, YAML extraction, missing object references).

Expanding the GeoTask Core Normalizer to handle all new operators, object types, and output formats simultaneously would have introduced **premature complexity** and risked breaking existing v0.1.1 evidence stability.

### 2.2 Solution: benchmark-local verifier

Instead, v0.2 introduced `benchmarks/encoding_v0_2/local_verifier.py` — a **benchmark-layer** verifier that:

1. Reads case definitions from `cases.yaml`;
2. Compares simulated model outputs against expected values;
3. Handles operator-specific value extraction (distance, boolean, time, altitude);
4. Classifies outcomes as `verified`, `contradicted`, or `need_review`;
5. Generates review reasons consistent with v0.1.1 pattern.

The local verifier is:

- **Scoped to the benchmark layer only** — it does not modify `src/geotask_core/`;
- **Deterministic and reproducible** — no external APIs;
- **Not production-grade** — it lacks the robustness, edge-case handling, and generalizability of GeoTask Core Normalizer.

### 2.3 What this means for evidence

```
v0.2 的 100% verification success
⇓ 并不表示
GeoTask Core Normalizer 已完整支持所有新增算子
```

**Correct interpretation:**

> v0.2 demonstrates that task-related spatial encodings preserve object references, operator references, propositions, expected outputs, and verification requirements across a broader set of spatial task types — enabling a benchmark-local verifier to perform structured validation.

**Incorrect interpretation:**

> v0.2 proves that the GeoTask Core Normalizer can extract, normalize, and verify all six spatial operators from arbitrary natural language outputs.

---

## 3. Relationship Between v0.1.1 and v0.2 Evidence

| Version | Evidence Focus | Operators | Verification Path | Evidence Boundary |
|---------|---------------|-----------|-------------------|-------------------|
| **v0.1.1** | End-to-end GeoTask Normalizer + Verifier loop | 2 | Core normalizer + core verifier | Small case set, stronger end-to-end chain |
| **v0.2** | Multi-case / multi-operator encoding robustness | 6 | Benchmark local verifier | Larger coverage, not full core normalizer claim |

### 3.1 How they complement each other

| Evidence Need | Use This Version | Why |
|--------------|-----------------|-----|
| Proving end-to-end normalization + verification | **v0.1.1** | Normalizer + verifier are production GeoTask Core code |
| Proving encoding extensibility to more operators | **v0.2** | 6 operators, 24 cases demonstrate structural extensibility |
| Proving encoding handles diverse error types | **v0.2** | 8 error types vs 1 in v0.1.1 |
| Proving token efficiency at scale | **v0.2** | 24 cases provide more robust token cost comparison |
| Proving production normalizer supports all ops | **Neither alone** | Wait for v0.3 core normalizer expansion |

---

## 4. What v0.2 Proves

### 4.1 Engineering claims supported by v0.2

**Primary claim:**

> Task-related spatial encodings can preserve object references, operator references, propositions, expected outputs, and verification requirements across a broader set of spatial task types.

**中文：**

> 任务相关空间编码能够在更广泛的空间任务类型中保留对象引用、算子引用、空间命题、期望输出和验证需求。

### 4.2 Supporting findings

| Finding | Quantitative Support |
|---------|---------------------|
| Compact DSL token efficiency | 35% fewer tokens than NL, 60% fewer than YAML |
| Structured encoding verification reliability | YAML and DSL: 100% status match |
| Natural language robustness boundary | NL: 95.8% status match (Chinese negation, Markdown limitations) |
| Multi-operator structural extensibility | 6 operators all expressible in all 3 encodings |
| Error type coverage | 8 error types detected with 96%+ accuracy |

---

## 5. What v0.2 Does NOT Prove

| Does NOT Prove | Explanation |
|----------------|-------------|
| Real LLM accuracy | All outputs are deterministic simulations |
| Production GeoTask Core Normalizer supports all 6 operators | v0.2 uses benchmark local verifier, not core normalizer |
| Local verifier equals production verifier | Local verifier lacks generalizability and edge-case handling |
| Compact DSL is optimal for all models and tasks | Token estimates are approximate; task context varies |
| Statistical significance | 24 cases is descriptive, not inferential |
| Live LLM API benchmark | v0.2 explicitly avoids external API calls |
| Formal attorney examination response | Evidence is reference material, not legal argument |

---

## 6. Recommended Wording for Attorney Communication

### 6.1 English

> Benchmark v0.2 extends the evidence from 4 cases and 2 operators to 24 cases and 6 operators. It uses a benchmark-local verifier to evaluate whether task-related encodings preserve the object references, operator references, propositions, and expected outputs required for deterministic verification. It should be interpreted as **multi-scenario structural evidence**, not as a claim that the production GeoTask Core Normalizer fully supports all new operators.

### 6.2 Chinese

> Benchmark v0.2 将证据从 4 个样例、2 类算子扩展到 24 个样例、6 类算子，并使用 benchmark 本地验证器评估任务相关编码是否保留确定性验证所需的对象引用、算子引用、空间命题和期望输出。该证据应理解为**多场景结构化证据**，而不应理解为生产级 GeoTask Core Normalizer 已完整支持全部新增算子。

### 6.3 When an examiner asks about verification capability

> "The v0.1.1 evidence demonstrates the end-to-end normalization-verification loop for the two core operators (distance_2d, line_intersects_rect). The v0.2 evidence demonstrates that the encoding structure itself is extensible to additional spatial operators, error types, and encoding formats, supporting the engineering claim that the encoding structure is generalizable. Full production normalizer support for all six operators is planned for v0.3."

---

## 7. Implication for GeoTask Core v0.3

The v0.2 benchmark evidence informs a clear path to v0.3:

| v0.2 Finding | v0.3 Action |
|-------------|-------------|
| point_to_line_distance_2d, rect_contains_point work in local verifier | **Port** these operators to core normalizer extraction patterns |
| time_overlap, altitude_overlap work in local verifier | **Add** time/altitude parsing to core normalizer |
| 8 error types detected | **Unify** error handling in core verifier (numeric, bool, invalid-op, invalid-ref, missing-value, unit-mismatch) |
| Markdown and YAML extraction works | **Generalize** normalizer to handle mixed-format outputs |
| Chinese negation detection works | **Integrate** Chinese NLP patterns into normalizer language support |
| 24 cases validate encoding structure | **Expand** core test suite with v0.2 cases using production normalizer |

### v0.3 Goal

```
v0.3 = v0.1.1 end-to-end core loop + v0.2 operator/error coverage → unified production evidence
```

---

## 8. Reproducibility Commands

```bash
# Reproduce v0.2 benchmark
python benchmarks/encoding_v0_2/run_benchmark.py

# View benchmark results
cat benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_summary.md

# Run all tests (322 tests)
pytest

# Run v0.2-specific tests
pytest tests/test_encoding_benchmark_v0_2.py -v
pytest tests/test_benchmark_v0_2_evidence_addendum.py -v
```

---

*Evidence artifact: `patent_evidence/07_benchmark_v0_2/v0_2_normalizer_boundary.md`*
*Version: v0.2 addendum | Date: 2026-06-18*
*Related: `patent_evidence/07_benchmark_v0_2/v0_2_attorney_addendum.md`*
