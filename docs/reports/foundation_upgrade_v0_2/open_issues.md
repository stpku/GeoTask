# Foundation Upgrade v0.2 Open Issues

## Active

- CLI now exposes `validate`, `run`, `explain`, `inspect operators`,
  `inspect schema`, `inspect examples`, `report`, `normalize`, and `eval`.
  Remaining CLI hardening: fuller `--debug` handling and structured validation
  diagnostics.
- Parser validation still returns plain strings rather than structured
  diagnostics with paths, codes, and suggested fixes. Loop C added stable
  `invalid_interval` strings for generic time/altitude objects, but not the full
  structured diagnostic model.
- Existing public docs describe benchmark boundaries, but there is not yet a
  consolidated public-safe benchmark usage guide.

## Boundary Watch

- Do not expand LowAlt pack rules, thresholds, objects, workflows, or examples.
- Do not move patent evidence details into public-safe docs.
- Keep domain-pack work generic unless explicitly only recording an open issue.
