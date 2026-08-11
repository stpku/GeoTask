# GeoTask Architecture Series v0.1

本系列不按 GT 编号解释单项能力，而是从 AI Agent 进入现实世界时面临的可信问题出发，说明 GeoTask 为什么存在、它在 Agent 软件架构中的位置、它如何处理 Unknown / Evidence / World State / Impact / Control，以及如何用一个完整 Reference Agent 把这些思想跑通。

> **事实边界：** 当前公共 GeoTask 是面向 AI 智能体的可验证时空任务协议与确定性 Core；“Trusted World-State Runtime / 可信世界状态运行时”是产品演进方向。系列文章会明确区分当前已实现能力、Reference Agent 教材行为和长期目标，不把规划能力写成既成事实。

## 推荐阅读顺序

1. [为什么 Agent 需要可信世界状态](01-why-agents-need-trusted-world-state.zh-CN.md)
2. [GeoTask 不是 Agent Framework，而是可信状态与控制层](02-geotask-is-not-an-agent-framework.zh-CN.md)
3. [Context、Tool Result 与 World State 为什么必须分开](03-context-tool-result-world-state.zh-CN.md)
4. [AI 知道自己不知道之后，下一步做什么](04-unknown-evidence-and-recovery.zh-CN.md)
5. [从可信结论到可信行动：Eligibility、Authority 与 Execution](05-from-trusted-conclusion-to-trusted-action.zh-CN.md)
6. [从头到尾做一个 GeoTask Reference Agent](06-reference-agent-end-to-end.zh-CN.md)

## 这套系列与 GT 系列的关系

GT01—GT42 继续承担 **Capability Track**：用最小、可验证案例证明具体协议或 Core 能力。Architecture Series 承担另一件事：解释这些能力为什么属于同一个技术范式，以及它们如何共同形成 Agent 与现实世界之间的可信状态层。

因此，系列文章不追求新增 GT，也不把案例数量当作成熟度。产品成熟度仍按 P0—P5 Product Track 评估：Architecture Definition、Reference Agent、Core Product、Industry Integration、Ecosystem Validation、Commercial Validation。

## 配套运行材料

- [架构宣言 v1](../../architecture_manifesto_v1.md)
- [Reference Agent v0.1 规格](../../reference/reference-agent-v0.1.md)
- [Reference Agent 从零教程](../../tutorials/reference-agent.zh-CN.md)
- [状态、证据、冲突与恢复](../../reference/evidence-and-recovery.md)
- [Cross-Line Promotion Gate v0.1](../../reference/cross-line-promotion-gate-v0.1.md)

安装 GeoTask Core 后，可以直接生成并运行教材工作区：

```bash
pip install geotask-core
geotask agent demo --output ./geotask-reference-agent
```

这个入口会验证安装包内的 Reference Agent bundle、复制一份可修改的本地教材工作区，并执行一次确定性成功场景重放。它不会获取外部真实数据、写生产状态或授权现实动作。
