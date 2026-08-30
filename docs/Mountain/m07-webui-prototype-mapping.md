# M07 WebUI Prototype Mapping

> **迁移说明：** 本映射记录的是 Task 术语迁移前的实现差异。最终产品以 Task/`task_id`/`/tasks`、任务队列和任务工作台为准；文中 `/projects`、Project 和“项目列表/工作台”不构成最终术语或接口承诺。

> 原型唯一来源（只读）：`/mnt/d/Workstation/SynologyDrive/workbuddy/Workshop/mountain/`
> 本文档逐项记录原型文件与 web-v2 的对应关系、处理方式、mock 排除与 API gap。

---

## 1. 配置与入口

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `package.json` | 依赖声明 | `web-v2/package.json` | 保持 web-v2 现有依赖（React 18, RR6, Vitest），不引入原型额外依赖 | — |
| `vite.config.ts` | Vite 配置, proxy → 8787 | `web-v2/vite.config.ts` | 保持 web-v2 proxy → 8000 | 原型 proxy 到 8787，web-v2 proxy 到 8000（cs-board 后端） |
| `tsconfig.json` | TS 配置 | `web-v2/tsconfig.json` | 保持 web-v2 现有配置 | — |
| `index.html` | HTML 入口 | `web-v2/index.html` | 保持 | — |
| `src/main.tsx` | React 入口 | `web-v2/src/main.tsx` | 保持 | — |
| `src/vite-env.d.ts` | 类型声明 | `web-v2/src/vite-env.d.ts` | 保持 | — |

## 2. App 层

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `src/app/router.tsx` | 路由表：`/create`, `/projects`, `/assets`, `/projects/:projectId`, `/projects/:projectId/runs/:runId/diagnostics`, `/settings`, `/help` | `web-v2/src/app/router.tsx` | **适配**：调整路由为 `/projects`, `/projects/new`, `/projects/:id`, `/projects/:id/runs/:runId/diagnostics`, `/help`, `/settings/providers`, `/settings/providers/:name` | 原型用 `/create`，web-v2 用 `/projects/new`（RESTful）；原型有 `/assets` 和 `/settings`，web-v2 拆分为 `/settings/providers` |
| `src/app/providers.tsx` | `CurrentRunContext`：fetchCurrentRun 提供当前运行项目 | `web-v2/src/app/providers.tsx` | **适配**：用真实 `/api/v1/projects` 查找 running 状态项目替代 mock `fetchCurrentRun` | 原型依赖 `fetchCurrentRun()` mock；真实 API 无 `/runs/current` 端点，需从项目列表推断 |

## 3. 布局组件

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `src/components/layout/AppShell.tsx` | 根布局：sidebar pin/unpin 状态管理 + `<Sidebar>` + `<Outlet>` | `web-v2/src/components/layout/AppShell.tsx` | **重写**：移除内联 nav/topbar/breadcrumbs，改用 Sidebar 组件 + Outlet | — |
| `src/components/layout/Sidebar.tsx` | 侧边导航：品牌区、SVG 图标导航、pin 按钮、当前运行状态栏 | `web-v2/src/components/layout/Sidebar.tsx` | **新建**：迁移原型结构/SVG 图标/pin 逻辑，用真实 API 替代 `useCurrentRun` | 原型 `useCurrentRun()` 来自 mock；改为从项目列表推断 running 状态 |

## 4. UI 组件

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `src/components/ui/Tabs.tsx` | 通用标签栏 | 无 | **直接迁移** | 无 mock 依赖 |
| `src/components/ui/StatusBadge.tsx` | 状态徽章 | 无 | **直接迁移** | 无 mock 依赖 |
| `src/components/ui/CopyButton.tsx` | 剪贴板复制按钮 | 无 | **直接迁移** | 无 mock 依赖 |
| `src/components/ui/BackButton.tsx` | 返回导航按钮 | 无 | **直接迁移** | 无 mock 依赖 |

## 5. 页面

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `src/pages/ProjectsPage.tsx` | 项目列表：状态过滤 Tabs、搜索、项目卡片（进度条、操作按钮）、15s 轮询 | `web-v2/src/pages/ProjectsPage.tsx` | **重写**：采用原型信息架构（Tabs、搜索、卡片布局），用真实 `fetchProjects` API | 原型 `ProjectSummaryView.run` 含 voice_done/voice_total 等进度字段；真实 API 的 `GET /projects` 不返回 run 详情，进度条数据不可用，需省略 |
| `src/pages/CreateProjectPage.tsx` | 新建任务：6 Tab（介绍/文案/声音/输出/视觉/成片） | `web-v2/src/pages/CreateProjectPage.tsx` | **简化适配**：真实 API 仅支持 title+engine+pipeline，无法支持完整 6 Tab。保留原型视觉风格（page-head、action-bar），简化为单页表单 | 原型依赖 `assetStore`（音色/风格）、`splitText`（智能分段）、`submitCommand`（命令模式）；全部排除。真实 API 用 `POST /projects` |
| `src/pages/ProjectWorkbenchPage.tsx` | 项目工作台：三列布局（Unit 列表 / 阶段工作区 / 产物栏）、六阶段时间线、活动面板 | `web-v2/src/pages/ProjectWorkbenchPage.tsx` | **新建（shell）**：采用原型布局结构（header + timeline + 3-col body），用真实 `fetchProject` 数据填充，run/units/artifacts 为空时显示真实空态 | 原型 `RunView` 含 voice_units/artifacts/stages；真实 API 需分别调用 `/runs/:rid`、`/units`、`/artifacts`。本 PR 只做 shell + 空态，PR-3 接入完整数据 |
| `src/pages/RunDiagnosticsPage.tsx` | 运行诊断：trace_id + RunActivityPanel | `web-v2/src/pages/RunDiagnosticsPage.tsx` | **新建（shell）**：采用原型结构，真实 events/logs API，无数据时显示空态 | 原型 `RunActivityPanel` 含 4 Tab（Events/Logs/Metrics/Diagnostics），依赖 mock。本 PR 只做 shell + 空态 |
| `src/pages/HelpPage.tsx` | 帮助页：六阶段说明、状态说明、错误码、诊断说明 | 无 | **直接迁移** | 无 mock 依赖，使用 `STAGE_KEYS`/`STAGE_NAMES` |
| `src/pages/SettingsPage.tsx` | 设置页（5 Tab） | 不迁移 | **排除** | 依赖 `settingsStore`（localStorage 持久化）、`submitCommand`。Provider 配置已由 web-v2 的 `ProvidersPage`/`ProviderDetailPage` 覆盖 |

## 6. Features（均不迁移）

| 原型文件 | 职责 | 排除原因 |
|---|---|---|
| `src/features/stage-timeline/StageTimeline.tsx` | 六阶段时间线组件 | 将在 PR-3 用真实数据重新实现 |
| `src/features/voice-units/VoiceUnitList.tsx` | Voice Unit 列表 | 依赖 `RunView.voice_units`，将在 PR-3 用真实 `/units` API |
| `src/features/artifact-gallery/ArtifactPanel.tsx` | 产物面板 | 依赖 `RunView.artifacts`，将在 PR-3 用真实 `/artifacts` API |
| `src/features/project-workbench/StageWorkspace.tsx` | 阶段工作区 | 重度依赖 `submitCommand` mock，将在 PR-3 重新实现 |
| `src/features/run-activity/RunActivityPanel.tsx` | 活动与诊断面板 | 依赖 mock events/logs/metrics，将在 PR-3 用真实 API |
| `src/features/settings/*` | 设置页 + 设置存储 | 依赖 localStorage 持久化 + `submitCommand`，Provider 配置已覆盖 |
| `src/features/asset-management/*` | 资产管理（风格/音色库） | 依赖 localStorage 持久化 + seed 数据，不在当前范围 |

## 7. Lib

| 原型文件 | 职责 | web-v2 对应 | 处理方式 | mock/API gap |
|---|---|---|---|---|
| `src/lib/api/types.ts` | API View 类型定义（234 行） | `web-v2/src/lib/api/types.ts` | **合并**：将 `StageKey`、`STAGE_KEYS`、`STAGE_NAMES`、`ENGINE_NAMES` 迁移到 web-v2；保留 web-v2 现有真实 API 类型 | 原型 `RunView`/`ProjectSummaryView` 等与真实 API 响应形状不同，不直接复制 |
| `src/lib/api/client.ts` | API client（mock/real 切换） | `web-v2/src/lib/api/client.ts` | **扩展**：新增 `fetchRun`/`fetchStages`/`fetchEvents`/`fetchLogs`/`fetchUnits`/`fetchArtifacts`，全部调用真实 `/api/v1` | **排除 mock.ts 导入**。原型 `submitCommand()` 不存在于真实 API，用具体端点替代 |
| `src/lib/api/queries.ts` | `useAsync` hook（轮询） | 无 | **新建**：迁移 `useAsync` hook，去掉 mock 依赖 | 无 mock 依赖 |
| `src/lib/api/mock.ts` | Mock 数据层（441 行） | **不迁移** | **严格排除** | 全部是 mock 数据 |
| `src/lib/formatting.ts` | 格式化工具 | `web-v2/src/lib/formatting.ts` | **扩展**：添加 `formatBytes`/`formatSeconds`/`formatMs`/`formatClock`/`percent` | 无 mock 依赖 |
| `src/lib/splitText.ts` | 智能文本分段 | **不迁移** | 客户端分段逻辑，真实 API 由后端处理 | — |

## 8. Styles

| 原型文件 | 职责 | web-v2 对应 | 处理方式 |
|---|---|---|---|
| `src/styles/tokens.css` | NovaTech 设计 token（74 行） | `web-v2/src/styles/tokens.css` | **同步**：补充 letter-spacing、breakpoints 等缺失 token |
| `src/styles/app.css` | 组件样式（842 行） | `web-v2/src/styles/app.css` | **合并**：补充 sidebar pin/rail、tabs、back button、workbench grid、stage timeline、trace chips、activity panel、help page、responsive 等样式 |

## 9. Mock 排除清单

以下原型文件/导入在 web-v2 中**绝对禁止出现**：

- `src/lib/api/mock.ts` — 整个文件
- `import * as mock from './mock'` — 任何导入
- `mock.projects`、`mock.projectDetail()`、`mock.capability()` 等 — 任何 mock 返回值引用
- `USE_MOCK` 变量 — mock/real 切换逻辑
- `submitCommand()` — 命令模式（真实 API 用具体端点）
- `useAssetStore()` — 资产管理 localStorage
- `settingsStore` — 设置 localStorage
- `splitBySentences()` — 客户端分段

## 10. API Gap 汇总

| 原型期望 | 真实 API 状态 | 处理 |
|---|---|---|
| `GET /projects` 返回含 `run` 进度的列表 | `GET /api/v1/projects` 仅返回 project 基础字段 + `active_run_id` | 项目卡片不显示进度条 |
| `GET /runs/current` 获取当前运行 | 不存在 | 从项目列表推断 running 状态 |
| `POST /api/commands` 统一命令入口 | 不存在 | 用 `POST .../start`、`POST .../cancel`、`POST .../retry` |
| `RunView` 含 voice_units/artifacts 嵌套 | 需分别调用 `/units`、`/artifacts` | PR-3 分别获取 |
| `CapabilityView` 按 engine+visual_source 查询 | `GET /api/v1/capabilities` 返回全部 | 适配查询方式 |
| `SettingsSectionView` 设置分组 | Provider API 已覆盖 | 不迁移设置页 |

## 11. 后端 DTO 对照（webapp/mountain_v1_api.py → web-v2/src/lib/api/types.ts）

逐项对照后端实际响应，确认前端 DTO 字段完全匹配。

### GET /health
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `status: str` | `HealthResponse.status: string` | ✅ |
| `providers.all_available: bool` | `HealthResponse.providers.all_available: boolean` | ✅ |
| `providers.providers.<name>.available: bool` | `ProviderAvailability.available: boolean` | ✅ |
| `providers.providers.<name>.component: str` | `ProviderAvailability.component?: string` | ✅ |
| `providers.providers.<name>.error_code: str\|null` | `ProviderAvailability.error_code?: string\|null` | ✅ |
| `providers.providers.<name>.suggestion: str\|null` | `ProviderAvailability.suggestion?: string\|null` | ✅ |
| `providers.unavailable: [str]` | `HealthResponse.providers.unavailable: string[]` | ✅ |

### GET /capabilities
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[].engine: str` | `CapabilityItem.engine: string` | ✅ |
| `items[].visual_source: str` | `CapabilityItem.visual_source: string` | ✅ |
| `items[].supported: bool` | `CapabilityItem.supported: boolean` | ✅ |
| `items[].pipeline_id: str` | `CapabilityItem.pipeline_id: string` | ✅ |
| `items[].reason_code: str\|null` | `CapabilityItem.reason_code: string\|null` | ✅ |

### GET /providers
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `providers.<name>.profile.*` | `ProviderProfile` | ✅ |
| `providers.<name>.config_status.*` | `ConfigStatus` | ✅ |
| `providers.<name>.availability.*` | `ProviderAvailability` | ✅ |
| `all_configured: bool` | `ProviderListResponse.all_configured: boolean` | ✅ |
| `all_available: bool` | `ProviderListResponse.all_available: boolean` | ✅ |

### GET /providers/{name}
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `name, profile, config, config_status, availability` | `ProviderDetail` | ✅ |

### PUT /providers/{name}/config
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `ok: true, provider: str, config: {}` | `UpdateConfigResponse` | ✅ |

### GET /providers/{name}/secrets
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `provider: str` | `SecretStatusResponse.provider: string` | ✅ |
| `secrets.<key>.configured: bool` | `SecretInfo.configured: boolean` | ✅ |
| `secrets.<key>.masked_value: str\|null` | `SecretInfo.masked_value: string\|null` | ✅ |

### POST /providers/{name}/secrets
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `ok: true, provider: str, key: str` | `SecretOperationResponse` | ✅ |

### DELETE /providers/{name}/secrets/{key}
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `ok: true, provider: str, key: str` | `SecretOperationResponse` | ✅ |

### GET /projects
| 后端字段 (Project.to_dict) | 前端类型 | 匹配 |
|---|---|---|
| `project_id: str` | `Project.project_id: string` | ✅ |
| `title: str` | `Project.title: string` | ✅ |
| `pipeline_id: str` | `Project.pipeline_id: string` | ✅ |
| `engine: str` | `Project.engine: string` | ✅ |
| `status: str` | `Project.status: string` | ✅ |
| `created_at: str` | `Project.created_at: string` | ✅ |
| `updated_at: str` | `Project.updated_at: string` | ✅ |
| `active_run_id: str\|null` | `Project.active_run_id: string\|null` | ✅ |
| `revision: int` | `Project.revision: number` | ✅ |
| `schema_version: int` | `Project.schema_version: number` | ✅ |

### POST /projects
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `ok: true` | `CreateProjectResponse.ok: boolean` | ✅ |
| `command: str` | `CreateProjectResponse.command: string` | ✅ |
| `project_id: str` | `CreateProjectResponse.project_id: string` | ✅ |
| `run_id: str` | `CreateProjectResponse.run_id: string` | ✅ |
| `trace_id: str` | `CreateProjectResponse.trace_id: string` | ✅ |
| `command_id: str` | `CreateProjectResponse.command_id: string` | ✅ |
| `event_sequence: int` | `CreateProjectResponse.event_sequence: number` | ✅ |

### GET /projects/{id}
| 后端字段 (_project_detail_view) | 前端类型 | 匹配 |
|---|---|---|
| `project: Project.to_dict()` | `ProjectDetail.project: Project` | ✅ |
| `active_run: Run.to_dict()\|null` | `ProjectDetail.active_run: RunDetail\|null` | ✅ |
| `stages: [{stage, status, attempt}]` | `ProjectDetail.stages: StageListItem[]` | ✅ |
| `warnings: [...]` | `ProjectDetail.warnings: unknown[]` | ✅ |
| `artifacts: [{artifact_key, relative_path, sha256, size_bytes, producer_stage, status}]` | `ProjectDetail.artifacts: Artifact[]` | ✅ |
| `trace: {trace_id, command_ids}\|null` | `ProjectDetail.trace: TraceInfo\|null` | ✅ |

### GET /projects/{id}/runs/{runId}
| 后端字段 (Run.to_dict) | 前端类型 | 匹配 |
|---|---|---|
| `schema_version: int` | `RunDetail.schema_version: number` | ✅ |
| `run_id: str` | `RunDetail.run_id: string` | ✅ |
| `project_id: str` | `RunDetail.project_id: string` | ✅ |
| `trace_id: str` | `RunDetail.trace_id: string` | ✅ |
| `entrypoint: str` | `RunDetail.entrypoint: string` | ✅ |
| `command_ids: [str]` | `RunDetail.command_ids: string[]` | ✅ |
| `status: str` | `RunDetail.status: string` | ✅ |
| `target_stage: str\|null` | `RunDetail.target_stage: string\|null` | ✅ |
| `started_at: str` | `RunDetail.started_at: string` | ✅ |
| `finished_at: str\|null` | `RunDetail.finished_at: string\|null` | ✅ |
| `stages.<name>.status: str` | `StageState.status: string` | ✅ |
| `stages.<name>.attempt: int` | `StageState.attempt: number` | ✅ |
| `warnings: [...]` | `RunDetail.warnings: unknown[]` | ✅ |

### GET /projects/{id}/runs/{runId}/stages
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[].stage: str` | `StageListItem.stage: string` | ✅ |
| `items[].status: str` | `StageListItem.status: string` | ✅ |
| `items[].attempt: int` | `StageListItem.attempt: number` | ✅ |

### GET /projects/{id}/runs/{runId}/units
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[]` (merged av-plan + timeline) | `Unit` (flexible dict with `unit_id`, optional `text`, `order`, `timing`) | ✅ |

### GET /projects/{id}/runs/{runId}/artifacts
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[].artifact_key: str` | `Artifact.artifact_key: string` | ✅ |
| `items[].relative_path: str` | `Artifact.relative_path: string` | ✅ |
| `items[].sha256: str` | `Artifact.sha256: string` | ✅ |
| `items[].size_bytes: int` | `Artifact.size_bytes: number` | ✅ |
| `items[].producer_stage: str` | `Artifact.producer_stage: string` | ✅ |
| `items[].status: str` | `Artifact.status: string` | ✅ |

### GET /projects/{id}/runs/{runId}/events?after=N
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[]` (arbitrary event dicts) | `EventsResponse.items: Record<string, unknown>[]` | ✅ |
| `next_cursor: int` | `EventsResponse.next_cursor: number` | ✅ |

### GET /projects/{id}/runs/{runId}/logs?level=&component=&stage=
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `items[]` (parsed JSONL) | `LogsResponse.items: Record<string, unknown>[]` | ✅ |
| Query: `level`, `component`, `stage` | `fetchLogs(filters?)` | ✅ |

### POST /projects/{id}/runs/{runId}/cancel
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| `ok: true, status: "cancelled"` | `cancelRun()` returns `unknown` | ✅ |

### POST /projects/{id}/runs/{runId}/retry
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| Pipeline result shape | `retryRun()` returns `unknown` | ✅ |

### GET /projects/{id}/runs/{runId}/final
| 后端字段 | 前端类型 | 匹配 |
|---|---|---|
| FileResponse (video/mp4) | `getFinalUrl()` returns URL string | ✅ |
