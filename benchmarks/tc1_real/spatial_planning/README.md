# TC1-Real Spatial Planning

This package is a **repository-local benchmark harness**, not part of the public `geotask-core` API.

It exists to test one non-low-altitude question:

> For a long-cycle physical-world planning task, can task-bounded and multi-scale context preparation reduce irrelevant carried context without increasing frozen critical-context gaps?

Current scenario: Phoenix public-library service-coverage **context preparation**.

It does not decide where to build a library, estimate facility capacity, authorize investment, or claim planning-outcome accuracy.

Frozen spatial scopes and requirements are defined in:

`docs/reference/task-context-tc1-real-spatial-planning-plan-v0.1.md`

Live public-source acquisition is kept outside normal CI. Exact recorded source bytes and provenance may later be committed as compact fixtures for deterministic replay. Planning-specific benchmark policy must remain outside GeoTask Core.
