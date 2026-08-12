# GeoTask Core — Public Release Pipeline

Tools for exporting, verifying, and scanning a public release of GeoTask Core.

## Files

| File | Purpose |
|------|---------|
| `public-manifest.yaml` | Central manifest — include/exclude/required/forbidden rules |
| `export_public.py` | Copies Git-tracked, explicitly whitelisted public files to an output directory per manifest; untracked workspace files are never export candidates |
| `verify_public_export.py` | Checks whitelist, required files, internal imports |
| `verify_release_preflight.py` | Verifies version, date, tag text, release notes, Quickstarts, and optional wheel/sdist metadata |
| `verify_rc_readiness.py` | Audits 0.4 RC readiness across source identity, Python CI configuration/executed evidence, final distributions, public export, Reference Agent replay, and Promotion Gate boundaries without side effects |
| `collect_rc_evidence.py` | Generates fail-closed RC evidence shards from an exact clean target-version commit and merges same-commit Python CI shards; handwritten `passed` evidence is not accepted by the RC auditor |
| `core-baseline-manifest.yaml` | Closed-set declaration of the current Core/governance pre-RC batch plus explicit Integration/internal exclusions; any dirty path without a rule is a hard failure |
| `plan_core_baseline.py` | Classifies the real dirty workspace against the closed set, binds each Core path to HEAD and a SHA-256 content digest, and can write an exact staging pathspec without touching the Git index |
| `verify_core_commit_scope.py` | Verifies the staged Core/governance commit scope and, when given a generated baseline plan, requires exact path/HEAD/blob-hash equality while rejecting Integration-owned paths |
| `verify_schema_distribution.py` | Verifies wheel/sdist Schema Bundle manifests, digests, source parity, and CLI entry point |
| `scan_public_export.py` | Scans for secrets, internal paths, binary files |
| `scan_public_identity.py` | Fail-closed scan for source-private employer/internal identity markers using public-safe hashes; matched identifiers are never echoed |
| `hash_public_export.py` | Generates and verifies cross-platform SHA-256 manifests with UTF-8 text normalized to LF |
| `release_public.py` | Full pipeline: boundary check → export → verify → scan → protected-identity scan → hash |

## Quick Start

```bash
# Full pipeline (creates a public release outside the project tree)
python .release/release_public.py ../geotask-public-v1.0 --clean --report

# Dry-run to preview what would be exported
python .release/release_public.py ../geotask-public-v1.0 --dry-run

# Just export (without verification or scan)
python .release/export_public.py ../geotask-public-v1.0 --clean

# Verify an existing export
python .release/verify_public_export.py ../geotask-public-v1.0

# Verify source release identity before building
python .release/verify_release_preflight.py --expected-version 0.2.0

# Verify built wheel and sdist against release metadata
python .release/verify_release_preflight.py --expected-version 0.2.0 --expected-tag v0.2.0 --artifacts dist --format json

# Verify the built Schema Bundle
python .release/verify_schema_distribution.py dist --format json

# Build the exact Core baseline plan from the mixed dirty workspace. Any unclassified dirty path fails.
python .release/plan_core_baseline.py --output /tmp/geotask-core-baseline-plan.json --write-pathspec /tmp/geotask-core-baseline.pathspec

# A local executor may then stage ONLY that pathspec. After staging, bind the real index back to the plan:
# paths, HEAD and every staged blob SHA-256 must match exactly; the verifier never changes the index itself.
python .release/verify_core_commit_scope.py --baseline-plan /tmp/geotask-core-baseline-plan.json --format json

# Audit 0.4.1 RC readiness. Before the version bump/final evidence this intentionally exits 2 (pending).
python .release/verify_rc_readiness.py --target-version 0.4.1 --format json

# Generate one evidence shard from the exact clean RC. --record-python-ci only
# marks the current Python minor passed when CI=true and the full pytest suite reruns successfully.
python .release/collect_rc_evidence.py collect --target-version 0.4.1 --artifacts dist --public-export /tmp/geotask-public-rc --reference-python /path/to/installed/python --record-python-ci --output rc-evidence-3.13.json

# Merge generated shards from 3.10/3.11/3.12/3.13. Versions, commit and artifact hashes must match.
python .release/collect_rc_evidence.py merge rc-evidence-3.10.json rc-evidence-3.11.json rc-evidence-3.12.json rc-evidence-3.13.json --output rc-evidence.json

# Final RC audit after exact artifacts and machine-generated executed evidence exist.
python .release/verify_rc_readiness.py --target-version 0.4.1 --artifacts dist --evidence /path/to/rc-evidence.json --format json

# PyPI workflow dispatch: select the default branch (main) and enter version 0.2.0.
# The workflow checks out tag v0.2.0 and verifies HEAD before package build/upload.

# Scan for secrets/internal paths and then protected identity markers
python .release/scan_public_export.py ../geotask-public-v1.0
python .release/scan_public_identity.py ../geotask-public-v1.0
```

## Pipeline Stages

1. **Boundary Check** — Confirms forbidden paths are not exported (they may exist in
   the source tree but are excluded by manifest rules).

2. **Export** — Reads `public-manifest.yaml` and copies all include-matched files
   to the output directory, respecting exclude patterns and checking forbidden paths.

3. **Verify** — Ensures:
   - Every exported file matches a whitelist pattern
   - All required files (README.md, LICENSE, pyproject.toml, etc.) exist
   - No forbidden paths are present
   - Core source does not import internal modules

4. **Scan** — Scans for:
   - API keys, tokens, passwords, private keys
   - Internal paths (Windows `C:` disk, Linux `/` home dirs)
   - Binary files

5. **Protected Identity Scan** — Rejects source-private employer/internal identity markers before public distribution. Public code stores only protected hashes, the source-private plaintext denylist is excluded from export, and findings never echo the matched identifier.

6. **Hash** — Generates and verifies one SHA-256 manifest. UTF-8 text is
   normalized to LF before hashing, while binary and non-UTF-8 files retain
   their original bytes, so Windows and Linux checkouts verify identically.

## Manifest Rules

Edit `public-manifest.yaml` to adjust what is included or excluded:

- **include**: Glob patterns for files to export
- **exclude**: Glob patterns to suppress (applied after include)
- **required**: Files that must exist (error if missing)
- **forbidden_paths**: Paths that must not appear (error if present)
- **forbidden_content_patterns**: Regex patterns for sensitive content
- **boundary_rules**: Import rules that Core must respect
- **exact_exceptions**: Specific files allowed to bypass certain rules

## Requirements

- Python 3.10+
- PyYAML (same as GeoTask Core)

No network access, no heavy dependencies.
