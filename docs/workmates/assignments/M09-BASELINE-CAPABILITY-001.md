# M09-BASELINE-CAPABILITY-001 — restore handed-off CapabilityService probe interface

状态：implementation_complete / pending_G0_verification
Owner：`backend`，必须使用 G0 `%65` 退役后新建的正式 backend session。
独立验证：`verification`；回执：backend worktree `docs/workmates/receipts/M09-BASELINE-CAPABILITY-001.md`。

## Goal

只恢复 handed-off `tests/test_infographic_capability.py` 与当前 `CapabilityService` 之间的 `toolchain_probe` keyword interface compatibility。不得删除、skip 或弱化这些测试；不得把主集成区完整 P3a/activation diff 搬入本票。

## Exact scope

仅可修改 `csboard/application/capabilities.py`、`tests/test_infographic_capability.py`（只在必要时增加兼容回归断言）及本回执。构造器须安全接收可注入的 `toolchain_probe`，并仅使该注入在现有 bootstrap snapshot path 上可控、fail-closed。不得读取 P6 evidence、调用 activation、改变 `supported=false` 公共策略、探测/启动 renderer、创建任务、修改 API lifecycle repair 或 V1/V2/V3 文件。

## Evidence / exit

先记录当前 constructor signature、失败 keyword 和目标 diff。运行 G0 的组合门禁：`tests/test_capabilities_api.py tests/test_infographic_capability.py tests/test_cli_capabilities.py`；记录 exit、pass/fail、耗时、无 residual 和 `git diff --check`。若 keyword 修复后仍有非接口语义失败，记录 BLOCKED，禁止扩展范围。只有组合门禁全绿时才写 `READY_FOR_INDEPENDENT_BASELINE_VERIFICATION`；这仍不等于 G0 PASS，也不授权 V1。

## Consumed result

The injected `toolchain_probe` compatibility repair reduced the gate from `10 passed, 32 failed` to `41 passed, 1 deferred activation-gate failure`. The remaining test expects `REAL_SMOKE_EVIDENCE_REQUIRED` but current baseline returns `EVIDENCE_MISSING`; this is activation/evidence policy, not constructor compatibility. PM has explicitly retained the test and deferred its acceptance to V3/activation. No activation change was made. The compatibility implementation is complete and awaits independent G0 verification; it does not authorize V1 itself.
