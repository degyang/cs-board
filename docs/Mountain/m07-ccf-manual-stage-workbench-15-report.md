# CCF-MANUAL-STAGE-WORKBENCH-15 完成回执

#### 执行摘要

- instruction: `CCF-MANUAL-STAGE-WORKBENCH-15`
- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- starting HEAD: `0bf8fa3 docs(mountain): report manual stage workbench baseline`
- implementation commit: `03f10ba fix(mountain-web): isolate manual workbench identities`
- follow-up label commit: `6f60153 fix(mountain-web): preserve known stage labels`
- receipt commit: `docs(mountain): report manual workbench identity isolation`（本回执提交）
- push: 未推送
- backend / CCB Gate API / assets / settings: 未修改

#### §3T.2 修正映射

1. **身份绑定与旧数据清理**：`useAsync` 对依赖数组做 identity 比较；依赖改变时在当前 render 隐藏旧 data/error、标记 loading，并在 effect 中清理旧状态后启动新请求。工作台另以 `taskData.task.task_id === taskId` 校验 Task 详情，以 `inputs.task_id === taskId` 校验输入回读。
2. **Task 切换隔离**：A → B 期间不渲染 A 的标题、Run、Artifacts、Inputs；Units、Logs、Capabilities、Events 使用依赖变化后的空态，直到 B 请求完成。
3. **Run/Event 隔离**：事件 identity 为 `${taskId}:${runId}`。改变 task/run 后清零 `eventCursor`、`allEvents` 和 `eventIdsRef`；过渡 render 使用空集合，确保相同 sequence 在新 Run 不被旧 Run 去重。
4. **卸载安全**：`useAsync` 保留 alive guard；延迟成功/失败均在卸载后丢弃，不 setState、不重启 timer、不导航。
5. **真实 Stage 空态**：缺失 canonical Stage 使用 `unreported`/“尚未报告”，不显示 pending、不显示 attempt 0、不计入 `completedCount`。
6. **No Run / Empty Stage**：无 active Run 显示“任务尚未启动运行”；有 Run 但 `stages=[]` 显示“后端尚未报告 Stage 状态”；六张静态契约卡仍展示但不构造 Stage DTO。
7. **状态原样展示**：后端状态经 `StatusBadge` 安全显示，缺失状态与未知 Stage 不触发前端操作；只有实际 Stage 数据存在时才显示 attempt。
8. **Gate 保持禁用**：页面显示“后端 Gate 契约正在收口，CCB-25 通过后启用”，没有 approve/reject/redo 或 Stage run/retry 按钮。本轮没有编码 Gate API。

#### Identity 设计与重置点

| 资源 | identity | 旧数据清理/可见性保护 |
|---|---|---|
| Task detail | `taskId`，并校验响应 `task.task_id` | `useAsync` 依赖变更清理；响应 ID 不匹配时整页不读旧 Task |
| Inputs | `taskId`，并校验响应 `task_id` | 依赖变更清理；只读取当前 Task 的输入 |
| Units | `taskId + runId` | 依赖变更时 hook 隐藏并清理旧 response |
| Logs | `taskId + runId + logFilter` | run/filter 改变时 hook 隐藏并清理旧 response |
| Events | `taskId + runId + eventCursor` | identity effect 清零 cursor/list/dedup；过渡帧使用空集合 |
| Artifacts / trace | Task detail identity | 只从 ID 匹配的 Task detail 派生 |

#### 强制行为测试

`web-v2/tests/execution-plan.test.tsx` 使用生产 `TaskWorkbenchPage`、生产 `useAsync` 和 API mock 边界，新增/覆盖：

- `clears the previous task identity before the next task request settles`：同一 Router/组件实例从 task-a 导航 task-b，B 延迟期间不出现 A 或 B 的旧数据，B 完成后只显示 B。
- `uses an unavailable status for missing stages instead of fabricating pending or attempt zero`：active Run + empty stages 只显示尚未报告，不显示 pending/attempt 0。
- `preserves every backend stage status, including waiting-review and cancellation`：pending、running、waiting-external、waiting-review、succeeded、failed、skipped、stale、cancelled 与未知状态均安全呈现。
- `does not update state when task resources resolve or reject after unmount`：Task/Inputs 延迟成功与失败在卸载后不写入页面。
- 原有六阶段固定顺序、六类契约字段、Gate 缺失和 no active Run 行为继续通过。

#### Stage 空态矩阵

| 后端事实 | 卡片状态 | attempt | 完成计数 |
|---|---|---|---|
| 无 active Run | 尚未报告 | 不显示 | 不计入 |
| active Run，`stages=[]` | 尚未报告 | 不显示 | 不计入 |
| 部分 Stage | 已报告的状态；缺失者尚未报告 | 仅已报告者显示 | 仅真实 succeeded 计入 |
| 全部 Stage | 后端原始状态 | 每个来自后端 | 仅真实 succeeded 计入 |
| 未知 Stage | 原始状态 + 未知阶段 | 后端值（不参与 canonical 计数） | 不计入 |

#### CCB-25 Gate API 等待项

本轮不调用以下尚未通过审核的契约，仅记录真实路径与待最终字段：

| method | path | request | response | error / refresh |
|---|---|---|---|---|
| `GET` | `/api/v1/tasks/{task_id}/runs/{run_id}/gates` | 无 body | 六个 Gate，canonical 顺序；含 task/run/trace、stage、status、decision、actor、decided time、attempt、revision、evidence | 未找到/权限/服务错误由 CCB-25 定义；任务轮询时刷新 |
| `GET` | `/api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` | 无 body | 单 Gate，同上字段 | unknown stage 等错误由 CCB-25 定义；Stage 卡刷新时读取 |
| `POST` | `/api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` | `{decision: approve\|reject\|redo, actor, note?, evidence?: [{logical_key, sha256}]}` | 更新后的 Gate 与 revision | malformed/unknown stage `400 body.error`；冲突 `409 body.error`；相同 decision/evidence 幂等。CCB-25 稳定后再启用 |

前端仍显示：`后端 Gate 契约正在收口，CCB-25 通过后启用`。没有假 Gate、本地 Gate 状态或绕过上游批准的请求。

#### 门禁摘要

```text
$ npm --prefix web-v2 run build
✓ tsc --noEmit && vite build
✓ 68 modules transformed
✓ built successfully

$ npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-manual-stage-workbench-15-test.log
Test Files  15 passed (15)
Tests       351 passed (351)

$ ! rg -n "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection|state update on an unmounted" /tmp/ccf-manual-stage-workbench-15-test.log
0 matches

$ npm --prefix web-v2 run test:contract-checker
Test Files  2 passed (2)
Tests       48 passed (48)

$ ! rg -n "\\b(project|projects|Project|Projects|project_id)\\b|['\"]split['\"]|executionMode|manualStages|execution_mode|manual_stages" web-v2/src/pages/TaskWorkbenchPage.tsx web-v2/src/lib/api/types.ts web-v2/src/components web-v2/src/features
0 matches

$ ! rg -n "localStorage|sessionStorage|Math\\.random" web-v2/src/pages/TaskWorkbenchPage.tsx web-v2/tests
0 matches

$ git diff --check
0 errors

$ git status --short
(empty after receipt commit)
```

#### 遗留风险与验收距离

- CCB-25 Gate API 尚未通过独立审核；本轮未实现 Gate 操作，六阶段运行闭环仍等待后续授权切片。
- 轮询 hook 现在会在任意依赖改变时清理数据，调用方若需要保留旧快照必须显式建模，不得依赖旧 response。
- 用户真实文案、参考音频、风格偏好和最终媒体效果仍留待最终验收；本轮没有创建 Task 或冒充制作成果。
- 未启动 pos-magents、未调用队列、未自动派工；本回执不代表 PM 审核通过。
