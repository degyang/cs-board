# M09-G0-LIFECYCLE-001 — shared capability API lifecycle repair and proof

状态：implementation_partial / BLOCKED_INTERFACE_BASELINE
Owner：`backend`，工作树：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`
独立验证：`verification`；本次 fresh-session 回执：backend worktree `docs/workmates/receipts/M09-G0-LIFECYCLE-001-R.md`。

## Goal

在有界测试中复现并修复（或证实为 harness-only 的）`/api/v1/capabilities` API lifecycle 阻塞。成功只证明 G0；不产生 Remotion MP4、不创建 Task、不解锁公开提交。

## Current block

主集成区和 backend worktree 的 HEAD 都是 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`，但该提交只跟踪 `webapp/mountain_*`。本票指定的 `backend/mountain_*` 是主集成区未提交迁移，故 backend worktree 初始缺少目标文件；当前 worker 还继承了已完成 P2 的客户端会话。基线 handoff 已完成，详见 `docs/workmates/receipts/M09-G0-BASELINE-HANDOFF.md`；不得复用旧 session，必须通过 target-hash preflight 后全新正式 launch 再派发。

旧 `%59` 的 `docs/workmates/receipts/M09-G0-LIFECYCLE-001.md` 是不可覆盖的 `BASELINE_MISMATCH` 历史证据。fresh `%65` session 必须先在 `M09-G0-LIFECYCLE-001-R.md` 记录：新 pane ID、assignment hash、handoff snapshot hash、五个 target hashes 与“旧 block 已由 handoff 解除”，然后才可进行 G0 的任何读/改/测试。

## Scope and evidence

只允许修改 `backend/mountain_server.py`、`backend/mountain_capability_api.py`、`tests/test_capabilities_api.py`，及必要的项目本地 test harness/config。先记录目标 diff；建立一个单请求、明确短 timeout 的 API test，验证 HTTP 200、顶层 `items/providers`、infographic `supported=false`。以证据为准选择最小 product/harness 修复。

回执必须记录：修复前/后阻塞或完成证据；bounded test 命令、exit、耗时、HTTP/shape assertions；`test_capabilities_api.py`、`test_infographic_capability.py` 与相关 capability/CLI read-model tests 的实际结果；`git diff --check`、范围和无 residual。不得记录 secret、绝对路径或完整环境。

## Stop and done

不得运行 Remotion render、ffprobe、provider/image generation、任务创建、服务重启或公开 API/WebUI/CLI 提交；不得改 Task/Run/artifact schemas、renderer/domain、legacy 或 activation policy；不得 commit/push。无法在范围内建立有界复现时，写 BLOCKED 回执并停止。

新的 lifecycle evidence 必须在边界内结束、无 residual，且 API/CLI 与注入式 toolchain interface 边界通过；实现者只可写 `READY_FOR_INDEPENDENT_G0_VERIFICATION`。`test_bootstrap_ready_still_requires_real_smoke_evidence` 的 `REAL_SMOKE_EVIDENCE_REQUIRED` assertion 是保留的 V3 后 activation gate，不是 G0 绿灯、不得 delete/skip 或修改 product reason code 来取绿。verification PASS 后才可派 V1，公开入口仍关闭。

## Consumed result

Fresh G0 repaired the lifecycle and produced HTTP 200 plus API/CLI `10/10` PASS. `M09-BASELINE-CAPABILITY-001` then repaired the handed-off `toolchain_probe` keyword interface, reducing the combined gate to `41 passed, 1 deferred activation-gate failure`; the remaining `REAL_SMOKE_EVIDENCE_REQUIRED` vs `EVIDENCE_MISSING` assertion is preserved activation/evidence policy outside both tickets. PM has removed it from G0 acceptance without deleting/skipping it. G0 is **not yet PASS**: independent G0 verification is now required; V1 remains blocked.
