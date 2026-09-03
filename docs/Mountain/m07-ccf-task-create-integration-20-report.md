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
| warning/unhandled/unmounted 扫描 | 0 命中 | PASS |

## §4 全部门禁与耗时

- `npm --prefix web-v2 run build`：PASS；TypeScript 检查通过，Vite build 用时约 `2.04s`。
- `npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-task-create-integration-20-test.log`：PASS，16 files / 388 tests，用时 `17.24s`（命令 wall time 约 `18.08s`）。
- 测试日志扫描 act、Router Future Flag、Unhandled/unhandled rejection、unmounted state update：PASS，0 命中。
- `npm --prefix web-v2 run test:contract-checker`：PASS，48 tests，用时 `10.11s`（命令 wall time 约 `10.94s`）。
- 正式路径禁止 Project/project_id/策略词扫描：PASS，0 命中。
- `localStorage/sessionStorage/Math.random/submission-.*Date.now` 扫描：PASS，0 命中。
- `git diff --check 04a5087...HEAD`：PASS。
- 本轮未重做已有效的 Chromium 截图；新恢复/导航行为由实际组件自动化断言证明，未以 fixture 或旧后端冒充检查点 B。
- 本轮未重做视觉截图；Chromium 既有证据继续沿用，未新增浏览器证据文件。

## §5 clean status 和提交 hash

- 实现提交：`1afb033de0b51843945dafe767fa0640b8f9d054`，提交信息为 `test(mountain-web): close Task creation checkpoint A`。
- 实现提交前后均执行 `git status --short`；实现提交后工作区 clean；无 push。
- 报告提交信息：`docs(mountain): report Task creation integration`；报告提交后再次核验最终工作区 clean。

## §6 检查点 B 依赖状态

检查点 B 仍阻塞，等待 CCB 后端整改审核通过。本轮没有调用旧后端、fixture 或伪造响应进行真实联调，也没有报告队列创建、自动派工、run 启动或 USER_ACCEPTANCE 通过。

## §7 未完成项

1. 检查点 B 的 CCB 后端真实联调尚未执行，必须等待 CCB 审核通过后再验证正式 Task 创建、inputs 回写及服务端幂等返回。
2. 本轮未执行检查点 B，也未宣布整体审核或 `USER_ACCEPTANCE` 通过；该项仍由审核者决定。
