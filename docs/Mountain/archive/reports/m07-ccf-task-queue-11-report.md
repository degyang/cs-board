#### CCF-TASK-QUEUE-11 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation commit: `d8a2ce8`
- git status: clean

##### 生产 Router 验证

生产 `router.tsx` 定义的任务相关路由：
```
/tasks              → TasksPage
/tasks/new          → CreateTaskPage
/tasks/:taskId      → TaskWorkbenchPage
/tasks/:taskId/runs/:runId/diagnostics → RunDiagnosticsPage
```

无 `/tasks/:taskId/runs/:runId/final` 路由。成片入口改为 `<a href={getFinalUrl(...)}>` 指向后端媒体 endpoint。测试 `renderAt()` 不再注册 `/final` Route。

##### 成片 API URL

```typescript
getFinalUrl(taskId, runId)
  → `${BASE}/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/final`
```

组件使用：
```tsx
<a href={getFinalUrl(t.task_id, runId)} target="_blank" rel="noopener noreferrer">
  成片
</a>
```

##### 编码案例

所有 Task/Run ID 通过集中 helper 编码：
```typescript
encodeId(id) → encodeURIComponent(id)
taskWorkbenchPath(taskId)    → `/tasks/${encodeId(taskId)}`
runDiagnosticsPath(t, r)     → `/tasks/${encodeId(t)}/runs/${encodeId(r)}/diagnostics`
```

测试验证含 `+` 和 `/` 的 ID 正确编码。

##### 分页状态机

| 状态 | loading | loadingMore | 按钮 |
|---|---|---|---|
| 首次加载 | true | — | — |
| 加载更多 pending | false | true | disabled, "加载中…" |
| 加载更多完成 | false | false | enabled / 隐藏 |
| 加载更多失败 | false | false | 保留列表, 显示局部错误 + 重试 |

`pendingCursor.current` 防止同一 cursor 并发请求。

##### 旧响应隔离

`generation` ref 在每次筛选/卸载时递增。分页请求携带发起时的 generation，完成时比对：
- generation 不匹配 → 静默丢弃，不 setState
- 测试：旧分页挂起 → 切换筛选 → 新响应先到 → 旧分页后到 → DOM 只有新数据

##### 去重行为

`append` 时按 `task_id` 去重：
```typescript
setItems(prev => {
  const seen = new Set(prev.map(t => t.task_id))
  const newItems = data.items.filter(t => !seen.has(t.task_id))
  return [...prev, ...newItems]
})
```

测试验证跨页重复 task_id 只出现一次，顺序稳定。

##### 运行摘要映射

| 字段 | 表现 |
|---|---|
| `active_run.status` | 显示 "运行状态：" + StatusBadge（running=运行中, failed=失败 等） |
| `active_run.current_stage` | 显示 "当前阶段：" + STAGE_NAMES 映射，未知保留原值 |
| `active_run.retryable=true` | 显示 "可重试" 提示（纯文本，无按钮） |
| `active_run.retryable=false` | 不显示 "可重试" |
| `active_run.final_available` | 控制成片入口显示 |
| `active_run` 为 null | 显示 "尚未运行" |

##### 门禁原始摘要

```
build: ✓ (tsc --noEmit && vite build)
contract checker tests: 48/48
full tests: 329/329
act warnings: 0
Router warnings: 0
unhandled rejection: 0
rg /final route: 0 matches
rg localStorage/sessionStorage/Math.random: 0 matches
git diff --check: clean
```

##### 未完成事项

无。
