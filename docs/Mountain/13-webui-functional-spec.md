# WebUI 功能落地规格

状态：实施基线。

> 执行策略、任务队列控制、人工外部素材、资产回存和风格模板以 [15-production-control-and-style-assets.md](15-production-control-and-style-assets.md) 为权威；本文件不得以旧式“逐步执行”或前端 fixture 覆盖这些规则。

## 目标

新 WebUI 必须让普通用户完成“新建任务 → 文案整理 → 保存制作输入 → 启动自动流程 → 下载成片”。返工、恢复和诊断通过 Task、Run、Stage、Voice Unit、Visual Item 与 Artifact 的服务端 View 完成，前端不得读取内部文件或推导状态。

## 导航与路由

| 菜单 | 路由 | 功能 |
| --- | --- | --- |
| 新建任务 | `/create` | 内容、参考声音、输出与视觉设置、保存、启动 |
| 任务队列 | `/tasks` | 任务筛选、队列、成片、取消、重试、诊断 |
| 设置 | `/settings` | 模型、TTS、Whisper、工具链、存储、诊断；不显示 Secret |
| 帮助 | `/help` | 流程、状态、错误与诊断说明 |
| 任务工作台 | `/tasks/:taskId` | 当前 Run、六阶段、Unit/Visual、Artifact、活动 |
| 运行诊断 | `/tasks/:taskId/runs/:runId/diagnostics` | 活动、日志、指标、诊断包 |

## 新建任务

页面包含内容与声音、输出类型、视觉设置、成片设置、能力/成本提示和操作栏。文案在保存任务前按规则完成“文案整理”，其 Voice Unit 是后续配音的权威输入。M07 仅允许 `whiteboard + preset + mountain-av-v1`；动态信息图和自定义参考必须由 Capability View 返回 `unsupported`。保存任务与启动 Run 是两个动作，失败或刷新后不得丢失输入。

## 工作台

固定六阶段：生成画面锚定重点（可选）、配音、分镜、插画、白板渲染、合成。顶部显示任务 ID、Run、Trace、取消/恢复/重试/下载；左侧展示 Unit 与 Visual 的文字范围、时长、对齐状态、fallback、图片和 clip；中部展示阶段操作；右侧展示 Artifact 版本、hash、状态、失效原因和下载。

图片重生成只失效相关 Visual 下游，不能改变 Voice 或时间边界；前端不得通过删文件表达返工。

## 诊断与设置

诊断提供活动、日志、指标、诊断四页签；事件 cursor 增量读取；日志由服务端脱敏并按 level/component/stage/unit/visual 筛选。错误必须显示稳定 code、retryable、失败对象、Trace 与建议动作。设置只显示掩码、`has_secret` 和 `secret_ref`。

## 必需 API 与验收

View：TaskSummary、TaskDetail、Run、StageDetail、VoiceUnit、VisualItem、Artifact、Capability、ServiceHealth、Trace、LogEntry、RunMetrics、DiagnosticBundle。

命令：保存任务/制作输入、创建 Run、启动/取消/恢复/重试、Stage 重跑、Unit 重试、Visual 重生成/重绘、重新合成、导出诊断。

验收闭环：保存文案整理结果与参考声音；刷新后可恢复任务制作输入；启动自动 Run；六阶段和 Unit/Visual/Artifact 可刷新恢复；fallback 可见；A/V 校验通过后可下载成片；失败能 Trace 与导出脱敏诊断。
