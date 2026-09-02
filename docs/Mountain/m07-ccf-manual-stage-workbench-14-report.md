# CCF-MANUAL-STAGE-WORKBENCH-14 完成回执

#### 执行摘要

- instruction: `CCF-MANUAL-STAGE-WORKBENCH-14`
- worktree: `/mnt/d/workstation/projects/cs-board-worktrees-backup-20260902/mountain-assets-settings-web`（Git 注册工作树；对应用户指定的 `mountain-assets-settings-web` 工作树）
- branch: `feat/mountain-assets-settings-web`
- starting HEAD: `c221947 docs(mountain): report execution plan web evidence`
- implementation commit: `1a4f75d feat(mountain-web): establish manual stage workbench`
- receipt commit: `docs(mountain): report manual stage workbench baseline` (this receipt commit)
- push: 未推送
- backend/assets/settings: 未修改

#### 修改文件

- `web-v2/src/pages/TaskWorkbenchPage.tsx`：收口为六阶段信息展示与 Gate 不可用态；保留真实输入保存、任务读取、取消、日志和产物展示。
- `web-v2/src/lib/api/types.ts`：保留旧保存计划 DTO 的宽容读取类型，不再让计划字段进入正式 UI 或保存请求。
- `web-v2/tests/execution-plan.test.tsx`：重写为六阶段手工工作台行为测试。
- `web-v2/tests/contract.test.tsx`：更新工作台行为断言，证明自动启动、流水线重试和阶段变更入口均不再暴露。
- `web-v2/src/features/.gitkeep`：保留台账静态扫描目标目录为空。

#### 六阶段 typed metadata

| canonical ID | 用户名称 | 入口条件 | 持久化输入 | 预期输出 | 出口条件 | 操作 |
|---|---|---|---|---|---|---|
| `generate-visual-anchors` | 文案整理与画面锚定重点 | 已保存视频文案 | 文案、风格 | 画面锚点数据 | 画面锚定可供分镜使用 | 人工检查后等待 Gate |
| `clone-voice` | 克隆配音 | 文案已分段且参考音频已保存 | 文案、参考音频 | 配音单元与音频 | 配音单元与时长可用 | 人工确认后等待 Gate |
| `plan-storyboard` | 拆分分镜 | 画面锚点与配音单元可用 | 画面锚点、配音单元 | 分镜计划 | 每个单元都有分镜计划 | 人工检查后等待 Gate |
| `generate-illustrations` | 生成插画 | 分镜计划已完成 | 分镜计划、风格 | Codex 生成的插画候选 | 人工选择候选插画并确认 | 生成候选 → 人工选择 → 等待 Gate |
| `render-visuals` | 白板渲染 | 已选插画且分镜通过 Gate | 分镜计划、已选插画 | 视觉序列 | 视觉序列渲染完成 | 人工检查后等待 Gate |
| `compose-video` | 合成成片 | 视觉序列与配音均通过 Gate | 视觉序列、音频 | 最终视频 | 成片可下载并通过最终检查 | 人工验收后等待 Gate |

#### 正式入口收口

- 删除制作输入中的自动/选择性计划编辑、保存字段和计划回显。
- 删除工作台的整条流水线启动和流水线重试；页面不会调用 `startRun`、阶段自动推进或流水线 resume。
- Gate API 尚未提供时不渲染执行、批准、拒绝、重做或阶段重试按钮，避免越过未批准上游。取消运行仍使用既有真实取消 API。
- `generate-visual-anchors` 用户名称为“文案整理与画面锚定重点”，没有“文案分割”。
- 插画阶段明确要求 Codex image generation 候选与人工选择，不展示假缩略图、占位图或伪进度。

#### 状态与安全矩阵

| 场景/状态 | 行为 |
|---|---|
| `waiting-external` | 作为一级状态原样展示；不自动轮询推进或创建结果 |
| `pending` / `running` / `succeeded` / `failed` / `skipped` / `stale` / `cancelled` | `StatusBadge` 安全展示；attempt 来自后端阶段数据，缺失时为 0 |
| 未知状态 | 保留原始状态文本，不触发前端动作 |
| 无 active Run | 仍渲染六张契约卡并显示“任务尚未启动运行”，不补造 Run/Stage |
| Run 无 Stage | 六阶段使用 `pending` 展示，后端阶段集合不被改写 |
| 未知 Stage | 单独显示“未知阶段”和后端返回 ID，不参与六阶段操作 |
| 无 Artifact | 显示真实空态，不生成缩略图或假产物 |
| 后端请求失败 | 页面真实错误卡/安全空态；不吞异常、不写浏览器存储 |
| 轮询旧响应/卸载 | 继续使用 `useAsync` 的 alive guard，卸载后不 setState、不更新计时器 |

#### CCB Gate API gap

| method | path | request | response | error code | 刷新语义 |
|---|---|---|---|---|---|
| `GET` | 待 CCB 提供：run stage Gate 状态 | `task_id`、`run_id`、canonical `stage` | `gate_status`、`approved_by`、`approved_at`、`revision` | 待定义（包括未找到、权限、revision 冲突） | 页面轮询/任务详情刷新时读取 |
| `POST` | 待 CCB 提供：stage Gate approve | `{task_id, run_id, stage, revision, note?}` | 新 Gate 状态、revision、request_id | 待定义（重复批准、前置未批准、revision 冲突） | 成功后刷新该 stage 与后继入口 |
| `POST` | 待 CCB 提供：stage Gate reject | `{task_id, run_id, stage, revision, reason}` | 新 Gate 状态、revision、request_id | 待定义（参数、权限、revision 冲突） | 成功后刷新该 stage |
| `POST` | 待 CCB 提供：stage Gate redo | `{task_id, run_id, stage, revision, reason}` | 新 Stage/Gate 状态、attempt、revision | 待定义（前置、状态、revision 冲突） | 成功后刷新 stage、artifacts、events |

在上述契约冻结前，页面统一展示“后端 Gate 契约尚未提供”，不伪造 Gate 数据或本地保存决策。

#### 门禁原始摘要

```text
$ npm --prefix web-v2 run build
✓ tsc --noEmit && vite build
✓ 68 modules transformed
✓ built in 0.90s

$ npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-manual-stage-workbench-14-test.log
Test Files  15 passed (15)
Tests       347 passed (347)

$ ! rg -n "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection" /tmp/ccf-manual-stage-workbench-14-test.log
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

#### 残留风险与距离 USER_ACCEPTANCE 的差距

- CCB 尚未冻结 Gate API，因此本轮只能交付真实 Gate 不可用态；人工批准、拒绝、重做和逐阶段运行需待 CCB 契约后续切片。
- 阶段产物的具体视觉内容、真实文案、参考音频和风格偏好仍由用户在最终验收提供，本轮没有冒充真实制作成果。
- USER_ACCEPTANCE 所要求的端到端媒体生成和人工 Gate 闭环尚未宣称完成；本回执仅覆盖 §3R 的前端展示基线和门禁证据。
