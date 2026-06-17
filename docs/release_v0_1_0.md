# GeoTask Core v0.1.0 Release Notes

## Version Statement

GeoTask Core v0.1.0 demonstrates that LLMs can read a lightweight spatial task
representation, perform basic spatial measurement and topology judgment, and
that local deterministic operators can verify these results.

> GeoTask Core v0.1.0 证明了：大模型可以读取轻量空间任务表达，完成基础空间量算与
> 拓扑判断；本地确定性算子可以验证结果；Normalizer 可以处理模型输出格式不稳定的问题。

---

## Included

| Component               | Description                                              |
|-------------------------|----------------------------------------------------------|
| Format spec             | YAML schema with `geotask`, `space`, `objects`, `ops`, `task` |
| Object types            | `point`, `line` (segment), `rect` (axis-aligned)         |
| Operators               | `distance_2d`, `line_intersects_rect`                    |
| Parser                  | YAML loader + validator with backward compat for `stir:` |
| Runner                  | Auto-detection for takeoff-school distance and route-zone intersection |
| Normalizer (lite)       | Extract distance, intersection, operator mentions from LLM text |
| Evaluator (lite)        | 100-point scoring rubric comparing Core vs LLM output    |
| CLI                     | `geotask validate/run/normalize/eval`                    |
| Examples                | 5 example files including main and edge cases            |
| Tests                   | 57 tests covering parser, ops, runner, normalizer, evaluator |
| Docs                    | Design principles, format spec, open source boundary, patent boundary, migration |
| Migration tools         | MIGRATION.md, repository_migration.md, migrate_remote script |

## Not Included

| Component                   | Reason                                          |
|-----------------------------|-------------------------------------------------|
| GeoTask UAV complex rules   | Domain-specific; belongs in rule pack           |
| source_refs / provenance    | Heavy audit; belongs in GeoTask Audit            |
| audit workflow              | Not a Core concern                              |
| PostGIS / Shapely / GDAL    | Heavy dependencies; Core must stay lightweight  |
| Real map / airspace data    | Not open source                                 |
| Business workflow           | Platform-level concern                          |
| 3D coordinates / polygons   | Planned for future versions                     |
| Multi-segment polylines     | Planned for future versions                     |
| Task chaining               | Planned for future versions                     |
| Unit conversion             | Planned for future versions                     |

## Migration from STIR

This release represents the rename from STIR to GeoTask:

- Package: `stir_core` → `geotask_core`
- CLI: `stir` → `geotask` (old alias preserved)
- YAML field: `stir:` → `geotask:` (old field accepted)
- Repository: `gitee.com/stpku/stir` → `gitee.com/stpku/GeoTask`

See [MIGRATION.md](../MIGRATION.md) for detailed migration guidance.

## Dependencies

- Python >= 3.10
- PyYAML >= 6.0
- pytest >= 7.0 (dev only)

## License

MIT License. Patent rights retained separately for the underlying system and method.
See [docs/patent_boundary.md](patent_boundary.md).
