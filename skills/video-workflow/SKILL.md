---
name: video-workflow
description: Create, resume, inspect, or diagnose a standard whiteboard video project through the cs-board CLI. Use for end-to-end video workflow coordination, not for implementing individual production stages.
---

## 职责

- 创建或选择 Project；
- 收集文案、参考音频、引擎、视觉来源和成片设置；
- 校验 capability 并选择 execution policy；
- 编排六个生产阶段；
- 用事件 cursor 汇报进度，在中断后用同一 `trace_id` 恢复；
- 汇总最终产物、fallback 和质量告警；
- 必要时导出脱敏诊断包。

## 非职责

- 不自行拆分文案、生成 prompt 或执行 Provider/脚本；
- 不将对话记录、终端输出或日志当成 Task 状态；
- 不维护不同于 WebUI 的进度或重试规则。

## 执行策略

| 策略 | 行为 |
| --- | --- |
| `auto` | 验证后自动运行到 final，与 WebUI 默认行为一致 |
| `gated` | 每阶段成功后展示摘要并等待确认 |
| `targeted` | 只运行指定阶段及必要依赖 |

策略只控制是否继续，不改变领域结果或 fingerprint。

## CLI 命令

```bash
# 创建任务
python -m cli.csboard task create --request request.json --json

# 运行流水线
python -m cli.csboard pipeline run --task <id> --policy auto --json

# 恢复流水线
python -m cli.csboard pipeline resume --task <id> --json

# 查看任务状态
python -m cli.csboard task show --task <id> --json

# 查看运行追踪
python -m cli.csboard run trace --task <id> --run <run-id> --json

# 查看事件
python -m cli.csboard events list --task <id> --run <run-id> --after <cursor> --json

# 导出诊断包
python -m cli.csboard diagnostics export --task <id> --run <run-id> --json
```

## 请求格式

创建任务时通过 `--request` 传入 JSON 文件：

```json
{
  "title": "任务标题",
  "script": "旁白文案内容...",
  "reference_audio": "/path/to/reference.wav",
  "tts_url": "http://127.0.0.1:7860",
  "tts_mode": "gradio",
  "pipeline": "mountain-av-v1",
  "engine": "whiteboard"
}
```

## 错误处理

- 错误回复至少包含 `error_code`、Stage、可重试性和短 `trace_id`
- 只有排障需要时才读取 debug 日志，默认先读取 Trace 摘要
- 导出的诊断包必须由共享 Redactor 处理，不自行拼装日志压缩包

## 安全

不把 API key、完整 prompt、完整正文、参考音频内容或 Provider 原始响应回显到对话。

## 能力限制

M04 仅支持 `mountain-av-v1` + `whiteboard`。拒绝 custom-reference 和 infographic 请求，不静默切换到旧流程。
