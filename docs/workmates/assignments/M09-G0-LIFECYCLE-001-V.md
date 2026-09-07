# M09-G0-LIFECYCLE-001-V — independent boundary verification

状态：dispatch_ready
Owner：`verification`，全新正式 verification session；只读主集成区与冻结的 backend worktree。
目标：独立判断 G0 lifecycle + baseline-interface boundary，绝不改变产品、测试或任务状态。

## Frozen acceptance surface

1. 检查 G0/baseline diff 仅涉及 `backend/mountain_server.py`、`backend/mountain_capability_api.py`、`tests/test_capabilities_api.py`、`csboard/application/capabilities.py` 和对应新回执；不得接受 activation/renderer/V1 改动。
2. 独立运行并记录 bounded `/api/v1/capabilities` lifecycle proof：HTTP 200、顶层 `items/providers`、infographic `supported=false`、无 residual。
3. 独立运行 `tests/test_capabilities_api.py tests/test_cli_capabilities.py`，要求全绿；运行完整三文件组合门禁并确认唯一失败仍是保留的 `test_bootstrap_ready_still_requires_real_smoke_evidence`，且实际 `EVIDENCE_MISSING`，没有其它 failure。
4. 检查 `toolchain_probe` constructor injection 存在、异常/无效输入 fail-closed，且不读取 activation/P6 evidence、不把 public support 置真。
5. `git diff --check`、回执、无 V1/V2/V3/activation/render/ffprobe/task creation/service restart evidence。

## Verdict

测试本身不得删除、skip 或改写。上述唯一保留 failure 是 V3 后 activation gate，不计为 G0 failure；任何其它失败、范围漂移、reason-code 修改或公开入口变化都是 FAIL/BLOCKED。PASS 只授权 PM 派发 V1，不自动开放 create-options。
