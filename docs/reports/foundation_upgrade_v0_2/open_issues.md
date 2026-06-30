# Foundation Upgrade v0.2 Open Issues

## Active

- CLI now exposes `validate`, `run`, `explain`, `inspect operators`,
  `inspect schema`, `inspect examples`, `report`, `normalize`, and `eval`.
  Remaining CLI hardening: fuller `--debug` handling.
- Parser validation now has `validate_geotask_diagnostics()` with `path`,
  `code`, `message`, and `suggested_fix`, while keeping the legacy
  `validate_geotask()` string-list API. Remaining diagnostic work: broaden
  structured validation to invalid references, expected result sections, and
  richer task/assertion semantics. Unknown fields and unsupported operators are
  now covered.
- Existing public docs describe benchmark boundaries, but there is not yet a
  consolidated public-safe benchmark usage guide.

## Boundary Watch

- Do not expand LowAlt pack rules, thresholds, objects, workflows, or examples.
- Do not move patent evidence details into public-safe docs.
- Keep domain-pack work generic unless explicitly only recording an open issue.
