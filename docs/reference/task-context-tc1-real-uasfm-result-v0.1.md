# GeoTask TC1-Real UASFM Result v0.1

**Status:** first real-source acquisition comparison recorded  
**Date:** 2026-08-18  
**Scope:** one FAA UAS Facility Map provider, one task bbox, one broader regional R0 bbox  
**Decision boundary:** context-preparation evidence only; not flight authorization or flight-safety accuracy

## 1. Question

This slice tests one narrow part of the GeoTask hypothesis:

> When a public provider supports bounded spatial queries, can a task-bounded request reduce the amount of source context acquired relative to an explicitly broader regional request while preserving the same source family, format, and requested fields?

It does **not** test whether the resulting context is sufficient for a real flight decision. It tests acquisition breadth for one declared context source.

## 2. Recorded requests

Both acquisitions used the same UASFM FeatureServer source, GeoJSON format, and exact `out_fields` list.

### RG/task-bounded acquisition

```text
bbox                  -112.1,33.4,-112.0,33.5
retrieval_timestamp   2026-08-18T10:33:14.973330Z
feature_count         124
payload_bytes         67529
request_count         1
monetary_cost         0.0
wall_clock_seconds    0.3136501239999987
sha256                e9cf9402fb7c2fd583d04de5700e0bf7ac67bdda4a8d17a486105ea02470df05
```

### R0/broad regional acquisition

```text
bbox                  -112.2,33.3,-111.9,33.6
retrieval_timestamp   2026-08-18T10:37:47.602765Z
feature_count         516
payload_bytes         280585
request_count         1
monetary_cost         0.0
wall_clock_seconds    0.7391411730000073
sha256                fe9ef445eb75444c2b90848fb5fb6b88d217638411ba5e57c0e0c70dcf013e95
```

The R0 bbox contains the task bbox. The offline comparison refuses to calculate reductions if source identity, CRS, format, requested fields, or bbox containment do not match the comparison contract.

## 3. Measured burden difference

For this recorded pair:

```text
feature reduction ratio    0.7596899224806202   (~75.97%)
payload byte reduction     0.7593278329205053   (~75.93%)
observed wall-time change  0.5756559971798573   (~57.57% lower in this pair)
```

The feature and payload reductions are exact deterministic comparisons of the two stored responses.

The wall-clock value is **not** a stable latency benchmark: each request was recorded only once and network/server conditions were uncontrolled. It is preserved as an observed measurement but must not be promoted to a repeatable performance claim until replicated.

## 4. What this supports

This result supports only the following provider-specific statement:

> For the recorded UASFM provider and these two explicitly comparable requests, narrowing spatial acquisition from the documented R0 regional bbox to the task bbox reduced returned features and bytes by about 76%.

This is the first real-source evidence that a task-bounded context request can reduce **acquisition breadth** when the provider exposes server-side spatial selection.

## 5. What this does not support

This result does not establish that:

- 76% is a general GeoTask saving rate;
- the broad regional R0 represents expert or production practice;
- the task bbox is the minimum sufficient bbox;
- all UASFM context relevant to a real mission is present;
- UASFM data authorizes a flight;
- a smaller response improves downstream decision accuracy;
- DDOF or HRRR will show the same kind of cost reduction;
- GeoTask has yet solved automatic Relevance, Sufficiency, or decision-sensitive Resolution.

The result is deliberately provider-specific. DDOF is expected to expose a different cost structure because the current source profile is broad acquisition plus local selection rather than server-side bbox acquisition.

## 6. Reproducibility

Stored fixtures:

```text
benchmarks/tc1_real/fixtures/uasfm_phx_20260818/
benchmarks/tc1_real/fixtures/uasfm_phx_r0_regional_20260818/
```

Each directory preserves raw source bytes, acquisition/provenance record, and summary. Tests verify exact SHA-256/byte counts for the task fixture and validate the comparison contract and recorded reduction ratios.

The one-time live acquisition workflow is intentionally kept on temporary acquisition branches rather than added to normal CI. Normal CI replays the stored evidence offline.

## 7. Gate effect

TC1-Real status after this slice:

```text
measurement/provenance harness           READY
UASFM task-bounded real fixture           RECORDED
UASFM R0 broad real fixture               RECORDED
UASFM acquisition-breadth comparison      PASS (provider-specific)
DDOF real acquisition/selection           PENDING
HRRR real subset acquisition              PENDING
R1 fixed documented workflow              PENDING
M1–M4 complete R0/R1/RG comparison        PENDING
real-world decision/outcome regret        NOT ESTABLISHED
```

This evidence is sufficient to continue TC1-Real. It is not sufficient to promote the project publicly as a completed automatic Task Context Engine or to enter TC2 automatic context construction as a product claim.
