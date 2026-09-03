# CCF-TASK-CREATE-INTEGRATION-20 检查点 A 回执

## §1 执行基线与变更文件

- 起点：`3edabb1`；执行前 `git status --short` 为空。
- 本轮范围：仅完成不依赖 CCB 审核的 Task 创建恢复安全检查点 A；未修改后端、工作台、资产/设置业务、已通过侧栏交互或原型基准。
- 实现提交：`7769c0f fix(mountain-web): secure Task creation recovery`。
- 变更文件：
  - `web-v2/src/pages/CreateTaskPage.tsx`
  - `web-v2/src/components/ui/Tabs.tsx`
  - `web-v2/tests/create-task.test.tsx`
  - 清理 `docs/Mountain/evidence/ccf-task-create-19/` 中 6 张重复 `*-desktop.png`，保留唯一权威桌面图与 3 张移动图。

## §2 检查点 A 完成清单

- 空白新建表单默认值对齐 `45 / 2 / rich`；服务端 `create-options` 成功后填充能力和默认值，已恢复字段优先，异步返回顺序不会覆盖恢复值。
- URL 的 `task_id/run_id` 只触发恢复读取，不再直接构造 `created`。只有 Task 存在、Task ID 一致、`active_run.task_id/run_id` 与 URL 一致时才建立已创建身份；缺失、404、读取失败或身份不匹配均 fail closed 且禁用最终提交。
- Task detail 恢复 `title/summary/engine`，inputs readback 恢复 script、视觉/风格、音色、分段长度、分镜数、线条密度、品牌文字及两个开关；重挂载测试证明状态重新从真实读取结果恢复。
- `reference_audio.uploaded=false` 且选择上传参考音频时必须重新选择文件；`uploaded=true` 可省略文件并保留后端已存状态。
- 提交前先写入/复用 `submission_id`；创建响应丢失后的再次提交复用同一 ID，成功后只进行 inputs 保存，不启动 run。
- 恢复 loading、Task/inputs 404 或服务错误均展示区分明确且不含敏感详情的安全状态，恢复未完成时最终提交保持禁用。
- Tabs 补齐 roving focus：Arrow/Home/End 选择并聚焦新 Tab；活动面板具备匹配的 `id`、`role=tabpanel`、`aria-labelledby`，无悬空 `aria-controls`。
- 网络异常统一为稳定用户提示；未挂载组件的迟到请求不导航、不更新状态、不产生 warning/unhandled rejection；未使用 localStorage/sessionStorage 或旧 Project/fixture 路径冒充正式联调。
- 本轮新增 13 项强制行为测试：共享默认值/异步顺序、StrictMode 单次创建与 loading、pending create 卸载、恢复后仅保存 inputs、reference true/false、伪造身份/404/loading fail-closed、安全错误、标题/摘要/资产边界以及真实取消路由；同时修正 StrictMode effect 重挂载时的 mounted guard 初始化。
- 检查点 A 测试整改已保留并通过；新增的真实联调兼容性最小修复为：白板视觉预设请求显式携带 `engine=whiteboard`，避免真实后端返回其他引擎的首条风格；`submission_id` 改用 Web Crypto 高熵字母数字标识，满足 CCB 的唯一性校验。
- 检查点 B 已使用真实 CCB 后端 `cb22f684d4eea0eee7efe70584c27eb751b2f3c6` 和临时 data dir 执行：真实创建两个 Task、真实保存两个 Task 的输入；第二个 Task 的恢复重试场景使用浏览器注入一次 503 传输故障，刷新后从真实 Task/inputs 恢复，再调用真实后端重试保存。全程未调用 start、Stage、Gate 或媒体编排。

## §3 自动化测试类别、数量和结果

| 类别 | 数量 | 结果 |
|---|---:|---|
| 全量前端 Vitest 文件 | 16 | PASS |
| 全量前端测试用例 | 388 | PASS |
| Task 创建专项行为测试 | 31 | PASS |
| 本轮新增强制行为测试 | 13 | PASS |
| 默认值与 options/recovery 异步顺序 | 2 | PASS |
| recovery 身份、404、loading、inputs-only、reference true/false | 4 | PASS |
| StrictMode、pending create 卸载、错误脱敏、字段/资产/取消边界 | 7 | PASS |
| contract checker 测试 | 48 | PASS |
| 重挂载恢复实际断言 | 1 | PASS |
| 实际工作台 active route 导航断言 | 1 | PASS |
| response-lost 同 `submission_id` 重试断言 | 1 | PASS |
| B 真实后端兼容单元断言（白板 style engine 过滤、高熵 submission_id） | 2 | PASS |
| warning/unhandled/unmounted 扫描 | 0 命中 | PASS |
| 真实 Chromium Task 创建/恢复/重试联调 | 1 场景；2 次创建、1 次故障、1 次恢复、1 次真实重试 | PASS（见 `evidence/ccf-task-create-20-b/real-browser-summary.json`） |
| 真实后端 contract checker | 26 项后端 Style `config` 缺失 | FAIL（后端现状，未修改后端） |

## §4 全部门禁与耗时

- `npm --prefix web-v2 run build`：PASS；TypeScript 检查通过，Vite build 用时 `1.96s`（命令 wall time 约 `5.50s`）。
- `npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-task-create-integration-20-test.log`：PASS，16 files / 388 tests，Vitest duration `15.05s`（命令 wall time 约 `16.30s`）。
- 测试日志扫描 act、Router Future Flag、Unhandled/unhandled rejection、unmounted state update：PASS，0 命中。
- `npm --prefix web-v2 run test:contract-checker`：PASS，48 tests，Vitest duration `4.45s`（命令 wall time 约 `5.50s`）。
- 正式路径禁止 Project/project_id/策略词扫描：PASS，0 命中。
- `localStorage/sessionStorage/Math.random/submission-.*Date.now` 扫描：PASS，0 命中。
- `git diff --check 43b29e1...HEAD`：PASS。
- 真实 CCB contract checker：FAIL，`Style list` 与 preset list 共报告 26 个 `items[*].config (required)` 缺失；该问题来自指定 CCB 后端响应，按范围未修改后端，完整输出保存在 `/tmp/ccf-task-create-20-real-checker.log`。
- 真实 Chromium：Chromium `134.0.6998.35`，viewport `1440×1000`、DPR `1`；请求摘要、任务计数、故障/恢复/禁止执行请求及 6 张截图均保存在 `evidence/ccf-task-create-20-b/real-browser-summary.json`。
- Task 数量证据：`0 → 1 → 2`（两次创建）；故障前 `2`、故障后 `2`、真实重试后 `2`，证明输入保存失败/恢复重试没有重复创建 Task。真实浏览器请求包含两次 `POST /tasks`、三次输入 POST（成功、503 注入、真实重试 200），没有禁止执行 POST。

## §5 clean status 和提交 hash

- 实现提交：`976af50e7753c1ce19dd6d898a9c649a6ca4ac33`，提交信息为 `fix(mountain-web): integrate Task creation backend`；包含两处最小前端修复、对应测试断言和真实 Chromium 证据。
- 实现提交前后均执行 `git status --short`；实现提交后工作区 clean；无 push。
- 报告提交信息：`docs(mountain): report Task creation integration`；报告提交后再次核验最终工作区 clean。前后端临时进程和临时 data dir 已在最终核验后清理。

## §6 检查点 B 依赖状态

检查点 B 已完成真实浏览器联调步骤，但真实后端 contract checker 暴露 26 个 Style `config` 必填字段缺失，因此本回执只记录证据，不将检查点 B 标为审核通过。联调没有使用 fixture server、旧后端或正式用户数据；浏览器故障为一次明确的 503 传输注入，恢复后的重试请求实际到达指定 CCB 后端并返回 200。未执行队列创建、自动派工、run 启动、Stage、Gate、媒体编排或 `USER_ACCEPTANCE`。

## §7 未完成项

1. 指定 CCB 后端的真实 contract checker 仍失败：全量风格列表与 preset 风格列表共 26 项缺少必填 `config`；需由 CCB 后端整改并重新审核。
2. 本轮未宣布检查点 B、整体审核或 `USER_ACCEPTANCE` 通过；最终审核结论仍由审核者决定。
