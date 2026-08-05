# GeoTask轨迹与移动对象Profile v0.1

状态：公共实现已落地  
参考案例：GT33—GT36
范围：仅表达离散观测、相邻样本指标、调用方显式分段分类与受限标量加速度估计

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

合同要求：

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
- `distance_in_horizontal_unit`，继承文档Space合同中的水平单位；
- `average_speed_in_horizontal_units_per_second`。

分段算子不会把平均速度当作瞬时速度，也不执行插值、平滑、重采样、预测、地图匹配、外部真实性验证、生产发布、指令发送、动作授权或动作执行。

`trajectory_segment_classifications(trajectory, parameters...)`为每个相邻分段增加一个封闭分类状态：`stationary_candidate`、`moving_observed`、`observation_gap`或`unverifiable`。调用方必须显式提供：

- `stationary_radius_in_horizontal_unit`：文档水平单位下的有限非负距离；
- `minimum_stationary_duration_seconds`：有限正数持续时间；
- `maximum_observation_gap_seconds`：有限正数持续时间；
- `allow_observation_gap`：决定超限间隔是否允许标记为`observation_gap`的布尔值。

只有当分段距离不超过声明半径且持续时间达到声明下限时，才输出`stationary_candidate`。持续时间超过最大观测间隔时，仅在允许缺口标记的情况下输出`observation_gap`；否则输出`unverifiable`。其他有效分段输出`moving_observed`。Core不选择默认阈值，不推断失联或异常，不证明连续停留，也不在缺口中插值。

`trajectory_segment_acceleration_estimates(trajectory, parameters...)`为每一对相邻轨迹分段生成一条速度转换记录。调用方必须显式声明`representative_time_method: segment_midpoint`和有限正数`maximum_observation_gap_seconds`。每个分段平均速度绑定到该段时间中点，标量加速度按“后一段平均速度减前一段平均速度，再除以两个中点之间的秒数”计算。任一参与分段超过最大观测间隔时，转换状态为`unverifiable`，速度差和加速度均为`null`。该算子不宣称瞬时或向量加速度，不推断方向变化，不插值、平滑或预测，也不授权现实动作。

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
- GT36缺失中点方法或最大间隔参数、使用`segment_midpoint`之外的方法，或最大间隔非有限/不大于零。

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
- `site/gt33/index.html`
- `site/gt34/index.html`
- `site/gt35/index.html`
- `site/gt36/index.html`
