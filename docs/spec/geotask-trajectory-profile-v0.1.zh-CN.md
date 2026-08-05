# GeoTask轨迹与移动对象Profile v0.1

状态：公共实现已落地  
参考案例：GT33—GT39
范围：仅表达离散观测、相邻样本指标、调用方显式分段分类、受限标量加速度估计、边界样本对象同一性候选、原始字节级绑定的对象同一性审定与只读对象身份归并提案

## 目的

本Profile把移动对象身份与带时间的空间观测显式分开，防止静态折线被静默当成轨迹，也防止少量观测点被重新解释为轨迹插值、位置预测、地图匹配或动作授权。

## 移动对象

`moving_object`只声明身份：

```yaml
uav_alpha:
  type: moving_object
  object_class: uav
  identity: fictional-uav-alpha
```

必填字段：

- `object_class`：调用方声明的非空对象类别；
- `identity`：调用方声明的非空稳定身份。

位置、时间、速度、预测和指令状态不得内嵌在移动对象中，未声明字段失败关闭。

## 轨迹

`trajectory`把明确观测绑定到一个移动对象：

```yaml
uav_alpha_track:
  type: trajectory
  subject_ref: uav_alpha
  interpolation: none
  samples:
    - observed_at: "2026-08-05T08:00:00+08:00"
      coordinates: [0, 0]
    - observed_at: "2026-08-05T08:05:00+08:00"
      coordinates: [30, 40]
```

轨迹契约要求：

- `subject_ref`必须解析到已声明的`moving_object`；
- `interpolation`必须严格为`none`；
- 至少包含两个样本；
- 每个样本只能包含`observed_at`和`coordinates`；
- `observed_at`必须是带时区的ISO 8601/RFC3339时间；
- 样本时间必须严格递增；
- 坐标必须是按文档坐标顺序给出的两个有限数值。

## 确定性算子

`trajectory_duration_seconds(trajectory)`返回第一个和最后一个明确样本之间的秒数。

`trajectory_segment_metrics(trajectory)`为每一对相邻明确样本生成一条有序分段记录。每条记录绑定起止样本索引、时间戳和坐标，并输出：

- `duration_seconds`；
- `distance_in_horizontal_unit`，继承文档空间参考与单位约束中的水平单位；
- `average_speed_in_horizontal_units_per_second`。

分段算子不会把平均速度当作瞬时速度，也不执行插值、平滑、重采样、预测、地图匹配、外部真实性验证、生产发布、指令发送、动作授权或动作执行。

`trajectory_segment_classifications(trajectory, parameters...)`为每个相邻分段增加一个封闭分类状态：`stationary_candidate`、`moving_observed`、`observation_gap`或`unverifiable`。调用方必须显式提供：

- `stationary_radius_in_horizontal_unit`：文档水平单位下的有限非负距离；
- `minimum_stationary_duration_seconds`：有限正数持续时间；
- `maximum_observation_gap_seconds`：有限正数持续时间；
- `allow_observation_gap`：决定超限间隔是否允许标记为`observation_gap`的布尔值。

只有当分段距离不超过声明半径且持续时间达到声明下限时，才输出`stationary_candidate`。持续时间超过最大观测间隔时，仅在允许缺口标记的情况下输出`observation_gap`；否则输出`unverifiable`。其他有效分段输出`moving_observed`。Core不选择默认阈值，不推断失联或异常，不证明连续停留，也不在缺口中插值。

`trajectory_segment_acceleration_estimates(trajectory, parameters...)`为每一对相邻轨迹分段生成一条速度转换记录。调用方必须显式声明`representative_time_method: segment_midpoint`和有限正数`maximum_observation_gap_seconds`。每个分段平均速度绑定到该段时间中点，标量加速度按“后一段平均速度减前一段平均速度，再除以两个中点之间的秒数”计算。任一参与分段超过最大观测间隔时，转换状态为`unverifiable`，速度差和加速度均为`null`。该算子不宣称瞬时或向量加速度，不推断方向变化，不插值、平滑或预测，也不授权现实动作。

`trajectory_identity_candidate(first_trajectory, second_trajectory, parameters...)`只比较前一轨迹最后一个明确样本与后一轨迹第一个明确样本。调用方必须声明有限正数`maximum_identity_gap_seconds`、有限非负`maximum_identity_distance_in_horizontal_unit`和布尔值`require_same_object_class`。正时间差超过上限时先返回`unverifiable`；否则，要求同类但类别不同或边界距离超限时返回`different_object_candidate`，类别相容且时间、距离均在阈值内时返回`same_object_candidate`。结果保留两条轨迹引用、主体引用、对象类别、边界样本、时间差、距离和策略，不合并身份、不改写`subject_ref`、不证明现实身份、不插值路径、不预测、不发布、不授权也不执行动作。

GT38新增注册制品`geotask.trajectory-identity-adjudication`，将GT37执行结果原始字节级绑定到验证请求、调用方声明的可信保证策略，以及成对的验证提供方描述符和验证响应。策略可以输出`same_object_confirmed`、`different_objects_confirmed`或`unresolved`，并建议进入对象身份归并复核、保持身份分离或继续补证。即使输出同一对象确认，两个临时主体仍保持独立，外部身份真实性、对象身份归并、`subject_ref`改写、生产环境发布、授权和执行仍为假。详见[Trajectory Identity Adjudication v0.1](geotask-trajectory-identity-adjudication-v0.1.md)。

GT39新增注册制品`geotask.identity-merge-proposal`。它只接受满足GT38同一对象确认、候选一致、建议进入归并复核且所有非执行边界保持为假的审定结果。调用方必须从两个现有主体引用中选择一个`canonical_subject_ref`作为主对象引用；公共核心只为另一条轨迹提出一项受限引用改写，保留非主主体为可追溯别名，记录审批角色、封闭的阻断与撤销条件，并生成该改写的逆向归并回退方案。提案不创建新身份、不删除别名、不审批自身、不修改对象关系图或世界状态，也不发布、授权或执行更新。详见[Identity Merge Proposal v0.1](geotask-identity-merge-proposal-v0.1.md)。

## 失败关闭

以下情况验证失败：

- 引用对象缺失，或引用到静态几何对象；
- 时间戳没有时区；
- 时间戳重复或倒序；
- 样本包含`predicted`等未声明字段；
- 插值方式不是`none`；
- 将静态`polyline`传给轨迹算子；
- 任一GT35阈值缺失、非有限、应为非负时却为负数、应为正数时却不大于零，或类型错误；
- 包含未声明的分类参数；
- GT36缺失中点方法或最大间隔参数、使用`segment_midpoint`之外的方法，或最大间隔非有限/不大于零；
- GT37缺失任一身份候选参数、时间/距离/类别策略非法、重复引用同一轨迹，或后一轨迹边界时间不晚于前一轨迹边界；
- GT38无法闭合候选、请求、策略、验证提供方与响应的原始字节级引用，可信保证策略未阻断自动归并和引用改写，证据冲突或不足，响应分组与审定结论不一致，或任一字段声称公共核心已归并身份、改写`subject_ref`、发布、授权或执行更新；
- GT39选择的主对象引用不属于GT38两个现有主体、扩大受影响轨迹范围、未保留别名、修改封闭的阻断或撤销条件、缺少可逆的反向改写，或声称提案已获批、已应用、已发布、已授权或已执行。

## 能力边界

有效轨迹只证明提交的离散观测序列结构有效、能够进行本地确定性计算。它不证明外部对象身份、传感器真实性或连续现实运动，也不代表生产发布、指令发送、现实授权或动作执行。

## 参考文件

- `examples/core/gt33_moving_object_trajectory.yaml`
- `examples/core/gt33_moving_object_trajectory_result.json`
- `examples/core/gt33_moving_object_trajectory.json`
- `examples/core/gt34_trajectory_segment_metrics.yaml`
- `examples/core/gt34_trajectory_segment_metrics_result.json`
- `examples/core/gt34_trajectory_segment_metrics.json`
- `examples/core/gt35_trajectory_stop_move_gap.yaml`
- `examples/core/gt35_trajectory_stop_move_gap_result.json`
- `examples/core/gt35_trajectory_stop_move_gap.json`
- `examples/core/gt36_trajectory_acceleration.yaml`
- `examples/core/gt36_trajectory_acceleration_result.json`
- `examples/core/gt36_trajectory_acceleration.json`
- `examples/core/gt37_trajectory_identity_candidate.yaml`
- `examples/core/gt37_trajectory_identity_candidate_result.json`
- `examples/core/gt37_trajectory_identity_candidate.json`
- `examples/core/trajectory_identity_adjudication_gt38.json`
- `examples/core/gt38_trajectory_identity_adjudication.json`
- `docs/spec/geotask-trajectory-identity-adjudication-v0.1.md`
- `examples/core/identity_merge_proposal_gt39.json`
- `examples/core/gt39_identity_merge_proposal.json`
- `docs/spec/geotask-identity-merge-proposal-v0.1.md`
- `site/gt33/index.html`
- `site/gt34/index.html`
- `site/gt35/index.html`
- `site/gt36/index.html`
- `site/gt37/index.html`
- `site/gt38/index.html`
- `site/gt39/index.html`
