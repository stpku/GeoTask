# GeoTask Core v0.3.0 Agent Integration Release

- **Release date:** 2026-07-31
- **Git tag:** `v0.3.0`
- **Package version:** `0.3.0`
- **GeoTask Document Schema:** `1.0`
- **Agent Integration Profile:** `0.1`
- **Artifact Registry:** `1.0`
- **Artifact Validation Report:** `1.0`
- **Schema Bundle:** `1.0`

## 中文发布说明

GeoTask Core v0.3.0把公共Core从“制品可发现、可验证”推进到“Agent生成任务、失败关闭、结构化修订、补证据恢复和全过程审计均可验证”。本版本仍坚持模型无关与确定性执行边界：Core不调用大模型、不猜测坐标、对象、算子、证据或行业规则，也不执行`next_action`和生产动作。

### 主要新增

#### 1. Agent Integration Profile与可注入Skill

新增模型无关的Agent Integration Profile v0.1，并公开四类稳定工具契约：

- `inspect_artifacts`
- `validate_artifact`
- `execute_task`
- `evaluate_control`

Agent负责理解意图、生成任务和请求证据；GeoTask Core负责严格验证、确定性执行和只读控制评估；真实数据连接、证据认证、审批与生产动作仍属于外部Runtime或Domain Pack。

公共仓新增`skills/geotask-core/SKILL.md`，可直接注入Agent，并明确unknown、blocked、修订重试、证据恢复和禁止模型猜测的操作边界。

#### 2. Agent生成任务的机械修复闭环

```bash
geotask agent inspect --format json

geotask agent prepare \
  examples/core/agent_generated_distance_draft.yaml \
  --repaired-output prepared.yaml \
  --output preparation-report.json
```

`agent prepare`执行以下步骤：

1. 严格校验Agent生成草稿；
2. 仅补充无需领域推断的协议默认值与稳定ID；
3. 再次严格校验；
4. 仅在最终有效时执行本地确定性任务。

Core不会补猜坐标、对象绑定、算子、时间、高度、证据或行业规则。无法机械修复的草稿返回`state=blocked`和结构化`revision_request/0.1`。

#### 3. 受约束的Agent修订重试

```bash
geotask agent retry \
  blocked-preparation.json \
  examples/core/agent_generated_distance_revised.yaml \
  --verification-output revision-verification.json \
  --prepared-output prepared.yaml \
  --output retry-report.json
```

重试前，Core会：

- 重新生成并核对修订请求；
- 验证修订基准SHA-256；
- 只允许修改请求明确列出的字段；
- 拒绝偷偷改变坐标、证据、执行模式、元数据或其他已通过校验的内容；
- 要求选择值属于显式候选集合；
- 仅在差异审计与重新校验都通过后执行任务。

非法修订返回退出码2、`task_executed=false`，且不会生成prepared文档。

#### 4. GT08补证据恢复闭环

```bash
geotask agent recover \
  examples/core/evidence_request_plan.yaml \
  --evidence examples/core/evidence_request_verified_state.yaml \
  --output recovery-report.json
```

GT08现在完整展示：

```text
route_intersects_zone = true
altitude_conflict = true
temporal_conflict = unverifiable
full_conflict = unknown
        ↓
request_evidence
        ↓
验证全部required_fields与resume_when
        ↓
重新执行受影响断言
        ↓
temporal_conflict = true / verified
full_conflict = true
```

恢复报告明确记录：

```text
task_reexecuted = true
next_action_executed = false
model_guess_used = false
```

证据不完整或恢复条件未满足时，报告保持`state=blocked`，不会重写任务或释放输出。

#### 5. 四类Agent报告成为正式Artifact

新增四类公共Agent报告Artifact：

- `geotask.agent-generation-preparation`
- `geotask.agent-revision-verification`
- `geotask.agent-revision-retry`
- `geotask.agent-evidence-recovery`

对应报告版本均为`0.1`，可通过统一入口离线验证：

```bash
geotask artifact validate \
  geotask.agent-evidence-recovery \
  recovery-report.json \
  --format json
```

Artifact有效性与业务状态明确分离：一个如实记录`blocked`或`rejected`的报告仍可以是结构和交叉字段一致的有效Artifact。

#### 6. Registry与Schema Bundle扩展

Artifact Registry现包含8类公共Artifact，Schema Bundle包含9份JSON Schema：

```bash
geotask inspect schemas --verify --format json
geotask schema verify --format json
```

新增Schema：

- `geotask-agent-generation-preparation-v0.1.schema.json`
- `geotask-agent-revision-verification-v0.1.schema.json`
- `geotask-agent-revision-retry-v0.1.schema.json`
- `geotask-agent-integration-v0.1.schema.json`

三类生成/修订报告和补证据恢复报告均具备严格Python加载器、统一Artifact验证、发行完整性门禁和验证报告自验证。

### 安装与核验

```bash
python -m pip install --no-cache-dir geotask-core==0.3.0
geotask --version
geotask agent inspect --format json
geotask schema verify --format json
geotask inspect schemas --verify --format json
```

发行元数据、`geotask_core.__version__`和CLI均应报告`0.3.0`；Schema Bundle应报告9份Schema有效；Registry应报告8类公共Artifact。

### 验证结果

- 完整源仓：`1149 passed, 1 skipped`；
- Agent、Artifact、文档与发布聚焦回归：`153 passed`；
- wheel与sdist构建通过，并通过Twine检查；
- wheel与sdist的9-Schema分发完整性验证通过；
- 隔离环境安装后，恢复报告生成、恢复Artifact验证和Schema Bundle验证全部通过；
- 公共发布流水线导出272个文件，边界检查、导出验证、敏感扫描和哈希校验全部通过；
- 公共导出仓独立测试：`721 passed`。

## English release notes

GeoTask Core v0.3.0 advances the public Core from discoverable, verifiable artifacts to a complete Agent-facing loop for generated tasks, fail-closed preparation, constrained revision, evidence recovery, and offline-verifiable audit traces. Core remains model-neutral and deterministic: it does not call a hosted model, guess coordinates, bindings, operators, evidence, or domain policy, and it never executes `next_action` or production actions.

### Highlights

#### 1. Agent Integration Profile and injectable Skill

The model-neutral Agent Integration Profile v0.1 publishes four stable tool contracts:

- `inspect_artifacts`
- `validate_artifact`
- `execute_task`
- `evaluate_control`

Agents interpret intent, generate tasks, and request evidence. GeoTask Core performs strict validation, deterministic execution, and read-only control evaluation. Real connectors, evidence authentication, approvals, and production actions remain in an external Runtime or Domain Pack.

The public `skills/geotask-core/SKILL.md` provides directly injectable instructions for unknown states, blocked outputs, revision retries, evidence recovery, and the prohibition on model guesses.

#### 2. Mechanical preparation of Agent-generated tasks

```bash
geotask agent prepare \
  examples/core/agent_generated_distance_draft.yaml \
  --repaired-output prepared.yaml \
  --output preparation-report.json
```

`agent prepare` strictly validates the draft, applies only protocol-level mechanical repairs, validates again, and executes locally only when the final document is valid. It never invents coordinates, bindings, operators, evidence, time, altitude, or domain rules. Non-mechanical failures produce `state=blocked` plus a versioned `revision_request/0.1`.

#### 3. Guarded revision retry

```bash
geotask agent retry \
  blocked-preparation.json \
  examples/core/agent_generated_distance_revised.yaml \
  --verification-output revision-verification.json \
  --prepared-output prepared.yaml \
  --output retry-report.json
```

Before execution, Core regenerates the revision request, verifies the revision-base SHA-256, permits only requested paths, enforces explicit candidate sets, and rejects hidden changes to coordinates, evidence, execution mode, metadata, or other previously valid content. Rejected revisions exit with code 2, keep `task_executed=false`, and do not write a prepared document.

#### 4. GT08 evidence-recovery loop

```bash
geotask agent recover \
  examples/core/evidence_request_plan.yaml \
  --evidence examples/core/evidence_request_verified_state.yaml \
  --output recovery-report.json
```

After all declared evidence fields and `resume_when` pass, Core materializes only the supported single named condition in an in-memory copy, reruns the affected assertion, and reevaluates the final control state. The report records `task_reexecuted=true`, `next_action_executed=false`, and `model_guess_used=false`. Incomplete or unsatisfied evidence remains a valid blocked trace without releasing outputs.

#### 5. Four registered Agent report Artifacts

The Registry now includes:

- `geotask.agent-generation-preparation`
- `geotask.agent-revision-verification`
- `geotask.agent-revision-retry`
- `geotask.agent-evidence-recovery`

All use report version `0.1` and support unified offline validation. Artifact validity is distinct from workflow success: a truthful `blocked` or `rejected` report may still be a valid serialized Artifact.

#### 6. Eight Artifacts and nine Schemas

The public Registry now exposes eight Artifacts and the offline Schema Bundle contains nine JSON Schemas. The four Agent report contracts include strict Python loaders, unified Artifact validation, distribution-integrity gates, and validation-report self-validation.

### Install and verify

```bash
python -m pip install --no-cache-dir geotask-core==0.3.0
geotask --version
geotask agent inspect --format json
geotask schema verify --format json
geotask inspect schemas --verify --format json
```

Distribution metadata, `geotask_core.__version__`, and the CLI should report `0.3.0`. Schema verification should report nine valid Schemas, and Registry discovery should report eight public Artifacts.

### Verification

- Full source repository: `1149 passed, 1 skipped`;
- focused Agent, Artifact, documentation, and release suite: `153 passed`;
- wheel and sdist builds passed Twine checks;
- nine-Schema distribution integrity passed for wheel and sdist;
- isolated installation passed recovery generation, recovery Artifact validation, and Schema Bundle verification;
- the public release pipeline exported 272 files and passed boundary, export, sensitive-scan, and hash checks;
- independent public-export suite: `721 passed`.
