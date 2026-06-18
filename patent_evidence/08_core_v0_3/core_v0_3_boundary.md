# GeoTask Core v0.3 — Evidence Boundary

## What v0.3 Proves

✅ Production GeoTask Core Normalizer and Verifier handle 6 spatial operators.
✅ Unified status hierarchy (invalid_operator > invalid_reference > contradicted > need_review > verified).
✅ Chinese negation correctly detected for intersection and contains.
✅ Unit mismatch (km vs meter) detected in production code.
✅ Invalid operator names (e.g., haversine) rejected.
✅ Invalid object references detected.
✅ All existing v0.1/v0.2 tests continue to pass (backward compatible).

## What v0.3 Does NOT Prove

❌ Real LLM accuracy — all tests use deterministic simulated outputs.
❌ General NLP capability — normalizer uses regex patterns, not ML.
❌ Complex GIS support — no polygon, 3D, real coordinate systems, or real map data.
❌ External API integration — no map services, no data connectors.
❌ Statistical significance — end-to-end tests are functional, not inferential.
❌ Replacement for regulatory or human review — Core is a tool, not an authority.
❌ That benchmark v0.2 is obsolete — v0.2 provides broader structural coverage (24 cases).
❌ Live LLM API evaluation — no real model APIs are called; all outputs are deterministic.

## Relationship to v0.2

```
v0.2: 24 cases, 6 ops, local verifier → Structural extensibility evidence
v0.3: Core ops, normalizer, verifier → Production end-to-end evidence
```

v0.2 and v0.3 are complementary:
- Use v0.2 when arguing encoding format extensibility across diverse cases.
- Use v0.3 when arguing production-grade normalization and verification capability.

## Limitations

1. Deterministic tests only — no real LLM inference.
2. Regex-based extraction — limited generalization to unseen output formats.
3. Tolerance-based numeric comparison (0.05) — may need tuning for specific domains.
4. Object-type auto-detection in runner — works for well-structured geotask_data.
5. Time format limited to HH:MM — 12-hour or ISO formats not supported.
6. Altitude ranges assume same unit — no unit conversion for altitudes.

## Next: v0.4

- Real LLM API benchmark using 24-case structure from v0.2.
- Statistical significance analysis.
- Domain-specific operator extensions.

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_boundary.md`*
