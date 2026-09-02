# WEB-INTAKE-003：新建任务到工作台的真实浏览器闭环

- Owner: WEB
- Status: DISPATCHED
- Priority: P0
- Depends on: `BASELINE-WEB-001=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`
- Branch: `feat/mountain-webui-surface-parity`
- Base commit: `7dc2a93`

## Goal

建立真实后端、真实浏览器的 `/tasks/new → / → /tasks/{task_id}` intake 验收自动化：用户完成六 Tab、
上传参考音频、保存后在工作台回读同一输入，并能从任务队列重新找到和打开同一 Task。本任务只验证
Pipeline 启动前的工作条件，不依赖 CORE Work Order 或新状态 DTO。

## Authoritative references

- `docs/Mountain/04-webui-redesign.md` 的新建任务、任务队列、任务工作台；
- `docs/Mountain/24-codex-six-stage-execution-contract.md` 第 2、8 节；
- 现有 `/api/v1/tasks`、`POST/GET /inputs` 和 Task Queue DTO，不增加字段。

## Allowed surfaces

- `web-v2/scripts/`：新增聚焦 intake 的 Playwright 行为/证据脚本及可测试 helper；
- `web-v2/tests/`、`web-v2/package.json`：自动化入口和行为测试；
- 只有浏览器证据证明现有行为错误时，才可最小修改 `CreateTaskPage.tsx`、`TasksPage.tsx`、
  `TaskWorkbenchPage.tsx`；报告必须写复现；
- `docs/Mountain/webui-parity-evidence/tasks/` 的 intake 截图/安全 manifest；
- `docs/agents/reports/WEB-INTAKE-003.md`。

## Forbidden surfaces

- Python、Schema、API client/types/DTO、设置和资产页面、全局视觉重构；
- 调用 start/pipeline/stage run/retry、Provider/TTS/图片/媒体服务；
- mock API 作为最终浏览器证据；用户真实文案、Secret、绝对路径进入证据；
- 修改 `WEB-WO-003` 所依赖的未冻结 Work Order UI。

## Acceptance

1. 使用临时 data dir 启动真实 Mountain API 与 Vite，测试结束后停止；
2. 自动完成六 Tab；测试参考音频由脚本生成最小合法非敏感 WAV 到 ignored runtime，不提交用户音频；
3. 断言 `POST /tasks` 与 `POST /inputs` 成功，只创建一个 task_id，且没有 `/start`、pipeline/stage 请求；
4. 保存后 URL 为同一 `/tasks/{task_id}`，GET inputs 回读 script hash/长度、分割规则、风格、锚点、字幕、
   pen/stroke 和 reference 元数据；不得在日志/截图保存完整文案或绝对音频路径；
5. 返回队列，按 title/task_id 搜索后只出现一次；打开后仍是同一 Task 与输入；
6. console error/warning、pageerror、failed request、HTTP >=400 均为 0；加载态必须进入语义终态；
7. 提交至少三张真实截图：创建完成、队列定位、工作台输入回读，并生成带 hash 的 manifest。

## Gates

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> node web-v2/scripts/check-api-contract.mjs
WEBUI_BASE=http://127.0.0.1:<web-port> \
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> \
node web-v2/scripts/verify-task-intake-e2e.mjs
git diff --check 7dc2a93...HEAD
! rg -n 'Project|project_id|/projects|mockResolvedValue' web-v2/scripts/verify-task-intake-e2e.mjs
```

自动化脚本必须在依赖缺失、服务未启动或 API 错误时非零退出，不得用固定 sleep 冒充完成。

## Stop condition

提交并推送当前分支，报告写入实际端口、命令、task_id 脱敏摘要、截图 manifest 和任何最小 UI 修复。
直接唤醒 `/root/pm` 后停止，不进入 Pipeline/Work Order 页面。
