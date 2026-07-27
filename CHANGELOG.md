# Changelog

## 0.2.0-dev

- Add GeoTask Normalizer v0.2 with enhanced extraction (CN/EN/YAML/Markdown).
- Add local Verifier for normalized model outputs.
- Add verified / contradicted / need_review statuses.
- Add CLI --geotask flag for normalize command.
- Add model output examples (DeepSeek CN, GPT YAML-like, Markdown, error cases).
- Add result_schema.py with status constants and builder functions.
- Add docs: normalizer_v0_2_design.md, patent_normalizer_disclosure.md.

- Add GeoTask White Paper v0.1 and a public documentation index.
- Add the implemented GeoTask Language and Execution Specification v1.0.
- Add a Draft 2020-12 JSON Schema, Quickstart, status/evidence references, and GT01–GT13 Cookbook.
- Add documentation conformance tests and public-export requirements for the specification set.
- Restore a Chinese-first GitHub entry point with a full English mirror, localized Quickstart/Cookbook, bilingual contribution guidance, and community templates.
- Extend public-export checks to require localized entry points, reject obsolete repository URLs, and validate every public Markdown relative link.
- Replace the former GT01 root page with a Chinese project portal covering architecture, GT01–GT13, documentation, public boundaries, and contribution entry points.
- Move GT01 to `site/gt01/`, add project-home navigation to every case, and publish canonical metadata, `robots.txt`, and `sitemap.xml`.
- Make public-manifest documentation checks consistent across Python 3.10–3.13 and upgrade official GitHub Actions to their Node 24 major versions.
- Preserve GitHub-side Markdown formatting improvements in the development source so future public exports do not overwrite them.

## 0.1.0

- Rename project from STIR to GeoTask.
- Rename Python package from `stir_core` to `geotask_core`.
- Rename primary CLI from `stir` to `geotask`.
- Rename top-level YAML field from `stir:` to `geotask:`.
- Add deprecated compatibility for old `stir` YAML top-level field.
- Add deprecated compatibility for old `stir` CLI command.
- Add deprecated compatibility aliases for old Python function names.
- Add migration guide (MIGRATION.md).
- Add repository migration documentation (docs/repository_migration.md).
- Add remote migration helper script (scripts/migrate_remote_to_geotask.sh).
- Update all docs, examples, tests, and configs to GeoTask branding.
