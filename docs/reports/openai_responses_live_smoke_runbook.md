# OpenAI Responses私有线上冒烟运行手册

## 状态

当前状态：`harness_verified_live_request_not_executed`。

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
- 真实执行必须同时提供`--execute-live`和精确确认变量；
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
    "live_request_executed": false
  }
}
```

任何预检失败都必须先修复，不得通过修改脚本常量、放宽模型格式或删除安全检查来绕过。

## 第二步：显式授权一次线上请求

报告必须写入仓库外，例如系统临时目录：

```powershell
$env:GEOTASK_OPENAI_LIVE_SMOKE_ACK="I_ACCEPT_ONE_PAID_OPENAI_REQUEST"

python examples/runtime/openai_responses_live_smoke.py `
  --model <PINNED_MODEL_SNAPSHOT> `
  --max-output-tokens 2048 `
  --timeout-seconds 60 `
  --report "$env:TEMP\geotask-openai-live-smoke.json" `
  --execute-live

Remove-Item Env:GEOTASK_OPENAI_LIVE_SMOKE_ACK
```

脚本最多允许一次Provider调用，且SDK重试数为0。失败后不得在未阅读审计引用和诊断代码的情况下直接重复执行。

## 成功判据

同时满足以下条件才算线上冒烟成功：

```text
valid = true
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
2. 确认报告位于仓库外；
3. 只保留脱敏报告中的状态、版本和审计引用；
4. 不提交报告；
5. 记录实际模型快照、运行时间和最终状态；
6. 线上冒烟成功后，仍需独立评估模型输出质量和成本，不能直接标记为生产可用。
