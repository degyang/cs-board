#### CCF-TASK-QUEUE-12 完成报告 — 2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation commit: `41041dd`（原始）+ `7e4b534`（本轮纠偏 follow-up）
- report commit: `685787d`（原始）+ 本轮纠偏 follow-up（见下）
- git status: clean

##### 本轮纠偏（2026-09-01 逐字复核）：上一版报告 assertion-free 扫描范围错误

复核发现：上一版本报告（`685787d`）在「门禁原始摘要」中写为
`rg assertion-free test (task-queue): 0 matches`，将 §3P.3 逐字门禁的
`rg ... web-v2/tests` 扫描范围收窄为仅 `task-queue.test.tsx`。逐字门禁扫描整个
`web-v2/tests` 目录，命中 1 处：

```
web-v2/tests/race-condition.test.tsx:265:    // No assertion needed — test passes if no "setState on unmounted" warning
```

该无断言测试早于 CCF-TASK-QUEUE-12（由 `c7695e2` 引入，`41041dd` 未触及此文件），
其 `// No assertion needed` 注释命中门禁正则 `No assertion needed`。上一版报告的
`(task-queue)` 收窄掩盖了该命中。

本轮以真实断言修复（follow-up `7e4b534`，不 squash `41041dd`，遵循 §2.4）：

- 新增 call-through `vi.spyOn(console, 'error')`（不屏蔽——真实 warning 仍输出到
  stderr 且被门禁 warning 扫描捕获，符合 §2.3）；
- 断言 unmount 后 fetch resolve 不泄漏 `unmounted` / `can't perform a react state
  update` / `not wrapped in act` warning（真实 `expect`，`mockRestore` 收尾）；
- 删除 `// No assertion needed` 注释。

未修改任何生产代码、DTO、TasksPage 分页/创建/工作台/Pipeline 行为——仅测试证据
（§3P.2 item 6 约束）。

> 说明：上一版报告的 warning 结论（act / router / unhandled = 0）经本轮逐字复核
> **确实为真**——`41041dd` 删除了输出两条 act warning 的无断言 production-router
> 测试后，warning 扫描稳定为 0。本轮纠正的只是 assertion-free 扫描范围，非 warning
> 结论本身。

##### 上一报告 warning 结论错误

`m07-ccf-task-queue-11-report.md` 声称 `act warnings: 0`，但审核者复现时
`production router has no /final route` 测试（第492行）无断言且未等待异步 settle，
稳定输出两条 React act warning。本轮纠正该声明（`41041dd` 删除该测试）。

##### 删除的测试

```
旧: it('production router has no /final route (test does not fake one)', () => {
       renderAt(<TasksPage />)
       // No assertion needed — the absence of /final in renderAt is the proof.
     })
```

该测试无断言，渲染后未等待请求 settle，产生 act warning。已删除。

##### 导出的真实生产 RouteObject

`router.tsx` 导出：
```typescript
export const TASK_ROUTES = [
  { index: true, element: <TasksPage /> },
  { path: 'tasks/new', element: <CreateTaskPage /> },
  { path: 'tasks/:taskId', element: <TaskWorkbenchPage /> },
  { path: 'tasks/:taskId/runs/:runId/diagnostics', element: <RunDiagnosticsPage /> },
]
```

`createBrowserRouter` 通过 `...TASK_ROUTES` 展开复用，不重复定义；测试直接 import
`TASK_ROUTES` 与 `matchRoutes` 验证，非源码字符串检查。

##### matchRoutes 行为结果

```
✓ matches /tasks/:taskId as workbench page
✓ matches /tasks/:taskId/runs/:runId/diagnostics
✓ does NOT match /tasks/:taskId/runs/:runId/final as a task route
✓ matches /tasks/new
✓ index route matches / when wrapped in parent
```

`/tasks/:taskId/runs/:runId/final` 不匹配任何 TASK_ROUTES，在生产 Router 中落入
wildcard/404。本轮逐字复核全部通过（32/32 task-queue 测试）。

##### 成片 API 链接验证

```
✓ shows final as <a> with getFinalUrl href when final_available is true
  - el.tagName === 'A'（非 Router Link）
  - el.href === getFinalUrl('task/special+id', 'run/special+id')
  - el.target === '_blank'
  - el.rel === 'noopener noreferrer'
✓ hides final link when final_available is false
```

##### 全量测试与 warning 扫描结果（本轮逐字复核 2026-09-01）

```
build: ✓ (tsc --noEmit && vite build, 945ms)
Tests: 332 passed (332) — 14 files
warning scan: rg "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection" /tmp/ccf-task-queue-12-test.log → 0 matches
assertion-free scan: rg "No assertion needed|absence.*proof|it\([^)]*production router[^)]*,\s*\(\)\s*=>\s*\{\s*\}\)" web-v2/tests → 0 matches（7e4b534 修复 race-condition.test.tsx:265 后）
Act warnings: 0
Router warnings: 0
Unhandled rejections: 0
git diff --check: clean
git status --short: clean
```

##### checker 结果

```
npm --prefix web-v2 run test:contract-checker
contract checker tests: 48/48
  - tests/checker-behavior.test.ts: 33
  - tests/contract-checker-exec.test.ts: 15
```

##### 门禁原始摘要（本轮逐字 §3P.3）

```
build: ✓ (tsc --noEmit && vite build)
full tests: 332/332
warning scan: 0 matches
contract checker: 48/48
assertion-free scan (web-v2/tests 逐字范围): 0 matches（7e4b534 修复后）
git diff --check: clean
git status --short: clean
```

##### 未完成事项

无。本报告不自行宣布验收通过；最终通过由审核者判定。
