# GeoTask Core v0.1.0 Public Preview

> **Superseded by v0.1.1.** The 0.1.0 distribution metadata was correct, but `geotask_core.__version__` incorrectly reported `0.2.0`. CLI installation, validation, and deterministic execution were unaffected. Install `geotask-core>=0.1.1` for consistent version reporting.

- **Release date:** 2026-07-27
- **Git tag:** `v0.1.0-public-preview`
- **Package version:** `0.1.0`
- **Document Schema:** `1.0`

[中文说明](#中文发布说明) | [English notes](#english-release-notes)

## 中文发布说明

GeoTask Core v0.1.0 Public Preview是GeoTask首个可引用、可下载、可运行的公共预览版本。

GeoTask面向AI智能体提供一套可验证时空任务协议：模型负责理解任务并提出候选对象、断言和动作；GeoTask Core负责解析、规范化、验证引用，并通过本地确定性算子复算结果。模型生成的答案不会被直接当作已经验证的结论。

### 本次发布包含

- 六类Canonical对象：`point`、`polyline`、`rect`、`time_interval`、`altitude_interval`、`feature_collection`；
- 六个本地确定性算子：
  - `distance_2d`
  - `line_intersects_rect`
  - `point_to_line_distance_2d`
  - `rect_contains_point`
  - `time_overlap`
  - `altitude_overlap`
- YAML任务解析、Canonical IR、结构验证和确定性执行；
- 结构化结果、ClaimStatus、来源与Assurance元数据；
- 模型输出Normalizer与本地Verifier；
- `geotask validate`、`geotask run`、`geotask inspect`等CLI能力；
- GeoTask Language and Execution Specification 1.0；
- Draft 2020-12 JSON Schema；
- GT01—GT13渐进式应用案例，覆盖空间关系、时空组合、证据治理、机器人协同、无人机能源余量和车辆安全包络；
- 中文项目门户、白皮书、Quickstart、Cookbook、贡献指南和社区模板；
- Python 3.10、3.11、3.12和3.13持续集成；
- 公共导出白名单、敏感信息扫描和架构边界检查。

### 快速开始

优先从[PyPI](https://pypi.org/project/geotask-core/)安装正式发布包：

```bash
python -m pip install geotask-core
geotask --help
geotask inspect operators
```

参与源码开发时，再按照贡献指南使用`python -m pip install -e ".[dev]"`。

### 发布资产

- PyPI项目：[`geotask-core`](https://pypi.org/project/geotask-core/)；
- GitHub Release中的Python wheel：`geotask_core-0.1.0-py3-none-any.whl`；
- Source distribution：`geotask_core-0.1.0.tar.gz`；
- GitHub自动生成的源代码归档；
- 本发布说明和固定版本Tag。

### 验证状态

- 公共仓库测试：336项通过；
- Python 3.10—3.13 CI：全部通过；
- GitHub Pages门户与GT01—GT13：全部上线；
- Secret Scanning与Push Protection：已启用；
- 公共导出扫描：未发现密钥、内部路径或二进制泄露；
- PyPI隔离环境验证：`geotask-core==0.1.0`安装成功，CLI帮助、算子检查、发行版本、最小案例验证与执行全部通过。

### 当前定位

本版本是Public Preview，而不是稳定的1.0产品版本。当前重点是验证协议表达、确定性执行、模型结果比较、公开案例和开发者体验。未来路线见[`ROADMAP.md`](../ROADMAP.md)。

### 兼容性

项目早期名称为STIR。为降低迁移成本，本版本仍保留部分`stir`字段、CLI和函数兼容入口，但新项目应统一使用GeoTask命名。详见[`MIGRATION.md`](../MIGRATION.md)。

### 引用

研究论文、技术报告和软件项目可使用仓库根目录的[`CITATION.cff`](../CITATION.cff)生成推荐引用格式。

## English Release Notes

GeoTask Core v0.1.0 Public Preview is the first citable, downloadable, and runnable public preview of GeoTask.

GeoTask provides a verifiable spatiotemporal task protocol for AI agents. Models propose objects, assertions, explanations, and candidate actions. GeoTask Core parses and canonicalizes the task, validates references and operator contracts, and recomputes supported claims with deterministic local operators.

### Included in this release

- six canonical object types: `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`, and `feature_collection`;
- six deterministic local operators: `distance_2d`, `line_intersects_rect`, `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, and `altitude_overlap`;
- YAML parsing, Canonical IR, structural validation, and deterministic execution;
- structured results, claim status, source, and assurance metadata;
- model-output normalization and local verification;
- CLI commands including `geotask validate`, `geotask run`, and `geotask inspect`;
- GeoTask Language and Execution Specification 1.0;
- a Draft 2020-12 JSON Schema;
- GT01–GT13 progressive cases covering spatial relations, spatiotemporal composition, evidence governance, robot coordination, UAV energy reserve, and vehicle clearance envelopes;
- a project portal, white paper, Quickstart, Cookbook, contributor guides, and community templates;
- CI on Python 3.10 through 3.13;
- public-export allowlisting, secret scanning, and architecture-boundary checks.

### Quickstart

Install the published package from [PyPI](https://pypi.org/project/geotask-core/):

```bash
python -m pip install geotask-core
geotask --help
geotask inspect operators
```

Use `python -m pip install -e ".[dev]"` only when contributing to source development.

### Release assets

The package is available as [`geotask-core` on PyPI](https://pypi.org/project/geotask-core/). The GitHub Release also includes the Python wheel, source distribution, GitHub source archives, these release notes, and an immutable version tag.

### Verification

A clean virtual environment successfully installed `geotask-core==0.1.0` without cache. CLI help, operator inspection, distribution-version lookup, validation, and the minimal deterministic execution case all passed.

### Status

This is a Public Preview rather than a stable 1.0 product release. The current focus is protocol representation, deterministic execution, model-result comparison, public application cases, and developer experience. See [`ROADMAP.md`](../ROADMAP.md) for planned public directions.
