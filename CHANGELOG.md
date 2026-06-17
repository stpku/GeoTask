# Changelog

## 0.2.0-dev

- Add GeoTask Normalizer v0.2 with enhanced extraction (CN/EN/YAML/Markdown).
- Add local Verifier for normalized model outputs.
- Add verified / contradicted / need_review statuses.
- Add CLI --geotask flag for normalize command.
- Add model output examples (DeepSeek CN, GPT YAML-like, Markdown, error cases).
- Add result_schema.py with status constants and builder functions.
- Add docs: normalizer_v0_2_design.md, patent_normalizer_disclosure.md.

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
