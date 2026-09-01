#### CCF-TASK-QUEUE-10 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation commit: `ba2fc19`
- git status: clean

##### 原型映射

原型位于 `webui-prototype-baseline/source/src/features/project-workbench/`（任务队列属项目工作台子视图）。本轮实现：
- 任务列表：真实 `GET /api/v1/tasks` + 服务端筛选/分页
- 状态 Tabs：全部/运行中/已完成/失败/已取消
- 搜索：标题或 Task ID（`q` 参数）
- 任务卡片：标题、状态、更新时间、当前阶段、操作按钮

原型中存在但 API 尚未提供的能力：
- 逐阶段进度条/百分比
- 成果缩略图预览
- 批量选择/操作
- 取消/暂停/重试控制
- 任务排序（客户端自定义）

以上均不伪造，记录为 API gap。

##### DTO 字段表

| 渲染位置 | DTO 字段 | 说明 |
|---|---|---|
| 卡片标题 | `task.title` | 为空时显示"任务 {shortId}" |
| 状态徽章 | `task.status` | 通过 `statusText()` 映射 |
| 更新时间 | `task.updated_at` | `formatTime()` 格式化 |
| Task ID | `task.task_id` | `shortId()` 缩短显示 |
| 当前阶段 | `active_run.current_stage` | `STAGE_NAMES` 映射，未知阶段保留原值 |
| 尚未运行 | `active_run` 为 null | 显示"尚未运行" |

##### 状态/阶段映射

```
task.status → statusText():
  running    → 运行中
  succeeded  → 已成功
  failed     → 失败
  cancelled  → 已取消
  未知       → 原样

active_run.current_stage → STAGE_NAMES:
  generate-visual-anchors → 文案整理与画面锚定重点
  clone-voice             → 克隆配音
  plan-storyboard         → 拆分分镜
  generate-illustrations  → 生成插画
  render-visuals          → 白板渲染
  compose-video           → 合成成片
  未知                    → 原样
```

##### 操作显示条件

| 操作 | 条件 |
|---|---|
| 进入工作台 | 始终显示 |
| 运行诊断 | `active_run` 存在且 `run_id` 非空 |
| 成片 | `active_run.final_available === true` 且 `run_id` 非空 |

URL 编码：`task_id` 和 `run_id` 均使用 `encodeURIComponent()`。

##### 请求时序

```
T0: renderAt → fetchTasks({limit:20}) → call #1 挂起
T1: unmount (mounted=false, requestId++)
T2: renderAt → fetchTasks({limit:20}) → call #2 挂起
T3: resolve #2 → DOM 显示 winner task
T4: resolve #1 → guard 阻止 setState → DOM 仍显示 winner
```

两个 Promise 均 resolve，两个 fetch 均断言 `toHaveBeenCalledTimes(2)`。

##### API gap

| 原型能力 | 当前 API | 状态 |
|---|---|---|
| 逐阶段进度/百分比 | 无字段 | gap |
| 成果缩略图 | 无字段 | gap |
| 批量操作 | 无 endpoint | gap |
| 取消/暂停/重试 | 无可靠 endpoint | gap |
| 排序参数 | 无 sort 参数 | gap |
| 阶段完成数量 | 无字段 | gap |

##### 门禁原始摘要

```
build: ✓ (tsc --noEmit && vite build)
contract checker tests:48/48
full tests:327/327
act warnings:0
Router warnings:0
unhandled rejection:0
fixture checker: ✓ (fixture mode)
rg forbidden patterns:0 matches
git diff --check: clean
```

##### 未完成事项

- 真实 CCB checker 未运行（blocked: waiting for CCB runtime）
- API gap 中的原型能力等待后续 CCB 切片
