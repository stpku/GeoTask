# GeoTask 白皮书 v0.1

## 面向智能体的可验证时空任务表示与执行框架

**状态：Public Draft**  
**对应实现：GeoTask Core v1.0 public profile**  
**适用对象：AI Agent 开发者、GIS/时空智能开发者、机器人与无人系统工程师、研究人员、平台架构师**

---

## 摘要

大模型能够理解自然语言、生成计划并调用工具，但在距离、相交、时间重叠、高度冲突、可达性、资源余量和多约束组合等时空任务中，仍可能出现坐标混淆、边界语义不一致、计算错误、证据缺失和越权推断。仅依赖提示词无法稳定解决这些问题；仅依赖传统 GIS 接口，又难以表达模型生成的任务意图、证据状态、验证来源和后续动作。

GeoTask 提出一种面向智能体的可验证时空任务表示与执行框架。它把自然语言任务转化为显式的对象、算子、断言、执行步骤、输出契约和扩展语义，并通过本地确定性执行器对可计算命题进行复算。模型可以负责理解、分解、解释和提出动作，但不能仅凭语言流畅度宣布计算已经正确。每个结果都应携带来源、状态和保证等级，使上层系统能够区分“模型生成”“本地确定性计算”“模型与本地一致”“需要数据”以及“需要人工复核”。

GeoTask 的目标不是替代 GIS、工作流引擎或行业审批系统，而是在大模型与这些系统之间提供一层可读、可执行、可验证、可审计的时空任务协议。

---

## 1. 问题背景

### 1.1 智能体正在进入真实空间

AI Agent 正从文本问答扩展到机器人、无人机、自动驾驶、低空运行、城市治理、物流配送、应急救援和网络规划等场景。这些任务共同具有以下特点：

- 输入来自自然语言、地图、传感器、业务系统和规则文件；
- 任务包含位置、路线、区域、时间、高度、距离、资源和对象能力；
- 结论可能触发设备运动、任务审批、资源调度或风险处置；
- 错误不仅是“回答不准确”，还可能造成错误执行。

传统大模型通常把这些信息保存在上下文文本中。文本容易阅读，却缺少稳定的对象引用、单位、坐标系、边界语义和执行来源。模型可能正确理解业务意图，却在具体计算上出错；也可能算对一个局部结果，却忽略另一个约束。

### 1.2 单纯工具调用仍然不够

Tool Calling 能让模型调用距离或相交函数，但一次函数调用通常只表达局部计算，不能完整描述：

- 任务要解决什么问题；
- 哪些对象参与计算；
- 对象采用什么坐标参考和单位；
- 哪些断言相互依赖；
- 结果由模型还是本地算子产生；
- 缺少证据时应暂停什么；
- 多份证据冲突时由谁裁决；
- 条件恢复后从哪里继续执行。

因此，智能体需要的不只是“空间工具”，还需要一个任务级中间表示。

### 1.3 传统 GIS 脚本也不等于智能体协议

GIS 脚本能够精确计算，但往往默认开发者已经完成对象选择、数据绑定、规则解释和输出定义。它不天然包含模型可读的任务目标、断言状态、保证等级、证据请求和动作恢复逻辑。

GeoTask 位于自然语言与确定性执行之间：

```text
Natural Language / Agent Intent
              ↓
        GeoTask Document
              ↓
Parse → Canonicalize → Validate → Execute → Verify
              ↓
Structured Result / Action / Review Task
```

---

## 2. GeoTask 的定义

GeoTask 可以定义为：

> **面向智能体的可验证时空任务表示与执行协议。它使用统一的对象、算子、断言、执行计划和输出契约描述时空任务，使模型推理能够与本地确定性计算分离，并支持结果验证、证据治理、冲突处理、任务阻断和条件恢复。**

这一概念包含四个关键词。

### 2.1 面向智能体

GeoTask 文档既要让程序解析，也要让大模型理解。字段名称、对象引用和任务目标应保持明确，避免只对某个内部库可读。

### 2.2 时空任务

GeoTask 的核心对象不仅是几何图形，还包括时间区间、高度区间、移动对象、资源约束和任务上下文。空间关系只有与时间、对象能力和业务规则组合后，才能支撑真实行动。

### 2.3 可验证

模型产生的答案不是最终事实。可确定计算应由本地执行器复算，模型结果与本地结果应能够比较。无法验证时，系统应显式返回 `unverifiable`、`need_data` 或复核任务，而不是强行生成真假结论。

### 2.4 协议而非应用

GeoTask 不负责提供完整地图、设备控制、行业审批或商业调度。它定义这些系统之间如何表达和交换任务、断言、执行结果和治理状态。

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

公共 Core 当前支持：

- `point`
- `polyline`
- `rect`
- `time_interval`
- `altitude_interval`
- `feature_collection`

对象必须具有稳定 id，并在断言中通过 `object_refs` 引用。对象数据可以使用 v1 原生字段，也可以通过兼容层读取部分旧字段。

### 4.2 算子

公共 Core 当前提供六个本地确定性算子：

| 算子 | 作用 |
|---|---|
| `distance_2d` | 二维点到点欧氏距离 |
| `line_intersects_rect` | 折线是否接触或穿过轴对齐矩形 |
| `point_to_line_distance_2d` | 点到线段的最短距离 |
| `rect_contains_point` | 矩形是否包含点，边界计入 |
| `time_overlap` | 两个闭时间区间是否重叠 |
| `altitude_overlap` | 两个闭高度区间是否重叠 |

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

## 7. GT01–GT14 渐进式案例

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
- GT01–GT14 Cookbook。

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
- [GT01–GT14 Cookbook](../cookbook/gt01-gt14.md)
- [Status and Assurance Model](../reference/status-model.md)
- [Evidence and Recovery](../reference/evidence-and-recovery.md)
- [Machine-readable JSON Schema](../../schemas/geotask-v1.0.schema.json)
- [Target Specification Status](../spec/target-specification-status.md)
