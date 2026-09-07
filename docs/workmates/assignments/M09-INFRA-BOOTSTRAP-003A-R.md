# M09-INFRA-BOOTSTRAP-003A-R — P3a Bootstrap readiness

状态：dispatch_pending
Owner：`worker_runtime_p3a`（看板指定的可见 runtime owner；不得由 P2/backend owner 代写）
工作目录：`/mnt/d/Workstation/Projects/cs-board`（当前集成区；先记录既有脏 diff，仅写本票范围）

## Authority and dependency

- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` P3a
- `docs/workmates/receipts/M09-INFRA-PLAN-002-R-V.md` PASS
- `docs/workmates/receipts/M09-INFRA-CONTRACT-001-R-V.md` PASS

P1 已独立接受，P3a 可与 P2 并行。本票采用已接受 PLAN-002-R 的 P3a 单一诊断合同：P3a 是 bootstrap/toolchain 的唯一只读、fail-closed 诊断 owner；P2 不得替代、复制或覆盖本票的 capability/readiness 输出。

## Scope

只写 `csboard/application/capabilities.py`、必要的 `csboard/runtime/toolchain.py`、service probe read model、直接 capability/toolchain/API/CLI read-model tests，以及新回执 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R.md`。不修改 P2 adapter/domain/props/commands/task create/renderer/legacy/webapp/前端或任何 P6/P3b 文件；不覆盖既有脏 diff。

实现只读 fail-closed 的 bootstrap/toolchain 诊断，检查 Node、render script、锁定依赖、Remotion/browser、FFmpeg/ffprobe、service secret presence/probe 与 external-stage gate。输出仅可包含 `bootstrap_ready`、各项安全诊断、稳定首因 reason code 和 UTC 检查时间；不得泄露本机绝对路径或 secret。任一 probe 异常/缺项均为 false。即使 ready，公开 activation projection 仍必须 `supported=false`/unavailable，且不得读取 P6 evidence 或使用 mock/node_modules 宣称公开可用。

## Required tests and exit

覆盖每项单缺失、稳定多缺项优先级、probe exception、external gate false、bootstrap ready但unsupported、白板回归，以及 CLI/API 同源 read model。不得执行 adapter/真实 render、创建任务、activation、WebUI/API/CLI submission、commit 或 push。

运行 focused + affected suite，回执记录实际命令、退出码、pass/fail/skip、范围 diff、reason matrix 与安全确认。完成时仅写 `READY_FOR_INDEPENDENT_P3A_VERIFICATION` 并停止；P4 必须等待 P2 与 P3a 各自独立 PASS。
