# Recorded DDOF TC1-Real evidence — Phoenix bbox, 2026-08-18

This directory contains **compact evidence only** for one real FAA Daily Digital Obstacle File acquisition and one task-bounded local selection.

The original broad source files are intentionally not committed here:

```text
DAILY_DOF_CSV.ZIP   20,518,681 bytes
DOF.CSV             98,840,705 bytes / 653,466 rows
```

Their exact hashes and acquisition measurement are pinned by `acquisition.record.json`, `summary.json`, and `source-pin.json`.

Observed source pin:

```text
ZIP SHA-256  5cb2d97cd07553f51ce09b88829ea397041fdcb2e9f4b1963079592eaf7bf57d
CSV SHA-256  a01c47f57202305a39faf0b3c6bd44bb30428c2397312b2085006c012aba6f16
CSV member   DOF.CSV
```

The actual CSV header was observed before selection. Spatial selection therefore uses explicit `LATDEC` / `LONDEC`; source verification state is preserved from `VERIFIED STATUS`.

Task bbox:

```text
[-112.1, 33.4, -112.0, 33.5]
```

Recorded local-selection result:

```text
input rows                  653,466
selected rows               313
row reduction               ~99.9521%
input CSV bytes             98,840,705
selected serialized bytes   47,401
byte reduction              ~99.9520%
verified O                  139
unverified U                174
```

Interpretation boundary:

> This is **downstream context reduction**, not network acquisition reduction. The broad DDOF ZIP was still downloaded in full.

The selection also does not establish complete obstacle coverage or flight safety. Both verified and unverified source records are intentionally retained; their use remains an explicit downstream rule/context decision.
