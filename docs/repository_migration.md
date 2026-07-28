# Repository Migration: STIR → GeoTask

## Summary

STIR was the original prototype name. The project has been renamed to
**GeoTask** to better communicate its purpose: representing spatial tasks
for LLMs.

## Migration Map

| Element             | Old (STIR)                          | New (GeoTask)                            |
|---------------------|-------------------------------------|------------------------------------------|
| Project name        | STIR / STIR-Core                    | GeoTask / GeoTask Core                   |
| Python package      | `stir_core`                         | `geotask_core`                           |
| PyPI package        | `stir-core`                         | `geotask-core`                           |
| Primary CLI         | `stir`                              | `geotask`                                |
| Top-level YAML key  | `stir:`                             | `geotask:`                               |
| Repository          | `gitee.com/stpku/stir`              | `gitee.com/stpku/GeoTask`                |
| Example file        | `examples/stir_core_lite.yaml`      | `examples/geotask_core_lite.yaml`        |
| Source directory    | `src/stir_core/`                    | `src/geotask_core/`                      |
| Python imports      | `from stir_core import ...`         | `from geotask_core import ...`           |

## Compatibility Strategy

**Backward compatibility is maintained for one version:**

1. **Old `stir` YAML field**: Parser accepts `stir:` as a deprecated alias for
   `geotask:`. A deprecation warning is emitted via stderr.

2. **Old CLI command**: `stir` command still works as an alias for `geotask`.
   A deprecation warning is emitted via stderr.

3. **Old Python functions**: `load_stir`, `validate_stir`, `run_stir` remain as
   aliases for `load_geotask`, `validate_geotask`, `run_geotask`.

4. **Old examples**: `examples/stir_core_lite.yaml` is kept alongside the new
   `examples/geotask_core_lite.yaml` for transitional reference.

These deprecated entries will be removed in a future version.

## Remote Repository Migration

```bash
# 1. Rename old origin to preserve it
git remote rename origin stir-origin

# 2. Add new remote
git remote add origin https://gitee.com/stpku/GeoTask.git

# 3. Push the migration branch
git push origin rename/geotask

# 4. Or push directly to main after review
# git push origin main
```

For public checkouts, update the remote directly with `git remote set-url origin https://gitee.com/stpku/GeoTask.git` and verify it with `git remote -v`.

## Dependency Changes

None. GeoTask Core has the same minimal dependencies as STIR-Core:
- Python >= 3.10
- PyYAML >= 6.0
- pytest >= 7.0 (dev only)
