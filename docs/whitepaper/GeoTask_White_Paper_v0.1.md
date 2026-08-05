# GeoTask 白皮书 v0.1

## 面向智能体的显式、可验证时空世界模型

**状态：Public Draft**  
**对应实现：GeoTask Core v1.0 public profile**  
**适用对象：AI Agent 开发者、GIS/时空智能开发者、机器人与无人系统工程师、研究人员、平台架构师**

---

## 摘要

多模态大模型正在从“回答问题”走向“理解场景、生成计划并影响现实行动”。但模型对世界的理解通常隐含在上下文、向量或参数中，难以稳定回答：世界中有哪些对象、它们处于什么时空状态、哪些关系已经证实、哪些证据已经过期、状态变化会影响哪些结论，以及当前世界是否允许某个行动。模型能力越强、行动链越长，越需要一个外显、共享、可验证的世界状态。

GeoTask 将自身定位为面向智能体的显式、可验证时空世界模型。它把多模态模型、传感器、地图、权威数据和人工输入转化为世界对象、时空关系、状态、证据、约束与行动资格，使智能体依赖的现实事实能够被计算、验证、更新、追溯和纠偏。验错、补证、限定修订、状态复核和行动门控不是最高层定义，而是GeoTask维护可信世界状态的核心机制。

GeoTask不是以视频生成或隐式神经动力学预测为核心的单体世界模型。公共 Core 提供可验证时空世界模型的状态契约、任务与Artifact表示、本地确定性验证、证据绑定、Observation v0.1、World State v0.1、支持调用方显式同目标冲突策略的受限Observation Merge v0.1、State Transition v0.1、Verification Session v0.1、Discrepancy Report v0.1、Correction Request v0.1、Impact Graph v0.1、Recompute Derivation Result v0.1、受限后继状态物化、Incremental Reevaluation Result v0.1、控制评估和Agent修订基础；Runtime与Domain Pack负责权威数据、行业规则、本地预测模型、人工复核和生产动作。“可验证时空任务协议”是当前工程实现形式，而自动差异计算、对象身份发现、未声明策略的歧义命题冲突消解、影响图自动发现与传播执行以及受限推导方法扩展是下一阶段公共抽象。

## English Abstract

Multimodal foundation models are moving from answering questions to interpreting scenes, proposing plans, and influencing real-world action. Their understanding of the world, however, is usually implicit in prompts, vectors, or model parameters. It is therefore difficult to maintain stable answers about which objects exist, where and when they exist, which relations have been verified, which evidence has expired, which conclusions are affected by a state change, and whether an action is currently eligible. As model capability and action chains grow, agents need an explicit, shared, and verifiable world state.

GeoTask is an **explicit and verifiable spatiotemporal world model for AI agents**. It converts multimodal-model outputs, sensor observations, maps, authoritative data, and human input into explicit world objects, spatiotemporal relations, state, evidence, constraints, and action eligibility. This makes operational facts computable, verifiable, updateable, traceable, and correctable. Error detection, evidence recovery, bounded revision, state reevaluation, and action gating are mechanisms for maintaining a trustworthy world state rather than the complete definition of GeoTask.

GeoTask is not a monolithic neural world model centered on video generation or implicit dynamics prediction. The public Core provides state and Artifact contracts, task representation, deterministic local verification, provenance and evidence binding, Observation v0.1, World State v0.1, bounded Observation Merge v0.1 with caller-declared same-target conflict policies, State Transition v0.1, Verification Session v0.1, Discrepancy Report v0.1, Correction Request v0.1, Impact Graph v0.1, Recompute Derivation Result v0.1, bounded successor-state materialization, Incremental Reevaluation Result v0.1, control evaluation, and guarded Agent revision. External Runtimes and Domain Packs remain responsible for authoritative sources, domain rules, local predictive models, human review, credentials, and production actions. The verifiable spatiotemporal task protocol is the current engineering form; automatic diff computation, identity discovery, resolution of ambiguous claims without a declared policy, automatic impact-graph discovery and propagation execution, and expansion of the bounded derivation method registry remain the next public abstractions.

| 中文核心术语 | English term |
|---|---|
| 显式、可验证时空世界模型 | explicit and verifiable spatiotemporal world model |
| 世界状态 | world state |
| 观察 | Observation |
| 状态转换 | State Transition |
| 证据绑定 | evidence binding |
| 限定修订 | bounded revision |
| 增量复核 | incremental reevaluation |
| 行动资格 | action eligibility |

---

## 1. 问题背景

### 1.1 为什么是现在：从直接给答案到开放推理与后验验证

过去，时空智能系统通常由专用模型或 GIS 流程直接给出距离、相交、路径、风险和调度结果。多模态大模型出现后，系统架构开始变化：模型先理解场景、提出对象和假设、组合多源信息并生成方案，本地时空框架则更适合承担约束辅助、结果复算、差异检测和运行中的持续验证。

这不是传统时空技术价值下降，而是价值位置发生迁移：

```text
过去：专用时空模型直接计算局部关系并给出答案
现在：大模型理解场景并提出世界假设，本地时空框架验证关键关系
未来：多源观察持续更新显式世界状态，验证系统维护事实、预测和行动资格
```

模型能力越强，系统越需要回答以下问题：

- 世界中有哪些稳定对象，它们的身份、位置、时间和状态如何表示；
- 模型观察、传感器、地图、权威数据与人工判断之间如何绑定和冲突；
- 哪些关系符合几何、拓扑、时间和物理事实；
- 新观察到来后，哪些世界状态、预测和行动资格需要更新或失效；
- 未经验证或已经过期的世界状态是否会进入设备运动、任务审批或风险处置。

因此，多模态能力提升不会削弱 GeoTask 的价值，反而会把其作用从“给模型提供一个空间工具”提升为“为智能体维护显式、可信、可演化的时空世界模型”。

### 1.2 智能体正在进入真实空间

AI Agent 正从文本问答扩展到机器人、无人机、自动驾驶、低空运行、城市治理、物流配送、应急救援和网络规划等场景。这些任务共同具有以下特点：

- 输入来自自然语言、地图、图像、视频、传感器、业务系统和规则文件；
- 任务包含位置、路线、区域、时间、高度、距离、资源、环境和对象能力；
- 结论可能触发设备运动、任务审批、资源调度或风险处置；
- 状态和证据会持续变化，初始正确不代表后续持续正确；
- 错误不仅是“回答不准确”，还可能造成错误执行。

大模型通常把这些信息保存在上下文文本或内部表征中。文本容易阅读，却缺少稳定的对象引用、单位、坐标系、边界语义、证据来源和执行身份。模型可能正确理解业务意图，却在具体计算上出错；也可能算对一个局部结果，却忽略另一个约束；还可能在新状态到来后继续沿用已经过期的判断。

### 1.3 单纯工具调用仍然不够

Tool Calling 能让模型调用距离或相交函数，但一次函数调用通常只表达局部计算，不能完整描述：

- 任务要解决什么问题；
- 哪些对象和观察参与计算；
- 对象采用什么坐标参考、轴顺序和单位；
- 哪些断言相互依赖，哪些输出会受变化影响；
- 结果由模型、本地算子、规则、本地模型还是人工复核产生；
- 缺少或过期证据时应暂停什么；
- 多份证据冲突时如何保留冲突而不是强行选边；
- 允许模型修改哪些字段，哪些事实必须保持不变；
- 条件恢复或状态变化后从哪里重新验证。

因此，智能体需要的不只是“空间工具”，还需要任务级中间表示、验证状态、纠偏合同和行动门控。

### 1.4 传统 GIS 脚本也不等于验证循环

GIS 脚本能够精确计算，但往往默认开发者已经完成对象选择、数据绑定、规则解释和输出定义。它不天然包含模型可读的任务目标、断言状态、证据请求、限定修订路径、受影响输出和动作恢复逻辑。

GeoTask 位于开放推理、本地时空能力与现实行动之间：

```text
Multimodal Observation / External State
                 ↓
     Explicit Spatiotemporal World State
                 ↓
Relations / Constraints / World Claims
                 ↓
Local Verification → Evidence / Conflict / Uncertainty
                 ↓                         ↑
State Update / Bounded Correction ← New Observation
                 ↓
        Action Eligibility Gate
```

当前公共 Core 已实现世界对象和空间合同、来源与证据绑定、Observation v0.1、World State v0.1、支持`require_equal`与完整显式优先级的受限Observation Merge v0.1、State Transition v0.1、Verification Session v0.1、Discrepancy Report v0.1、Correction Request v0.1、Impact Graph v0.1、Recompute Derivation Result v0.1、受限后继状态物化、Incremental Reevaluation Result v0.1、世界命题、本地确定性验证、控制状态、Agent机械修复、限定路径重试和证据恢复。自动差异计算、对象身份发现、未声明策略的歧义命题冲突消解、Impact Graph自动发现与传播执行以及受限推导方法扩展仍是后续工程目标。

---

## 2. GeoTask 的定义

GeoTask 的本体定位可以定义为：

> **面向智能体的显式、可验证时空世界模型。**

完整定义是：

> **GeoTask通过显式描述世界对象、位置、时间、状态、关系、约束、证据及其变化，将多模态模型与外部系统对现实世界的理解转化为可计算、可验证、可更新、可追溯的时空世界状态，并据此支持推理、预测、纠偏与行动决策。**

其当前技术实现形式是：

> **面向智能体的可验证时空任务协议、Canonical IR、Artifact体系和本地验证内核。**

本体定位回答“GeoTask是什么”，技术定义回答“当前如何实现”。验错、纠偏、证据恢复和行动门控是世界模型的核心维护能力，而不是对GeoTask边界的全部定义。

### 2.1 面向智能体

GeoTask 文档既要让程序解析，也要让大模型理解。字段名称、对象引用和任务目标应保持明确，避免只对某个内部库可读。

### 2.2 时空任务

GeoTask 的核心对象不仅是几何图形，还包括时间区间、高度区间、移动对象、资源约束和任务上下文。空间关系只有与时间、对象能力和业务规则组合后，才能支撑真实行动。

### 2.3 可验证、可纠偏、可持续复核

模型产生的答案不是最终事实。可确定计算应由本地执行器复算，模型结果与本地结果应能够比较。无法验证时，系统应显式返回 `unverifiable`、`need_data` 或复核任务，而不是强行生成真假结论；发现矛盾时，应定位受影响命题和允许修改的范围；新状态到来后，应区分仍然有效的发现与必须失效的输出。

### 2.4 世界模型，而非完整应用

GeoTask 不负责提供完整地图、原始多模态识别、设备控制、行业审批或商业调度。它定义这些系统之间如何表达和交换世界对象、观察、状态、命题、证据、验证结果和行动资格，并为Runtime与Domain Pack保留明确扩展边界。

### 2.5 与隐式神经世界模型的区别

“世界模型”在当前研究中常指从视频或交互数据学习环境动力学、预测未来画面或模拟动作结果的神经网络。GeoTask不与这类模型竞争，也不宣称在公共Core中完成端到端感知和未来生成。

GeoTask更接近一种外显、符号—计算、组合式的世界模型：

| 维度 | 隐式神经世界模型 | GeoTask |
|---|---|---|
| 世界表达 | 隐藏在参数、向量或隐状态中 | 对象、关系、状态、证据和约束显式表达 |
| 状态来源 | 主要来自训练与感知模型 | 模型、传感器、地图、权威数据和人工均可接入 |
| 计算方式 | 神经预测或生成 | 确定性算子、规则、本地模型和人工复核组合 |
| 可信机制 | 置信度或评测指标 | 来源、证据、验证状态、冲突、有效范围和审计链 |
| 状态更新 | 更新上下文或隐状态 | Observation v0.1记录变化输入；World State v0.1记录时点快照；受限Observation Merge v0.1按完整显式映射生成后继快照，并对同一目标支持调用方声明的语义相等合并或完整优先级；State Transition v0.1绑定前后快照并记录变化；自动差异、身份发现、未声明策略的歧义冲突消解与Recheck编排仍在建设 |
| 行动边界 | 通常由外围系统处理 | 行动资格和阻断条件是世界状态合同的一部分 |

因此，GeoTask可以连接神经世界模型，将其输出作为带来源和不确定性的Observation，以World State v0.1表达共享时点快照，通过受限Observation Merge v0.1把完整显式映射写入既有状态目标，对同一目标仅按调用方声明的`require_equal`或完整显式优先级生成后继版本，再用State Transition v0.1绑定前后快照、记录显式变化；自动计算差异、推断对象身份、解决未声明策略的歧义冲突并编排增量复核，仍属于后续状态演化阶段。

---

## 3. 核心设计原则

### 3.1 对象、算子和命题显式绑定

自然语言中的“这条路线是否进入禁飞区”应被转化为稳定引用：

```yaml
assertions:
  - id: route_enters_zone
    operator: line_intersects_rect
    object_refs: [delivery_route, temporary_no_fly_zone]
    expected_type: bool
```

这使系统可以回答：使用了哪个算子、输入了哪些对象、输出应该是什么类型。

### 3.2 生成与验证分离

模型可以提出：

- 哪些对象需要创建；
- 哪些算子需要调用；
- 哪个动作更合适；
- 如何解释结果。

本地执行器负责：

- 解析对象；
- 检查引用和类型；
- 执行确定性算子；
- 生成可重复结果；
- 比较模型声明。

```text
Model-generated proposal
          ↘
           Comparator → verified / contradicted / review
          ↗
Local deterministic result
```

### 3.3 状态必须比真假更丰富

真实任务不能只用 `true` 和 `false` 表达。至少需要区分：

- `verified`：断言已由指定验证路径支持；
- `contradicted`：模型声明与确定性结果不一致；
- `unverifiable`：当前数据不足以完成验证；
- `need_data`：需要补充具体字段或来源；
- `need_review`：需要人工或权威系统裁决；
- `invalid_input`：输入结构或数据无效；
- `execution_error`：执行过程失败。

案例层还可以表达 `conflicted`、`blocked`、`coordinated` 等工作流状态，但这些扩展不得冒充 Core 的基础断言状态。

### 3.4 来源与保证等级必须保留

结果需要说明“谁算的”和“如何验证的”。GeoTask 的保证等级包括：

```text
unverified
model_generated
model_self_checked
local_deterministic
model_local_agreement
independent_cross_verified
human_reviewed
```

高等级不是由语言风格决定，而是由执行与验证链路决定。

### 3.5 不知道时生成下一步动作

可靠系统不能把缺证据包装成确定结论。GeoTask 案例使用结构化的证据请求表达：

- 为什么无法验证；
- 缺少哪些字段；
- 哪些输出必须暂停；
- 补齐后从哪个条件恢复；
- 下一步由谁执行。

### 3.6 行业规则与 Core 分离

Core 提供通用对象、算子、验证和结果结构。行业阈值、审批权限、客户数据、评分模型、调度策略和商业优化应放在 Domain Pack 或上层 Runtime。这样既保持开源核心稳定，也避免通用语义被单一行业污染。

---

## 4. 文档模型

当前公共 v1.0 profile 的主要结构为：

```yaml
geotask:          # 任务元数据
space:            # 坐标参考、单位、精度
objects:          # 空间、时间和高度对象
operator_set:     # 允许使用的算子
operator_contracts: # 可选算子契约

tasks:            # 任务、约束和断言
execution:        # 执行模式与步骤
verification:     # 验证策略
output_contract:  # 输出约束
extensions:       # 行业或案例扩展
expected_results: # 可选测试夹具
```

### 4.1 对象

公共 Core 当前支持十类Canonical对象：

- `point`
- `polyline`
- `multi_polyline`
- `polygon`
- `rect`
- `time_interval`
- `altitude_interval`
- `feature_collection`
- `moving_object`
- `trajectory`

对象必须具有稳定 id，并在断言中通过 `object_refs` 引用。`moving_object`只声明身份；`trajectory`通过严格递增、带时区的二维观测样本引用一个移动对象，并显式禁止隐式插值。对象数据可以使用 v1 原生字段，也可以通过兼容层读取部分旧字段。

### 4.2 算子

公共 Core 当前提供十三个本地确定性算子：

| 算子 | 作用 |
|---|---|
| `distance_2d` | 二维点到点欧氏距离 |
| `line_intersects_rect` | 折线是否接触或穿过轴对齐矩形 |
| `multi_polyline_intersects_rect` | 多折线任一成员是否接触或穿过矩形 |
| `point_in_polygon` | 点是否位于单环多边形内部或闭边界上（点在前） |
| `polygon_contains_point` | 单环多边形是否包含点或与点接触（多边形在前） |
| `point_to_line_distance_2d` | 点到折线的最短距离 |
| `rect_contains_point` | 矩形是否包含点，边界计入 |
| `time_overlap` | 两个闭时间区间是否重叠 |
| `altitude_overlap` | 两个闭高度区间是否重叠 |
| `trajectory_duration_seconds` | 离散轨迹首末明确观测之间的持续秒数，不插值、不预测 |
| `trajectory_segment_metrics` | 相邻明确样本的持续时间、二维距离与平均速度，不把平均速度冒充瞬时状态 |
| `trajectory_segment_classifications` | 使用调用方显式声明的停留与观测间隔阈值，将相邻分段分类为停留候选、已观测移动、观测缺口或不可核验，不推断失联或异常 |
| `trajectory_segment_acceleration_estimates` | 将相邻分段平均速度绑定到显式中点代表时刻，计算标量速度变化率；任一分段超过声明的最大观测间隔时返回不可核验并保持数值为空 |

算子语义必须稳定。Domain Pack 可以组合 Core 算子，但不应修改同名算子的边界规则。

### 4.3 断言

断言是可验证命题的最小单位：

```yaml
- id: temporal_conflict
  operator: time_overlap
  object_refs: [flight_window, restricted_window]
  expected_type: bool
  on_error: stop
```

断言可以具有参数、单位、容差、依赖和错误策略。执行器为每个断言生成独立检查结果。

### 4.4 执行

公共 Core 推荐使用 `local_only`：

```yaml
execution:
  mode: local_only
  steps:
    - id: run_checks
      executor: local
      assertion_refs: [distance_check, zone_check]
```

体系级目标还包括 `model_only`、`hybrid` 和 `shadow_compare`。当前公共 Core 不保存模型密钥，也不直接调用外部模型。

### 4.5 扩展

`extensions` 用于承载不改变 Core 算子语义的任务层信息，例如：

- 应用场景；
- 对象能力；
- 资源预算；
- 优先级策略；
- 证据请求；
- 冲突复核；
- 阻断输出；
- 恢复条件；
- 下一步动作。

扩展字段应可追溯、可测试，不应成为绕过 Core 验证的隐藏通道。

---

## 5. 执行与信任链

### 5.1 主执行链

```text
YAML / JSON
  ↓ parse
Raw document
  ↓ canonicalize
CanonicalDocument
  ↓ validate
Diagnostics
  ↓ execute
CheckResult[]
  ↓ aggregate
GeotaskResult + Assurance
```

Canonical IR 是公共 v1 模块之间的单一事实来源。旧版文档可以通过兼容层迁移到 CanonicalDocument。

### 5.2 结果不等于保证

任务完成表示执行流程走完，不代表所有断言都正确。一个结果需要同时查看：

- `execution.status`
- 每个 check 的 `status`
- `value` 和 `unit`
- `assurance_level`
- derivation / provenance
- output contract violations

### 5.3 三值与未知传播

组合任务中，一个无法验证的必要条件不能被当成 `false`，也不能被忽略。例如：

```text
route_conflict = true
altitude_conflict = true
temporal_conflict = unknown
```

在显式 `AND` 规则下，完整冲突应保持 unknown/unverifiable，而不是强行输出 true 或 false。上层系统应生成补证据动作。

### 5.4 证据冲突

两份证据可以分别完成核验，却给出互不兼容的结果。此时“各自 verified”不等于“彼此一致”。系统必须进入冲突复核，明确：

- 权威来源；
- 被替代版本；
- 最终生效内容；
- 裁决依据；
- 裁决责任人；
- 裁决时间。

在裁决完成前，系统不得擅自选择看起来更正式或发布时间更晚的来源。

---

## 6. 从空间判断到可执行动作

GeoTask 的价值不止是计算“是否相交”，还在于把验证结果转化为受约束动作。

### 6.1 协同动作

两台机器人争用容量为 1 的窄通道时，系统需要结合路线、时间、容量和显式优先级生成：

- 谁先行；
- 谁等待；
- 在哪里等待；
- 等待多久；
- 新进入时间；
- 恢复条件。

### 6.2 对象相关可达性

两点直线距离 50 米，不代表轮式机器人能够直达。路径可能穿过台阶、围栏和机动车道。可达性是对象、空间和规则的函数：

```text
accessibility = f(object, network, constraints)
```

### 6.3 资源可行性

无人机剩余航程可以覆盖目的地，却可能无法在合法绕飞后保留安全余量：

```text
mission requirement = legal route + mandatory reserve
```

“能到达”与“能安全完成”必须分开表达。

### 6.4 空间包络

道路开放并不代表所有车辆可通过。施工净空必须与车辆本体及安全缓冲构成的对象包络比较：

```text
required envelope = body width + left buffer + right buffer
```

对象尺度、动态缓冲和运行规则共同决定通行能力。

---

## 7. GT01–GT20 渐进式案例

| 阶段 | 案例 | 核心能力 |
|---|---|---|
| 基础几何 | GT01 | 点到点距离与本地复算 |
| 边界语义 | GT02 | 相切是否计入相交 |
| 路线结构 | GT03 | 多段路线逐段检查 |
| 垂直空间 | GT04 | 平面重合但高度分离 |
| 时间窗口 | GT05 | 空间相同但时间分离 |
| 多条件组合 | GT06 | 路线、高度、时间显式 AND |
| 未知传播 | GT07 | 必要条件不可验证 |
| 证据请求 | GT08 | 缺证据后生成补证任务 |
| 证据冲突 | GT09 | 两份已核验证据互相矛盾 |
| 协同调度 | GT10 | 窄通道容量与优先级动作 |
| 对象可达性 | GT11 | 50 米直线与 300 米可通行网络 |
| 资源余量 | GT12 | 到达能力与安全完成能力 |
| 空间包络 | GT13 | 道路开放与车辆净空约束 |
| 应急调度 | GT14 | 最近距离与最早验证到达时间 |
| 实时环境状态 | GT15 | 静态地图与当前路线占用状态 |
| 多机时空冲突 | GT16 | 路线交叉、高度重叠与时间分离 |
| 城市事件去重 | GT17 | 多源上报、时空聚类与单任务派发 |
| 设备能力约束 | GT18 | 最短路线、环境风险与机器人耐受能力 |
| 高风险动作门控 | GT19 | 到达条件、地面净空与载荷释放授权 |
| 路口入口门控 | GT20 | 绿灯许可、下游净空与完整驶离能力 |

这些案例不是独立技巧，而是同一任务模型的逐步展开：

```text
对象 → 关系 → 多条件 → 未知 → 证据 → 动作 → 恢复
```

---

## 8. 与相关技术的边界

### 8.1 与 GeoJSON 的区别

GeoJSON 主要描述地理要素。GeoTask 描述要对这些对象执行什么任务、使用什么算子、验证什么命题以及输出什么结果。GeoTask 可以引用或嵌入由 GeoJSON 转换的对象，但不替代 GeoJSON。

### 8.2 与 GIS 工作流的区别

GIS 工作流强调数据处理和算子编排。GeoTask 额外强调模型可读性、断言级验证、来源保证、证据状态和动作治理。

### 8.3 与 Agent Tool Calling 的区别

Tool Calling 描述一次或一组函数调用。GeoTask 提供跨调用的任务对象模型、断言依赖、执行模式、输出契约和恢复语义，可作为 Agent 生成工具调用之前的中间表示。

### 8.4 与机器人任务规划语言的区别

机器人任务规划语言通常针对特定设备或控制系统。GeoTask Core 保持设备中立，以通用时空对象和确定性验证为基础；设备动力学和控制约束应由 Domain Pack 扩展。

---

## 9. 开源边界与知识产权

GeoTask Core 采用 MIT 许可，公开以下能力：

- 通用时空任务结构；
- 公共对象类型；
- 通用确定性算子；
- Parser、Canonical IR、Validator、Executor；
- 结果和保证等级；
- 公共示例与测试；
- 语言规范和 JSON Schema。

以下内容不应因白皮书发布而默认公开：

- 客户数据和内部连接器；
- 行业审批权重和商业阈值；
- 模型密钥、路由和成本策略；
- 未公开的专利实现细节；
- 能直接复现商业优化壁垒的参数和流程；
- 真实设备控制与生产运营规则。

白皮书解释系统做什么、接口如何使用和结果如何验证，不要求公开所有内部优化方法。

---

## 10. 符合性与生态

一个符合公共 GeoTask v1.0 profile 的实现，应至少能够：

1. 读取 YAML 或 JSON 文档；
2. 构造 CanonicalDocument；
3. 验证对象、算子、引用和执行步骤；
4. 执行声明支持的本地确定性算子；
5. 为每个断言输出状态、值和保证等级；
6. 保留扩展字段而不修改 Core 算子语义；
7. 对非法输入生成结构化诊断；
8. 通过公共 conformance tests。

第三方可以基于 GeoTask 构建：

- Agent Skill；
- MCP/Tool 适配器；
- GIS 插件；
- 机器人和无人机 Domain Pack；
- 证据治理服务；
- 模型空间推理 Benchmark；
- 可视化任务编辑器；
- IDE 语法提示与校验插件。

---

## 11. 路线图

### v0.1 文档闭环

- 白皮书；
- 实现规范；
- JSON Schema；
- 快速入门；
- 状态和证据参考；
- GT01–GT20 Cookbook。

### 后续候选方向

- 规范化组合逻辑表达；
- 可验证派生命题；
- 证据对象的一等化；
- 任务图与条件恢复；
- CRS 和单位转换契约；
- 更丰富的几何类型；
- Domain Pack conformance；
- model/local shadow compare 标准结果；
- IDE 与 Agent 框架集成。

路线图中的能力只有在代码、测试和实现规范同步完成后，才应被标记为公共实现能力。

---

## 12. 结语

大模型可以生成看起来合理的时空答案，但真实系统需要知道这些答案是否来自正确对象、正确算子、正确规则和可重复计算。GeoTask 的核心不是让模型“更会解释地图”，而是让智能体把空间任务转化为可执行命题，并在不知道、冲突或资源不足时采取正确的下一步动作。

GeoTask 试图建立的，是自然语言智能与确定性时空计算之间的一条可信接口：

> **让模型负责理解与生成，让确定性系统负责计算与验证，让证据和状态决定任务是否继续。**

---

## 相关文档

- [GeoTask Language and Execution Specification v1.0](../spec/geotask-language-spec-v1.0.md)
- [Quickstart](../tutorials/quickstart.md)
- [GT01–GT20 Cookbook](../cookbook/gt01-gt20.md)
- [Status and Assurance Model](../reference/status-model.md)
- [Evidence and Recovery](../reference/evidence-and-recovery.md)
- [Machine-readable JSON Schema](../../schemas/geotask-v1.0.schema.json)
- [Target Specification Status](../spec/target-specification-status.md)
