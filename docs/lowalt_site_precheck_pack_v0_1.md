# LowAlt Site Precheck Pack v0.1 — MOCK MVP

## Purpose

The LowAlt Site Precheck Pack is a **mock domain pack** that demonstrates how GeoTask Core operators can be composed into industry-specific precheck workflows for low-altitude flight operations.

This is a **Mock MVP (v0.1)** using fictional `local_xy_m` coordinates. It does NOT access real airspace, maps, obstacles, airports, weather, regulatory, or customer data. It does NOT provide flight authorization or regulatory approval.

## Scope

- Demonstrate domain pack architecture using GeoTask Core operators
- Provide deterministic mock checks for candidate site evaluation
- Show how verification results, risk items, and data gaps are structured
- Serve as a reference implementation for future production domain packs

## Explicit Non-Goals

- **NOT a flight system.** This pack does not control, authorize, or manage any flight operations.
- **NOT regulatory.** This pack does not implement or enforce any real aviation regulations (CAAC, FAA, EASA, or otherwise).
- **NOT real data.** All coordinates are fictional `local_xy_m`. No real airport names, locations, or airspace data.
- **NOT production-ready.** This is a mock MVP for architecture validation and patent evidence only.

## Mock Spatial Object Model

All objects use simple Python `dataclass` types with fictional coordinates:

| Object | Fields | Description |
|--------|--------|-------------|
| `CandidateSite` | `site_id`, `name`, `xy`, `site_type` | Candidate takeoff/landing site |
| `InitialRoute` | `route_id`, `points` | Route as list of [x,y] waypoints |
| `SensitiveSite` | `site_id`, `category`, `xy`, `risk_radius_m` | Sensitive area with safe distance |
| `RestrictedZone` | `zone_id`, `bbox`, `restriction_type` | Restricted zone as axis-aligned rect |
| `ObstacleBand` | `obstacle_id`, `xy`, `height_range_m`, `clearance_margin_m` | Obstacle with altitude band |
| `FlightTimeWindow` | `start_time`, `end_time` | Time window as HH:MM strings |
| `FlightAltitudeBand` | `min_alt_m`, `max_alt_m` | Altitude range in meters |

## Deterministic Checks (6 Core Operators)

| Check | Core Operator | What It Checks |
|-------|---------------|----------------|
| Sensitive site distance | `distance_2d` | Candidate site distance to sensitive sites vs. risk radius |
| Route-zone conflict | `line_intersects_rect` | Whether initial route intersects restricted zone |
| Site in restricted zone | `rect_contains_point` | Whether candidate site falls inside a restricted zone |
| Obstacle altitude conflict | `altitude_overlap` | Whether flight altitude band overlaps obstacle effective range |
| Time window conflict | `time_overlap` | Whether flight time window overlaps restriction time window |
| (Available for future) | `point_to_line_distance_2d` | Point-to-line distance for route proximity checks |

## Status Model

### Production Statuses (v0.3 Core)

Priority: `invalid_operator` > `invalid_reference` > `contradicted` > `need_review` > `verified`

| Status | Meaning |
|--------|---------|
| `verified` | All deterministic checks passed |
| `contradicted` | One or more checks failed (conflict detected) |
| `need_review` | Insufficient data or ambiguous result |
| `invalid_operator` | Unknown or unsupported operator referenced |
| `invalid_reference` | Unknown object reference in check |

### Planned Statuses (Future)

| Planned Status | Meaning |
|----------------|---------|
| `need_data` | Real data source required but not available |
| `model_inferred` | Result inferred by model, not deterministically verified |

These are tracked in `planned_data_gaps` and `planned_model_inferred_items` fields but are NOT used as production statuses.

## Planned Data Gaps

The `planned_data_gaps` field identifies missing data that would be required for a complete production precheck:

- `sensitive_sites`: no sensitive sites provided
- `restricted_zones`: no restricted zones provided
- `obstacles`: no obstacle data provided
- `restriction_time_windows`: no time restrictions provided
- `flight_altitude_band`: no flight altitude band defined
- `flight_time_windows`: no flight time windows defined

These gaps are informational and marked as planned/future capability.

## Relationship to GeoTask Core

- All deterministic checks call production Core operators from `geotask_core.ops`
- No Core files are modified by this domain pack
- The pack uses Core's result status constants and hierarchy
- The pack follows Core's `local_xy_m` coordinate system

## Relationship to P5 Candidate Patent

This mock MVP provides evidence that:

1. The **domain pack architecture** (enrich_context, build_verification_plan, run_precheck) is a composable extension mechanism on top of GeoTask Core
2. **Deterministic verification** using Core operators can be applied to industry-specific precheck workflows
3. The **status hierarchy** and **data gap identification** patterns are general-purpose and reusable across domains
4. The **mock-first development approach** enables architecture validation without real data dependencies

## Disclosure Boundary

| Layer | Disclosure Status |
|-------|-------------------|
| GeoTask Core operators | Open source (MIT) |
| Domain Pack protocol | Open source (reference interface in `geotask_runtime/domain_pack.py`) |
| LowAlt precheck rules | Private (this pack) |
| Mock data | Private (this pack, fictional coordinates only) |
| Real data adapters | Not implemented (future, private) |

## Limitations

1. **Mock only** — all coordinates are fictional `local_xy_m`, no real locations
2. **No real regulatory rules** — checks are illustrative, not compliant with any aviation regulation
3. **No external data** — no APIs, databases, map services, or weather data
4. **Simplified geometry** — routes use first/last point as line segment, no multi-segment support
5. **No scoring/ranking** — sites are not ranked or scored, only checked for conflicts
6. **No 3D terrain** — altitude checks are 1D band overlaps, no terrain model
7. **No weather/wind** — no meteorological data integration

## Files

```
src/geotask_domain_packs/
├── __init__.py
└── lowalt_site_precheck/
    ├── __init__.py
    ├── models.py        # Dataclasses for all domain objects
    ├── rules.py         # Deterministic checks using Core operators
    ├── pack.py          # Main orchestrator (DomainPack implementation)
    ├── mock_data.py     # 4 mock scenarios with fictional coordinates
    └── report.py        # Report builder

tests/
└── test_lowalt_site_precheck_v0_1.py   # 14 tests

examples/domain_packs/lowalt_site_precheck/
├── basic_site_precheck.yaml
├── route_zone_conflict.yaml
├── missing_data_precheck.yaml
└── invalid_reference_precheck.yaml
```
