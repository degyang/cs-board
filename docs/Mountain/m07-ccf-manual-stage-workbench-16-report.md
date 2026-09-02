# CCF-MANUAL-STAGE-WORKBENCH-16 完成回执

#### 执行摘要

- instruction: `CCF-MANUAL-STAGE-WORKBENCH-16`
- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- starting HEAD: `f2b15f9 docs(mountain): report manual workbench identity isolation`
- implementation commit: `61c6c1b fix(mountain-web): close workbench polling races`
- receipt commit: `docs(mountain): report workbench polling race closeout`（本回执提交）
- push: 未推送
- backend / CCB Gate API / assets / settings: 未修改
- pos-magents / queue / automatic dispatch: 未启动、未调用、未执行

#### §3V.2 完成映射

1. **A→B 完整隔离**：`useAsync` 以依赖数组作 identity；Task 响应校验 `task.task_id`，Inputs 响应校验 `task_id`，Units/Events/Logs 使用 task+run 依赖。identity 变化的 render 立即隐藏旧 data/error，effect 再清理旧状态。
2. **乱序响应**：任务页面只接受当前 task identity；旧 Task/Inputs/Units/Events/Logs 的迟到成功或失败无法覆盖 B。A 资源仍 pending 时，B 先完成后页面只保留 B。
3. **Run/Event 隔离**：事件 identity 为 `${taskId}:${runId}`；变化时重置 `eventCursor`、`allEvents` 和 `eventIdsRef`。同 sequence 在不同 Run 不会被旧 dedup 丢弃。
4. **卸载安全**：`useAsync` alive guard 对 Task、Inputs、Units、Events、Logs 的延迟 resolve/reject 均生效；卸载后不 setState、导航或创建新 timer。
5. **pollMs 生命周期**：`pollMs` 纳入 hook effect 依赖；从 10 秒变为 `undefined` 时清理 effect timer 并跳过新的 load。旧请求因 `alive=false` 不再安排后续 timer。
6. **canonical 状态矩阵**：六个 canonical Stage 的 pending/running/waiting-external/waiting-review/succeeded/failed/skipped/stale/cancelled 均按后端值安全显示；真实 Stage 才显示 attempt，只有 succeeded 计入完成数；unknown Stage 独立显示。
7. **稳定产品文案**：Gate 区域使用“后端人工 Gate 尚未就绪，当前操作不可用”，不暴露 CCF/CCB、工作单号、分支或内部审核状态；无任何可点击 Gate/Stage 操作。
8. **真实生产测试边界**：新测试渲染生产 `TaskWorkbenchPage`，通过生产 `useAsync` 和 API mock 边界驱动，不使用源码文本断言替代竞态行为。

#### 生产竞态测试名称与 fixture 标记

文件：`web-v2/tests/execution-plan.test.tsx`

| 测试 | 证据 |
|---|---|
| `keeps every A marker out of the B page while B is pending and after it completes` | A/B title、run、trace、artifact、unit、event、log、input 均使用可辨识标记；B pending 与完成后逐项断言 A 不可见 |
| `lets B win when A resources are still pending and A later rejects` | A Inputs/Units/Events/Logs deferred；B 先完成；再分别 reject A，B 页面不被迟到错误污染 |
| `clears the previous task identity before the next task request settles` | 同一 Router/组件实例 task-a → task-b，B 请求未完成期间不显示 A |
| `uses an unavailable status for missing stages instead of fabricating pending or attempt zero` | active Run + empty stages 显示尚未报告，不显示 pending/attempt 0 |
| `preserves every backend stage status, including waiting-review and cancellation` | canonical Stage 覆盖九类状态，unknown Stage 独立覆盖 skipped/stale/cancelled |
| `does not update state when task resources resolve or reject after unmount` | Task resolve、Inputs reject 在卸载后均无页面更新；hook alive guard 负责其余资源 |

#### Stage 空态与完成计数

| 后端事实 | 卡片状态 | attempt | completed count |
|---|---|---|---|
| 无 active Run | `尚未报告` | 不显示 | 不计入 |
| active Run 且 `stages=[]` | `尚未报告`，并提示“后端尚未报告 Stage 状态” | 不显示 | 不计入 |
| 部分 canonical stages | 已报告值；其余 `尚未报告` | 仅已报告者显示 | 仅真实 `succeeded` |
| 全部 canonical stages | 后端原始值 | 每个来自后端 | 仅真实 `succeeded` |
| unknown Stage | 原始状态 + 未知阶段 | 不参与 canonical 计数 | 不计入 |

#### CCB-25 Gate 对接等待项

本轮不调用以下尚未通过独立审核的真实接口；字段以 CCB-25 最终稳定契约为准：

| method | path | request | response | error / refresh |
|---|---|---|---|---|
| `GET` | `/api/v1/tasks/{task_id}/runs/{run_id}/gates` | 无 body | 六个 Gate，canonical 顺序；task/run/trace、stage、status、decision、actor、decided time、attempt、revision、evidence | 失败由后端 `body.error` 定义；任务轮询刷新 |
| `GET` | `/api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` | 无 body | 单 Gate，同上字段 | unknown stage 等错误由后端定义；Stage 卡刷新 |
| `POST` | `/api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` | `{decision: approve|reject|redo, actor, note?, evidence?: [{logical_key, sha256}]}` | 更新后的 Gate、revision | malformed/unknown stage `400 body.error`；冲突 `409 body.error`；相同 decision/evidence 幂等 |

页面目前只展示稳定不可用文案，不生成本地 Gate 状态，不绕过上游批准。

#### 门禁原始摘要

```text
$ npm --prefix web-v2 run build
✓ tsc --noEmit && vite build
✓ 68 modules transformed
✓ built successfully

$ npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-manual-stage-workbench-16-test.log
Test Files  15 passed (15)
Tests       353 passed (353)

$ ! rg -n "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection|state update on an unmounted" /tmp/ccf-manual-stage-workbench-16-test.log
0 matches

$ npm --prefix web-v2 run test:contract-checker
Test Files  2 passed (2)
Tests       48 passed (48)

$ ! rg -n "CCF|CCB|WORKBENCH-[0-9]+|STAGE-GATE-[A-Z-]*[0-9]+" web-v2/src
0 matches

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

- Gate API 仍需独立审核与最终字段冻结；本轮未启用任何 Gate 或 Stage 操作。
- 轮询资源在 identity 变化时会清理旧快照，调用方不可依赖旧 response 继续展示。
- 真实文案、参考音频、Codex 插画候选与最终 MP4 仍待用户最终验收；本轮没有创建 Task 或冒充真实制作成果。
- 本回执不代表 PM 审核通过，也未进入 `USER_ACCEPTANCE`。

