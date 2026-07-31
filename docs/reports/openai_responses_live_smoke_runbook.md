# OpenAI Responses私有线上冒烟运行手册

## 状态

当前状态：`single_use_authorization_verified_live_request_not_executed`。

本手册对应`examples/runtime/openai_responses_live_smoke.py`。脚本、测试和本手册均位于私有边界，不进入公共导出，也不进入常规公共CI。

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
- 报告不得写入仓库内部，只记录状态、审计引用、诊断代码和版本，不记录请求正文、模型正文或认证材料。

## 运行前检查

1. 确认Git工作区干净；
2. 使用隔离Python环境安装GeoTask Core、Provider-neutral Adapter、OpenAI Responses Adapter和官方OpenAI SDK；
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

## 第三步：认领票据并执行一次请求

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
preflight_blocked       本地约束、确认声明、凭据环境或票据检查未通过
live_execution_blocked  客户端或Adapter初始化失败，未进入提交阶段
live_smoke_indeterminate 已认领票据，但提交未返回结构化结果
live_smoke_failed       已返回结构化结果，但未满足成功判据
live_smoke_verified     单次线上冒烟全部判据通过
```

只有`live_smoke_verified`允许关闭“线上兼容性待验证”门禁；它仍不代表生产就绪。

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
2. 确认授权票据、`.claimed`认领记录和报告均位于仓库外；
3. 保留三份脱敏证据，核对其授权ID一致；
4. 不修改或复用已认领票据；
5. 不提交票据、认领记录或报告；
6. 记录实际模型快照、运行时间和发布门禁状态；
7. 线上冒烟成功后，仍需独立评估模型输出质量和成本，不能直接标记为生产可用。
