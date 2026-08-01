# Changelog

All notable public changes to GeoTask Core are documented here.

## [Unreleased]

### Added

- Add the public GeoTask Runtime Interface Profile v0.1 with `RuntimeAdapter`, versioned Runtime Descriptor, Request, and Response Artifacts, strict loaders, model-neutral operation identifiers, and three-way Descriptor/Request/Response exchange validation.
- Add file-based `geotask runtime inspect`, side-effect-free `geotask runtime check`, explicit operation input cardinality, and a fail-closed `geotask runtime mock` reference adapter. Offline checks never submit a request; post-submission validation rejects input-count, output, synchrony, audit, authorization, and side-effect claims that contradict the inspected Descriptor or submitted Request.
- Register `geotask.runtime-descriptor`, `geotask.runtime-request`, and `geotask.runtime-response` as offline-verifiable public Artifacts. The development Registry now exposes eleven Artifacts and the Schema Bundle contains twelve Schemas.
- Add a public-safe `HttpJsonRuntimeAdapter` example outside `geotask_core`, proving a real HTTP transport boundary while keeping Descriptor discovery offline and leaving credentials, retries, model calls, evidence access, and production actions outside Core. The example rejects redirects, embedded URL credentials, duplicate keys, non-finite JSON, non-JSON or oversized responses, and keeps HTTP transport failures separate from Runtime operation states.
- Add a paired loopback-only reference HTTP Endpoint that accepts strict `POST /runtime` requests, dispatches only to `FailClosedMockRuntime`, returns Problem JSON for malformed transport input, and returns contract-valid `completed` or `rejected` Runtime Responses for valid Request Artifacts. The service rejects credential headers, remote binding, chunked bodies, duplicate keys, non-finite JSON, and oversized requests without adding service hosting to Core.
- Add an independently buildable `geotask-provider-neutral-model-adapter` package skeleton targeting Core `0.4.x`, with non-secret configuration, a structural Provider Protocol, a no-network Mock Provider, `execute-nonlocal` Request/Response mapping, registered input/output Artifact validation, opaque authorization/audit propagation, and truthfulness guards that reject model output claiming deterministic or independently verified assurance. CI builds and Twine-checks its wheel and sdist.
- Add the first provider-specific package, `geotask-openai-responses-adapter`, targeting the official OpenAI Python SDK `2.46.x`. Private startup code injects an authenticated client by opaque authorization reference; the public package performs one synchronous no-retry Responses API call with strict JSON Schema Structured Outputs, `store=false`, no tools or conversation state, request/response audit references, generic failure diagnostics, and the existing registered Artifact and truthfulness guards. Tests and the installed-wheel smoke are fully offline and use an SDK-shaped fake client; no key is read and no live request is made.
- Add public `polygon` and `multi_polyline` object contracts with strict Canonical validation, JSON Schema support for inline and `data`-wrapped forms, deterministic `point_in_polygon` and `multi_polyline_intersects_rect` operators, closed-boundary semantics, legacy runner and Normalizer/Verifier compatibility, CLI coverage, and a fully executable fictional example.
- Add one document-wide space execution contract across tasks: planar operators reject geographic or unknown CRS, projected CRS requires an identifier, planar coordinate order must be `[x, y]`, distance and altitude units must match the shared horizontal/vertical units, altitude datums must agree, and boundary-sensitive operators fail closed unless `boundary_semantics` is `closed`. Common unit spelling aliases are recognized without numeric conversion, and pure temporal tasks remain independent of the planar CRS gate.
- Add optional document-level provenance with strict source identities, kinds, URI/Artifact references, SHA-256, timezone-aware timestamps, assertion evidence bindings, and authoring audit metadata. Valid bindings propagate to `CheckResult.evidence_refs` without increasing assurance or fetching external sources. Artifact Registry descriptors now expose portable `ide_file_patterns` through `geotask inspect schemas --format json` for direct IDE Schema association.
- Add the public `geotask benchmark core` release gate and registered `geotask.core-benchmark-report` Artifact. Five fixed fictional cases cover all eight deterministic operators, result round trips, semantic replay hashes, and evidence propagation while measuring the production JSON-decode-to-result-serialization path. The optional p95 guardrail is local-only and explicitly does not support cross-hardware performance claims.

### Changed

- Reframe the architecture documentation from a single execution pipeline into four explicit planes: open reasoning, spatiotemporal task contracts, local verification/correction, and control/action boundaries. The document now distinguishes implemented Core, Agent, Artifact, and Runtime capabilities from planned `VerificationSession`, discrepancy, impact, observation, provider, and reevaluation abstractions.
- Upgrade GT16 from a static route-crossing question into a dynamic verification replay. The initial 120-second separation remains verified, a fictional 40-second delay reduces the predicted margin to 80 seconds, and the action gate preserves valid findings while requiring continued monitoring and recheck at the 60-second threshold. Catalog-driven portal metadata, navigation JSON, Sitemap, bilingual Cookbook entries, page logic, example data, and tests are synchronized.

## [0.3.0] - 2026-07-31

### Added

- Add the model-neutral GeoTask Agent Integration Profile v0.1 with four discoverable tools: Artifact inspection, Artifact validation, deterministic task execution, and read-only control evaluation.
- Add `geotask agent inspect`, fail-closed `geotask agent prepare`, guarded `geotask agent retry`, and fail-closed `geotask agent recover` commands. Generated drafts are strictly validated, mechanically repaired, revalidated, and locally executed without inferring coordinates, operators, object bindings, evidence, or domain policy. Blocked preparation reports include a versioned revision request; retry recomputes that request, verifies the revision-base SHA-256, rejects changes outside requested paths, and executes only after the diff is accepted.
- Register `agent_generation_preparation/0.1`, `agent_revision_verification/0.1`, `agent_revision_retry/0.1`, and `agent_integration/0.1` evidence-recovery reports as public Artifacts with offline Draft 2020-12 Schemas, strict loaders, unified Artifact validation, and distribution integrity gates. The Registry now exposes eight Artifacts and the Schema Bundle contains nine Schemas.
- Extend GT08 with fictional verified schedule evidence and deterministic re-execution of the previously unverifiable temporal assertion after all required evidence and `resume_when` checks pass.
- Add a public `skills/geotask-core/SKILL.md` for Agent injection and bilingual Profile, Cookbook, CLI, evidence-recovery, and experience-page documentation.

### Fixed

- Make manual PyPI publication web-compatible by dispatching from the default branch, checking out the requested `v<version>` tag, and verifying that HEAD matches the tag before building.
- Replace the brittle nested-quote package-version command with a shell-safe Python heredoc that writes a valid `version=<value>` record to `GITHUB_OUTPUT`.

## [0.2.0] - 2026-07-30

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
- Add GT18, a rescue-robot route-feasibility case that separates geometric shortest path from hazard avoidance and equipment temperature capability.
- Add the GT18 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add GT19, an emergency-supply UAV release-gate case that separates target-overhead arrival from live ground-clearance authorization.
- Add the GT19 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add GT20, a vehicle intersection-entry case that separates green-signal permission from downstream storage and junction-clearance feasibility.
- Add the GT20 interactive page, public example, bilingual cookbook coverage, site navigation, and regression tests.
- Add a versioned case catalog, generator, deployment slug list, JSON navigation index, and catalog conformance tests for GT01—GT20.
- Add shared case navigation CSS and JavaScript that consume the generated same-origin case index on every public case page.
- Add a preview-first, transactional case scaffold command that creates the three case files and one catalog entry required for the next public case.
- Add the opt-in `geotask.control/1.0` Extension Profile, machine-readable schema, Core validation, public constants, and normative documentation for decision rules, evidence requests, evidence conflicts, and task gates.
- Add the safe finite `geotask.control-expression/1.0` parser and evaluator with three-valued logic, scalar comparisons, identifier inspection, resource limits, and normative language documentation.
- Add read-only control contexts and the versioned Control Evaluation Result contract for gate state, unknown identifiers, blocked outputs, output eligibility, and provenance without executing actions.
- Add `geotask control evaluate` for schema-compatible, non-executing control evaluation from a GeoTask document, canonical execution-result JSON, and optional JSON/YAML domain state.
- Add `geotask run --format v1-json --output result.json` so the CLI can produce the canonical `GeotaskResult.to_dict()` payload consumed by control evaluation while preserving compatibility YAML as the default.
- Add the public `geotask-result-v1.0` JSON Schema, strict result enum validation, and `geotask result validate` with text or machine-readable JSON reports.
- Add `geotask control validate`, strict Control Evaluation Result loading, and a shared versioned-payload validation framework for execution and control result reports.
- Add the public Artifact Registry and `geotask inspect schemas --format json` for discovering task-document, execution-result, control-evaluation, and Artifact Validation Report schemas and commands.
- Add exact Artifact Registry lookup with `geotask inspect schemas <artifact-id> --format json`, preserving the versioned registry envelope and failing explicitly for unknown IDs.
- Bundle the five public JSON Schemas in built distributions and add offline `load_bundled_schema()` and `load_artifact_schema()` APIs with Schema ID verification.
- Add `geotask schema export <artifact-id>` with clean stdout JSON, compact mode, file output, and stable failure behavior for offline Schema materialization.
- Add a generated Schema Bundle Manifest with byte sizes and SHA-256 digests, automatic integrity checks on Schema loads and exports, and `geotask schema verify [artifact-id] --format text|json`.
- Add a standard-library wheel/sdist Schema distribution verifier and enforce it in CI and the PyPI publication workflow, including sdist rebuild and isolated installed-CLI smoke tests.
- Add `geotask inspect schemas [artifact-id] --verify` to combine stable Artifact Registry discovery with installed Schema Bundle integrity results while preserving the default v1.0 registry payload.
- Add unified `geotask artifact validate <artifact-id> <file> --format text|json` and public `validate_artifact_file()` / `validate_artifact_payload()` APIs, with Schema Bundle fail-closed checks and one `artifact_validation/1.0` report for all registered artifacts.
- Register `geotask.artifact-validation-report` as a fourth public artifact, publish its JSON Schema, and add strict `load_artifact_validation_report()` self-validation without repeating the original target validation.
- Add a local, standard-library release preflight that verifies package version, release date, tag text, release notes, Quickstarts, README navigation, and optional wheel/sdist metadata before PyPI publication.

### Changed

- Make `cases/catalog.yaml` the single source of truth for portal case cards, Sitemap entries, deployment case discovery, and cross-case navigation metadata.
- Generate shared asset references on every case page while preserving existing hand-authored links as an offline fallback.
- Replace 20 hand-written deployment checks and output lines with a generated case slug list and one validation loop.
- Reduce future case authoring to four inputs while generated portal, Sitemap, deployment, and navigation files remain derivative outputs.
- Keep extensions open by default, but apply strict structural, assertion-reference, and finite-expression syntax validation when a document explicitly declares `geotask.control/1.0`.
- Keep control evaluation observational: it never mutates execution results, changes assurance, releases outputs, or executes `next_action`; satisfied outputs are reported only as eligible for separate authorization.
- Deserialize canonical `geotask_result` payloads strictly for control evaluation, rejecting unknown or missing fields, non-v1 versions, invalid types, negative summary counts, and check-count mismatches.
- Make `OperatorContract` the single source of truth for public operator metadata, eliminating the separate hand-maintained registry table.
- Enforce operator output types, assertion `expected_type`, and executable basic invariants before granting deterministic assurance.
- Return explicit `unverifiable` checks for `hybrid`, `shadow_compare`, and non-`local` executors instead of substituting local execution.
- Serialize PyPI publishing workflows, require dispatch from the default branch, explicitly check out the requested `v<version>` tag, and skip the publish job when the package version already exists, preventing branch-content or duplicate releases.
- Ensure subprocess-based CLI tests execute the current source tree rather than an older installed package.

### Fixed

- Correct compatibility documentation: selected STIR function, CLI, and YAML aliases remain, but the old `stir_core` Python package path is not distributed.
- Replace migration guidance that referenced a helper script excluded from the public repository with direct Git commands.
- Restrict source-checkout Schema Manifest reconstruction to the repository `src/` layout so an installed package missing its Manifest fails closed instead of silently rebuilding trust metadata.
- Normalize UTF-8 text to LF before public-export hashing so SHA-256 manifests remain stable across Windows CRLF exports and Linux/GitHub checkouts.

### Verification

- Full source repository: 1070 tests passing, 1 skipped.
- Artifact Registry: 4 stable public artifacts with exact lookup and composite integrity discovery.
- Offline Schema Bundle: 5 JSON Schemas with generated byte-size and SHA-256 manifest verification.
- Distribution checks: direct wheel/sdist, sdist-rebuilt wheel, isolated installed CLI/API smoke tests, and Twine checks passing.
- Public release pipeline: 253 exported files; boundary, verification, sensitive scan, hash generation, and hash verification passing.

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

[0.3.0]: https://github.com/stpku/GeoTask/releases/tag/v0.3.0
[0.2.0]: https://github.com/stpku/GeoTask/releases/tag/v0.2.0
[0.1.1]: https://github.com/stpku/GeoTask/releases/tag/v0.1.1
[0.1.0]: https://github.com/stpku/GeoTask/releases/tag/v0.1.0-public-preview
