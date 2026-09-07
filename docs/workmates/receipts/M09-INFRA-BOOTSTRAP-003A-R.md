# M09-INFRA-BOOTSTRAP-003A-R — P3a Bootstrap readiness receipt

状态：**READY_FOR_INDEPENDENT_P3A_VERIFICATION**

范围仅限 `csboard/application/capabilities.py`、`csboard/runtime/toolchain.py`、直接 capability/toolchain 测试和本回执。未修改 P2 adapter/domain/props/commands、P3b、P4、P6、legacy 或前端；未执行 render、adapter、任务创建、activation、提交、commit 或 push。

## 实现事实

- P3a 以固定顺序做只读、fail-closed 检查：Node、render script、有效 lockfile、锁定 Remotion、`render.mjs` 实际采用的 browser 候选、FFmpeg、ffprobe、五类 stage service 的 secret presence/cache probe、external-stage gate。
- 每项 diagnostics 只含 `component`、`ready`、`reason_code`；不输出路径、命令、环境值、异常文本或 secret。任一 probe 异常都归约为安全的 false。
- `bootstrap_reason_code` 始终是固定顺序中首个失败项；多缺项仍保留完整 diagnostics。`bootstrap_checked_at` 是 UTC ISO-8601。
- 本票没有导入或读取 P3b/P6 activation evidence。即使 `bootstrap_ready=true`，公开 `infographic-remotion` projection 仍固定 `supported=false`，reason 为 `REAL_SMOKE_EVIDENCE_REQUIRED`。
- whiteboard projection 未依赖 P3a bootstrap。

## Reason matrix

| 检查 | 首因 code |
| --- | --- |
| Node | `NODE_NOT_FOUND` |
| Render script | `RENDER_SCRIPT_MISSING` |
| Lockfile | `LOCKFILE_INVALID` |
| Locked Remotion | `REMOTION_NOT_INSTALLED` |
| Browser | `BROWSER_UNAVAILABLE` |
| FFmpeg | `FFMPEG_NOT_FOUND` |
| ffprobe | `FFPROBE_NOT_FOUND` |
| Service secret | `SERVICE_SECRET_MISSING` |
| Service cached probe | `SERVICE_PROBE_FAILED` |
| External stage gate | `EXTERNAL_STAGE_BLOCKED` |

## Checks

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_infographic_capability.py tests/test_toolchain_resolver.py` | 0 | 38 passed; every toolchain single-missing check, service/secret/probe, external gate, exception, multi-missing priority, UTC and ready-but-unsupported covered. |
| `.venv/bin/python -m pytest -q tests/test_cli_capabilities.py` | 0 | 4 passed; CLI consumes the shared capability read model. |
| `.venv/bin/python -m pytest -q tests/test_capabilities_api.py -x` | not completed | Current constrained execution ended at the 30-second command boundary before this suite emitted a result. It is not claimed as passed and remains for the independent verifier. |
| `git diff --check` | 0 | Passed. |

## Scope diff

Modified P3a files:

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`
- `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R.md`

The integration worktree was already dirty before this ticket; unrelated changes were preserved. No P2/P3b/P4/P6 files were touched by this ticket.

**READY_FOR_INDEPENDENT_P3A_VERIFICATION**
