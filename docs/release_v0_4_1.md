# GeoTask Core v0.4.1 Capability Discovery and Release-Hardening Maintenance Release

- **Release date:** 2026-08-12
- **Git tag:** `v0.4.1`
- **Package version:** `0.4.1`
- **Release line:** backward-compatible `0.4.x` maintenance/productization update

GeoTask Core v0.4.1 publishes the public changes accumulated after v0.4.0 while preserving the existing Core compatibility boundary: the GT capability baseline remains through GT42, the deterministic Operator Registry remains 14 operators, the public Artifact Registry remains 32 Artifacts, and the Schema Bundle remains 33 Schemas. This release improves installed capability discovery, self-diagnosis, verification-quality testing, developer activation, architecture communication, and public-distribution governance without introducing a new GT number or expanding production authority.

## What this release adds

### 1. Installed capability discovery

`geotask inspect capabilities` exposes nine installed public Core capability surfaces in a deterministic, fail-closed registry projection. The projection describes already shipped Operator/Artifact/Schema registries, Runtime and Verification Provider interfaces, the Reference Agent, Core Benchmark, Verification Quality Benchmark, and self-diagnostic surface. Unknown capability IDs fail closed.

The capability registry does **not** discover external plugins, runtime/provider instances, domain packs, network resources, external truth, or real-world authorization, and it does not register a new Schema or Operator.

### 2. Installed self-diagnostic

`geotask inspect health --format text|json` provides one installed-package health surface with ten checks covering package/version identity, Python support, Schema Bundle, Artifact Registry, Operator Registry, Capability Registry, Reference Agent bundle/replay, Core Benchmark, and Verification Quality Benchmark. Diagnostic execution keeps production access, network use, external truth fetching, model calls, authorization, and action execution false.

### 3. Verification Quality Benchmark v0.2

The deterministic synthetic perturbation suite extends verification-quality coverage across threshold boundaries, freshness, conflict/consistency, human-control gating, bounded correction/impact, deterministic replay, and side-effect boundaries. It remains a fictional fixed suite and makes no real-world safety-accuracy, production-readiness, cross-domain-generalization, or Promotion claim.

### 4. Developer activation and architecture communication

The public project now includes the packaged Reference Agent Activation Pack, the fail-closed external-developer activation evidence kit, and the six-part GeoTask Architecture Series. These assets make the current Core easier to discover, run, inspect, and explain without turning documentation or participant evidence into an automatic product-maturity or Core-Promotion claim.

### 5. Public distribution and provenance hardening

Public export is Git-tracked and explicitly whitelisted, protected-identity scanning is part of the release boundary, and second-system promotion pre-review remains fail-closed. Repository co-location, validation success, or external-system consumption does not transfer ownership into Core.

## Compatibility and boundaries

- `geotask-core>=0.4.0,<0.5.0` remains the supported provider-adapter compatibility line.
- No new deterministic Operator is introduced; count remains 14.
- No new public Artifact is introduced; count remains 32.
- No new bundled Schema is introduced; count remains 33.
- GT capability numbering remains through GT42.
- `eligible != authorized != released != sent != executed` remains a hard control invariant.
- No production write, publication authority, real-world authorization, or external action is granted by this release.

## Install

```bash
python -m pip install --no-cache-dir geotask-core==0.4.1
geotask inspect capabilities
geotask inspect health --format json
```

## Verification expectation

The exact release candidate must pass public export verification, protected-identity and sensitive-content scans, wheel/sdist release preflight, 33-Schema distribution verification, installed-package diagnostics, Reference Agent replay, and Python 3.10–3.13 CI evidence on the same release commit before the tag is authorized.
