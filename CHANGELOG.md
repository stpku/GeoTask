# Changelog

All notable public changes to GeoTask Core are documented here.

## [Unreleased]

### Added

- Add `geotask --version`, `geotask -V`, and `geotask version` for direct CLI version inspection.
- Add GT14, an emergency-response dispatch case that distinguishes nearest distance from earliest verified arrival using readiness, route time, response deadlines, and evidence freshness.
- Add the GT14 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add GT15, a robot live-obstacle case that separates static structural map passability from current route occupancy and verifies a safe stop-and-replan action.
- Add the GT15 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add GT16, a multi-UAV crossing case that combines shared crossing location, altitude overlap, and non-overlapping crossing windows to verify temporal separation.
- Add the GT16 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add GT17, a city-event deduplication case that merges ten semantically consistent spatiotemporal reports into one dispatch task while preserving every source as evidence.
- Add the GT17 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.

### Changed

- Serialize PyPI publishing workflows and skip the publish job when the package version already exists, preventing duplicate manual dispatches from ending as failed releases.
- Ensure subprocess-based CLI tests execute the current source tree rather than an older installed package.

## [0.1.1] - 2026-07-27

### Fixed

- Align the Python distribution version and `geotask_core.__version__` through a single version source.
- Correct the version-reporting mismatch discovered by a clean PyPI installation of 0.1.0.

### Changed

- Pin bilingual Quickstarts to `geotask-core==0.1.1` for reproducible installation checks.
- Add a version-consistency regression test and a dedicated v0.1.1 release note.

### Verification

- Full source repository: 766 tests passing, 1 skipped.
- Public export: 338 tests passing.
- Public release pipeline: export, verification, sensitive scan, hash generation, and hash verification passing.
- Wheel and source distribution: Twine checks passing.
- Clean local-wheel installation: distribution metadata and `geotask_core.__version__` both report `0.1.1`; CLI and minimal deterministic execution pass.

## [0.1.0] - 2026-07-27

### Added

- Publish the first GeoTask Core Public Preview.
- Publish `geotask-core==0.1.0` to [PyPI](https://pypi.org/project/geotask-core/).
- Add six canonical object types: `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`, and `feature_collection`.
- Add six deterministic local operators: `distance_2d`, `line_intersects_rect`, `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, and `altitude_overlap`.
- Add YAML parsing, canonicalization, structural validation, deterministic execution, structured result models, and assurance metadata.
- Add model-output normalization, local verification, evaluator support, and CLI commands for validation, execution, inspection, normalization, and evaluation.
- Add GT01–GT13 progressive public cases covering spatial relations, spatiotemporal composition, evidence governance, robot coordination, UAV energy reserve, and vehicle clearance envelopes.
- Add the GeoTask White Paper v0.1, implemented Language and Execution Specification v1.0, Draft 2020-12 JSON Schema, Quickstart, status/evidence references, and bilingual Cookbook.
- Add a Chinese-first GitHub entry point with a full English mirror, bilingual contribution guidance, community templates, and a public project portal.
- Add GitHub Pages deployment, canonical metadata, `robots.txt`, `sitemap.xml`, and stable routes for GT01–GT13.
- Add `CITATION.cff`, a public roadmap, bilingual release notes, CODEOWNERS, and a Trusted Publishing workflow for PyPI.
- Add Python 3.10–3.13 CI, package build checks, public-export allowlisting, secret scanning, architecture-boundary checks, and documentation conformance tests.

### Changed

- Rename the project from STIR to GeoTask while retaining selected deprecated compatibility aliases for migration.
- Make documentation and public-manifest checks consistent across Python 3.10–3.13.
- Upgrade official GitHub Actions to Node 24-compatible major versions.
- Restrict Python package discovery to `geotask_core*` so Runtime and Domain Pack source trees cannot enter the public wheel.
- Adopt PEP 639 project license metadata and publish repository, documentation, issue, changelog, and roadmap URLs in package metadata.
- Make PyPI installation the primary path in both README files and Quickstarts; move editable source installation to contributor sections.

### Verification

- Public repository test suite: 336 tests passing.
- Full source test suite: 764 tests passing, 1 skipped.
- GitHub CI: Python 3.10, 3.11, 3.12, and 3.13 passing.
- GitHub Pages portal and GT01–GT13 routes deployed.
- Public export verification and sensitive-content scan passing.
- Clean-environment PyPI smoke test passing for installation, CLI help, operator inspection, distribution version `0.1.0`, validation, and minimal deterministic execution.
- Known issue: the published `0.1.0` artifact reports `geotask_core.__version__ == "0.2.0"`; a patch release is required to align the module attribute with distribution metadata.

[0.1.1]: https://github.com/stpku/GeoTask/releases/tag/v0.1.1
[0.1.0]: https://github.com/stpku/GeoTask/releases/tag/v0.1.0-public-preview
