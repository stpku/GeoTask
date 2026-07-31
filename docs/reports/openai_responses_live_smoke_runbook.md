# OpenAI Responses私有线上冒烟运行手册

## 状态

当前状态：`closure_manifest_verifier_verified_server_readiness_blocked_external_authorization_pending_live_request_not_executed`。

本手册对应`examples/runtime/openai_responses_live_smoke.py`、`examples/runtime/openai_responses_live_smoke_audit.py`、`examples/runtime/openai_responses_live_smoke_evidence.py`、`examples/runtime/openai_responses_live_smoke_closure.py`和`examples/runtime/openai_responses_live_smoke_closure_verifier.py`。执行器、只读就绪审计器、证据校验器、显式闭环凭证写入器、只读闭环复核器、测试和本手册均位于私有边界，不进入公共导出，也不进入常规公共CI。

## 目的

线上冒烟只验证以下四项：

1. 当前OpenAI项目可访问指定的固定模型快照；
2. Responses API接受严格Structured Outputs配置；
3. 服务端返回可追踪的请求ID和响应ID；
4. 返回结果能够通过GeoTask Artifact、真实性和Runtime三方合同门禁。

该冒烟不证明生产可用性、质量稳定性、成本可控性、配额充足性或高并发能力。

## 不可绕过的边界

- 默认只执行预检，不导入OpenAI SDK，不解析认证材料，也不发起网络请求；
- 授权票据必须写在仓库外，默认有效15分钟，硬上限60分钟；
- 票据绑定模型、请求SHA-256、输出预算、超时、零重试和一次调用约束；
- 票据使用排他文件创建，执行前原子认领，同一票据不得复用；
- 真实执行必须同时提供`--execute-live`、精确确认变量、服务器侧认证材料和未认领票据；
- 模型必须是以`YYYY-MM-DD`结尾的固定快照；
- 输出预算默认2048，硬上限4096；
- 超时默认60秒，硬上限120秒；
- SDK自动重试固定为0；
- 固定使用仓库中的最小距离Runtime Request，并核对已评审文件的SHA-256；
- 拒绝自定义`OPENAI_BASE_URL`，避免误发到替代端点；
- 要求`OPENAI_LOG`完全未设置；
- 不配置工具、对话状态或生产动作；
- Provider Adapter固定使用`store=false`；
- 只读审计器只检查凭据变量是否存在且非空，不输出其值，不导入Provider模块，不创建认领记录；
- 授权票据、`.claimed`认领记录和报告必须是三个不同文件，全部位于仓库外；
- 报告不得写入仓库内部，只记录状态、审计引用、诊断代码和版本，不记录请求正文、模型正文或认证材料。

## 运行前检查

1. 确认Git工作区干净；
2. 使用仓库外隔离Python环境准备官方OpenAI SDK、GeoTask Core、Provider-neutral Adapter和OpenAI Responses Adapter；在GeoTask Core v0.4.0正式标记前，只允许通过明确的源码路径加载两个Adapter，不得降低其未来Core依赖、使用`--no-deps`伪装可安装性或提前发布；
3. 在服务器侧安全配置官方SDK认证材料，不要把认证材料写入命令行、源码、Runtime Artifact或报告；
4. 确认`OPENAI_BASE_URL`未设置；
5. 确认`OPENAI_LOG`未设置；
6. 选择当前项目实际可访问、并已完成兼容性检查的固定模型快照；
7. 确认接受一次可能计费的API请求。

## 第一步：离线预检

PowerShell：

```powershell
python examples/runtime/openai_responses_live_smoke.py `
  --model <PINNED_MODEL_SNAPSHOT>
```

预期结果：

```json
{
  "live_smoke_plan": {
    "valid": true,
    "execute_live": false,
    "provider_calls_allowed": 0,
    "automatic_retries_allowed": 0,
    "tools_allowed": false,
    "response_storage_allowed": false,
    "live_request_executed": false,
    "release_gate_state": "authorization_pending"
  }
}
```

任何预检失败都必须先修复，不得通过修改脚本常量、放宽模型格式或删除安全检查来绕过。

### 官方SDK离线传输兼容性门禁

首次真实执行前，必须在目标隔离环境运行：

```bash
python -m pytest \
  tests/test_openai_responses_live_smoke_audit.py \
  -k official_sdk_mock_transport \
  -q
```

该测试使用官方OpenAI SDK和`httpx.MockTransport`，实际经过`OpenAI.responses.create`的请求序列化与响应反序列化，但不会访问外网。通过条件包括：生成`POST /v1/responses`、`store=false`、严格JSON Schema、无工具、零自动重试，以及服务端请求ID和响应ID能够形成GeoTask审计引用。

该门禁只证明当前SDK版本与Adapter传输合同兼容，不证明账户访问权限、模型可用性、余额、配额、计费状态或真实服务稳定性。

## 第二步：签发一次性授权票据

票据必须写入仓库外，例如系统临时目录：

```powershell
$env:GEOTASK_OPENAI_LIVE_SMOKE_ACK="I_ACCEPT_ONE_PAID_OPENAI_REQUEST"

python examples/runtime/openai_responses_live_smoke.py `
  --model <PINNED_MODEL_SNAPSHOT> `
  --max-output-tokens 2048 `
  --timeout-seconds 60 `
  --authorization-valid-minutes 15 `
  --issue-authorization "$env:TEMP\geotask-openai-live-authorization.json"
```

签发过程不读取服务器认证材料，也不发起网络请求。票据文件不包含API密钥或确认字符串，只包含授权ID、固定约束、签发时间和到期时间。已存在的票据路径不会被覆盖。

## 第三步：执行只读就绪审计

```powershell
python examples/runtime/openai_responses_live_smoke_audit.py readiness `
  --repository-root . `
  --model <PINNED_MODEL_SNAPSHOT> `
  --max-output-tokens 2048 `
  --timeout-seconds 60 `
  --authorization-ticket "$env:TEMP\geotask-openai-live-authorization.json"
```

只有结果同时满足以下条件才允许进入真实执行：

```text
valid = true
release_gate_state = live_execution_ready
provider_calls_allowed = 0
live_request_executed = false
provider_modules_imported = false
authorization_claim_created = false
credential_value_exposed = false
```

审计器会一次性列出确认声明、服务器凭据存在性、替代端点、SDK日志、OpenAI SDK、GeoTask Core、Provider-neutral Adapter、OpenAI Responses Adapter、固定请求摘要以及票据有效性等全部检查项。审计只读，不会创建`.claimed`文件；任何检查失败都返回`readiness_blocked`。

## 第四步：认领票据并执行一次请求

```powershell
python examples/runtime/openai_responses_live_smoke.py `
  --model <PINNED_MODEL_SNAPSHOT> `
  --max-output-tokens 2048 `
  --timeout-seconds 60 `
  --authorization-ticket "$env:TEMP\geotask-openai-live-authorization.json" `
  --report "$env:TEMP\geotask-openai-live-smoke.json" `
  --execute-live

Remove-Item Env:GEOTASK_OPENAI_LIVE_SMOKE_ACK
```

执行前会原子创建`geotask-openai-live-authorization.json.claimed`。客户端或Adapter初始化失败时不认领票据；进入Runtime提交阶段后，无论成功、失败还是结果未知，票据都不可复用。认领文件会更新为脱敏最终状态。脚本最多允许一次Provider调用，且SDK重试数为0。

## 第五步：校验脱敏证据包

```powershell
python examples/runtime/openai_responses_live_smoke_audit.py verify-evidence `
  --repository-root . `
  --authorization-ticket "$env:TEMP\geotask-openai-live-authorization.json" `
  --report "$env:TEMP\geotask-openai-live-smoke.json"
```

默认读取与票据同目录、同文件名追加`.claimed`的认领记录。校验器要求三份文件互不相同且全部位于仓库外，并交叉验证：

```text
授权ID一致
认领记录绑定原票据SHA-256
认领时间位于票据有效期内
服务端request-id与response-id真实存在
Runtime状态为completed
唯一输出为geotask.execution-result
预算、超时、零重试、无工具、store=false约束一致
三份文件均为严格JSON且使用私有权限
```

校验成功输出`release_gate_state=live_smoke_verified`、三份文件SHA-256及一个组合证据摘要；任何不一致均输出`evidence_invalid`，不得人工覆盖。

## 第六步：写入一次性闭环凭证

不要只依赖第五步的标准输出。证据验证通过后，将脱敏摘要写入仓库外的独立闭环文件：

```powershell
python examples/runtime/openai_responses_live_smoke_audit.py write-closure `
  --repository-root . `
  --authorization-ticket "$env:TEMP\geotask-openai-live-authorization.json" `
  --report "$env:TEMP\geotask-openai-live-smoke.json" `
  --output "$env:TEMP\geotask-openai-live-smoke-closure.json"
```

`write-closure`会重新执行全部证据校验，只有`live_smoke_verified`才写文件。闭环文件采用仓库外路径、私有权限和同目录硬链接原子发布，目标已存在、与票据/认领记录/报告碰撞或位于仓库内时均失败且不覆盖原文件。

闭环文件只保留：格式和校验器版本、授权ID、固定模型快照、服务端审计引用、验证时间、三份证据SHA-256、组合证据摘要以及`credential_data_retained=false`。它不保留证据正文、请求正文、模型正文、文件路径或认证材料。成功输出`release_gate_state=live_smoke_closure_recorded`和闭环文件自身SHA-256。该SHA-256必须保存在闭环文件之外，不能写回同一文件自证完整性。

## 第七步：只读复核闭环凭证

使用第六步输出并外部留存的`closure_manifest_sha256`，重新验证闭环文件的精确身份和当前三份源证据：

```powershell
python examples/runtime/openai_responses_live_smoke_audit.py verify-closure `
  --repository-root . `
  --authorization-ticket "$env:TEMP\geotask-openai-live-authorization.json" `
  --report "$env:TEMP\geotask-openai-live-smoke.json" `
  --closure "$env:TEMP\geotask-openai-live-smoke-closure.json" `
  --expected-closure-sha256 <CLOSURE_MANIFEST_SHA256>
```

`verify-closure`完全只读，不创建文件、不修改证据，也不导入Provider模块。它首先重新执行票据、认领记录和报告的严格校验，再验证闭环文件的外部SHA-256锚点、精确字段合同、私有权限、验证时间不得早于认领最终化、授权ID、模型快照、服务端审计引用、三份文件哈希和组合证据摘要；结束前再次复核源证据绑定，防止验证过程中发生替换。

成功输出`release_gate_state=live_smoke_closure_verified`和`closure_digest_anchored=true`。如果闭环文件被改写、外部摘要错误、源证据发生变化、时间回退、字段增删、权限放宽或任一文件进入仓库，均输出`closure_invalid`。摘要不匹配时会返回当前文件的实际SHA-256以支持脱敏排障，但不输出文件路径或正文。

## 成功判据

同时满足以下条件才算线上冒烟成功：

```text
valid = true
release_gate_state = live_smoke_verified
authorization_id = <issued-ticket-id>
runtime_state = completed
side_effects_executed = true
live_request_executed = true
provider_calls_allowed = 1
automatic_retries_allowed = 0
tools_allowed = false
response_storage_allowed = false
audit_ref = openai://responses/<request-id>/<response-id>
output_artifact_ids = [geotask.execution-result]
```

即使结果为`completed`，输出仍然只是`model_generated`，不得提升为`verified`或`local_deterministic`。

## 发布门禁状态

```text
authorization_pending   默认预检通过，尚未签发票据
live_execution_pending  一次性票据已签发，尚未执行
readiness_blocked       只读就绪审计至少一项未通过
live_execution_ready    所有执行前条件满足，但尚未调用Provider
preflight_blocked       执行器本地约束、确认声明、凭据环境或票据检查未通过
live_execution_blocked  客户端或Adapter初始化失败，未进入提交阶段
live_smoke_indeterminate 已认领票据，但提交未返回结构化结果
live_smoke_failed       已返回结构化结果，但未满足成功判据
evidence_invalid        三份脱敏证据缺失、冲突、被篡改或位于仓库内
live_smoke_verified     单次线上冒烟与脱敏证据包全部判据通过
closure_not_recorded    证据未通过或闭环输出路径、权限、原子发布门禁失败
live_smoke_closure_recorded 已验证证据的脱敏闭环凭证已一次性写入
closure_invalid         闭环外部摘要、合同、时间、权限或当前源证据绑定不一致
live_smoke_closure_verified 闭环精确身份与当前源证据已只读复核通过
```

只有`live_smoke_verified`允许关闭“线上兼容性待验证”门禁；运行记录的完整操作闭环要求先`live_smoke_closure_recorded`，再达到`live_smoke_closure_verified`。这些状态均不代表生产就绪。

## 失败处理

- `preflight`失败：未发起线上请求，修复本地配置后重新预检；
- `blocked`且`side_effects_executed=false`：认证客户端或Runtime合同未满足，未证明线上请求已经执行；
- `failed`且`side_effects_executed=true`：保留审计引用，检查模型权限、限流、输出格式或服务状态；
- `phase=execution`且`live_request_executed=false`：客户端或Adapter初始化失败，确认未进入提交阶段；
- `phase=execution`且`live_request_executed=null`：提交阶段未返回结构化结果，不能断言服务端是否收到请求，必须先检查外部审计和账户记录；
- `retryable=true`：只表示具备重新提交条件，不表示脚本会自动重试；
- 无服务端请求ID：使用确定性本地审计引用，只能证明尝试过调用，不能证明服务端已接收。

不得把Provider异常原文、认证材料、模型完整输出或Runtime Request正文复制到Issue、聊天记录或公共日志。

## 结束后

1. 删除确认变量；
2. 确认授权票据、`.claimed`认领记录、报告和闭环凭证均位于仓库外；
3. 保留三份脱敏证据、一次性闭环凭证及其外部SHA-256锚点，核对授权ID和组合证据摘要一致；
4. 不修改或复用已认领票据，不覆盖或重写闭环凭证；
5. 不提交票据、认领记录、报告、闭环凭证或外部摘要记录；
6. 执行`verify-closure`并记录实际模型快照、运行时间、`live_smoke_verified`、`live_smoke_closure_recorded`和`live_smoke_closure_verified`状态；
7. 线上冒烟成功后，仍需独立评估模型输出质量和成本，不能直接标记为生产可用。
