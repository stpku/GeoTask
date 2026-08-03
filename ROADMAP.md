# GeoTask Public Roadmap

[简体中文](#中文路线图) | [English](#english-roadmap)

GeoTask follows an open, incremental roadmap. Items below describe public protocol, Core, tooling, and ecosystem directions; they are not promises of delivery dates.

## 中文路线图

### v0.1：公共预览 ✅

- 六类Canonical对象与六个本地确定性算子；
- YAML任务解析、规范化、结构验证与执行；
- 结果状态、Assurance和模型输出比较验证；
- Language Specification 1.0与JSON Schema 1.0；
- GT01—GT20渐进式应用案例；
- 中文项目门户、白皮书、Quickstart和Cookbook；
- Python 3.10—3.13持续集成与公共导出安全检查。

### v0.2.0：制品契约 ✅

- 公共Artifact Registry——Agent可在运行时发现四类注册制品；
- 离线Schema Bundle——五份公共JSON Schema及SHA-256 manifest随发行包分发；
- 统一制品校验入口——`geotask artifact validate`按Artifact ID分发验证；
- 验证报告自验证——报告自身作为注册制品可被再次校验，闭合信任环；
- 公共Python API——`geotask_core`与`geotask_core.v1`统一导出；
- 发布身份预检——版本溯源、Git标签、CHANGELOG、README导航与包元数据交叉核对。

### v0.3.0：Agent集成（当前稳定） 🏷️

- 发布模型无关的Agent Integration Profile，明确Agent、Core与Runtime职责边界；
- 提供`inspect_artifacts`、`validate_artifact`、`execute_task`和`evaluate_control`四类稳定工具契约；
- 提供可直接注入Agent的GeoTask Core Skill；
- 建立Agent生成草稿的严格校验、机械修复、结构化修订请求、差异约束重试、重新校验和本地执行闭环，并将四类Agent报告注册为可离线验证的公共Artifact；
- 完成GT08补证据、恢复条件求值和受影响断言重新执行闭环；
- 保持unknown、blocked和`next_action`的失败关闭语义；
- 增加Agent生成路径与确定性验证路径的联合测试。

### v0.4：Runtime接口、模型适配与对象扩展（进行中）

- 发布Runtime Interface Profile v0.1，定义Descriptor、Request、Response、输入基数、授权、幂等、审计及副作用边界；
- 提供Runtime Descriptor离线发现、Request无副作用预检和Descriptor/Request/Response三方交换校验；
- 提供仅执行只读Artifact验证的失败关闭参考Runtime，明确不调用模型、不解析外部证据、不执行生产动作；
- 提供至少两种模型适配参考实现；
- ✅ 已增加polygon、multi-polyline通用空间对象，以及point-in-polygon和multi-polyline/rect确定性算子；
- ✅ 已建立CRS、坐标顺序、水平/垂直单位和闭边界语义的跨任务失败关闭门禁；
- ✅ 已增加文档级来源、证据绑定与审计元数据，并通过Artifact Registry输出IDE Schema文件匹配；
- ✅ 已建立覆盖全部公共确定性算子的离线一致性与本机性能回归基准。

### v0.5：Verifiable World-State Cycle

- ✅ 已发布Observation v0.1 Artifact，使模型、传感器、地图、权威数据和人工输入以带来源、时间、生产者、不确定性和世界命题的结构化观察进入系统，同时明确不验证命题真实性、不更新World State；
- ✅ 已发布World State v0.1 Artifact，表达某一时刻版本化的世界对象、属性、关系、证据、有效时间和不确定状态，并提供严格引用闭包、快照时点有效性和确定性语义指纹校验；
- ✅ 已发布State Transition v0.1 Artifact，以前后World State语义指纹绑定快照，记录Observation支持的对象、属性、关系和行动资格变化，同时明确不自动计算差异、不应用补丁、不物化状态或授权行动；
- ✅ 已发布Verification Session v0.1 Artifact，绑定一个World State语义指纹与任务、执行结果、控制评估、State Transition及差异制品的精确字节哈希，记录行动资格与复核触发条件，同时明确不验证引用制品语义、不执行任务、控制或复核；
- ✅ 已发布Discrepancy Report v0.1 Artifact，绑定一个World State语义指纹与精确来源制品字节，记录差异类型、期望值/观测值、影响范围及可变/不可变修订路径，同时明确不自动比较来源、传播影响、生成修订请求或应用纠正；
- ✅ 已发布Correction Request v0.1 Artifact，绑定不可变基准World State与Discrepancy Report，限定后继状态允许变更、验收标准、不可变路径保护及输出/行动门禁，同时明确不原地修改快照、不应用修订、不物化后继状态或释放输出；
- ✅ 已发布Impact Graph v0.1 Artifact，将差异、修订、状态路径、断言、输出、动作和复核目标组织为来源绑定的有向无环图，并验证根可达性、无环性、精确文件绑定和关键边语义，同时明确不自动生成图、不执行传播或复核；
- ✅ 已发布Recompute Derivation Result v0.1 Artifact，将Correction Request中的每项`recompute`变更绑定到精确Observation/GeoTask Document路径，并通过有限白名单方法确定性生成完整重算值映射，同时明确不执行任意代码、模型调用、状态物化、复核或动作授权；
- ✅ 已发布受限后继World State物化与World State Materialization Result v0.1，将一个required Correction Request应用于不可变基准快照，绑定精确字节并保留来源、输出门禁和动作门禁；
- ✅ 已发布Incremental Reevaluation Result v0.1 Artifact，绑定基准/后继World State、Impact Graph、Correction Request、Discrepancy Report与执行结果的精确字节，完整记录节点/目标结果、验收条件、差异消解和输出/动作门禁，同时明确不执行复核、不生成后继状态、不授权或执行动作；
- 提供Observation合并以及`geotask verify`、`geotask recheck`高层命令，保持本地、显式、可复现的世界状态快照语义；
- 将GT21—GT28建设为Observation接入、世界状态构建、状态变化、影响传播、限定纠偏和行动门控案例。

### v0.6：Local Verification Providers与Domain Pack生态

- 发布统一Verification Provider Contract，覆盖确定性算子、规则引擎、本地预测模型、权威数据提供者和人工复核；
- 增加多维Assurance Profile，表达来源、方法、可重复性、独立性、证据新鲜度、校准与人工复核；
- 扩展trajectory、moving object及动态时空对象；
- 发布可复用的Domain Pack规范，并提供低空、机器人或交通方向的参考Pack；
- 建立验错率、漏检率、纠偏成功率、增量复核范围和执行时延基准；
- 支持社区维护的Provider、案例、算子和行业扩展目录。

## 参与方式

- 在[Issues](https://github.com/stpku/GeoTask/issues)提交Bug、算子建议或案例建议；
- 在[Discussions](https://github.com/stpku/GeoTask/discussions)讨论应用方式和协议演进；
- 从带有`good first issue`标签的任务开始贡献；
- 阅读[中文贡献指南](CONTRIBUTING.zh-CN.md)。

## English Roadmap

### v0.1: Public Preview ✅

- Six canonical object types and six deterministic local operators;
- YAML parsing, canonicalization, validation, and execution;
- result status, assurance metadata, and model-output comparison;
- Language Specification 1.0 and JSON Schema 1.0;
- GT01–GT20 progressive application cases;
- project portal, white paper, Quickstart, and Cookbook;
- CI on Python 3.10–3.13 and public-export safety checks.

### v0.2.0: Artifact Contracts ✅

- Public Artifact Registry — agents discover registered artifacts at runtime;
- Offline Schema Bundle — five public JSON Schemas distributed with SHA-256 manifest;
- Unified artifact validation — `geotask artifact validate` dispatches by Artifact ID;
- Self-validating reports — validation reports are registered artifacts, closing the trust loop;
- Public Python API — unified exports from `geotask_core` and `geotask_core.v1`;
- Release identity preflight — version source, tag, CHANGELOG, README, and metadata cross-check.

### v0.3.0: Agent Integration (current stable) 🏷️

- Publish a model-neutral Agent Integration Profile that separates Agent, Core, and Runtime responsibilities;
- expose stable contracts for `inspect_artifacts`, `validate_artifact`, `execute_task`, and `evaluate_control`;
- provide a directly injectable GeoTask Core Agent Skill;
- establish strict validation, mechanical repair, structured revision requests, guarded revision-diff retries, evidence-gated recovery, revalidation, and local execution for Agent-generated drafts, with four Agent reports registered as offline-verifiable public Artifacts;
- complete the GT08 evidence request, resume-condition evaluation, and affected-assertion re-execution loop;
- preserve fail-closed semantics for unknown, blocked outputs, and `next_action`;
- add joint tests for Agent generation paths and deterministic verification paths.

### v0.4: Runtime Interfaces, Model Adapters, and Object Extensions (in progress)

- Publish Runtime Interface Profile v0.1 for Descriptor, Request, Response, input cardinality, authorization, idempotency, audit, and side-effect boundaries;
- provide offline Runtime Descriptor discovery, side-effect-free Request preflight, and three-way Descriptor/Request/Response exchange validation;
- provide a fail-closed reference Runtime that performs only read-only Artifact validation and never calls a model, resolves external evidence, or executes production actions;
- provide a public-safe external HTTP JSON transport Adapter and paired loopback-only reference Endpoint outside Core, with offline Descriptor binding, strict Request/Response loading, and transport/operation failure separation;
- provide an independently buildable provider-neutral model Adapter package skeleton with a no-network Mock Provider, opaque authorization/audit mapping, registered input/output Artifact validation, and model-output truthfulness guards;
- provide the first provider-specific OpenAI Responses Adapter with externally injected authenticated client, one no-retry strict Structured Outputs call, disabled storage/tools, audit binding, and fully offline contract tests;
- add a second provider-specific model Adapter only after installed-package compatibility and one explicitly authorized live smoke test are stable;
- ✅ Added polygon and multi-polyline objects plus deterministic point-in-polygon and multi-polyline/rectangle operators;
- ✅ Added fail-closed cross-task gates for CRS, coordinate order, horizontal/vertical units, and closed-boundary semantics;
- ✅ Added document-level source, evidence-binding, and audit metadata plus Artifact Registry IDE Schema file mappings;
- ✅ Established an offline conformance and local performance-regression benchmark covering every public deterministic operator.

### v0.5: Verifiable World-State Cycle

- ✅ Published Observation v0.1 so models, sensors, maps, authoritative data, and humans enter the system as structured observations with source, time, producer identity, uncertainty, and world claims, while explicitly not verifying claim truth or updating a World State;
- ✅ Published World State v0.1 for versioned objects, attributes, relations, evidence, validity time, and uncertainty at one snapshot, with strict reference closure, as-of validity, and deterministic semantic fingerprints;
- ✅ Published State Transition v0.1, binding before/after World State snapshots by semantic fingerprint and recording Observation-supported object, attribute, relation, and action-eligibility changes, while explicitly not calculating diffs, applying patches, materializing state, or authorizing action;
- ✅ Published Verification Session v0.1, binding one World State semantic fingerprint to exact-byte task, execution-result, control-evaluation, State Transition, and discrepancy references plus action eligibility and recheck triggers, while explicitly not validating linked artifact semantics or executing tasks, controls, or rechecks;
- ✅ Published Discrepancy Report v0.1, binding one World State semantic fingerprint to exact source-artifact bytes and recording discrepancy kind, expected/observed values, downstream impact, and mutable/immutable correction paths, while explicitly not comparing sources, propagating impact, creating correction requests, or applying corrections;
- ✅ Published Correction Request v0.1, binding one immutable base World State to exact Discrepancy Reports and constraining successor-state changes, acceptance criteria, immutable-path preservation, and output/action gates while explicitly not editing snapshots, applying changes, materializing successors, or releasing outputs;
- ✅ Published Impact Graph v0.1, representing discrepancies, corrections, state paths, assertions, outputs, actions, and reevaluation targets as a source-bound directed acyclic graph with root reachability, exact-byte bindings, and key edge-semantic checks, while explicitly not discovering the graph or executing propagation or reevaluation;
- ✅ Published bounded successor-World-State materialization and World State Materialization Result v0.1, applying one required Correction Request to one immutable base snapshot with exact-byte bindings and explicit recompute values while preserving provenance, output gates, and action gates;
- ✅ Published Recompute Derivation Result v0.1, binding exact World State, Correction Request, Observation, and GeoTask Document bytes and deriving every requested `recompute` value through small allowlisted deterministic methods, without arbitrary code, model calls, state mutation, reevaluation, release, or action authorization;
- ✅ Published Incremental Reevaluation Result v0.1, binding exact base/successor World States, Impact Graph, Correction Requests, Discrepancy Reports, and execution results while closing graph-node, target, acceptance, discrepancy-resolution, output-gate, and action-eligibility outcomes without executing reevaluation, generating successors, authorizing actions, or executing actions;
- expand the bounded derivation method registry, provide Observation merging, and add high-level `geotask verify` and `geotask recheck` commands with explicit, local, reproducible snapshot semantics;
- build GT21–GT28 around Observation ingestion, world-state construction, state change, impact propagation, bounded correction, and action gating.

### v0.6: Local Verification Providers and Domain Pack Ecosystem

- Publish a common Verification Provider Contract for deterministic operators, rule engines, local predictive models, authoritative data providers, and human review;
- add a multidimensional Assurance Profile for source, method, reproducibility, independence, evidence freshness, calibration, and human review;
- extend trajectory, moving-object, and dynamic spatiotemporal object contracts;
- publish a reusable Domain Pack specification with reference low-altitude, robotics, or transportation Packs;
- establish benchmarks for error-detection rate, missed errors, correction success, incremental scope, and execution latency;
- support community-maintained catalogs of Providers, cases, operators, and domain extensions.
