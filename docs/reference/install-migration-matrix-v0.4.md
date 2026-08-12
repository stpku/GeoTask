# GeoTask Core 0.4.1 Installation and Migration Matrix

**Status:** P2 release preparation; 0.4.1 is not released
**Date:** 2026-08-07  
**Current published/repository version used by this local verification:** 0.3.0  
**Target release scope:** 0.4.1

## 1. Why this matrix exists

P2 requires installation and migration to be treated as product behavior, not as an afterthought after tagging a release. This matrix separates three kinds of evidence:

1. **declared support** in `pyproject.toml`;
2. **CI-configured verification** in `.github/workflows/ci.yml`;
3. **local clean-room evidence** actually executed for this release-preparation cycle.

A configured CI version is not described as locally tested unless it was actually executed in the current environment.

## 2. Python support matrix

| Python | Declared by package | CI matrix configured | 2026-08-07 local clean-room evidence |
|---|---|---|---|
| 3.10 | yes | yes | not locally executed in this session |
| 3.11 | yes | yes | not locally executed in this session |
| 3.12 | yes | yes | **passed** |
| 3.13 | yes | yes | not locally executed in this session |

Package contract:

```text
requires-python >= 3.10
classifiers: Python 3.10 / 3.11 / 3.12 / 3.13
```

The release workflow must still obtain the normal CI evidence for all four minors before 0.4.1 publication.

## 3. 3.12 clean-room evidence completed on 2026-08-07

### Public-export editable installation

A fresh public export was created outside the development checkout and installed into a new virtual environment:

```text
public export: 656 files / approximately 5.9 MB
package installed: geotask-core 0.3.0
Reference Agent success replay: PASS
Verification Quality Benchmark v0.1: PASS
```

This proves the Reference Agent public workflow does not depend on excluded private/internal files.

### Wheel/sdist build

Using the project development environment:

```text
geotask_core-0.3.0-py3-none-any.whl: built
geotask_core-0.3.0.tar.gz: built
release preflight with both artifacts: PASS
Schema Bundle distribution: 33 schemas, PASS
```

### Installed-wheel Reference Agent

A second fresh virtual environment installed **only the built wheel** (plus its declared PyYAML dependency). The Reference Agent script was then executed from the public export using the installed wheel as its `geotask_core` implementation:

```text
geotask inspect schemas: 32 registered Artifacts / 33 Schemas, PASS
Reference Agent success replay: PASS
Verification Quality Benchmark v0.1: PASS
```

This is the P2 interpretation of “Reference Agent runs from an installed package”: the example remains a public repository/example asset, while its GeoTask implementation dependency comes from the built wheel. The example is intentionally not bundled inside `geotask-core` wheel.

## 4. Upgrade path: 0.3.x → target 0.4.1

0.4.1 has not been published yet. Do not run a pinned `geotask-core==0.4.1` installation command until the release exists.

For release-candidate testing, install the candidate wheel explicitly:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install /path/to/geotask_core-0.4.1-py3-none-any.whl
geotask --help
geotask inspect schemas --format json
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

At the final published release, the equivalent upgrade command will be:

```bash
python -m pip install --upgrade geotask-core==0.4.1
```

but this line is documentation of the future release procedure, not evidence that 0.4.1 is currently available.

## 5. Public-name migration expectations

The target 0.4.1 release scope is governed by `p2-release-contract-freeze-v0.4.json`.

Expected non-breaking names include:

```text
PyPI: geotask-core
Python: geotask_core
CLI: geotask
14 current deterministic operator IDs
32 current registered Artifact IDs
18 current top-level CLI command names
```

A breaking rename requires an explicit migration entry before the freeze snapshot may be updated.

## 6. STIR compatibility

The older STIR migration rules remain in force:

- `stir` CLI remains a deprecated alias;
- old `stir` top-level YAML compatibility remains deprecated where supported;
- old Python helper aliases remain compatibility aliases where documented;
- the `stir_core` Python package path is **not** distributed;
- new integrations must use `geotask_core` and `geotask`.

0.4.1 preparation does not reintroduce STIR as a product name.

## 7. 0.3.x user migration checklist

For an existing `geotask-core` user:

1. preserve existing task/result/control Artifacts used for regression replay;
2. install the 0.4.1 candidate in a clean environment rather than over an uncontrolled development environment;
3. run `geotask --help` and Registry inspection;
4. validate stored public Artifacts with their registered Artifact IDs;
5. rerun representative deterministic tasks;
6. rerun any World State / Verification / Control bundles that the application depends on;
7. if using Agent integration, replay the public Reference Agent and confirm `eligible != executed` remains understood;
8. review `CHANGELOG.md` and this migration matrix for any explicit compatibility entry;
9. do not treat a new Artifact type as permission to mutate production state;
10. only then upgrade the application environment.

## 8. Release gate still outstanding

This matrix does **not** close the 0.4.1 release by itself. The machine-auditable companion gate is `core-0.4-rc-readiness-v0.1.md`, executed with `.release/verify_rc_readiness.py`; it must remain `pending` while final release evidence is incomplete. Before publication the project still needs:

- full CI evidence on Python 3.10, 3.11, 3.12 and 3.13 for the release candidate;
- final version/tag/date metadata update to 0.4.1;
- clean 0.4.1 wheel/sdist build;
- Schema Bundle verification on those exact 0.4.1 artifacts;
- release preflight against the final 0.4.1 artifacts;
- final public-export and Reference Agent replay;
- review of migration entries and release-scope naming freeze.

The matrix therefore turns “0.4.1 ready” into an evidence checklist rather than a calendar decision.
