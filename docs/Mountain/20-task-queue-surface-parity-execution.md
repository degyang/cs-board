# Task Queue 表面对齐执行指令

状态：CCF 下一批执行基线。

分支：继续使用 `feat/mountain-webui-surface-parity`。

前置结论：设置与资产主体视觉通过；以下三项证据收尾完成后，进入 Task Queue，不再改动设置/资产业务结构。

## 1. 三项收尾（必须与 Task Queue 同一提交批次完成）

1. `app-shell.test.tsx` 的 `MemoryRouter` 增加 React Router future flags，使全量 Vitest stderr 中两条 future warning 归零。
2. `webui-parity-evidence/README.md` 将前端基线从旧 `d579358` 修正为实际实现 commit `3757cb6`，后端基线保持真实值。
3. 截图脚本增加 `settings/models-secret.png`：固定 `openai-compatible-text`，滚动到“Secret 管理”区域后截图；只允许 masked 状态和空 password 输入，不得写入或截取真实 API Key。

完成三项后，不需要单独等待审核，直接执行以下 Task Queue 范围。

## 2. 页面范围

只修改生产任务队列页面及必要的共享表面组件：

```text
路由：/
生产：web-v2/src/pages/TasksPage.tsx
原型：prototypes/webui/src/pages/ProjectsPage.tsx
共享：AppShell / Sidebar / 通用 Tabs、StatusBadge、空状态
```

原型中的“项目”全部翻译成“任务”；不得恢复 Project DTO、`/projects` 路由或旧 API。

本批次禁止进入：新建任务、任务工作台、运行诊断和后端实现。

## 3. 表面对齐要求

- 页面标题为“任务队列”，副标题说明这里用于查看制作任务、当前工序、状态和最终成果。
- 对齐原型的完整侧栏、内容宽度、页头、状态 Tabs、搜索、筛选、列表/卡片、分页和空状态。
- 每个 Task 项只展示真实 API 字段：标题、task_id、更新时间、状态、当前 Stage、重试能力和成片可用状态。
- running、failed、succeeded、pending/cancelled 使用统一 StatusBadge，不自行创造状态。
- 主操作层级：打开任务为主操作；可重试失败任务、继续运行等动作只有真实 API 支持时才显示。
- 不显示物理路径、Secret、原始日志、虚构进度百分比或伪造缩略图。
- loading、empty、error、filtered-empty、running、failed、completed 状态必须有清晰且与原型一致的表面。
- 筛选、搜索和 cursor 分页继续调用真实 `/api/v1/tasks`；不得在前端对当前页数据伪造全局排序或总数。

## 4. 测试和证据

补充或更新组件测试，至少覆盖：

- 默认完整侧栏；
- 状态 Tab 与 API status 参数；
- 搜索 q 参数；
- running/failed/succeeded 显示；
- final_available、retryable 和 current_stage；
- cursor 下一页去重；
- loading、empty、error、filtered-empty；
- 旧 Project 术语和 `/projects` URL 为 0。

使用独立验收数据目录和真实后端生成 1440×900 截图：

```text
docs/Mountain/webui-parity-evidence/tasks/queue-mixed.png
docs/Mountain/webui-parity-evidence/tasks/queue-filtered.png
docs/Mountain/webui-parity-evidence/tasks/queue-empty.png
```

截图脚本必须通过公开 Task API 准备或读取状态，不得写磁盘伪造 Task JSON。若现有 API 无法安全准备 mixed 状态，在证据 README 如实记录，只截取真实可构造状态并登记契约缺口。

## 5. 门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test
MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
git diff --check
rg -n "Project|project_id|/projects" web-v2/src
```

最后一个 `rg` 必须为 0。全量 Vitest stderr、Playwright console/page/request/API errors 和浏览器 warning 必须为 0。

## 6. 交付

完成后在本文追加报告，包含：

- commit；
- 修改文件；
- 三项前置收尾证据；
- Task Queue 状态覆盖；
- 三张截图及 SHA-256；
- 真实 API 请求摘要；
- 全部门禁原始结果；
- 契约缺口和未完成项。

提交并推送原分支，不要自行合入 `integration/mountain-v2`。
