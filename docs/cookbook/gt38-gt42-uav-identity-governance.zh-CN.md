# GT38—GT42：巡检无人机失联后的身份治理复合案例

## 场景

虚构巡检无人机 **UAV-017** 正在执行园区电力线路巡检：

- 08:02，系统记录失联前轨迹 `track_alpha`，主体引用为 `provisional_alpha`；
- 无人机进入建筑遮挡区后短暂失联；
- 08:03，系统在5米外恢复观测，但建立了新轨迹 `track_beta` 和临时主体 `provisional_beta`；
- 两段轨迹时间间隔60秒，对象类别均为 `uav`。

为了兼顾机器标识稳定性与人类可理解性，公开页面使用以下显示映射：

| 机器引用 | 对外显示 |
|---|---|
| `track_alpha` | 失联前轨迹 |
| `track_beta` | 恢复后轨迹 |
| `provisional_alpha` | UAV-017原始主体 |
| `provisional_beta` | 遮挡后临时主体 |

## 为什么不能直接合并

错误归并可能把另一架无人机的轨迹并入UAV-017，污染任务历史、风险判断和责任追溯；漏归并则会把同一架无人机重复计数，割裂连续任务轨迹和风险状态。

因此，GeoTask不把“同一性判断、归并提案、审批、变更请求、应用审批和实际应用”压缩成一次自动操作。

## 五个阶段

### GT38：证据审定

GT37只形成 `same_object_candidate`。GT38进一步绑定：

- 虚构资产登记系统：相同Remote ID和设备序列号；
- 虚构人工复核：任务编号、机型、运营人和时间连续性一致；
- 调用方声明的可信保证策略；
- 候选、请求、Provider描述符和响应的精确字节。

输出为 `same_object_confirmed`，但只建议 `review_identity_merge`，不归并身份。

### GT39：归并提案

调用方选择 `provisional_alpha` 作为主对象引用，将 `provisional_beta` 保留为别名。提案只覆盖两条原始轨迹，声明阻断、撤销、审批和回退要求，但不修改对象关系图。

### GT40：提案审批

`identity_governance_reviewer` 与 `world_state_maintainer` 分别作出明确决定。全部批准只使后续变更请求具备条件：

```text
approved ≠ identity_merge_performed
```

### GT41：变更请求

请求范围被收敛为一项操作：

```text
track_beta /subject_ref
provisional_beta → provisional_alpha
```

同时声明应用前置条件、应用后验收条件和逆向回退操作。请求仍不等于应用。

### GT42：应用审批

`object_graph_change_owner` 与 `world_state_governance_reviewer` 审批GT41请求。全部批准只使后续受限应用制品具备条件：

```text
application approval complete
≠ application authorized
≠ change applied
```

## 当前边界

截至GT42：

- `track_beta`仍指向`provisional_beta`；
- 两个主体记录仍然存在；
- 别名尚未实际写入对象关系图；
- World State尚未更新；
- 实际应用、应用后验收和后继World State必须由后续独立Artifact证明。

GT38—GT42是一个业务场景的五个可审计步骤，不应被理解为五个彼此无关的应用案例。
