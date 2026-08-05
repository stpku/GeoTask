# GeoTask轨迹与移动对象Profile v0.1

状态：公共实现已落地  
参考案例：GT33  
范围：仅表达离散观测

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

`trajectory_duration_seconds(trajectory)`返回第一个和最后一个明确样本之间的秒数。除结构验证外，它不解释中间几何，不计算距离、速度、加速度、插值、预测或地图匹配。

## 失败关闭

以下情况验证失败：

- 引用对象缺失，或引用到静态几何对象；
- 时间戳没有时区；
- 时间戳重复或倒序；
- 样本包含`predicted`等未声明字段；
- 插值方式不是`none`；
- 将静态`polyline`传给轨迹算子。

## 能力边界

有效轨迹只证明提交的离散观测序列结构有效、能够进行本地确定性计算。它不证明外部对象身份、传感器真实性或连续现实运动，也不代表生产发布、指令发送、现实授权或动作执行。

## 参考文件

- `examples/core/gt33_moving_object_trajectory.yaml`
- `examples/core/gt33_moving_object_trajectory_result.json`
- `examples/core/gt33_moving_object_trajectory.json`
- `site/gt33/index.html`
