# WebUI 整改设计

> **现行产品设计，分阶段实现。** 页面表面以 `prototypes/webui/` 为设计源，生产实现为 `web-v2/`，真实进展和未实现项见 [23-current-delivery-status.md](23-current-delivery-status.md)。原型中的 mock、Project 术语和不存在的 API 不属于生产契约。

## 1. 产品目标

WebUI 面向不关心技术细节的用户：提交文案、参考声音和视觉设置后，一次启动即可自动完成视频。同时为检查、返工和故障分析提供阶段、Voice Unit、Visual Item、Artifact 和 Trace 级视图。

自动执行是默认体验，阶段化主要用于理解、恢复和编辑，不把默认流程变成强制向导。

## 2. 概念模型

当前三个并列页面模式拆为两组独立选择。

### 2.1 输出引擎 `engine`

| 值 | 用户名称 | 新任务 Pipeline |
| --- | --- | --- |
| `whiteboard` | 白板动画 | `mountain-av-v1` |
| `infographic-remotion` | 动态信息图 | `mountain-av-v1` |

### 2.2 视觉来源 `visual_source`

| 值 | 用户名称 | 配置 |
| --- | --- | --- |
| `preset` | 预设风格 | 选择内置 style preset |
| `custom-reference` | 自定义参考 | 风格图 + 1–5 个人物组 |

不支持的组合由后端 Capability API 返回，不能在前端用 `pageMode` 隐藏业务规则。

实施顺序上，M07 先只开放 `whiteboard + preset` 的标准制作；`custom-reference` 与 `infographic-remotion` 在 M09 完成各自 adapter、回归和 capability 测试前返回明确 `unsupported`，不显示为可提交任务。

## 3. 信息架构

```text
/tasks/new                 新建任务
/                         任务队列
/tasks/:taskId             任务工作台
/tasks/:taskId/runs/:runId/diagnostics  运行诊断
/settings                  服务、模型、存储与诊断设置
```

顶层导航保持新建任务、任务队列、设置、帮助四项。当前 Run 可以作为全局小型状态条展示；不展示“项目”这一当前不存在的产品对象。

## 4. 新建任务 `/tasks/new`

采用原型已验证的分区/页签结构，而不是多页强制向导。任务创建与资产管理必须使用同一风格/音色 API View，不能以浏览器 fixture 或 localStorage 作为生产真相。

### 4.1 内容与声音

- 任务名称、视频文案、参考音频上传与试听；
- 文案整理规则、图片规划规则、每图 1–4 Shot 规则，以及字数、预计 Voice Unit/Visual Item/Shot 数量和成本提示；
- 说明系统会先确定“文字—Voice—图片”关系，再逐单元生成 Voice 并同步画面；
- 图片数量支持固定、自适应和逐 Unit 人工覆盖；Shot 是同一张图片的渲染分镜，不是额外生成图片；
- 2–3 句话和 1–2 张图只作为常见提示，不向用户承诺固定数量。

### 4.2 输出类型

- 白板动画；
- 动态信息图；
- 展示简短示例、适用内容和关键差异。

### 4.3 视觉设置

- 预设风格，或自定义风格参考与人物组；
- 参考素材独立预览；
- 显示当前引擎/视觉来源组合是否受支持。

### 4.4 成片设置

- 字幕开关；
- 白板模式的重点文字、线条绘制量和笔身文字；
- 执行策略默认“自动完成”；
- 手动完成支持“每道工序”或多选需要人工触发的 Stage；未选 Stage 必须连续执行，直至下一个门禁；
- 当前视觉来源为人工 Codex 时，插画阶段等待外部成果，不能伪称无人值守自动完成；
- 高级选项不暴露队列并发、采样率和单元最大字符等基础设施参数。

### 4.5 提交

```text
客户端校验
→ 确定性文案整理，生成并确认 Voice Unit
→ POST /api/tasks
→ 保存任务制作输入并返回 task_id
→ POST /api/tasks/{id}/runs
→ 返回 run_id / trace_id / command_id
→ 跳转任务工作台
```

上传成功和启动执行是两个明确动作。启动失败时 Task 仍然存在，不需要重新上传大文件。文案整理结果随任务输入保存，刷新后必须可恢复。

## 5. 任务队列 `/tasks`

筛选包括状态、输出引擎、入口和任务名。任务卡片固定展示：

- 任务名称、时间、引擎、视觉来源和 pipeline version；
- 汇总状态、当前 Stage、Voice Unit/Visual Item 进度；
- 同步质量：Whisper 成功单元数、等分 fallback 单元数；
- 最近入口 `web|desktop|cli|skill` 和短 `trace_id`；
- 最终视频或当前可用产物；
- 进入工作台和诊断入口。

取消、重试和下载使用独立按钮，不能与整卡点击冲突。

## 6. 任务工作台 `/tasks/:taskId`

### 6.1 页面框架

```text
┌ 任务标题 / Run 状态 / 启停操作 / trace_id ──────────────────┐
│ 阶段时间线：画面锚定重点 → 配音 → 分镜 → 插画 → 动画 → 合成  │
├────────────────┬──────────────────────────┬──────────────────┤
│ Unit/Visual 列表│ 当前阶段预览、错误和重试 │ 产物、版本与下载 │
├────────────────┴──────────────────────────┴──────────────────┤
│ 活动与诊断：事件 / 日志 / 指标 / fallback / 诊断包（可折叠） │
└───────────────────────────────────────────────────────────────┘
```

### 6.2 六个生产阶段

1. 生成画面锚定重点（可选；文案整理已在新建任务时完成）；
2. 克隆参考音色；
3. 拆分文案分镜；
4. 生成统一插画；
5. 绘制白板动画或渲染信息图；
6. 合成音画成片。

总编排不作为第七个进度节点；它体现在 Run 状态和执行策略中。每个 Stage 显示 `pending/running/succeeded/failed/cancelled/stale/skipped`，以及 `waiting-manual-trigger`（执行门禁）和 `waiting-external-output`（外部素材门禁）；两者均非失败，且必须显示下一动作。

### 6.3 Voice Unit 与 Visual Item 列表

每个 Voice Unit 显示：

- 序号、完整原文或摘要、字符数和独立 Voice 状态；
- Voice 实际时长、试听和重试入口；
- 一个或多个 Visual Item 的文字范围、图片、clip、切换点和每图 1–4 个 Shot；
- `Whisper 对齐` 或 `平均切图` 标签；
- fallback 原因、对齐覆盖率/置信度（普通用户默认折叠）；
- 选中项对应的 `unit_id/visual_id`。

首版只读展示边界。开放合并/拆分前，必须完成下游失效、Voice 重生成和稳定 ID 迁移设计。

### 6.4 阶段主工作区

| 阶段 | 主要内容 | 允许操作 |
| --- | --- | --- |
| 文案整理 / 画面锚定重点 | 已保存 Unit、图片/Shot 规则、锚定文字范围与覆盖率 | 重新整理并使下游失效；首版不在运行期编辑 |
| 配音 | 单元播放器、Whisper/fallback、时长和音频质量 | 重试失败单元、播放母带 |
| 分镜 | 每个 Visual 的文字、时间、画面意图、overlay 和 prompt | 重跑一个 Unit 或全部规划 |
| 插画 | Visual 图片网格、revision、Codex 任务包与候选验收状态 | 查看/复制任务包、导入、验收、只重做一张 |
| 动画/渲染 | annotation、clip、目标/实际时长 | 重绘一个 Visual 或全部 |
| 合成 | 字幕、成片、A/V 校验报告 | 修改成片设置后重合成 |

所有操作调用共享 Application Command。前端不能通过删除文件表达“重做”。

### 6.5 产物侧栏

显示 Artifact 逻辑 key、schema version、revision、创建时间、hash 摘要和下载入口。外部制作任务包显示受控相对输入/输出路径；普通用户不显示物理绝对路径。

### 6.6 活动与诊断面板

提供四个页签：

- 活动：按事件 cursor 展示 Stage、Unit、Visual、重试、取消、fallback 和完成；
- 日志：按级别、组件、Stage、Unit、Visual、Provider 筛选，默认隐藏 debug；
- 指标：各阶段耗时、Provider 延迟/重试、TTS/Whisper/渲染耗时、fallback 比例和音画时差；
- 诊断：复制 `trace_id`、查看错误链、导出脱敏诊断包。

错误卡固定显示 `error_code`、是否可重试、失败 Stage、相关 Unit/Visual、`trace_id` 和建议动作。UI 不解析中文日志决定按钮。

## 7. 资产管理 `/assets`

原型中的“预置风格 / 自定义风格 / 音色库”是独立资产管理领域。模板创建、参考素材、版本、启停、预览在此完成；新建任务仅选择模板 ID/revision，Run 启动时保存不可变风格快照。Pipeline、设置页和新服务入口不得保存硬编码风格常量。

风格详情不显示或编辑“输出引擎”，资产列表也不按引擎筛选；同一风格可被不同输出引擎复用。预置风格详情在 Prompt 下方展示“参考图路由规则”：按顺序列出规则名称、关键字和真实图片缩略图；编辑状态允许新增、删除和上下移动规则，编辑逗号分隔关键字，并为每条规则上传、移除一至三张图片。匹配语义为首条命中；空列表或未命中表示不使用参考图。历史代码中已经固化路由素材的“纸感隐喻拼贴风”和“漫画墨线解释风”必须迁入这一结构化资产契约，运行时不得回读旧常量或旧目录。

第四个一级 Tab 使用“前置条件”，承接从旧业务代码提取的有人讲解、只显示手部等可启停制作条件；它不同于风格中的人物画法，也不命名为“自定义人物”。更深的人物/人物组资产模型仍是后续规划，详见 [28-domain-extraction-and-character-assets-roadmap.md](28-domain-extraction-and-character-assets-roadmap.md)。

## 8. 设置 `/settings`

- 模型服务采用与资产管理一致的主从布局：左侧为新建、搜索和服务列表，右侧为选中服务预览；编辑时右侧原位切换为表单，新建仍使用独立表单；
- 模型服务只管理外部 Provider，不展示 IndexTTS、Whisper、FFmpeg、白板渲染器等本地运行时；这些能力分别归入“语音与对齐”或“工具链”，底层运行时注册信息可继续供 Pipeline 使用；
- 模型服务表单只包含名称、可多选能力、适配器、BaseURL、逗号分隔的模型、自动生成且只读的服务 ID 和默认项；能力首项兼容现行 `capability`，完整列表保存在 `config.capabilities`，直至后端数组契约升级；
- 可选能力为文本、多模态、图片、视频和音频；适配器首批为 OpenAI 兼容、Anthropic 兼容和其他。“其他”必须在取得厂商 API 参考后由 Provider 定制，不在页面臆造参数；
- 语音节点与 Whisper 能力；
- 本地渲染环境和工具版本；
- 服务健康、队列、存储和保留策略；
- 日志级别与诊断包导出；
- 高级能力探测。

API Key 只保存在本机后端或系统密钥存储。前端配置 View 只包含掩码、`has_secret` 和 `secret_ref`，日志及诊断包也不得出现 Secret。

## 8. React + Vite 代码组织

```text
web-v2/src/
├── app/
│   ├── router.tsx
│   └── providers.tsx
├── pages/
│   ├── CreateTaskPage.tsx
│   ├── TasksPage.tsx
│   ├── TaskWorkbenchPage.tsx
│   ├── RunDiagnosticsPage.tsx
│   └── SettingsPage.tsx
├── features/
│   ├── project-create/
│   ├── project-list/
│   ├── project-workbench/
│   ├── stage-timeline/
│   ├── voice-units/
│   ├── visual-items/
│   ├── artifact-gallery/
│   ├── run-activity/
│   ├── diagnostics/
│   └── service-settings/
└── lib/
    ├── api/client.ts
    ├── api/types.ts
    ├── api/queries.ts
    └── formatting.ts
```

组件按业务特征拆分。WebUI v2 只消费 API View，不导入 Python Domain，也不复制状态机或 fallback 公式。`web-v2/` 与 legacy `web/` 不共享页面、状态或构建目录；迁移只允许通过 API 契约和独立复写完成。

## 9. 状态同步

第一阶段保留轮询，但集中到统一 query 层：列表只轮询列表 View，工作台只轮询当前任务 View，活动面板以事件 cursor 增量读取，日志面板按需加载。页面隐藏时降频，terminal 状态停止高频轮询。

事件稳定后增加 SSE：

```text
GET /api/tasks/{task_id}/runs/{run_id}/events?after=<cursor>
```

断线后用最后 cursor 恢复；发生 cursor 过期时重新获取 Task/Run View。SSE 只优化及时性，页面刷新仍以服务器投影为权威。

## 10. API View 与诊断 API

- `TaskSummaryView`、`TaskDetailView`、`RunView`；
- `StageDetailView`、`VoiceUnitView`、`VisualItemView`；
- `ArtifactView`、`CapabilityView`、`ServiceHealthView`；
- `TraceView`、`LogEntryView`、`RunMetricsView`、`DiagnosticBundleView`。

建议端点：

```text
GET  /api/tasks/{task_id}/runs/{run_id}/events?after=<cursor>
GET  /api/tasks/{task_id}/runs/{run_id}/logs?level=&component=&after=
GET  /api/tasks/{task_id}/runs/{run_id}/trace
POST /api/tasks/{task_id}/runs/{run_id}/diagnostics
GET  /api/tasks/{task_id}/runs/{run_id}/diagnostics/{bundle_id}
```

## 11. 渐进迁移

1. 抽出当前 API client、types 和查询逻辑，不改变视觉。
2. 引入共享 Task/Run View、关联 ID 和统一事件读取。
3. 建立任务队列、任务工作台、Voice Unit/Visual Item View。
4. 新创建流程接入 `mountain-av-v1`。
5. 增加活动/诊断面板、日志筛选和诊断包。
6. 旧任务通过 Legacy Adapter 展示，并明确标记旧版同步精度。
7. 新工作台稳定后移除旧详情 overlay、浮动素材 Dock 和重复轮询。

## 12. WebUI 验收

- 用户不理解 Stage 也能一次点击完成视频；
- 引擎和视觉来源是两个独立字段；
- 任意图片可反查 Visual Item 原文、Voice Unit、实际时间和 Artifact；
- fallback 单元可见但不会被误报为失败；
- 单图重生成明确提示“不改变 Voice 与时间边界”；
- 错误展示稳定 code、失败对象、`trace_id` 和可执行建议；
- Web 创建的 Run 可由 Skill 通过同一 `trace_id` 继续，反向亦然；
- 刷新、浏览器关闭或服务重启后状态和事件 cursor 可恢复；
- 页面没有多个组件重复轮询同一 Task；
- 日志、Trace 和诊断包经过自动脱敏测试；
- 旧任务仍可查看和下载，需重渲染时显式迁移为新 Run。
