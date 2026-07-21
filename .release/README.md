# GeoTask Core — Public Release Pipeline

Tools for exporting, verifying, and scanning a public release of GeoTask Core.

## Files

| File | Purpose |
|------|---------|
| `public-manifest.yaml` | Central manifest — include/exclude/required/forbidden rules |
| `export_public.py` | Copies public files to an output directory per manifest |
| `verify_public_export.py` | Checks whitelist, required files, internal imports |
| `scan_public_export.py` | Scans for secrets, internal paths, binary files |
| `release_public.py` | Full pipeline: boundary check → export → verify → scan |

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

# Scan for secrets and internal paths
python .release/scan_public_export.py ../geotask-public-v1.0
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
