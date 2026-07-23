# GeoTask Specification v1.0（目标规范草案）

**状态：Draft**
**定位：GeoTask 体系级目标规范，不等同于当前仓库实现**
**适用对象：大模型、开发者、本地执行器、Runtime、Domain Pack、测评系统**

将 GeoTask 定义为：

> **面向大模型空间推理的双执行任务协议。GeoTask 使用统一的对象、约束、算子、断言、任务图和输出契约描述地理任务，使任务既能由推理大模型端到端执行，也能由本地确定性算子执行，并支持模型执行、本地执行和混合执行结果之间的验证、比较与治理。**

---

# 1. 规范性术语

本文使用以下规范性术语：

* **MUST／必须**：实现若不满足，则不符合本规范。
* **MUST NOT／不得**：实现绝对禁止的行为。
* **SHOULD／应当**：强烈推荐，偏离时应说明理由。
* **SHOULD NOT／不应**：通常不建议。
* **MAY／可以**：可选能力。

---

# 2. 设计目标

GeoTask v1.0 必须解决六类核心问题。

## 2.1 空间意图结构化

将自然语言请求转换成显式空间任务：

```text
用户问题
→ 对象
→ 约束
→ Task Family
→ 算子
→ 参数绑定
→ 执行图
→ 输出契约
```

## 2.2 模型可执行

GeoTask 文档必须能够由推理大模型直接理解和执行。

即使没有：

* Python；
* GIS 库；
* 本地算子；
* 外部工具；
* Runtime；

模型仍应能对规模受控的任务进行端到端计算。

## 2.3 本地可执行

同一 GeoTask 文档必须能够由本地确定性执行器解释和执行。

## 2.4 双路可比较

模型执行结果和本地执行结果必须使用兼容的结果格式，从而支持：

```text
Model Result ↔ Local Result
```

自动比较。

## 2.5 结果可验证

GeoTask 必须区分：

* 任务是否完成；
* 结果是否正确；
* 结果由谁计算；
* 结果经过什么验证；
* 结果达到何种可信保证等级。

## 2.6 行业可扩展

GeoTask Core 只定义通用空间任务基础能力。

行业对象、行业规则、行业阈值、审批流程和人工复核要求应由 Domain Pack 扩展，不应污染 Core 语义。

---

# 3. 非目标

GeoTask Core 本身不是：

* GIS 数据库；
* GeoJSON 替代品；
* 地图渲染引擎；
* 大规模空间计算平台；
* 模型 API 网关；
* 行业审批系统；
* 监管结论系统；
* 完整业务工作流平台；
* 自动驾驶、无人机或通信网络专用系统。

GeoTask 可以调用或连接这些能力，但不直接替代它们。

---

# 4. 总体体系架构

```text
┌────────────────────────────────────────────┐
│ 7. Domain Application                      │
│ 用户界面、业务场景、行业工作流             │
├────────────────────────────────────────────┤
│ 6. Domain Pack                             │
│ 行业对象、行业规则、模板、报告、复核规则   │
├────────────────────────────────────────────┤
│ 5. Governance & Evaluation                 │
│ 审计、测评、可信等级、人工复核、成本治理   │
├────────────────────────────────────────────┤
│ 4. GeoTask Runtime                         │
│ Model / Local / Connector / Human 编排     │
├────────────────────────────────────────────┤
│ 3. GeoTask IR                              │
│ 对象、约束、断言、任务图、输出契约         │
├────────────────────────────────────────────┤
│ 2. Task Compiler                           │
│ 意图识别、对象抽取、分解、算子绑定         │
├────────────────────────────────────────────┤
│ 1. Operator & Data Foundation              │
│ 本地算子、模型算子契约、数据连接器         │
└────────────────────────────────────────────┘
```

## 4.1 GeoTask Core

Core 负责：

* GeoTask IR；
* Schema；
* 对象类型；
* Operator Contract；
* 本地确定性算子；
* Parser；
* Validator；
* Result Schema；
* CLI；
* 基础 Evaluator。

Core MUST NOT：

* 保存模型凭据；
* 调用外部模型；
* 连接业务数据库；
* 包含行业审批规则；
* 执行商业模型路由策略。

## 4.2 GeoTask Runtime

Runtime 负责：

* 调用模型；
* 选择执行模式；
* 任务分解与编排；
* 调用数据连接器；
* 运行本地执行器；
* Shadow Compare；
* 结果治理；
* 成本与配额；
* 审计记录。

## 4.3 Domain Pack

Domain Pack 负责：

* 行业对象；
* 行业任务模板；
* 行业规则；
* 行业算子映射；
* 数据连接器配置；
* 报告模板；
* 人工复核要求。

---

# 5. 执行模式

GeoTask 必须支持四种执行模式。

## 5.1 `model_only`

大模型端到端完成：

```text
GeoTask IR
→ 理解任务
→ 构建执行计划
→ 执行计算
→ 自检
→ 输出结构化结果
```

适用于：

* 轻量任务；
* 小规模数据；
* 教学与研究；
* 零部署环境；
* 无本地 GIS 运行环境；
* 快速验证。

## 5.2 `local_only`

本地确定性执行：

```text
GeoTask IR
→ Parser
→ Assertion Dispatcher
→ Local Operators
→ Structured Result
```

适用于：

* 精确计算；
* 批处理；
* Ground Truth；
* 高稳定性要求；
* 大规模或复杂计算。

## 5.3 `hybrid`

模型与本地协同：

```text
自然语言
→ 模型编译 GeoTask
→ 本地执行确定性算子
→ 模型处理开放语义
→ 本地验证
→ 模型生成解释
```

这是生产环境推荐模式。

## 5.4 `shadow_compare`

同一任务由模型和本地系统独立执行：

```text
                 ┌→ Model Executor ─┐
GeoTask IR ──────┤                  ├→ Comparator
                 └→ Local Executor ─┘
```

用于：

* Benchmark；
* 模型能力画像；
* 错误分析；
* 确定 Model Executability Level；
* 发布质量门禁。

---

# 6. 编码、执行与验证必须分离

## 6.1 Encoding Type

表示任务如何表达：

```text
natural_language
geotask_yaml
geotask_json
compact_dsl
```

## 6.2 Execution Mode

表示任务由谁执行：

```text
model_only
local_only
hybrid
shadow_compare
```

## 6.3 Verification Mode

表示如何验证：

```text
none
model_self_check
local_deterministic
model_local_compare
cross_model_compare
human_review
```

## 6.4 Assurance Level

表示结果达到的可信等级：

```text
unverified
model_generated
model_self_checked
local_deterministic
model_local_agreement
independent_cross_verified
human_reviewed
```

这四个概念不得混用。

---

# 7. GeoTask 文档格式

推荐文件扩展名：

```text
.geotask.yaml
.geotask.yml
.geotask.json
```

YAML 是标准人类可读表示，JSON 是标准机器交换表示。

---

# 8. 顶层结构

GeoTask v1.0 标准结构如下：

```yaml
geotask:
space:
objects:
operator_set:
operator_contracts:
tasks:
execution:
verification:
output_contract:
extensions:
expected_results:
```

## 8.1 必需字段

必须包含：

```text
geotask
space
objects
tasks
execution
output_contract
```

## 8.2 可选字段

可以包含：

```text
operator_set
operator_contracts
verification
extensions
expected_results
```

`expected_results` 主要用于测试、Benchmark 和 Golden Cases，不应作为普通生产任务的必要字段。

---

# 9. `geotask` 元数据

```yaml
geotask:
  id: "site-filter-001"
  name: "Candidate site proximity filtering"
  description: "Filter candidate sites using spatial constraints."
  schema_version: "1.0"
  language: "zh-CN"
  domain: "general_spatial"
  created_at: "2026-07-20T06:00:00Z"
  tags:
    - proximity
    - filtering
```

## 9.1 字段

| 字段               | 类型       | 必需 | 说明                   |
| ---------------- | -------- | -: | -------------------- |
| `id`             | string   |  是 | 文档唯一标识               |
| `name`           | string   |  是 | 人类可读名称               |
| `description`    | string   |  否 | 任务说明                 |
| `schema_version` | string   |  是 | GeoTask Schema 版本    |
| `language`       | string   |  否 | 默认自然语言               |
| `domain`         | string   |  否 | 默认 `general_spatial` |
| `created_at`     | RFC 3339 |  否 | 创建时间                 |
| `tags`           | string[] |  否 | 标签                   |

## 9.2 ID 约束

所有 ID MUST 满足：

```regex
^[A-Za-z][A-Za-z0-9_.-]{0,127}$
```

ID 必须在其作用域内唯一。

---

# 10. `space` 空间基准

```yaml
space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  axes:
    x: "east"
    y: "north"
  horizontal_unit: "meter"
  vertical_unit: "meter"
  coordinate_order: ["x", "y"]
  precision:
    decimal_places: 3
    tolerance: 0.01
```

## 10.1 CRS 类型

标准类型：

```text
local_cartesian
projected
geographic
unknown
```

## 10.2 地理坐标

若：

```yaml
type: geographic
```

则必须声明：

```yaml
coordinate_order: ["longitude", "latitude"]
```

不得依靠默认推断经纬度顺序。

## 10.3 CRS 转换

Core Minimal Profile 不要求实现 CRS 转换。

若任务中的对象使用不同 CRS：

* Validator MUST 报错；或
* Runtime MUST 在执行前显式插入转换步骤。

不得静默混算。

---

# 11. 对象模型

## 11.1 基础对象

GeoTask Standard Profile 定义以下对象类型：

```text
point
polyline
polygon
rect
circle
time_interval
altitude_interval
scalar
table
graph
raster_ref
feature_collection
```

Core Minimal Profile 可以只实现其中一部分。

---

## 11.2 Point

```yaml
site_a:
  type: point
  coordinates: [100.0, 50.0]
```

兼容字段：

```yaml
xy: [100.0, 50.0]
```

`xy` 在兼容期内可接受，但标准字段应为 `coordinates`。

---

## 11.3 Polyline

```yaml
route_a:
  type: polyline
  coordinates:
    - [0, 0]
    - [10, 0]
    - [20, 10]
```

本规范中 polyline 的所有连续点对均构成有效 segment。

执行器不得只处理第一段而忽略其余点。

---

## 11.4 Polygon

```yaml
zone_a:
  type: polygon
  rings:
    -
      - [0, 0]
      - [10, 0]
      - [10, 10]
      - [0, 10]
      - [0, 0]
```

要求：

* 外环必须闭合；
* 每个环至少四个坐标；
* 第一个坐标和最后一个坐标必须相同；
* Hole 作为后续 ring 表示。

---

## 11.5 Rectangle

```yaml
zone_rect:
  type: rect
  bbox: [0, 0, 10, 10]
```

要求：

```text
min_x <= max_x
min_y <= max_y
```

---

## 11.6 Circle

```yaml
buffer_area:
  type: circle
  center: [10, 20]
  radius: 500
  unit: meter
```

---

## 11.7 Time Interval

```yaml
window_a:
  type: time_interval
  start: "2026-07-20T08:00:00Z"
  end: "2026-07-20T10:00:00Z"
```

短时教学任务可以使用：

```yaml
interval: ["08:00", "10:00"]
```

但必须声明时区或表明这是无日期的本地时段。

---

## 11.8 Altitude Interval

```yaml
band_a:
  type: altitude_interval
  min: 100
  max: 200
  unit: meter
  datum: "relative"
```

---

## 11.9 Feature Collection

```yaml
candidate_sites:
  type: feature_collection
  feature_type: point
  features:
    - id: site_1
      coordinates: [0, 0]
    - id: site_2
      coordinates: [10, 20]
```

---

## 11.10 External Reference

大型对象可以使用引用：

```yaml
road_network:
  type: graph
  source_ref: "connector://city-road-network/v1"
  content_hash: "sha256:..."
```

Core 不负责获取数据，但必须保留引用。

---

# 12. Task 模型

GeoTask 使用 `tasks` 列表描述一个或多个任务。

```yaml
tasks:
  - id: "filter_candidates"
    family: "spatial_filter"
    goal: "Select sites within 500 meters of a road and outside restricted zones."
    inputs:
      - candidate_sites
      - roads
      - restricted_zones
    constraints:
      - id: road_distance
        expression:
          operator: within_distance
          object_refs: [candidate_sites, roads]
          parameters:
            threshold: 500
            unit: meter
      - id: exclusion
        expression:
          operator: intersects
          object_refs: [candidate_sites, restricted_zones]
          expected: false
    assertions:
      - id: nearest_road_distance
        operator: nearest_distance
        object_refs: [candidate_sites, roads]
      - id: restricted_zone_intersection
        operator: intersects
        object_refs: [candidate_sites, restricted_zones]
    outputs:
      - selected_sites
```

---

# 13. Task Family

GeoTask v1.0 定义十类顶层任务。

| 编号  | Task Family               | 说明              |
| --- | ------------------------- | --------------- |
| T01 | `object_extraction`       | 识别空间对象          |
| T02 | `constraint_extraction`   | 抽取阈值、条件和偏好      |
| T03 | `measurement`             | 距离、长度、面积、方位     |
| T04 | `spatial_relation`        | 相交、包含、邻接、重叠     |
| T05 | `spatiotemporal_relation` | 时间、高度和轨迹关系      |
| T06 | `spatial_query`           | 查询、过滤、最近邻、Top-K |
| T07 | `network_routing`         | 路径、可达性、网络分析     |
| T08 | `spatial_evaluation`      | 多指标评价、风险和适宜性    |
| T09 | `planning_optimization`   | 选址、规划、调度和优化     |
| T10 | `explanation_review`      | 解释、报告、缺口和复核     |

Domain Pack 可以增加二级分类，但不得修改顶层 Task Family 的基本语义。

---

# 14. Assertion

Assertion 是 GeoTask 的标准可执行单元。

```yaml
assertions:
  - id: "a_to_b_distance"
    operator: "distance_2d"
    object_refs: ["a", "b"]
    parameters: {}
    expected_type: number
    unit: meter
```

## 14.1 Assertion 必需字段

```text
id
operator
object_refs
```

## 14.2 Assertion 可选字段

```text
parameters
expected_type
unit
tolerance
depends_on
condition
on_error
```

## 14.3 多次调用

同一 operator 可以在一个任务中被调用多次。

执行器必须通过 assertion ID 区分调用，不得将 operator name 当作唯一执行 ID。

## 14.4 显式绑定

执行器必须根据：

```text
assertion.operator
assertion.object_refs
assertion.parameters
```

执行任务。

不得根据“对象出现顺序”自动猜测计算对象，除非任务明确使用自动绑定模式。

---

# 15. Operator Contract

每个算子必须具有完整契约。

```yaml
operator_contracts:
  distance_2d:
    version: "1.0"
    family: measurement
    description: "Euclidean distance between two planar points."
    arity: 2
    input_types: [point, point]
    output:
      type: number
      unit_behavior: inherit_horizontal_unit
    deterministic: true

    semantics:
      formula: "sqrt((x2-x1)^2 + (y2-y1)^2)"
      boundary_rules:
        - "Distance is non-negative."
        - "Identical points produce zero."
        - "Do not interpret coordinates as geographic unless CRS is geographic."

    model_execution:
      level: M1
      supported: true
      recommended_max_items: 50
      precision_tolerance: 0.01

    invariants:
      - id: non_negative
        expression: "result >= 0"
      - id: symmetric
        expression: "distance(a,b) == distance(b,a)"

    examples:
      - inputs:
          a: [0, 0]
          b: [3, 4]
        expected: 5
```

---

# 16. Operator 分类

## 16.1 确定性算子

由本地系统或模型按照确定规则执行。

### Measurement

```text
distance_2d
point_to_polyline_distance
polyline_length
polygon_area
rect_area
bearing
```

### Topology

```text
intersects
contains
within
touches
overlaps
disjoint
```

### Proximity

```text
within_distance
nearest_object
nearest_distance
buffer
```

### Temporal

```text
time_overlap
before
after
during
```

### Vertical

```text
altitude_overlap
vertical_distance
```

### Query

```text
filter
spatial_join
top_k
sort_by
```

### Network

```text
shortest_path
reachable
service_area
path_length
```

### Aggregation

```text
count
sum
mean
min_by
max_by
group_by
```

---

## 16.2 语义算子

语义算子主要由模型执行：

```text
classify_task
extract_objects
extract_constraints
resolve_ambiguity
select_operator
bind_arguments
decompose_task
identify_data_gap
generate_explanation
summarize_evidence
```

语义算子输出默认不得标记为 `local_deterministic`。

---

## 16.3 复合算子

复合算子由多个标准算子构成：

```text
constrained_filter
candidate_ranking
route_with_exclusions
multi_criteria_evaluation
```

复合算子必须展开为可追踪的执行图。

---

# 17. Model Executability Level

每个算子必须声明模型可执行等级。

## M0：不支持模型独立执行

典型场景：

* 百万级空间连接；
* 复杂多边形布尔运算；
* 高精度投影；
* 大型路网；
* 高分辨率栅格；
* 安全关键精确计算。

## M1：模型适合执行

典型场景：

* 两点距离；
* 矩形包含点；
* 时间区间重叠；
* 高度区间重叠；
* 简单计数；
* 小集合最大最小值。

## M2：模型条件执行

要求限制对象和步骤规模。

例如：

```yaml
model_execution:
  level: M2
  max_objects: 20
  max_segments: 20
  max_steps: 16
  local_verification_recommended: true
```

## M3：模型生成候选，本地或人工确认

例如：

* 复杂选址；
* 多目标规划；
* 风险评价；
* 复杂路径优化；
* 空间模式解释。

---

# 18. 执行图

```yaml
execution:
  mode: hybrid
  steps:
    - id: compile_constraints
      executor: model
      operation: extract_constraints
      outputs: [normalized_constraints]

    - id: calculate_distances
      executor: local
      assertion_refs: [nearest_road_distance]
      depends_on: [compile_constraints]

    - id: apply_exclusion
      executor: local
      assertion_refs: [restricted_zone_intersection]
      depends_on: [compile_constraints]

    - id: explain_result
      executor: model
      operation: generate_explanation
      depends_on:
        - calculate_distances
        - apply_exclusion
```

## 18.1 Executor

允许：

```text
model
local
connector
human
runtime
```

## 18.2 依赖

执行图必须是有向无环图，除非 Runtime 明确支持循环。

Core v1.0 不要求支持循环执行。

## 18.3 条件执行

```yaml
condition:
  expression: "previous.status == completed"
```

## 18.4 错误策略

```yaml
on_error: stop
```

允许：

```text
stop
skip
continue
need_review
fallback
```

---

# 19. Model-Only 执行协议

Model-Only 执行器必须按以下逻辑工作。

## 19.1 Task Understanding

输出：

```yaml
task_understanding:
  task_family: measurement
  required_objects: [a, b]
  required_operators: [distance_2d]
  ambiguities: []
```

## 19.2 Execution Planning

```yaml
execution_plan:
  - step_id: calculate_distance
    operator: distance_2d
    object_refs: [a, b]
```

## 19.3 Computation

按照 Operator Contract 计算。

## 19.4 Invariant Check

运行算子契约中的 invariant。

## 19.5 Constraint Check

确认：

* 所有对象均已使用；
* 所有约束均已处理；
* 未使用非法算子；
* 未修改原始输入；
* 未产生无证据结论。

## 19.6 Structured Result

必须按照统一 Result Schema 输出。

---

# 20. 最小可核查执行证据

GeoTask 不要求模型输出完整内部思维链。

模型应输出最小结构化执行证据：

```yaml
execution_evidence:
  - step_id: calculate_distance
    assertion_id: a_to_b_distance
    executor: model
    operator: distance_2d
    object_refs: [a, b]
    normalized_inputs:
      a: [0, 0]
      b: [3, 4]
    result: 5
    invariant_checks:
      non_negative: passed
      symmetric: passed
```

不得强制模型输出自由形式的完整思维过程。

---

# 21. Verification Policy

```yaml
verification:
  mode: model_local_compare
  required_assurance: model_local_agreement
  compare:
    numeric_tolerance: 0.01
    boolean_exact: true
    collection_order: insensitive
  failure_policy:
    mismatch: contradicted
    missing_result: need_review
    unsupported_operator: invalid_operator
```

---

# 22. 结果模型

结果必须区分三个维度。

## 22.1 Execution Status

```text
pending
running
completed
partial
failed
skipped
```

## 22.2 Claim Status

```text
proposed
computed
verified
contradicted
need_review
need_data
invalid_input
invalid_operator
invalid_reference
execution_error
unverifiable
```

## 22.3 Assurance Level

```text
unverified
model_generated
model_self_checked
local_deterministic
model_local_agreement
independent_cross_verified
human_reviewed
```

---

# 23. 标准结果结构

```yaml
geotask_result:
  schema_version: "1.0"
  task_id: "site-filter-001"

  execution:
    mode: hybrid
    status: completed
    started_at: "2026-07-20T06:00:00Z"
    finished_at: "2026-07-20T06:00:01Z"

  checks:
    - assertion_id: nearest_road_distance
      operator: nearest_distance
      object_refs: [candidate_sites, roads]
      executor: local
      value:
        site_1: 320
        site_2: 710
      unit: meter
      status: verified
      assurance_level: local_deterministic
      deterministic: true
      evidence_refs: []

  outputs:
    selected_sites:
      - site_1

  summary:
    total_checks: 2
    verified: 2
    contradicted: 0
    need_review: 0
    invalid: 0

  overall:
    status: verified
    assurance_level: model_local_agreement

  warnings: []
  errors: []
```

---

# 24. Assurance 规则

## 24.1 模型独立输出

```yaml
status: computed
assurance_level: model_generated
```

## 24.2 模型完成自检

```yaml
status: computed
assurance_level: model_self_checked
```

不能仅因为模型自检通过就标记为：

```text
local_deterministic
model_local_agreement
```

## 24.3 本地执行

```yaml
status: verified
assurance_level: local_deterministic
```

前提是：

* 输入有效；
* operator 注册；
* object type 匹配；
* 执行成功。

## 24.4 模型与本地一致

```yaml
status: verified
assurance_level: model_local_agreement
```

## 24.5 人工确认

```yaml
assurance_level: human_reviewed
```

应同时记录 reviewer reference，而不是覆盖原始执行记录。

---

# 25. Output Contract

```yaml
output_contract:
  format: structured
  required_fields:
    - site_id
    - nearest_road_distance
    - intersects_restricted_zone
    - selected
  ordering:
    by: nearest_road_distance
    direction: ascending
  allow_additional_fields: false
  allow_model_inference: false
  numeric_precision:
    decimal_places: 2
```

Output Contract 必须明确：

* 必需字段；
* 类型；
* 单位；
* 排序；
* 是否允许额外字段；
* 是否允许模型推断；
* 缺失字段处理。

---

# 26. 数据缺口

若任务缺少必需输入，系统不得伪造数据。

标准输出：

```yaml
status: need_data
missing_data:
  - id: roads
    reason: "Required for nearest road distance."
    acquisition_hint: "Provide a road polyline collection or connector reference."
```

数据缺口与人工复核应区分：

* `need_data`：缺少输入；
* `need_review`：输入存在，但结论不能自动确认。

---

# 27. Extension 机制

```yaml
extensions:
  com.example.facility_siting:
    version: "1.0"
    data:
      priority_policy: balanced
```

## 27.1 命名空间

自定义扩展必须使用命名空间：

```text
组织或域名反写 + 扩展名称
```

## 27.2 扩展约束

扩展：

* MUST NOT 修改 Core operator 的语义；
* MUST NOT 覆盖标准字段；
* MUST NOT 静默改变单位或 CRS；
* MUST 声明版本；
* SHOULD 提供独立 Schema。

---

# 28. Domain Pack Contract

每个 Domain Pack 应声明：

```yaml
domain_pack:
  id: "example.facility_siting"
  version: "1.0"
  compatible_geotask_versions: [">=1.0,<2.0"]
  object_types: []
  task_templates: []
  operator_mappings: []
  rule_sets: []
  report_templates: []
  review_policies: []
  disclaimers: []
```

Domain Pack 不得直接修改 Core Registry。

新增行业算子必须使用命名空间，例如：

```text
example.facility_siting.accessibility_score
```

---

# 29. Validation

Validator 至少必须检查：

## 29.1 文档结构

* 缺失必需字段；
* 未知字段；
* 字段类型；
* 重复 YAML key；
* 重复 ID；
* Schema 版本。

## 29.2 空间对象

* 坐标必须为有限数字；
* 点坐标维度；
* polyline 点数；
* polygon 闭合；
* bbox 顺序；
* interval 顺序；
* 单位合法性；
* CRS 一致性。

## 29.3 Assertion

* operator 是否存在；
* object_refs 是否存在；
* arity 是否匹配；
* object type 是否匹配；
* parameters 是否完整；
* depends_on 是否存在；
* 是否存在依赖环。

## 29.4 执行策略

* mode 是否受支持；
* model_only 是否超过规模上限；
* required assurance 是否可由当前模式达到；
* fallback 是否有效。

## 29.5 输出契约

* required_fields 是否重复；
* 类型是否有效；
* 单位是否一致；
* 是否存在无法生成的输出。

---

# 30. 标准错误码

```text
missing_field
unknown_field
invalid_type
duplicate_id
duplicate_key
unknown_object_type
invalid_coordinates
invalid_geometry
invalid_interval
invalid_crs
unit_mismatch
invalid_operator
invalid_reference
arity_mismatch
object_type_mismatch
unsupported_execution_mode
execution_limit_exceeded
cyclic_dependency
missing_data
unverifiable_claim
execution_error
output_contract_violation
```

每个错误必须包含：

```yaml
path:
code:
message:
suggested_fix:
severity:
```

---

# 31. GeoTask 测评体系

GeoTask 的有效性必须通过分层测评证明。

## 31.1 Task Compilation Evaluation

指标：

```text
Task Family Accuracy
Object Extraction Precision / Recall / F1
Constraint Extraction F1
Operator Selection Accuracy
Object Binding Accuracy
Argument Completeness
Task Graph Exact Match
Task Graph Semantic Match
```

## 31.2 Operator Execution Evaluation

指标：

```text
Operator Accuracy
Boundary Case Accuracy
Numerical Error
Determinism
Repeatability
Invalid Input Rejection Rate
```

## 31.3 Verification Evaluation

指标：

```text
Contradiction Recall
Invalid Operator Recall
Invalid Reference Recall
Unit Error Recall
Constraint Omission Recall
Unverifiable Claim Recall
False Verification Rate
False Review Rate
```

其中：

> **False Verification Rate 是最重要的发布红线。**

## 31.4 End-to-End Evaluation

指标：

```text
Task Success Rate
Constraint Satisfaction Rate
Output Contract Compliance
Traceability Rate
Data Gap Detection Rate
Human Review Rate
Fail-Safe Rate
```

## 31.5 Robustness Evaluation

覆盖：

* 中文和英文；
* 口语和书面语；
* 同义表达；
* 否定表达；
* 对象顺序变化；
* 格式变化；
* Markdown；
* YAML-like；
* 缺失数据；
* 干扰文本；
* 矛盾输入。

## 31.6 Efficiency Evaluation

指标：

```text
Prompt Tokens
Completion Tokens
Model Calls
Latency
Local Compute Time
Total Cost
Accuracy per Cost
Verified Result per Cost
```

---

# 32. 标准 Benchmark

## 32.1 OperatorBench

验证单个本地和模型算子：

* 正常案例；
* 边界案例；
* 异常输入；
* 数值误差；
* 对象顺序；
* 多次调用；
* 规模增长。

## 32.2 TaskCompileBench

测试自然语言到 GeoTask IR：

* Task 分类；
* 对象抽取；
* 约束抽取；
* operator 选择；
* 参数绑定；
* execution graph。

## 32.3 ModelGeoBench

测试纯大模型执行：

### L1：单算子

```text
distance
contains
intersects
time overlap
altitude overlap
```

### L2：批量同类计算

```text
多个距离
多个包含关系
多个时间窗口
```

### L3：复合任务

```text
计算
→ 过滤
→ 排序
```

### L4：执行计划构建

模型根据 GeoTask 自动构建 execution plan。

### L5：异常、自检和拒答

测试：

* 非法算子；
* 错误对象；
* 单位错误；
* 数据缺失；
* 约束遗漏；
* 超出模型执行规模。

## 32.4 HybridReasonBench

比较：

```text
Natural Language + LLM
GeoTask + LLM Model-Only
GeoTask + Local
GeoTask Hybrid
```

## 32.5 VerificationBench

主动注入：

* 错误数值；
* 错误布尔值；
* 错误对象；
* 非法 operator；
* 单位错误；
* 缺少条件；
* 幻觉字段；
* 不可验证结论。

---

# 33. 标准对比实验

每个 Benchmark 应至少包含四组。

| 组别 | 输入      | 执行             |
| -- | ------- | -------------- |
| A  | 自然语言    | LLM            |
| B  | GeoTask | LLM Model-Only |
| C  | GeoTask | Local          |
| D  | GeoTask | Hybrid         |

核心研究问题：

1. GeoTask 是否提高大模型计算准确率？
2. GeoTask 是否提高对象绑定准确率？
3. GeoTask 是否降低约束遗漏？
4. Local 执行比 Model-Only 提升多少？
5. Hybrid 是否在成本、准确率和可验证性之间取得更优平衡？
6. 哪些 Task 和 Operator 适合 Model-Only？

---

# 34. Conformance Profiles

## 34.1 GeoTask IR Profile

实现必须：

* 解析 v1.0 文档；
* 验证必需字段；
* 处理对象、任务、断言；
* 生成结构化 diagnostics。

## 34.2 Local Executor Profile

除 IR Profile 外，还必须：

* 执行 assertion；
* 校验 operator arity；
* 校验 object type；
* 返回标准结果；
* 保证确定性。

## 34.3 Model Executor Profile

必须：

* 理解 Operator Contract；
* 输出 execution plan；
* 输出结构化结果；
* 执行 invariant check；
* 遵守执行规模限制；
* 不把自检结果冒充本地确定性验证。

## 34.4 Hybrid Runtime Profile

必须：

* 支持 model 和 local executor；
* 支持执行图；
* 支持结果比较；
* 支持 assurance level；
* 支持审计事件。

## 34.5 Evaluation Profile

必须：

* 运行标准 Benchmark；
* 计算规定指标；
* 输出机器可读报告；
* 保存模型、版本和参数元数据。

---

# 35. 版本管理

必须区分：

## 35.1 Package Version

例如：

```text
geotask-core 0.2.0
```

## 35.2 Schema Version

例如：

```text
GeoTask Schema 1.0
```

## 35.3 Operator Version

例如：

```text
distance_2d@1.0
```

## 35.4 Benchmark Version

例如：

```text
ModelGeoBench 0.1
```

## 35.5 Domain Pack Version

例如：

```text
facility-siting-pack 1.2.0
```

这些版本不得混用。

---

# 36. 向后兼容

当前文档：

```yaml
geotask:
space:
objects:
ops:
task:
assertions:
expected_results:
```

可以映射到 v1.0：

| 当前字段               | v1.0                                  |
| ------------------ | ------------------------------------- |
| `geotask.version`  | `geotask.schema_version`              |
| `ops`              | `operator_set` 或 `operator_contracts` |
| `task`             | 单元素 `tasks`                           |
| 顶层 `assertions`    | `tasks[].assertions`                  |
| `expected_results` | 保持 Benchmark 用途                       |
| `line`             | `polyline` 或兼容 alias                  |
| `time`             | `time_interval`                       |
| `altitude`         | `altitude_interval`                   |
| `stir`             | deprecated，不进入 v2.0                   |

---

# 37. 安全与可信边界

GeoTask 实现：

* 不得把 Model-Only 结果描述为确定性真值；
* 不得在数据缺失时虚构输入；
* 不得静默忽略未知 operator；
* 不得静默忽略多段 polyline；
* 不得静默混用不同 CRS；
* 不得静默转换单位；
* 不得把行业预审结果表述为行政审批；
* 不得把 `model_self_checked` 表述为 `local_deterministic`；
* 必须记录外部数据来源或连接器引用；
* 必须保留执行模式和 assurance level。

---

# 38. 完整示例

```yaml
geotask:
  id: "candidate-site-filter-001"
  name: "Candidate site spatial filtering"
  description: >
    Select candidate sites within 500 meters of a road and outside
    restricted zones.
  schema_version: "1.0"
  language: "en"
  domain: "general_spatial"

space:
  crs:
    type: local_cartesian
    identifier: local_xy_m
  coordinate_order: [x, y]
  horizontal_unit: meter
  precision:
    decimal_places: 2
    tolerance: 0.01

objects:
  candidate_sites:
    type: feature_collection
    feature_type: point
    features:
      - id: site_1
        coordinates: [0, 0]
      - id: site_2
        coordinates: [1000, 0]

  roads:
    type: feature_collection
    feature_type: polyline
    features:
      - id: road_1
        coordinates:
          - [-100, 100]
          - [1200, 100]

  restricted_zones:
    type: feature_collection
    feature_type: rect
    features:
      - id: zone_1
        bbox: [900, -100, 1100, 200]

operator_set:
  - nearest_distance
  - intersects
  - filter

tasks:
  - id: filter_candidates
    family: spatial_query
    goal: >
      Select candidate sites with nearest road distance <= 500 meters
      and no intersection with restricted zones.

    inputs:
      - candidate_sites
      - roads
      - restricted_zones

    assertions:
      - id: road_distance
        operator: nearest_distance
        object_refs: [candidate_sites, roads]
        parameters:
          foreach: feature
        expected_type: mapping
        unit: meter

      - id: exclusion_check
        operator: intersects
        object_refs: [candidate_sites, restricted_zones]
        parameters:
          foreach: feature
        expected_type: mapping

    outputs:
      - selected_sites

execution:
  mode: hybrid
  allowed_modes:
    - model_only
    - local_only
    - hybrid
    - shadow_compare

  model_execution_limits:
    max_objects: 20
    max_steps: 16
    numeric_tolerance: 0.01

  steps:
    - id: calculate_distances
      executor: local
      assertion_refs: [road_distance]

    - id: check_exclusions
      executor: local
      assertion_refs: [exclusion_check]

    - id: filter_results
      executor: local
      operation: filter
      depends_on:
        - calculate_distances
        - check_exclusions

    - id: explain
      executor: model
      operation: generate_explanation
      depends_on:
        - filter_results

verification:
  mode: model_local_compare
  required_assurance: model_local_agreement
  compare:
    numeric_tolerance: 0.01
    boolean_exact: true

output_contract:
  format: structured
  required_fields:
    - site_id
    - nearest_road_distance
    - intersects_restricted_zone
    - selected
  allow_additional_fields: false
  allow_model_inference: false
```

---

# 39. GeoTask v1.0 开源发布最低门禁

发布前必须至少形成：

1. **GeoTask IR Schema 1.0**
2. **Task Taxonomy 1.0**
3. **Operator Contract 1.0**
4. **Execution Mode 规范**
5. **Assurance Level 规范**
6. **Assertion-driven Local Executor**
7. **Model-Only Protocol**
8. **统一 Result Schema**
9. **OperatorBench**
10. **TaskCompileBench**
11. **ModelGeoBench**
12. **VerificationBench**
13. **Natural Language／Model-Only／Local／Hybrid 四组基线**
14. **公开安全 Core 仓库边界**
15. **规范一致性测试**

---

# 40. 推荐的 v1.0 实施范围

为了避免首版范围失控，建议开源 v1.0 首先实现：

## Task Family

```text
measurement
spatial_relation
spatiotemporal_relation
spatial_query
explanation_review
```

## 基础对象

```text
point
polyline
rect
time_interval
altitude_interval
feature_collection
```

## 确定性算子

```text
distance_2d
point_to_polyline_distance
polyline_length
line_intersects_rect
rect_contains_point
rect_intersects_rect
within_distance
nearest_distance
time_overlap
altitude_overlap
filter
count
min_by
max_by
top_k
```

## 模型语义能力

```text
classify_task
extract_objects
extract_constraints
select_operator
bind_arguments
generate_explanation
identify_data_gap
```

## 执行模式

四种模式均在规范中定义，但首版实现优先支持：

```text
model_only
local_only
shadow_compare
```

Hybrid 可以建立基础骨架，不必在首版完成复杂商业编排。

---

## 最终产品定义

> **GeoTask 是面向大模型地理推理的任务中间表示、双执行协议和验证框架。它将自然语言地理问题表示为显式对象、约束、算子、断言和任务图，使推理大模型能够端到端执行轻量地理任务，同时允许本地确定性系统执行同一任务，并通过统一结果、可信等级和测评体系实现相互验证。**

这份规范应作为后续 `GeoTask Specification v1.0` 的母文档；当前 `format_spec.md`、`geotask_yaml_schema.md`、`operator_registry.md`、`eval_spec.md` 和 Runtime Contracts 应逐步收敛到该规范。
