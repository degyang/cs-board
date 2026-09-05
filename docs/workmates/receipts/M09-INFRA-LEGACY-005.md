# M09-INFRA-LEGACY-005 — P5 Legacy Separation Receipt

状态：READY_FOR_VERIFY
范围：legacy/native 隔离与只读 legacy projection；未提交、未推送、未真实渲染。

## 实现

- `LegacyJobBridge` 现在仅以 `reference_mode=infographic`、`job_type=infographic` 或既有 `pipeline_id=infographic-remotion-v8` 识别 legacy infographic，并保持 `infographic-remotion-v8` 的只读 projection。
- MountainCommands 对任何非 `mountain-av-v1` Task 在 `start`、stage run/retry、pipeline run/resume 前稳定拒绝为 `LEGACY_READ_ONLY`。没有迁移 legacy Task/Run，也不会将其作为 native run 恢复。
- native `infographic-remotion` 路径仍在 Commands/Remotion adapter 内；AST 与子进程隔离测试确认它们不导入 `webapp.server`、`mountain_api`、`mountain_stages` 或 `LegacyJobBridge`。P4 的专用 Remotion factory 路径未访问 generic renderer。
- route inventory 明确 native `mountain_server` 使用 native task/capability routers；未改 `webapp/server.py` 或旧 `mountain_api.py`。旧 router 的 infographic projection 仍为 `supported=false`，不是 native capability authority。

## 验证

- 新增 `tests/test_infographic_legacy_p5.py`：三类 legacy marker/v8 read projection、stage/retry/run/resume reject fixtures、route inventory、AST import boundary，以及 clean subprocess module-isolation/no-fallback。
- `pytest -q tests/test_infographic_legacy_p5.py tests/test_legacy_bridge.py tests/test_legacy_isolation.py tests/test_infographic_routing_p4.py tests/test_capabilities_api.py tests/test_cli_capabilities.py` → **32 passed**，exit 0（1 个既有 Starlette deprecation warning）。
- `python scripts/legacy_dependency_guard.py` → PASS；`git diff --check` → exit 0。
- 未改 `webapp/server.py`，未开放 capability/create-options/submission，未执行真实 render。
