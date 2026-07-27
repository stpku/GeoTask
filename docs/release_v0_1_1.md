# GeoTask Core v0.1.1 PyPI Hotfix

- **Release date:** 2026-07-27
- **Git tag:** `v0.1.1`
- **Package version:** `0.1.1`
- **Document Schema:** `1.0`

## 中文发布说明

GeoTask Core v0.1.1是首个PyPI发布后的补丁版本，不改变任务语法、算子行为或公共API。

0.1.0在PyPI中的发行元数据正确标记为`0.1.0`，但模块内部的`geotask_core.__version__`错误返回`0.2.0`。v0.1.1将版本号收敛到`src/geotask_core/_version.py`，构建元数据和运行时导出均读取同一来源。

```bash
python -m pip install --no-cache-dir geotask-core==0.1.1
python -c "from importlib.metadata import version; import geotask_core; print(version('geotask-core')); print(geotask_core.__version__)"
```

两行都应输出`0.1.1`。

验证结果：完整源仓`765 passed, 1 skipped`，公共导出仓`337 passed`，Wheel与sdist均通过Twine检查。

## English release notes

GeoTask Core v0.1.1 is a post-PyPI patch release with no task-syntax, operator-behavior, or public-API changes.

The 0.1.0 distribution metadata correctly reported `0.1.0`, while `geotask_core.__version__` incorrectly returned `0.2.0`. Version 0.1.1 introduces one version source in `src/geotask_core/_version.py`; both build metadata and runtime exports read from it.

```bash
python -m pip install --no-cache-dir geotask-core==0.1.1
python -c "from importlib.metadata import version; import geotask_core; print(version('geotask-core')); print(geotask_core.__version__)"
```

Both lines should print `0.1.1`.

Verification: `765 passed, 1 skipped` in the full source repository, `337 passed` in the public export, and both wheel and sdist passed Twine checks.
