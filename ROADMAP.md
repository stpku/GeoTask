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
- ✅ 已发布Observation Merge Result v0.1 Artifact，将精确Observation字节按完整显式映射写入既有属性或关系；当多条命题指向同一目标时，仅接受调用方声明的语义相等合并或完整显式优先级，并记录全部参与命题的`applied`、`consolidated`或`superseded`审计状态，确定性生成后继World State，同时明确不推断对象身份、不发明优先级、不排序来源、不解决未声明策略的歧义冲突或计算State Transition；
- ✅ 已发布State Transition v0.1 Artifact，以前后World State语义指纹绑定快照，记录Observation支持的对象、属性、关系和行动资格变化，同时明确不自动计算差异、不应用补丁、不物化状态或授权行动；
- ✅ 已发布Verification Session v0.1 Artifact，绑定一个World State语义指纹与任务、执行结果、控制评估、State Transition及差异制品的精确字节哈希，记录行动资格与复核触发条件，同时明确不验证引用制品语义、不执行任务、控制或复核；
- ✅ 已发布Discrepancy Report v0.1 Artifact，绑定一个World State语义指纹与精确来源制品字节，记录差异类型、期望值/观测值、影响范围及可变/不可变修订路径，同时明确不自动比较来源、传播影响、生成修订请求或应用纠正；
- ✅ 已发布Correction Request v0.1 Artifact，绑定不可变基准World State与Discrepancy Report，限定后继状态允许变更、验收标准、不可变路径保护及输出/行动门禁，同时明确不原地修改快照、不应用修订、不物化后继状态或释放输出；
- ✅ 已发布Impact Graph v0.1 Artifact，将差异、修订、状态路径、断言、输出、动作和复核目标组织为来源绑定的有向无环图，并验证根可达性、无环性、精确文件绑定和关键边语义，同时明确不自动生成图、不执行传播或复核；
- ✅ 已发布Recompute Derivation Result v0.1 Artifact，将Correction Request中的每项`recompute`变更绑定到精确Observation/GeoTask Document路径，并通过有限白名单方法确定性生成完整重算值映射，同时明确不执行任意代码、模型调用、状态物化、复核或动作授权；
- ✅ 已发布受限后继World State物化与World State Materialization Result v0.1，将一个required Correction Request应用于不可变基准快照，绑定精确字节并保留来源、输出门禁和动作门禁；
- ✅ 已发布Incremental Reevaluation Result v0.1 Artifact，绑定基准/后继World State、Impact Graph、Correction Request、Discrepancy Report与执行结果的精确字节，完整记录节点/目标结果、验收条件、差异消解和输出/动作门禁，同时明确不执行复核、不生成后继状态、不授权或执行动作；
- ✅ 已提供`geotask verify`与`geotask recheck`高层只读入口，对完整显式Verification Session或Incremental Reevaluation Result制品束执行注册制品语义校验、精确引用覆盖和SHA-256绑定验证，同时明确不执行任务、复核、状态物化、输出释放或动作；
- 扩展受限Observation Merge的对象身份发现与未声明歧义冲突策略，并扩展重算推导方法注册表，保持本地、显式、可复现的世界状态快照语义；
- ✅ 已将GT21改为现实冲突主线：遥测显示延误60秒、运行审核记录显示55秒，先解释静默覆盖、取平均和擅自判断来源权威的业务风险，再在技术层展示失败关闭、`require_equal`与完整`explicit_precedence`；
- ✅ 已将GT22改为多源运行态势主线：位置与电量来自两个系统，先解释对象、时间和字段可能被错误拼接，再展示显式映射、revision 1、引用闭包、不确定性和稳定语义指纹；
- ✅ GT21—GT28统一采用“现实场景优先、必要性先行、技术概念后置”的案例叙事规范，主标题不得由Artifact、revision、semantic fingerprint或materialization等术语主导；
- ✅ 已发布GT23连续飞行状态案例，以10:02与10:07两个无人机运行快照展示只覆盖最新值为何会丢失历史和变化依据；案例显式记录位置、电量和对象有效期3项变化，绑定revision 1/2及语义指纹，并通过案例级路径核验确认before/after值，同时明确公共State Transition不执行通用diff、影响传播、风险重算或行动授权；
- ✅ 已发布GT24临时禁飞区影响范围案例：一条医疗航线穿越有效禁飞区，另一条巡检航线绕开；案例以显式声明的有限依赖链将医疗航线、任务、审批输出和起飞动作纳入复核，同时排除巡检链，并验证7节点、7条边、4个复核目标、精确文件绑定和无环结构，明确不执行几何求交、自动影响发现、传播、复核、输出释放或动作授权；
- ✅ 已发布GT25局部安全距离重算案例：无人机从走廊100米移动到130米后，只对两条无人机相关距离执行白名单`subtract`推导，将50/160米重算为20/130米，同时把110米固定设施间距和48%电池余量列为不可变复用路径；案例验证范围完整、范围互斥、精确字节绑定和未注册方法拒绝，并明确不自动发现依赖、不执行任意代码、状态物化、复核、输出释放或行动授权；
- ✅ 已发布GT26飞行服务站营业时间限定纠偏案例：新公告将营业计划从08:00—22:00调整为09:00—18:00，案例只允许替换1条营业计划路径，保留位置编码、通信频率、服务类型和联系方式4项不可变属性，并阻断20:30任务输出与派发动作直至后继状态有效且完成复核；案例明确不获取或比较真实公告、不应用修订、不物化状态、不发布输出或授权动作；
- ✅ 已发布GT27气象更新增量复核案例：东区风速由6升至12米/秒后，revision 7先吸收新气象值，再仅将同区域且处于更新生效时段的任务A、D纳入复核；任务A由适飞变为不适飞，任务D复核后仍适飞，任务B、C保持复用。案例绑定前后状态、差异、纠偏、影响图、执行结果和输出门禁，明确不自动发现依赖、不证明生产输出已发布或飞行动作获授权；
- ✅ 已发布GT28自动起飞授权门禁案例：路线、高度、天气窗口和风速预检全部满足，但空域、运营人、起降场、气象放行和任务授权五项信息仍为unknown；案例将可引用的路线天气预检标记为eligible，同时保持自动起飞授权与起飞指令blocked，并验证即使授权条件全部显式为true，公共Control Evaluation仍只标记输出eligible且`action_executed=false`；
- ✅ GT21—GT28世界状态循环场景案例已全部发布。

### v0.6：验证提供方与生态扩展（进行中）

- ✅ 已发布验证提供方接口规范v0.1，覆盖确定性算子、规则引擎、权威数据提供方、传感器数据提供方、本地预测模型和人工复核；
- ✅ 已发布验证提供方描述符、验证请求、验证响应和可信保证策略四类公共制品，并提供只读的`geotask provider inspect/check/validate`命令；
- ✅ 已建立反自我增信、精确请求/描述符字节绑定、独立分组、时效、可复现性、校准和行动边界校验；
- ✅ 已发布GT29虚构气象冲突案例：模拟气象服务给出8米/秒、现场传感器给出13米/秒，两个新鲜独立来源仍冲突时保持未知并请求第三个独立来源；
- ✅ 已发布GT30三源气象冲突案例：第三个独立来源也给出13米/秒，形成二比一；由于可信保证策略未声明多数表决规则，系统仍保持未知、保留少数来源并请求显式气象审定；
- ✅ 已发布GT31人工气象裁决案例：虚构人工复核精确绑定GT30三份冲突响应和上下文证据，保留全部原始结果并限定两份13米/秒读数的适用范围；天气结论升级为可用，但自动起飞授权与起飞指令继续由独立控制门禁阻断；
- ✅ 已发布GT32渐进授权门禁案例：五份虚构授权记录逐项到达，公共核心在每次累计输入后重新评估同一有限控制表达式，未知授权从5项降至0项；最终两个起飞相关输出转为可用，但生产发布、指令发送、现实授权与动作执行继续保持为假；
- ✅ 已发布GT33首个移动对象与离散轨迹案例：移动对象身份与三次带时区二维观测分离表达，轨迹引用必须闭合、时间必须严格递增且插值固定为none；新增第10个确定性算子计算首末样本持续300秒，同时拒绝静态折线替代、隐式插值、未来位置预测、地图匹配和现实动作推断；
- ✅ 已发布GT34离散轨迹分段与平均速度案例：三次明确观测按相邻顺序形成两个分段，分别绑定起止样本索引、时间和坐标，计算120/180秒持续时间、60/90个文档水平单位距离与0.5水平单位/秒平均速度；新增第11个确定性算子，同时拒绝非相邻分段、零时长、单位冒充、瞬时速度推断、插值、平滑、预测和现实动作；
- ✅ 已发布GT35停留、移动与观测缺口案例：调用方显式声明停留半径、最短停留时长、最大观测间隔和缺口许可，三个相邻分段分别输出停留候选、已观测移动和观测缺口；新增第12个确定性算子，缺口不允许时返回不可核验，同时拒绝默认阈值、连续停留、失联、异常、插值和现实动作推断；
- ✅ 已发布GT36加速度与运动连续性案例：调用方显式声明分段中点代表时刻和最大观测间隔，前两个相邻速度转换输出0和1/300水平单位/秒²，第三个转换因下一分段持续600秒而返回不可核验并保持速度差与加速度为null；新增第13个确定性算子，同时拒绝瞬时/向量加速度、方向变化、跨缺口计算、预测和现实动作推断；
- ✅ 已发布GT37对象同一性候选案例：比较前一轨迹末样本与后一轨迹首样本，在调用方显式声明的最大时间差、最大空间距离和对象类别要求下输出同一对象候选、不同对象候选或不可核验；新增第14个确定性算子，保留原始轨迹、主体和类别引用，同时拒绝自动身份归并、subject_ref改写、现实身份自证、插值、预测和现实动作；
- ✅ 已发布GT38对象同一性证据与显式审定案例：新增第28类公共制品和第29份公共Schema，将GT37候选与原始字节级绑定的验证请求、可信保证策略、两个独立验证提供方及其响应组合为同一对象确认、不同对象确认或未决审定；即使同一对象证据满足策略，也只输出身份归并复核建议，不归并对象、不改写subject_ref、不发布、不授权也不执行身份更新；
- ✅ 已发布GT39对象身份归并提案案例：新增第29类公共制品和第30份公共Schema，将GT38对象同一性审定结果、调用方选择的现有主对象引用、提案理由和审批角色组合为ready_for_review提案；提案只覆盖两条原始轨迹，提出一项subject_ref改写，保留非主主体为别名，并声明阻断、撤销和回退要求，不创建新身份、不删除别名、不审批、不修改对象关系图或世界状态，也不发布、授权或执行更新；
- ✅ 已建立中英文独立项目入口及术语映射，并明确“契约、规范、协议、合同”四类中文用法，机器标识保持稳定；
- 继续扩展对象身份归并审批、对象关系图变更请求、后继世界状态生成和可撤销身份治理规范；
- 发布可复用的行业扩展接口和非行业敏感的参考实现；
- 建立验错率、漏检率、纠偏成功率、增量复核范围和执行时延基准；
- 支持社区维护的验证提供方、案例、算子和通用扩展目录。

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
- ✅ Published Observation Merge Result v0.1, applying complete explicit mappings from exact Observation bytes to existing attributes or relations; when multiple claims target one path, Core accepts only caller-declared semantic-equality consolidation or complete explicit precedence, records every participant as `applied`, `consolidated`, or `superseded`, and deterministically emits one successor World State revision without identity inference, invented precedence, source ranking, undeclared ambiguous-conflict resolution, or State Transition computation;
- ✅ Published State Transition v0.1, binding before/after World State snapshots by semantic fingerprint and recording Observation-supported object, attribute, relation, and action-eligibility changes, while explicitly not calculating diffs, applying patches, materializing state, or authorizing action;
- ✅ Published Verification Session v0.1, binding one World State semantic fingerprint to exact-byte task, execution-result, control-evaluation, State Transition, and discrepancy references plus action eligibility and recheck triggers, while explicitly not validating linked artifact semantics or executing tasks, controls, or rechecks;
- ✅ Published Discrepancy Report v0.1, binding one World State semantic fingerprint to exact source-artifact bytes and recording discrepancy kind, expected/observed values, downstream impact, and mutable/immutable correction paths, while explicitly not comparing sources, propagating impact, creating correction requests, or applying corrections;
- ✅ Published Correction Request v0.1, binding one immutable base World State to exact Discrepancy Reports and constraining successor-state changes, acceptance criteria, immutable-path preservation, and output/action gates while explicitly not editing snapshots, applying changes, materializing successors, or releasing outputs;
- ✅ Published Impact Graph v0.1, representing discrepancies, corrections, state paths, assertions, outputs, actions, and reevaluation targets as a source-bound directed acyclic graph with root reachability, exact-byte bindings, and key edge-semantic checks, while explicitly not discovering the graph or executing propagation or reevaluation;
- ✅ Published bounded successor-World-State materialization and World State Materialization Result v0.1, applying one required Correction Request to one immutable base snapshot with exact-byte bindings and explicit recompute values while preserving provenance, output gates, and action gates;
- ✅ Published Recompute Derivation Result v0.1, binding exact World State, Correction Request, Observation, and GeoTask Document bytes and deriving every requested `recompute` value through small allowlisted deterministic methods, without arbitrary code, model calls, state mutation, reevaluation, release, or action authorization;
- ✅ Published Incremental Reevaluation Result v0.1, binding exact base/successor World States, Impact Graph, Correction Requests, Discrepancy Reports, and execution results while closing graph-node, target, acceptance, discrepancy-resolution, output-gate, and action-eligibility outcomes without executing reevaluation, generating successors, authorizing actions, or executing actions;
- ✅ Added high-level, read-only `geotask verify` and `geotask recheck` commands that run registered semantic validation, exact reference coverage, and SHA-256 binding checks over complete explicit Verification Session or Incremental Reevaluation Result bundles while explicitly not executing tasks, reevaluation, state materialization, output release, or actions;
- expand the bounded derivation method registry and extend Observation Merge with object-identity discovery and policies for ambiguous conflicts that lack an explicit caller declaration, while preserving explicit, local, reproducible snapshot semantics;
- ✅ Reframed GT21 around the operational conflict: telemetry reports a 60-second delay while an operations review reports 55 seconds. The page explains the business risk of silent overwrite, averaging, and invented authority before deferring fail-closed behavior, `require_equal`, and complete `explicit_precedence` to the technical layer;
- ✅ Reframed GT22 around multi-source operational awareness: position and battery arrive from different systems. The page explains object, time, and field-mapping risks before deferring explicit mapping, revision 1, reference closure, uncertainty, and semantic fingerprinting to the technical layer;
- ✅ Adopted a scenario-first narrative contract for GT21–GT28: real task and necessity lead, generic-AI failure modes follow, and Artifact/revision/semantic-fingerprint/materialization terminology is deferred to technical implementation;
- ✅ Published GT23 as a continuous-flight state-change case using the 10:02 and 10:07 UAV snapshots to show why overwriting the latest fields loses history and change evidence. The case explicitly records position, battery, and object-validity changes, binds revisions 1 and 2 by semantic fingerprints, and checks every declared before/after value against the snapshots while preserving the boundary that public State Transition does not compute a generic diff, propagate impact, recompute risk, or authorize action;
- ✅ Published GT24 as a bounded temporary-no-fly-zone impact case: one medical route intersects the active zone while an inspection route avoids it. The case validates an explicit finite dependency chain covering the medical route, mission, approval outputs, and launch action while excluding the inspection chain, with seven nodes, seven edges, four reevaluation targets, exact-byte bindings, and acyclic structure; it does not compute geometry, discover impact automatically, execute propagation or reevaluation, release outputs, or authorize action;
- ✅ Published GT25 as a bounded safety-distance recompute case: after a UAV moves from corridor chainage 100 to 130 metres, only two UAV-dependent distances are derived through the allowlisted `subtract` method, changing 50/160 metres to 20/130 metres, while 110-metre fixed-facility spacing and 48% battery remain immutable reusable paths. The case validates complete and disjoint scope, exact-byte bindings, and rejection of unregistered methods while explicitly not discovering dependencies automatically, executing arbitrary code, materializing state, rerunning checks, releasing outputs, or authorizing action;
- ✅ Published GT26 as a bounded flight-service-station schedule correction case: a fictional notice narrows the schedule from 08:00–22:00 to 09:00–18:00; the case permits one schedule-path replacement, preserves four immutable station attributes, and blocks the 20:30 mission output and dispatch action until a valid successor state and completed recheck exist, while explicitly not fetching real notices, applying correction, materializing state, releasing output, or authorizing action;
- ✅ Published GT27 as a weather-triggered incremental reevaluation case: after east-zone wind rises from 6 to 12 m/s, revision 7 first absorbs the new weather value and only Missions A and D in the matching region and active time window enter recheck. Mission A changes from suitable to unsuitable, Mission D remains suitable after explicit recheck, and Missions B and C are reused. The case binds both states, discrepancy, correction, impact graph, execution result, and output gates while not claiming automatic dependency discovery, production output release, or flight authorization;
- ✅ Published GT28 as an automatic-takeoff authorization-gate case: route, altitude, weather-window, and wind preconditions pass, but five independent authorization identifiers remain unknown. The case records the reusable route-weather precheck as eligible while automatic-takeoff authorization and the takeoff command remain blocked, and proves that even a fully true authorization context only makes outputs eligible while `action_executed` stays false;
- ✅ Completed publication of the GT21–GT28 scenario-first World-State Cycle.

### v0.6: Verification Providers and Ecosystem Extensions (in progress)

- ✅ Published Verification Provider Profile v0.1 for deterministic operators, rule engines, authoritative data providers, sensor data providers, local predictive models, and human review;
- ✅ Published four public Artifacts: Verification Provider Descriptor, Verification Request, Verification Response, and Assurance Profile, with read-only `geotask provider inspect/check/validate` commands;
- ✅ Added anti-self-assurance rules, exact Request/Descriptor byte bindings, independent-group, freshness, reproducibility, calibration, and action-boundary validation;
- ✅ Published GT29 as a fictional weather conflict: a mock weather service reports 8 m/s and an onsite sensor reports 13 m/s; two fresh independent sources still conflict, so Assurance remains unknown and a third independent source is requested;
- ✅ Published GT30 as a three-source weather conflict: a third independent source also reports 13 m/s, producing a two-to-one split; without a declared majority policy, Assurance remains unknown, the minority source is preserved, and explicit adjudication is requested;
- ✅ Published GT31 as a fictional human weather adjudication: the review binds all three GT30 responses and scoped context evidence, preserves every raw result, and limits the applicability of the two 13 m/s readings; the weather conclusion becomes eligible while a separate Control Evaluation keeps automatic takeoff authorization and the takeoff command blocked;
- ✅ Published GT32 as a progressive authorization-gate case: five fictional authorization records arrive one by one, the same finite control profile is reevaluated after each cumulative input, and unknown identifiers fall from five to zero; both takeoff-related outputs become eligible only at the final step, while publication, command delivery, real-world authorization, and action execution remain false;
- ✅ Published GT33 as the first moving-object and discrete-trajectory case: identity is separated from three timezone-aware 2D observations, trajectory references must close, timestamps must be strictly increasing, and interpolation is fixed to `none`; the tenth deterministic operator returns a 300-second endpoint duration while rejecting static-polyline substitution, implicit interpolation, future-position prediction, map matching, and action inference;
- ✅ Published GT34 for discrete trajectory segments and average speed: three explicit observations form two adjacent segments that bind sample indexes, timestamps, and coordinates, returning 120/180-second durations, 60/90 document-horizontal-unit distances, and 0.5 horizontal-unit-per-second averages; the eleventh deterministic operator rejects non-adjacent collapse, zero duration, unit overclaiming, instantaneous-speed inference, interpolation, smoothing, prediction, and real-world action;
- ✅ Published GT35 for stop/move and observation-gap classification: caller-declared stationary radius, minimum stationary duration, maximum observation interval, and gap permission classify three adjacent segments as `stationary_candidate`, `moving_observed`, and `observation_gap`; the twelfth deterministic operator returns `unverifiable` when gap marking is disallowed and rejects default thresholds, continuous-stop, lost-link, anomaly, interpolation, and action inference;
- ✅ Published GT36 for acceleration and motion continuity: caller-declared segment-midpoint representative time and maximum observation interval produce scalar estimates of 0 and 1/300 horizontal units per second squared for the first two adjacent speed transitions; the third transition becomes `unverifiable` with null speed change and acceleration because the next segment lasts 600 seconds. The thirteenth deterministic operator rejects instantaneous/vector acceleration, direction change, cross-gap computation, prediction, and action inference;
- ✅ Published GT37 for object-identity candidates: the final explicit sample of one trajectory and the first explicit sample of another are evaluated under caller-declared time, distance, and object-class policy to return `same_object_candidate`, `different_object_candidate`, or `unverifiable`. The fourteenth deterministic operator preserves original trajectory, subject, and class references while rejecting automatic identity merge, `subject_ref` mutation, real-world identity self-verification, interpolation, prediction, and action inference;
- ✅ Published GT38 for identity-candidate evidence and explicit adjudication: the twenty-eighth public Artifact and twenty-ninth public Schema bind the exact GT37 candidate, Verification Request, caller-authored Assurance Profile, and two independently grouped Provider responses into confirmed-same, confirmed-different, or unresolved adjudication. Even confirmed same-object evidence only enables merge review and never merges objects, mutates `subject_ref`, publishes, authorizes, or executes an identity update;
- ✅ Published GT39 for bounded identity-merge proposals: the twenty-ninth public Artifact and thirtieth public Schema bind one exact GT38 same-object adjudication to a caller-selected existing canonical subject, exactly one proposed `subject_ref` rewrite, retained alias history, approval roles, closed blocking and withdrawal conditions, and an inverse reversal plan. The proposal never creates or deletes identity, approves itself, mutates the object graph or World State, publishes, authorizes, or executes an update;
- ✅ Established separate Chinese and English project entry points plus terminology maps while keeping machine identifiers stable; the Chinese guide now distinguishes software contracts, specifications, protocols, and legal/commercial contracts by function;
- continue with identity-merge approval, object-graph change requests, successor World State generation, and reversible identity-governance specifications;
- publish reusable extension interfaces and non-sensitive reference implementations;
- establish benchmarks for error-detection rate, missed errors, correction success, incremental scope, and execution latency;
- support community-maintained catalogs of Verification Providers, cases, operators, and generic extensions.
