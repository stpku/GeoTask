# TC1 Provider Truncation Proof v0.1

**Status:** REAL RECORDED EVIDENCE / OFFLINE REPLAY  
**Scenario:** Phoenix public-library service-coverage context preparation  
**Scope:** Benchmark method evidence only; no GeoTask Core change

## 1. Problem

A bounded provider response can look smaller than a broader response even when
neither response is complete. If a benchmark compares response bytes before
proving completeness, provider pagination/transfer limits can masquerade as
Task Context reduction.

The first Phoenix planning acquisition appeared attractive:

```text
ordinary growth broad   2,000 features   4,573,559 bytes
ordinary growth task    2,000 features   2,485,291 bytes
```

A naive byte comparison would report:

```text
task vs broad byte reduction ~= 45.66%
```

But both ordinary queries hit the same observed 2,000-record transfer ceiling.
The later IDs-first complete retrieval for the same broad joined representation
proved:

```text
complete broad features    118,190
unique planning units           471
pages                            119
network bytes            172,127,458
complete                       true
```

The ordinary broad response therefore returned only about 1.69% of the complete
feature cardinality and undercounted it by about 98.31%.

## 2. Method correction

The benchmark rule is frozen as:

```text
Completeness Before Reduction

scope
  -> provider object-ID set
  -> complete paged retrieval
  -> prove retrieved IDs == source IDs
  -> only then compare context burden
```

A smaller response is not admitted as evidence of better Task Context until the
candidate source response is proven complete for the measured scope.

## 3. Counterexample / anti-gaming condition

The replay intentionally keeps the attractive naive reduction visible while
rejecting it as a scoreable result.

```text
naive task-vs-broad byte reduction     ~45.66%
both ordinary queries hit 2,000 cap     yes
complete broad > ordinary broad         yes
headline reduction scoreable             no
verdict  REJECT_NAIVE_REDUCTION_PROVIDER_TRUNCATED
```

This prevents a pathological benchmark from becoming "better" merely because a
provider silently returned fewer records than actually existed.

## 4. Important separation

This proof establishes only the completeness prerequisite. It does not make the
joined layer 2 representation a valid benchmark baseline. A separate diagnostic
showed that layer 2 repeats planning-unit geometry across Pop/Emp records and is
therefore the wrong task representation. The formal planning benchmark uses base
planning-unit layer 4 plus population table 13 instead.

So the method order is:

```text
1. choose a task-appropriate representation
2. prove provider completeness
3. prove semantic/entity coverage
4. only then measure context reduction
```

## 5. What this changes

It does **not** add a new GeoTask Core object or algorithm.

It strengthens the benchmark discipline:

> **Reduction without completeness evidence is not a valid GeoTask result.**

The method is potentially reusable beyond GIS/ArcGIS providers, including RAG,
API pagination, database sampling, catalog search, and any system where a bounded
response can be mistaken for the full candidate set.

## 6. Files

```text
benchmarks/tc1_real/fixtures/planning_phx_20260818/provider-truncation-evidence.json
benchmarks/tc1_real/spatial_planning/provider_truncation_proof.py
tests/test_tc1_real_spatial_planning_provider_truncation.py
```
