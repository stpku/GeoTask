# Migrating from STIR to GeoTask

> **0.4.0 release status:** GeoTask Core 0.4.0 was released on 2026-08-08. The installation/upgrade evidence matrix is maintained at `docs/reference/install-migration-matrix-v0.4.md`; it distinguishes declared Python support, CI-configured coverage, and clean-room evidence executed during P2 hardening and release verification.

STIR was the prototype name. GeoTask is the new project name.

## Python imports

Before:

```python
from stir_core.parser import load_stir
```

After:

```python
from geotask_core.parser import load_geotask
```

## CLI

Before:

```bash
stir run examples/stir_core_lite.yaml
```

After:

```bash
geotask run examples/geotask_core_lite.yaml
```

## YAML top-level field

Before:

```yaml
stir:
  version: "0.1-lite"
```

After:

```yaml
geotask:
  version: "0.1-lite"
```

## Package name

Before:

```toml
[project]
name = "stir-core"
```

After:

```toml
[project]
name = "geotask-core"
```

## Compatibility

The old `stir` CLI command and `stir` top-level YAML field are temporarily
supported but deprecated. A deprecation warning is emitted via stderr when
using them.

The old Python function names (`load_stir`, `validate_stir`, `run_stir`)
remain as aliases for the new names (`load_geotask`, `validate_geotask`,
`run_geotask`). The old `stir_core` Python package path is not distributed;
update imports to use `geotask_core`.

## Remote Repository

Before:

```
https://gitee.com/stpku/stir.git
```

After:

```
https://gitee.com/stpku/GeoTask.git
```

Update the remote directly with `git remote set-url origin https://gitee.com/stpku/GeoTask.git`, then verify it with `git remote -v`.
