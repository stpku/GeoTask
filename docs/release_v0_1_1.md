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

验证结果：完整源仓`766 passed, 1 skipped`，公共导出仓`338 passed`；公共发布流水线的导出、验证、敏感扫描、哈希生成与哈希校验全部通过；Wheel与sdist均通过Twine检查；全新环境安装本地Wheel后，发行元数据与模块版本均为`0.1.1`，CLI和最小确定性案例通过。

## English release notes

GeoTask Core v0.1.1 is a post-PyPI patch release with no task-syntax, operator-behavior, or public-API changes.

The 0.1.0 distribution metadata correctly reported `0.1.0`, while `geotask_core.__version__` incorrectly returned `0.2.0`. Version 0.1.1 introduces one version source in `src/geotask_core/_version.py`; both build metadata and runtime exports read from it.

```bash
python -m pip install --no-cache-dir geotask-core==0.1.1
python -c "from importlib.metadata import version; import geotask_core; print(version('geotask-core')); print(geotask_core.__version__)"
```

Both lines should print `0.1.1`.

Verification: `766 passed, 1 skipped` in the full source repository and `338 passed` in the public export. Export, verification, sensitive scanning, hash generation, and hash verification all passed. Both wheel and sdist passed Twine checks. A clean local-wheel installation reported `0.1.1` from both distribution metadata and `geotask_core.__version__`; CLI and minimal deterministic execution also passed.
