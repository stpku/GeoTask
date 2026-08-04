# Changelog

All notable public changes to GeoTask Core are documented here.

## [Unreleased]

### Added

- Add `polygon_contains_point(polygon, point)` as a deterministic container-first Core predicate equivalent to `point_in_polygon(point, polygon)`, with explicit object-order validation, closed-boundary semantics, legacy audit preservation, Schema metadata, a three-boundary-case example, and Core Benchmark coverage.
- Add matching English and Chinese native-v1 `point_to_line_distance_2d` examples with deterministic four-meter and zero-distance boundary checks, plus regression coverage that keeps their machine contracts identical.
- Add a repository-local VS Code YAML Schema association for native v1 GeoTask files and document it in both Quickstarts without requiring a remote Schema service.
- Add an English abstract and core terminology map inside the existing non-normative white paper, with bilingual README and documentation-index navigation.
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
- Add the public `geotask benchmark core` release gate and registered `geotask.core-benchmark-report` Artifact. Five fixed fictional cases cover all nine deterministic operators, result round trips, semantic replay hashes, and evidence propagation while measuring the production JSON-decode-to-result-serialization path. The optional p95 guardrail is local-only and explicitly does not support cross-hardware performance claims.
- Add `geotask.observation` v0.1 as the first public world-model Artifact. It records source-bound, timezone-aware observations containing producer identity, explicit world claims, evidence references, declared uncertainty, validity windows, and optional supersession links. Strict loading and unified Artifact validation reject malformed time order, duplicate claims or references, invalid uncertainty, non-finite values, and unknown fields while explicitly reporting `truth_verified=false` and `world_state_updated=false`.
- Add `geotask.world-state` v0.1 as a versioned point-in-time snapshot of world objects, attributes, relations, validity, uncertainty, and closed Observation/Evidence references. Strict loading rejects inactive facts, unresolved object or evidence references, duplicate identities and attributes, traceable statuses without support, non-finite values, and unknown fields; unified validation exposes a deterministic semantic fingerprint while explicitly reporting `external_truth_verified=false`, `state_transition_computed=false`, and `action_eligibility_changed=false`.
- Add `geotask.state-transition` v0.1 as an auditable binding between two World State snapshots. It records Observation-supported object, attribute, relation, and action-eligibility changes using identity-based paths, enforces revision/time ordering, reference closure, operation-specific before/after rules, deterministic fingerprints, and explicit snapshot binding verification while reporting that generic Artifact validation did not compare snapshots, apply changes, materialize state, verify truth, or authorize action.
- Add `geotask.verification-session` v0.1 as an immutable audit snapshot binding one World State semantic fingerprint to exact serialized task, execution-result, control-evaluation, State Transition, and Discrepancy Report artifacts. It records session outcome, action eligibility, and recheck triggers, provides exact-byte SHA-256 binding validation, and keeps Session structure, binding verification, linked-artifact semantic validation, and operational execution as separate layers.
- Add `geotask.discrepancy-report` v0.1 as an auditable bounded-difference record for one World State. It binds exact source bytes, enforces kind-specific expected/observed values, identity-based subject paths, reference closure, aggregate state/severity, declared downstream impact, and non-overlapping mutable/immutable correction scope while explicitly not comparing sources, propagating impact, creating a Correction Request, applying correction, materializing state, running rechecks, verifying truth, or authorizing action.
- Add `geotask.correction-request` v0.1 as an immutable bounded request for a successor World State. It binds one base snapshot and exact Discrepancy Reports, constrains non-overlapping changes to mutable identity paths, rejects intrinsic identity/provenance edits, anchors every declared `before` value to the actual base snapshot, requires complete discrepancy-resolution, successor-validation, and blocked-output recheck criteria, requires a later World State revision, and keeps affected outputs/actions blocked while explicitly not applying changes, materializing a successor, evaluating criteria, resolving discrepancies, releasing outputs, or authorizing action.
- Add `geotask.impact-graph` v0.1 as an immutable source-bound directed acyclic graph connecting Discrepancy Report and Correction Request entities to affected World State paths, assertions, outputs, actions, and explicit reevaluation targets. Strict loading enforces roots, reachability, acyclicity, reference closure, target ancestry, blocked gates, aggregate state, and deterministic fingerprints; binding validation verifies exact bytes, source entities, and key edge semantics while explicitly not discovering impact, executing propagation, applying correction, materializing state, running reevaluation, releasing outputs, or authorizing action.
- Add `geotask.incremental-reevaluation-result` v0.1 as an immutable bounded result binding exact base/successor World States, Impact Graph, Correction Requests, Discrepancy Reports, and execution results. Strict loading closes node, target, acceptance, discrepancy, output-gate, and action-gate outcomes; binding validation enforces exact bytes, graph/request coverage, requested-path confinement, immutable-path preservation, execution-result semantics, acceptance evaluation, discrepancy resolution, and output/action gate closure while forcing external action authorization and execution to remain false.
- Add bounded `materialize_successor_world_state()` execution and `geotask.world-state-materialization-result` v0.1. Core validates the required Correction Request and exact source bytes, applies only declared add/replace/remove values plus an explicit recompute-value map, emits a new immutable World State revision, records complete before/after change coverage, preserves Observation/Evidence references and output/action gates, and keeps reevaluation, output release, external truth, authorization, and action execution false.
- Add `geotask.recompute-derivation-result` v0.1 as an immutable source-bound derivation contract for every Correction Request `recompute` change. Exact World State, Correction Request, Observation, and GeoTask Document bytes are bound by SHA-256; named inputs resolve through exact JSON Pointers; only `copy_input`, finite numeric `subtract`, and `interval_gap_minus_delay_seconds` are allowed; deterministic evaluation produces the complete materializer value map while forbidding arbitrary code, network or model calls, state mutation, reevaluation, output release, external truth claims, and action authorization.
- Add bounded Observation Merge v0.1 and the registered `geotask.observation-merge-result` Artifact. Core consumes exact base World State and Observation bytes, requires complete explicit claim-to-existing-target mappings, updates only existing attributes or relations as asserted claims, emits a canonical successor revision, and supports exact-byte deterministic replay validation while refusing identity inference, object/relation creation, undeclared ambiguous-conflict resolution, State Transition computation, impact propagation, reevaluation, output release, truth verification, or action authorization. The Registry now exposes twenty-three Artifacts and the offline Schema Bundle contains twenty-four Schemas.
- Extend bounded Observation Merge v0.1 with target-scoped `require_equal` and `explicit_precedence` conflict policies. Duplicate targets still fail closed by default. Semantic-equality consolidation unions source references while recording one `applied` and the remaining `consolidated` participants; explicit precedence requires a complete caller-authored order, records the selected claim as `applied` and every other participant as `superseded`, and never infers authority or ranks sources. The optional `conflict_resolutions` result section is deterministically replayed and preserves the serialized shape and semantic fingerprint of existing single-target results.
- Add high-level, read-only `geotask verify` and `geotask recheck` commands plus public Python helpers for complete explicit world-state cycle bundles. `verify` validates a Verification Session, bound World State, exact Observation set, every referenced registered Artifact, and all fingerprint/SHA-256 bindings. `recheck` validates an already-authored Incremental Reevaluation Result and its complete base/successor World State, Impact Graph, Correction Request, Discrepancy Report, and execution-result source bundle, including declared outcome semantics and exact bytes. Both commands fail closed on missing, duplicate, extra, invalid, or mismatched inputs and explicitly do not execute tasks, controls, reevaluation, state materialization, output release, authorization, or actions.
- Add GT21 as the first GT21–GT28 World-State Cycle case. Two fictional Observations claim 60 and 55 seconds for the same existing `uav-b.delay_seconds` path: no policy fails closed, `require_equal` rejects the unequal projections, and a complete caller-declared `explicit_precedence` deterministically selects 55 while recording `applied` and `superseded` participants in successor World State revision 2. The executable test proves input-order independence, strict Schema loading, and exact replay bindings; the static page, bilingual cookbook, generated catalog, sitemap, navigation, and public export expose the same safety boundary without claiming source authority, external truth, State Transition completion, or action authorization.
- Add GT22 as the first-snapshot World-State Cycle case. A case-specific builder strictly loads fictional position and battery Observations, requires a caller-authored object/attribute plan with every claim mapped exactly once, fixes the initial World State at revision 1, and validates reference closure, validity, uncertainty, JSON Schema conformance, input-order independence, and semantic fingerprint `bb57804b830e08dc361bc04e3ca96f4530ea525c198857492dcb6c304dbe540f`. Tests also prove that World State references do not bind insignificant changes to Observation file bytes. The page and bilingual cookbook preserve `asserted` status and explicitly avoid identity inference, external-truth claims, State Transition claims, or action authorization.
- Add GT23 as a scenario-first continuous-flight change case. Two new fictional telemetry Observations move `uav-alpha` from `(120, 80, 35)` to `(260, 180, 48)` metres and reduce battery from 68% to 52% over 300 seconds. The case-specific builder retains revision 1, constructs revision 2, explicitly refreshes the object validity window instead of silently extending expired state, records three before/after changes, binds both snapshots by semantic fingerprint, checks every declared path against the snapshots, and remains input-order independent. The page, bilingual cookbook, catalog, sitemap, navigation, and public export explain why latest-value overwrite is insufficient while preserving that State Transition v0.1 does not compute a generic diff, propagate impact, recompute risk, establish external truth, or authorize action.
- Add GT24 as a scenario-first temporary-no-fly-zone impact case. A fictional 14:00–16:00 restriction intersects medical route A while inspection route B remains outside. A case-specific builder binds the notice Observation and World State to a Discrepancy Report and a finite Impact Graph containing seven nodes, seven edges, four reevaluation targets, two blocked outputs, and one blocked launch action. Tests enforce the complete declared medical dependency chain, exclude the inspection chain, reject missing scope, unexpected intersection, cycles, and byte tampering, and preserve that Core does not compute geometry, discover impact automatically, execute propagation or reevaluation, release outputs, establish external truth, or authorize launch.

### Changed

- Reframe GT21 and GT22 around concrete operational problems rather than Artifact terminology. GT21 now leads with the 60-second telemetry versus 55-second operations-review conflict and explains why silent overwrite, averaging, or invented authority is unsafe before revealing the bounded conflict-policy mechanics. GT22 now leads with position and battery data arriving from different systems and explains object/time/field assembly risks before revealing World State revision and fingerprint details. The bilingual GT21–GT28 cookbook now defines a scenario-first narrative contract and fixes concrete real-world scenarios for GT23–GT28.
- Upgrade the public GitHub Actions workflow stack to `actions/checkout@v7`, `actions/setup-python@v7`, `actions/upload-pages-artifact@v5`, `actions/upload-artifact@v7`, and `actions/download-artifact@v8`, with regression coverage that keeps CI, Pages, and PyPI workflow majors synchronized and a no-release Artifact upload/download roundtrip smoke.
- Extend the wheel/sdist Schema distribution release gate and installed-package smoke workflows to recognize all twenty-four public Schemas and validate the registered Observation, World State, Observation Merge Result, State Transition, Verification Session, Discrepancy Report, Correction Request, Impact Graph, Recompute Derivation Result, World State Materialization Result, Incremental Reevaluation Result, and Core Benchmark Artifacts.
- Reframe the architecture documentation from a single execution pipeline into four explicit planes: perception/open reasoning, explicit spatiotemporal world state, verification/state evolution, and control/real-world action. The document now distinguishes the implemented Observation, World State, bounded Observation Merge with caller-declared same-target policies, State Transition, Verification Session, Discrepancy Report, Correction Request, Impact Graph, bounded Recompute Derivation Result, successor-state materialization, and Incremental Reevaluation Result foundations from planned automatic diff, identity discovery, resolution of ambiguous claims without a declared policy, impact discovery/propagation, bounded derivation-method expansion, and provider abstractions.
- Upgrade GT16 from a static route-crossing question into a world-state update replay. The initial snapshot contains a 120-second separation; a fictional telemetry Observation records a 40-second delay; the predicted relation changes to 80 seconds; and the action gate preserves valid findings while requiring continued monitoring and recheck at the 60-second threshold.
- Reposition the README, public portal, documentation indexes, white paper, and architecture around GeoTask as an explicit and verifiable spatiotemporal world model for agents. The verifiable task protocol remains the current implementation form; error detection, bounded correction, evidence recovery, and action gating are described as world-state maintenance capabilities rather than the complete product definition. The white paper now distinguishes GeoTask from implicit neural world models and explains how their outputs can enter GeoTask as Observations.
- Move the post-v0.4 roadmap to `v0.5: Verifiable World-State Cycle` and `v0.6: Local Verification Providers and Domain Pack Ecosystem` without redefining the in-progress v0.4 package and Adapter compatibility target.

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
