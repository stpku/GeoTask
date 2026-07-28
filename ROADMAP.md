# GeoTask Public Roadmap

[简体中文](#中文路线图) | [English](#english-roadmap)

GeoTask follows an open, incremental roadmap. Items below describe public protocol, Core, tooling, and ecosystem directions; they are not promises of delivery dates.

## 中文路线图

### v0.1：公共预览（当前）

- 六类Canonical对象与六个本地确定性算子；
- YAML任务解析、规范化、结构验证与执行；
- 结果状态、Assurance和模型输出比较验证；
- Language Specification 1.0与JSON Schema 1.0；
- GT01—GT15渐进式应用案例；
- 中文项目门户、白皮书、Quickstart和Cookbook；
- Python 3.10—3.13持续集成与公共导出安全检查。

### v0.2：扩展空间对象与开发体验

- 增加polygon、multi-polyline等通用空间对象；
- 明确CRS、单位和边界语义的跨任务约束；
- 增加更多可组合确定性算子；
- 提供更完整的IDE Schema映射与编辑器示例；
- 建立公共算子一致性与性能基准；
- 扩充`good first issue`和贡献者文档。

### v0.3：Runtime接口与模型适配

- 发布稳定的Runtime接口约定；
- 提供至少两种模型适配参考实现；
- 增加结构化任务生成、结果比较和重试示例；
- 完善来源、证据和审计元数据接口；
- 建立模型生成路径与确定性验证路径的联合评测。

### v0.4：Domain Pack规范与生态

- 发布可复用的Domain Pack规范；
- 提供机器人、低空或交通方向的参考Pack；
- 增加数据连接器、规则包与工作流扩展点；
- 建立Pack兼容性检查和版本协商机制；
- 支持社区维护的案例、算子和行业扩展目录。

## 参与方式

- 在[Issues](https://github.com/stpku/GeoTask/issues)提交Bug、算子建议或案例建议；
- 在[Discussions](https://github.com/stpku/GeoTask/discussions)讨论应用方式和协议演进；
- 从带有`good first issue`标签的任务开始贡献；
- 阅读[中文贡献指南](CONTRIBUTING.zh-CN.md)。

## English Roadmap

### v0.1: Public Preview (current)

- Six canonical object types and six deterministic local operators;
- YAML parsing, canonicalization, validation, and execution;
- result status, assurance metadata, and model-output comparison;
- Language Specification 1.0 and JSON Schema 1.0;
- GT01–GT15 progressive application cases;
- project portal, white paper, Quickstart, and Cookbook;
- CI on Python 3.10–3.13 and public-export safety checks.

### v0.2: Extended Spatial Objects and Developer Experience

- Add common objects such as polygon and multi-polyline;
- define CRS, units, and boundary semantics across tasks;
- add more composable deterministic operators;
- provide editor and IDE Schema examples;
- establish public conformance and performance benchmarks;
- expand newcomer-friendly issues and contributor documentation.

### v0.3: Runtime Interfaces and Model Adapters

- Publish stable Runtime interface contracts;
- provide at least two reference model adapters;
- add structured generation, comparison, retry, and recovery examples;
- improve provenance, evidence, and audit metadata interfaces;
- evaluate model-generation and deterministic-verification paths together.

### v0.4: Domain Pack Specification and Ecosystem

- Publish a reusable Domain Pack specification;
- provide reference Packs for robotics, low-altitude, or transportation use cases;
- add extension points for connectors, rules, and workflows;
- establish Pack compatibility checks and version negotiation;
- support a community-maintained catalog of cases, operators, and domain extensions.
