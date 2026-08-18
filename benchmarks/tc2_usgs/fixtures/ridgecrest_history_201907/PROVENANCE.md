# TC2 recorded USGS historical fixture

This directory contains a one-time read-only USGS FDSN Event Web Service GeoJSON response recorded for the TC2 cross-domain applicability promotion gate.

Recorded query contract:

```text
starttime     2019-07-04T00:00:00Z
endtime       2019-07-08T00:00:00Z
minlatitude   33.0
maxlatitude   37.0
minlongitude  -120.0
maxlongitude  -115.0
minmagnitude  4.5
format        geojson
orderby       time-asc
```

The exact raw provider bytes and acquisition summary are replayed offline in normal tests. Live USGS access is not required by CI.

The benchmark uses earthquake events only as context candidates. An event does not imply infrastructure damage, inspection priority, safety status, or authorization to act.
