# TC1-Real M3 HRRR wrong-valid-time fixture

This directory contains one read-only NOAA/NCEP HRRR subset recorded for the M3 temporal-applicability counterexample.

The fixture intentionally holds the non-temporal request dimensions equal to the accepted M1 task HRRR fixture:

```text
source        NOAA/NCEP HRRR
model date    20260818
run cycle     06Z
bbox          -112.1,33.4,-112.0,33.5
variables     UGRD, VGRD, VIS
levels        10_m_above_ground, surface
```

The temporal difference is:

```text
M1 control    forecast hour 4 -> valid 2026-08-18T10:00:00Z
M3 mismatch   forecast hour 2 -> valid 2026-08-18T08:00:00Z
```

Recorded M3 mismatch evidence:

```text
payload bytes 596
sha256         f1da0c670a6998f945d06d7de6e55e1a292b1e3b33f042f1707b479b674591c2
```

The benchmark task window is `[2026-08-18T10:00:00Z, 2026-08-18T11:00:00Z)`. The fixture is therefore real provider evidence that is deliberately outside the benchmark task time window.

This fixture does not claim flight feasibility, safety, or authorization. Its purpose is only to test whether time-mismatched context remains a gap instead of being accepted merely because weather data exists.
