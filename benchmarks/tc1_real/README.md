# TC1-Real — public physical-world context measurement

This directory is a **repository-local experiment harness**, not part of the public `geotask-core` package API.

TC1-Real starts from the product question:

> Can GeoTask reduce or redirect context-preparation effort toward task-critical spatiotemporal information without increasing critical-context misses?

The first domain is fictional low-altitude mission **context preparation** using public source families. It does not grant flight authorization or claim flight-safety accuracy.

## Current source profiles

The first experiment deliberately includes providers with different acquisition shapes:

- **FAA UAS Facility Maps** — controlled-airspace planning context; a FeatureServer allows bounded spatial retrieval. FAA UASFM remains informational and is not authorization.
- **FAA Daily Digital Obstacle File** — obstacle context; the current profile is a broad ZIP/CSV download followed by local task-bounded selection. FAA's DDOF documentation also cautions that the file is not exhaustive and contains both verified and unverified records.
- **NOAA/NCEP HRRR** — weather context; NOMADS Grib Filter supports bounded region plus variable/level subsetting for HRRR GRIB2.

This distinction matters to the benchmark:

```text
UASFM  -> server-side spatial selection can reduce acquisition burden
HRRR   -> server-side region/variable/level selection can reduce acquisition burden
DDOF   -> broad acquisition cost remains; local selection can reduce downstream context burden
```

GeoTask must not report all three as the same kind of "context saving".

Each live experiment must capture the exact endpoint/request/time/hash actually used. `source_profiles.py` contains observed source metadata for experiment setup, not an eternal authority registry.

## First recorded real fixture

A one-time read-only acquisition run recorded the first bounded UASFM fixture under:

```text
benchmarks/tc1_real/fixtures/uasfm_phx_20260818/
  uasfm-phx.geojson
  uasfm-phx.record.json
  summary.json
```

Recorded evidence:

```text
bbox                  -112.1,33.4,-112.0,33.5
retrieval_timestamp   2026-08-18T10:33:14.973330Z
feature_count         124
payload_bytes         67529
request_count         1
monetary_cost         0.0  # explicitly supplied for this recorded request
wall_clock_seconds    0.3136501239999987
sha256                e9cf9402fb7c2fd583d04de5700e0bf7ac67bdda4a8d17a486105ea02470df05
```

The raw GeoJSON is stored byte-for-byte from the acquisition run and the offline test suite verifies its exact size/hash, source record binding, feature count, EPSG:4326 declaration, and the M1 non-empty-intersection activation condition.

The fixture contains source `CEILING` values, airport/airspace attributes, and geometry. Those are recorded source data only; neither the fixture nor its tests translate a ceiling value into real flight authorization.

## Real cost is multi-dimensional

`AcquisitionMeasurement` keeps these dimensions separate:

```text
monetary_cost
request_count
bytes_transferred
wall_clock_seconds
processing_cpu_seconds
storage_bytes
human_preparation_seconds
```

Unknown values remain `None`. Known zero and unknown are intentionally different.

The current Core `acquisition_cost: float` remains an abstract declared budget mechanism; TC1-Real does not treat it as a universal real-cost model.

## Read-only UASFM acquisition

The UASFM helper builds a bounded ArcGIS FeatureServer envelope query and records exact returned bytes plus measurement/provenance metadata:

```bash
python -m benchmarks.tc1_real.uasfm_acquisition \
  --bbox MIN_LON,MIN_LAT,MAX_LON,MAX_LAT \
  --output /tmp/uasfm.geojson \
  --record /tmp/uasfm.record.json
```

The command performs a read-only HTTPS GET. It does not access credentials, submit an FAA authorization request, or infer that the returned ceiling permits a real flight.

## DDOF broad acquisition and local selection

DDOF acquisition is measured separately from local selection. The selection command deliberately requires the actual CSV field names from the acquired file instead of guessing them from documentation or past versions.

Inspect a new CSV first:

```bash
python -m benchmarks.tc1_real.ddof_processing \
  --csv /tmp/DOF.CSV \
  --inspect-fields
```

Then select a task bbox using explicitly observed decimal-coordinate fields:

```bash
python -m benchmarks.tc1_real.ddof_processing \
  --csv /tmp/DOF.CSV \
  --bbox MIN_LON,MIN_LAT,MAX_LON,MAX_LAT \
  --lat-field ACTUAL_LAT_FIELD \
  --lon-field ACTUAL_LON_FIELD \
  --result /tmp/ddof.selection.json
```

A caller may also declare a verification field and accepted values for a named experiment. That is an explicit selection policy; GeoTask does not silently discard unverified source records.

## Bounded HRRR acquisition

The HRRR helper records exact model date, UTC cycle, forecast hour, region, variables, and levels. Example shape:

```bash
python -m benchmarks.tc1_real.hrrr_acquisition \
  --date YYYYMMDD \
  --cycle HH \
  --forecast-hour FF \
  --bbox MIN_LON,MIN_LAT,MAX_LON,MAX_LAT \
  --variable UGRD \
  --variable VGRD \
  --variable VIS \
  --level 10_m_above_ground \
  --level surface \
  --output /tmp/hrrr.grib2 \
  --record /tmp/hrrr.record.json
```

The helper validates that the returned bytes are GRIB2 before recording the fixture. It does not interpret the meteorological fields or infer mission feasibility.

## Frozen experiment cases

`experiment_cases.py` freezes M1–M4 before the GeoTask policy is evaluated:

- **M1 controlled-airspace context** — provider composition;
- **M2 local obstacle selection** — broad-provider acquisition versus bounded downstream context;
- **M3 weather temporal mismatch** — stale/wrong-time weather must remain a gap;
- **M4 unnecessary weather breadth** — compare task-specific region/variables/levels against broader retrieval.

The critical-context requirements are part of the experiment specification, not generated by the RG policy under test. Disputed requirements must be marked as such rather than silently included in headline CCMR.

## Network/CI boundary

Live network access is **not** part of normal CI. CI tests request construction, measurement semantics, source limitations, recorded fixture integrity, offline byte/provenance binding, DDOF local filtering, HRRR run/valid-time binding, and frozen experiment requirements.

Live acquisition is separated from deterministic replay:

```text
one-time/live acquisition
  -> exact public bytes + provenance + raw measurement
  -> bounded recorded fixture
  -> normal offline CI/replay
```

## Next slices

1. record one real DDOF broad acquisition and local-selection measurement;
2. record one exact HRRR run/valid-time subset;
3. normalize the recorded UASFM/DDOF/HRRR artifacts into ContextCandidates without collapsing the real cost vector into one scalar;
4. run R0 broad preparation, R1 fixed documented checklist/script, and RG GeoTask against the same frozen M1–M4 requirements;
5. record cases where GeoTask adds overhead without context-quality benefit.

Do not promote new Core semantics until the real experiment exposes a reusable need that current contracts cannot express.
