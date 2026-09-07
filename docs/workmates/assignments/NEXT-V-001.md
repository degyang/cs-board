# NEXT-V-001 — 首轮独立验收准备与冻结目标复验

状态：blocked-input → ready when PM names frozen targets。Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。

## Goal

独立验证 NEXT-FE-001 和 NEXT-BE-001 的冻结提交/回执。测试者不修改产品实现，不自行接受任务；分别给出 PASS、FAIL 或 BLOCKED。

## Scope and entry

- 工作目录 `/mnt/d/Workstation/Projects/cs-board`。先读 `AGENTS.md`、`CLAUDE.md`、`docs/workmates/team-setup.md` 和本任务。
- 在 PM 提供冻结 commit/diff hash 前，仅可读任务、现有历史回执并准备复验矩阵，不得把历史截图或测试当作新证据。
- 前端目标：实际目标提交、1024/1440 完整页面、双栏位置、试听区终态、创建/编辑契约和专项/全量/build。
- 后端目标：实际目标提交、activation freshness、reason codes、artifact/receipt/tool/service binding、public submission fail-closed 和完整后端门禁。
- 可写新的 `docs/workmates/receipts/NEXT-FE-001-V.md`、`NEXT-BE-001-V.md` 及 `/tmp` 证据；不写实现、既有测试、共享看板或历史回执。
- 禁止真实图片/TTS调用、真实 Remotion render、用户数据写请求和 public submission。

## Stop condition

如果 worker 未冻结目标或服务缺失，记录具体依赖并等待 PM；目标就绪后独立复现关键反证和门禁，回执绑定 commit、命令、退出码、截图/哈希与结论。
