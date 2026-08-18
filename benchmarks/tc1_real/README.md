# TC1-Real — public physical-world context measurement

This directory is a **repository-local experiment harness**, not part of the public `geotask-core` package API.

TC1-Real starts from the product question:

> Can GeoTask reduce or redirect context-preparation effort toward task-critical spatiotemporal information without increasing critical-context misses?

The first domain is fictional low-altitude mission **context preparation** using public source families. It does not grant flight authorization or claim flight-safety accuracy.

## Current source profiles

- FAA UAS Facility Maps — controlled-airspace planning context; informational only, not authorization;
- FAA Daily Digital Obstacle File — aviation obstacle context;
- NOAA HRRR — time-varying weather context.

Each live experiment must capture the exact endpoint/request/time/hash actually used. `source_profiles.py` contains observed source metadata for experiment setup, not an eternal authority registry.

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

## First read-only acquisition helper

The UASFM helper builds a bounded ArcGIS FeatureServer envelope query and records exact returned bytes plus measurement/provenance metadata:

```bash
python -m benchmarks.tc1_real.uasfm_acquisition \
  --bbox MIN_LON,MIN_LAT,MAX_LON,MAX_LAT \
  --output /tmp/uasfm.geojson \
  --record /tmp/uasfm.record.json
```

The command performs a read-only HTTPS GET. It does not access credentials, submit an FAA authorization request, or infer that the returned ceiling permits a real flight.

Live network access is **not** part of CI. CI tests request construction, measurement semantics, and offline byte/provenance binding only.

## Next slices

1. record one bounded UASFM fixture with exact provenance;
2. add an FAA DDOF broad-download + local-filter measurement path;
3. add one exact HRRR run/valid-time weather fixture;
4. freeze mission variants M1–M4 and independent critical-context reference requirements;
5. compare R0 broad preparation, R1 fixed checklist/script, and RG GeoTask policy using raw cost dimensions rather than one synthetic score.

Do not promote new Core semantics until the real experiment exposes a reusable need that current contracts cannot express.
