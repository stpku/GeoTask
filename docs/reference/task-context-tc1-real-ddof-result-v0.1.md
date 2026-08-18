# GeoTask TC1-Real DDOF Result v0.1

**Status:** real broad-acquisition + task-bounded local-selection evidence recorded  
**Date:** 2026-08-18  
**Scope:** FAA Daily Digital Obstacle File, one pinned source snapshot, Phoenix experiment bbox  
**Decision boundary:** context-preparation evidence only; not complete obstacle coverage or flight-safety accuracy

## 1. Question

This slice tests a provider shape different from UASFM:

> When the source is available only as a broad file download, can GeoTask still reduce the amount of obstacle data carried into a bounded task context without falsely claiming that network acquisition cost was reduced?

DDOF is therefore split into two measured stages:

```text
broad source acquisition
  -> exact ZIP / CSV source pin
  -> local task-bbox selection
  -> downstream Task Context candidate
```

## 2. Recorded broad acquisition

The first stage acquired the current Daily DOF ZIP exactly once and recorded the response before any spatial filtering.

```text
source                 FAA Daily Digital Obstacle File
retrieval_timestamp    2026-08-18T10:48:07.252806Z
request_count          1
monetary_cost          unknown
ZIP bytes              20,518,681
ZIP SHA-256             5cb2d97cd07553f51ce09b88829ea397041fdcb2e9f4b1963079592eaf7bf57d
CSV member              DOF.CSV
CSV bytes               98,840,705
CSV rows                653,466
CSV SHA-256             a01c47f57202305a39faf0b3c6bd44bb30428c2397312b2085006c012aba6f16
observed wall time      0.12639463499999692 s
```

The monetary dimension is deliberately `unknown`, not zero.

A second acquisition used for the selection stage was allowed to continue only after ZIP SHA-256, CSV SHA-256, and member name matched this Stage-1 source pin exactly. This prevents a daily source refresh from being compared as if it were the same dataset.

## 3. Observed source header

The benchmark did not guess DDOF column aliases before acquisition. Stage 1 inspected the actual pinned CSV header and recorded:

```text
OAS
VERIFIED STATUS
COUNTRY
STATE
CITY
LATDEC
LONDEC
DMSLAT
DMSLON
TYPE
QUANTITY
AGL
AMSL
LIGHTING
ACCURACY
MARKING
FAA STUDY
ACTION
JDATE
```

Stage 2 therefore used the exact observed `LATDEC`, `LONDEC`, and `VERIFIED STATUS` fields.

## 4. Task-bounded local selection

Task bbox:

```text
[-112.1, 33.4, -112.0, 33.5]
```

The selection policy applied only the declared spatial bbox. It did **not** filter source rows by verification status.

Recorded result:

```text
input CSV rows                 653,466
selected rows                  313
row reduction ratio            0.9995210156304996  (~99.9521%)

input CSV bytes                98,840,705
selected serialized bytes      47,401
byte reduction ratio           0.9995204303732961  (~99.9520%)

local processing wall time     3.9159282620000013 s
source CSV SHA-256             a01c47f57202305a39faf0b3c6bd44bb30428c2397312b2085006c012aba6f16
```

The selected rows preserved both source verification states:

```text
verified O       139
unverified U     174
```

GeoTask did not silently reinterpret `U` as false, discard it, or promote `O` to a complete obstacle truth set. Verification handling remains an explicit downstream rule/context requirement.

## 5. What this supports

This recorded result supports a provider-specific statement:

> **For the pinned DDOF snapshot, task-bounded local spatial selection reduced the obstacle records carried downstream from 653,466 rows to 313 rows, and a deterministic CSV serialization from 98.84 MB to 47.4 KB, while preserving both verified and unverified source records.**

This is strong evidence for **downstream context reduction** on a broad-download provider.

It also demonstrates that GeoTask's value cannot be expressed by one universal “data saving” metric:

```text
UASFM
  -> server-side task bounding reduced acquired bytes/features

DDOF
  -> broad network acquisition stayed broad
  -> task bounding reduced local/downstream context instead
```

## 6. What this does not support

This result does not establish that:

- DDOF network download was reduced by 99.95%; it was not;
- the 313 rows are a complete list of obstacles relevant to a real flight;
- DDOF itself is exhaustive;
- unverified rows are invalid or verified rows are sufficient;
- the selected bbox is minimum sufficient;
- local spatial filtering improves a real mission decision;
- 3.92 seconds is a general processing-performance result;
- 99.95% is a general GeoTask reduction rate across providers or missions.

The source's own scope/verification limitations remain part of the context evidence.

## 7. Reproducibility

Only compact evidence is stored in the product branch:

```text
benchmarks/tc1_real/fixtures/ddof_phx_20260818/
  acquisition.record.json
  header.json
  summary.json
  source-pin.json
  selection.json
  selection-summary.json
```

The 20.5 MB ZIP and 98.8 MB CSV are not committed to the normal repository. Their exact SHA-256 pins, sizes, header and selection evidence are retained; the raw acquisition was also uploaded as a short-lived one-time workflow artifact.

Offline tests verify:

- acquisition/source pins and sizes;
- exact observed header fields;
- selection bound to the exact pinned CSV;
- recorded row/byte reduction ratios;
- all selected coordinates lie in the declared bbox;
- both `O` and `U` source rows remain present.

## 8. Gate effect

TC1-Real status after DDOF:

```text
UASFM acquisition-breadth comparison       PASS (provider-specific)
DDOF broad acquisition                     RECORDED
DDOF task-bounded local selection           RECORDED
DDOF downstream-context comparison          PASS (provider-specific)
HRRR real subset acquisition                PENDING
R1 fixed documented workflow                PENDING
complete M1–M4 R0/R1/RG comparison          PENDING
real-world decision/outcome regret          NOT ESTABLISHED
```

The next physical evidence step is HRRR: record exact run/valid-time task-bounded weather context and compare it with a documented broader retrieval, while preserving the same separation between acquisition burden, context breadth, and downstream decision quality.
