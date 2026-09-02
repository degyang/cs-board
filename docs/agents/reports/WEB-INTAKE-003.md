# WEB-INTAKE-003 阻塞报告

状态：`BLOCKED`

基线：`7dc2a93`，分支 `feat/mountain-webui-surface-parity`

## 已完成

- 新增 `web-v2/scripts/verify-task-intake-e2e.mjs`，覆盖六 Tab 填写、最小 WAV、Task/inputs 请求观测、输入回读、队列搜索、工作台回读、截图和脱敏 manifest。
- `npm --prefix web-v2 run build`：通过。
- `npm --prefix web-v2 test -- --run`：16 files / 347 tests passed。
- `MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs`：`All contracts aligned against real backend ✓`。
- 浏览器脚本依赖缺失、服务未启动和 HTTP 错误均会非零退出；未调用 start、pipeline、stage run/retry。

## 阻塞证据

使用隔离后端（8000）、同源 Vite `/api` 代理（5275）执行真实浏览器脚本时，工作台产生 `404 GET /api/v1/capabilities`。真实后端入口 [webapp/mountain_server.py](/mnt/d/workstation/projects/cs-board/.claude/worktrees/mountain-webui-surface-parity/webapp/mountain_server.py) 只挂载 `mountain_task_router`，其 [webapp/mountain_task_api.py](/mnt/d/workstation/projects/cs-board/.claude/worktrees/mountain-webui-surface-parity/webapp/mountain_task_api.py) 没有 capabilities 路由；旧 `mountain_v1_api.py` 的同名路由未被该启动器挂载。

浏览器原始结果：`404 GET /api/v1/capabilities`，页面 console 同步记录 `Failed to load resource: the server responded with a status of 404`。该结果违反任务门禁“HTTP >=400 为 0”。

契约禁止 Python、API client/types/DTO 变更；当前仅允许在浏览器证明确有问题时做最小 UI 修复。需要 PM 明确是否授权将 Workbench 的 capability 查询延后/改为可用入口。未获授权前不修改产品 UI，不提交伪造证据。

## 运行环境

- API：`127.0.0.1:8000`，临时 data dir；已停止。
- Web：`127.0.0.1:5275`，`VITE_API_BASE_URL=/api/v1`；已停止。
- 首次未注入 Vite 同源变量时另复现 CORS preflight 400；按既有证据流程修正后仍稳定复现 capability 404。
- 未生成可接受的 intake manifest；任何截图仅为失败运行中间产物，不应作为通过证据。

