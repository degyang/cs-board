# WebUI / Skills 可观测性与诊断设计

> 术语迁移：本文中当前实现遗留的 `project_id`/Project 均将随 Task 迁移改为 `task_id`/Task。用户可见界面统一称“任务工作台”；Project 不是当前制作对象。

状态：目标架构约束

更新时间：2026-08-29

## 1. 目标

WebUI、CLI、Skills 和桌面 APP 必须观察同一条执行事实。任意一次失败、fallback、重试、缓存复用或产物失效，都能从用户入口追踪到：

```text
Project
→ Run / trace_id
→ Application Command / command_id
→ Stage / span_id
→ Voice Unit / Visual Item
→ Provider 请求或本地进程
→ 输入/输出 Artifact
→ 稳定错误码与恢复动作
```

日志不是 UI 临时文案，也不是把所有 stdout 拼成一个文本文件。Mountain 使用结构化事件、诊断日志和审计记录三个互相关联但职责不同的通道。

## 2. 三类记录

| 类型 | 目的 | 典型内容 | 保存方式 |
| --- | --- | --- | --- |
| Domain Event | 解释业务状态为什么变化 | stage started/succeeded、fallback、artifact committed | Project 内追加式 `events.jsonl` |
| Diagnostic Log | 排查 Provider、媒体和进程问题 | latency、retry、exit code、stderr 摘要 | Run 级轮转 JSONL |
| Audit Record | 记录谁从哪个入口执行了什么命令 | create、retry、cancel、regenerate、settings change | Project/全局追加式 audit JSONL |

Domain Event 是状态投影的事实来源；Diagnostic Log 不能驱动恢复状态；Audit Record 不保存敏感输入内容。

## 3. 关联标识

### 3.1 必需 ID

| 字段 | 生命周期 |
| --- | --- |
| `project_id` | 一个持久项目 |
| `run_id` | 一次完整或恢复执行 |
| `trace_id` | 与 Run 一一对应，贯穿全部阶段和入口 |
| `command_id` | 一次 Web/CLI/Skill/Desktop 应用命令 |
| `span_id` | 一个 Stage、Provider 调用或子进程尝试 |
| `parent_span_id` | 建立 Stage → Provider/Process 子跨度 |
| `unit_id` | 可选，定位 Voice Unit |
| `visual_id` | 可选，定位 Visual Item |
| `artifact_key` | 可选，定位输入或输出产物 |

每条记录还包含唯一 `record_id`。Domain Event 额外包含 Run 内单调递增的 `sequence`，它就是订阅 cursor；Diagnostic Log 使用独立日志 cursor，不能与事件 sequence 混用。

同一个 Run 被 WebUI 创建、Skill 恢复、CLI 重试时保持相同 `trace_id`，每个入口动作获得新的 `command_id`。不得用前端请求 ID 替代持久 `trace_id`。

### 3.2 入口标识

```text
entrypoint = web | desktop | cli | skill
```

Skill 额外记录 `skill_name` 和 `skill_contract_version`，不记录自然语言会话全文。Desktop 同时记录应用版本和平台，不记录设备用户名或绝对用户目录。

## 4. 结构化日志 Schema

最小日志记录：

```json
{
  "schema_version": 1,
  "record_id": "log-01J6...",
  "timestamp": "2026-08-29T12:34:56.789Z",
  "level": "INFO",
  "event_name": "provider.request.completed",
  "message": "文本模型请求完成",
  "component": "openai-compatible-text-adapter",
  "entrypoint": "skill",
  "project_id": "project-123",
  "run_id": "run-456",
  "trace_id": "trace-456",
  "command_id": "cmd-789",
  "span_id": "span-provider-003",
  "parent_span_id": "span-stage-storyboard",
  "stage": "plan-storyboard",
  "unit_id": "unit-003",
  "attempt": 2,
  "status": "succeeded",
  "duration_ms": 1840,
  "provider": {
    "profile_id": "primary-text",
    "protocol": "chat_completions",
    "model": "example-model",
    "request_id": "provider-request-id",
    "http_status": 200
  },
  "metrics": {
    "input_tokens": 820,
    "output_tokens": 310
  }
}
```

失败记录使用统一错误对象：

```json
{
  "level": "ERROR",
  "event_name": "process.completed",
  "trace_id": "trace-456",
  "span_id": "span-whisper-003",
  "stage": "clone-voice",
  "unit_id": "unit-003",
  "status": "failed",
  "error": {
    "code": "WHISPER_ALIGNMENT_FAILED",
    "retryable": true,
    "message": "该单元无法形成合法时间边界"
  },
  "process": {
    "tool": "whisper",
    "exit_code": 1,
    "stderr_summary": "alignment output is empty"
  }
}
```

## 5. Domain Event

业务事件使用稳定名称：

```text
project.created
run.created
run.started
run.succeeded
run.failed
run.cancelled
stage.queued
stage.started
stage.progress
stage.cached
stage.succeeded
stage.failed
artifact.committed
artifact.invalidated
voice_unit.started
voice_unit.progress
voice_unit.succeeded
voice_unit.failed
visual_item.generated
alignment.succeeded
alignment.fallback
```

Provider retry、HTTP attempt、子进程输出和取消信号属于 Diagnostic Log；只有它们最终引起 Run/Stage 状态变化时，才产生对应领域事件。

`alignment.fallback` 必须包含失败原因、图片数、实际 Voice 时长和 `timing_source=equal_fallback`，使 WebUI 与 Skills 对降级结果给出同一解释。

事件写入顺序：

```text
先把候选 Artifact 写入临时路径、校验并原子移动到最终路径（尚未注册）
→ 在 Project 锁内分配 event sequence
→ 追加并 fsync Domain Event（包含待注册 Artifact 引用）
→ 原子更新 Artifact 索引与 Project/Run View 投影
→ 通知 WebUI/CLI 订阅者
```

Artifact 文件已存在但未被事件和索引注册时仍视为孤立临时结果。若事件已提交而 View 更新失败，启动恢复从 Event 重建投影；不得反过来从普通日志或文件存在性推断成功。

首版使用本地 append-only JSONL 和集中轮询；SSE 只改变传输方式，不改变事件 Schema。

Domain Event 是恢复所需数据：若事件写入失败，本次状态/Artifact 提交不能被报告为成功，并在启动恢复时执行状态—事件一致性修复。Diagnostic Log 是尽力写入：写入或轮转失败不能破坏业务 Artifact，但必须通过健康状态和一次有界 stderr 告警暴露，避免递归记录日志失败。

## 6. 诊断日志

### 6.1 Stage

每次 Stage 至少记录：

- queued/start/end 时间；
- queue wait、execution 和 validation 时长；
- fingerprint 与 cached/stale 决策；
- 输入/输出 Artifact key 和 hash 前缀；
- Unit/Visual 完成计数；
- retry、cancel 和最终状态。

### 6.2 Provider

记录：

- profile id、protocol、model 和 capability snapshot hash；
- request id、attempt、HTTP status、latency 和 Retry-After；
- token usage、图片数量和已知费用单位；
- 响应格式校验结果。

默认不记录完整 Prompt、原文、参考图、API Key、Authorization header 或完整响应。Prompt 版本和内容 hash 足以关联 Artifact；若启用显式开发诊断，原始 payload 也必须先脱敏并写入独立受限文件。

### 6.3 本地进程

记录逻辑工具名、受控参数摘要、PID、开始/结束、退出码、signal、时长和截断后的 stderr。绝对用户路径转换为 Project 相对路径；命令行中的 token、URL query secret 和环境变量值必须脱敏。

### 6.4 媒体质量

记录 ffprobe 结果摘要：容器、codec、采样率、声道、帧率、分辨率和时长。不得把二进制媒体内容写入日志。

### 6.5 指标与分析

Run 汇总至少计算：

- `queue_wait_ms`、`stage_duration_ms`、`run_duration_ms`；
- Provider latency、attempt、rate-limit 和 token/图片数；
- TTS real-time factor、Whisper latency、coverage/confidence；
- `alignment_fallback_units / total_units` 及 reason code 分布；
- image/renderer 成功率与单项耗时；
- cache hit、retry、cancel、stale/invalidation 数；
- Voice/Visual/final 实际时长与 `av_duration_delta_ms`。

本地 `metrics.json` 保存 Run 汇总；未来导出聚合指标时使用有限标签集合，不把 `project_id/unit_id/visual_id` 作为全局 metrics label，避免高基数。精确对象分析仍通过 Trace 和日志完成。

## 7. WebUI 能力

任务工作台增加“活动与诊断”面板：

- 显示 `trace_id`、Run、入口、开始/结束和总耗时；
- 按 Stage、Voice Unit、Visual Item、level 和 event 筛选；
- 展示队列等待、阶段耗时、Provider 重试和 fallback；
- 错误卡片显示稳定错误码、失败跨度和建议恢复动作；
- Artifact 可反查产生它的 span、输入 hash 和后续失效；
- 支持复制 trace id；
- 支持下载脱敏诊断包；
- 普通模式隐藏 DEBUG 细节，开发模式可展开结构化字段。
- 对比多个 Run 的 Stage 耗时、fallback 比例、Provider 重试和最终质量，支持定位版本回归。

WebUI 不直接读取日志文件。建议 API：

```text
GET /api/projects/{project_id}/runs/{run_id}/events?after=<cursor>
GET /api/projects/{project_id}/runs/{run_id}/logs?after=<cursor>&level=&stage=&unit_id=
GET /api/projects/{project_id}/runs/{run_id}/trace
POST /api/projects/{project_id}/runs/{run_id}/diagnostics
GET /api/projects/{project_id}/runs/{run_id}/diagnostics/{bundle_id}
```

服务端返回 cursor，避免每次轮询重新下载全部历史记录。

## 8. CLI 与 Skills 能力

CLI 必须将机器结果和人类日志分离：

```text
stdout：最终 JSON 或 JSONL event stream
stderr：面向终端的进度/诊断摘要
exit code：稳定成功/失败语义
```

建议命令：

```text
pipeline run --project <id> --json --events jsonl
run trace --project <id> --run <id> --json
events list --project <id> --run <id> --after <cursor> --json
logs tail --project <id> --run <id> --level warning --follow --json
diagnostics export --project <id> --run <id> --output <path> --json
```

每个 Skill：

- 启动命令后保存返回的 `project_id/run_id/trace_id/command_id`；
- 只通过结构化事件判断进度和下一步；
- 向用户报告失败 Stage、Unit、稳定错误码和 trace id；
- 对 fallback 明确说明，但不把 warning 当作失败；
- 不解析自由文本日志决定恢复行为；
- 不复制 Provider 或子进程原始日志到对话，除非已脱敏且用户明确请求。

WebUI 启动的 Run 可由 Skills 使用同一个 `trace_id` 查询；Skills 启动的 Run 也能在 WebUI 工作台完整展示。

## 9. 诊断包

脱敏诊断包建议包含：

```text
diagnostics.json
project-view.json
run-state.json
events.jsonl
logs.filtered.jsonl
artifact-index.json
environment.json
toolchain.json
```

不默认包含：

- API Key、Authorization、Cookie；
- 完整文案和 Prompt；
- 参考音频、人物图片和生成图片；
- Voice 或视频；
- 用户主目录绝对路径；
- Provider 原始响应正文。

`environment.json` 只记录应用版本、pipeline/schema、OS、CPU 架构、工具版本、可用能力和非敏感设置。

## 10. 脱敏

所有日志写入前经过统一 `Redactor`：

- 字段名匹配 `api_key/token/authorization/cookie/secret/password` 时强制删除或掩码；
- URL 删除 query 和 userinfo；
- Header 使用白名单；
- 路径替换为 `$PROJECT/`、`$DATA/`、`$CACHE/`；
- Provider 响应只保留允许字段；
- message/details 通过长度限制和敏感模式扫描。
- 结构化字段使用允许列表，未知嵌套对象先序列化、限长、再扫描；禁止把 Python exception locals 或整个环境变量映射写入日志。

测试必须使用 canary secret，验证它不会出现在事件、日志、异常、诊断包、CLI stdout/stderr 或 Web API 响应中。

## 11. 保存与轮转

- Domain Event 与 Artifact lineage 随 Project 保存；
- Audit Record 默认保留最近 180 天，可配置；
- Diagnostic Log 按 Run 和大小轮转，默认保留 30 天或项目最近 20 个 Run；
- DEBUG 日志默认关闭；
- 清理日志不能删除 Project 状态、Artifact 或恢复所需事件；
- 桌面 APP 日志写入平台 logs 目录，不写安装目录。

## 12. OpenTelemetry 兼容

首版不要求部署外部日志平台。Schema 保留 `trace_id/span_id/parent_span_id`，未来可以增加 OTLP adapter，将同一跨度和指标发送到 OpenTelemetry Collector；本地 JSONL 仍是离线桌面环境的权威诊断来源。

## 13. 验收标准

1. 任意 Run 可通过一个 trace id 串联 WebUI、Skill、Stage、Provider、Process 和 Artifact；
2. WebUI 与 Skills 对同一 Run 显示相同状态、warning 和错误码；
3. Whisper fallback 可定位到具体 Unit 并显示原因；
4. Provider 重试可看到次数、延迟和最终结果，但看不到密钥和完整 Prompt；
5. 子进程失败可看到工具、退出码和受控 stderr 摘要；
6. cached/stale/invalidation 决策可解释；
7. 日志轮转不会破坏恢复；
8. 脱敏诊断包可以从 WebUI 和 CLI/Skill 生成；
9. canary secret 在所有输出面均不可检索；
10. Web 创建、Skill 恢复、桌面查看的跨入口场景保留相同 trace id。
