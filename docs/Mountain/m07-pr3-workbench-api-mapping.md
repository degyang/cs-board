# M07 PR-3 Workbench API Mapping

## 实际调用的 API 端点

| 前端调用 | HTTP 方法 | 端点 | 请求体 | 响应体 |
|---------|----------|------|--------|--------|
| `fetchProject(projectId)` | GET | `/api/v1/projects/{projectId}` | — | `{project, active_run, stages, artifacts, trace, warnings}` |
| `fetchCapabilities()` | GET | `/api/v1/capabilities` | — | `{items[], providers{available[], unavailable[], all_available}}` |
| `fetchUnits(projectId, runId)` | GET | `/api/v1/projects/{projectId}/runs/{runId}/units` | — | `{items[]}` |
| `fetchEvents(projectId, runId, after?)` | GET | `/api/v1/projects/{projectId}/runs/{runId}/events?after={cursor}` | — | `{items[], next_cursor}` |
| `fetchLogs(projectId, runId, filter?)` | GET | `/api/v1/projects/{projectId}/runs/{runId}/logs` | — | `{items[]}` |
| `uploadInputs(projectId, form)` | POST | `/api/v1/projects/{projectId}/inputs` | FormData: script, reference, style, include_subtitles, pen_text, stroke_detail | `{ok, project_id, input_saved}` |
| `startRun(projectId, runId)` | POST | `/api/v1/projects/{projectId}/runs/{runId}/start` | — | `PipelineRunResponse` |
| `cancelRun(projectId, runId)` | POST | `/api/v1/projects/{projectId}/runs/{runId}/cancel` | — | `{ok, status}` |
| `retryRun(projectId, runId)` | POST | `/api/v1/projects/{projectId}/runs/{runId}/retry` | — | `PipelineRunResponse` |
| `runStage(projectId, runId, stage)` | POST | `/api/v1/projects/{projectId}/runs/{runId}/stages/{stage}/run` | — | `PipelineRunResponse` |
| `retryStage(projectId, runId, stage)` | POST | `/api/v1/projects/{projectId}/runs/{runId}/stages/{stage}/retry` | — | `PipelineRunResponse` |
| `getFinalUrl(projectId, runId)` | GET | `/api/v1/projects/{projectId}/runs/{runId}/final` | — | (video binary) |

## 前端组件与 API 的对应关系

### ProjectWorkbenchPage

| 组件区域 | 数据来源 | 说明 |
|---------|---------|------|
| 顶部标题/状态 | `fetchProject` → `project.title`, `active_run.status` | 10s 轮询，terminal 停止 |
| ID 芯片 | `fetchProject` → `project.project_id`, `active_run.run_id`, `active_run.trace_id` | 支持复制 |
| 能力警告 | `fetchCapabilities` → `providers.unavailable` + `providers.providers[name].{error_code,suggestion}` | 显示 provider 名称、error_code、suggestion + 链接 |
| 制作输入表单 | 用户输入 → `uploadInputs` | FormData 上传，浏览器自动设置 Content-Type |
| Start/Cancel/Retry | `startRun` / `cancelRun` / `retryRun` | Start 按钮 disabled 当 inputs 未保存或 capData 未加载或 capability 不可用 |
| 阶段时间线 | `fetchProject` → `stages[]` | 6 阶段节点，状态着色 |
| 阶段工作区 | `fetchProject` → `stages[]` | 每阶段显示状态 + attempt，支持单阶段执行/重试 |
| 配音单元 | `fetchUnits` → `items[]` | 显示 timing.duration_ms, alignment_source, fallback |
| 产物表格 | `fetchProject` → `artifacts[]` | artifact_key, producer_stage, status, size_bytes |
| 成片预览 | `getFinalUrl` → `<video controls>` | 当 compose-video 阶段 succeeded 时显示 |
| 事件列表 | `fetchEvents` → `items[]` | cursor 分页，首次 after=0 |
| 日志列表 | `fetchLogs` → `items[]` | level/component/stage 筛选 |

### RunDiagnosticsPage

| 组件区域 | 数据来源 | 说明 |
|---------|---------|------|
| 运行信息 | `fetchRun` → RunDetail | 状态、target_stage、时间 |
| 阶段状态 | `fetchRun` → `stages` (dict) | 每阶段 status + attempt |
| 事件流 | `fetchEvents` → `items[]` | cursor 分页 |
| 日志 | `fetchLogs` → `items[]` | level 筛选 |

## API Gap

**`GET /projects/{id}/inputs`** — 不存在

- 前端无法读取已保存的制作输入
- 首次访问 pending 状态的运行时，输入表单显示为空
- 无回填策略，用户需重新输入
- 不影响流程：保存后直接进入 pipeline

## 生命周期管理

### 轮询控制

- `useAsync` hook 支持 `pollMs` 参数
- 默认 10s 轮询间隔
- 当 `active_run.status` 为 terminal (`succeeded`/`failed`/`cancelled`) 时停止轮询
- 启动新运行时恢复轮询

### Terminal 状态检测

```typescript
function isTerminal(status: string): boolean {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled'
}
```

### 错误处理

- `CAPABILITY_NOT_AVAILABLE` → 显示 provider 链接，禁用 Start
- API 错误 → error-card 显示错误信息
- 操作反馈 → actionSuccess/actionError 临时提示

## 约束遵守

- [x] 所有 API 调用通过 `/src/lib/api/client.ts` 集中管理
- [x] 禁止组件自行 fetch
- [x] 禁止 mock/fake/localStorage 保存业务状态
- [x] 后端无数据时显示真实空态
- [x] FormData 上传不手工设置 Content-Type
- [x] 不显示物理文件路径
- [x] 不缓存参考音频内容
- [x] API Gap 已记录（无 GET /projects/{id}/inputs）
