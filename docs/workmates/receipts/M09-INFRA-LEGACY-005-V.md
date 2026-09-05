# M09-INFRA-LEGACY-005 独立验证回执

结论：**PASS**

验证范围严格限于 PLAN-004 P5 的 legacy 只读隔离；未修改产品实现，未执行真实渲染。

## 复跑结果（2 条命令，均 exit 0）

1. `.venv/bin/python -m pytest -q tests/test_infographic_legacy_p5.py tests/test_legacy_bridge.py tests/test_legacy_isolation.py tests/test_infographic_routing_p4.py tests/test_capabilities_api.py tests/test_cli_capabilities.py`
   - `32 passed, 1 warning`，exit 0。
2. `.venv/bin/python scripts/legacy_dependency_guard.py`，exit 0：`legacy dependency guard: PASS (no forbidden reachable imports)`。

另以 `python -B` 干净子进程仅导入 `MountainCommands` 和 `RemotionRendererAdapter`（不实例化或调用 render）复核：`webapp.server`、`webapp.mountain_api`、`webapp.mountain_stages`、`csboard.application.legacy_bridge`、`csboard.adapters.whiteboard.renderer_adapter` 均未载入。

## 核验明细

- 三种 legacy marker 均为只读投影：`reference_mode=infographic`、`job_type=infographic`、`pipeline_id=infographic-remotion-v8` 由 `LegacyJobBridge._is_infographic` 统一识别（`csboard/application/legacy_bridge.py:120`），并投影至 v8 pipeline（:82）。专项参数化测试逐一覆盖。
- `stage_run`、`stage_retry`、`pipeline_run`、`pipeline_resume` 均先调用 `_require_native_task`（`csboard/application/commands.py:1119, 1178, 1267, 1298`）；非 `mountain-av-v1` 稳定抛出 `LEGACY_READ_ONLY`（:1322-1325）。复跑中的三 marker × 四操作均已验证。
- native 路由唯一真源为 `webapp/mountain_server.py` 注册的 `mountain_task_api` 与 `mountain_capability_api`（:163-165）；其 AST 不导入旧 `webapp.mountain_api` 或 legacy bridge。旧静态路由保留为隔离的 fail-closed 兼容面，未成为 native capability authority。
- AST 检查确认 `commands.py` 和 Remotion adapter 不导入 legacy/webapp fallback；依赖守卫与上述干净子进程进一步确认不存在旧 WebUI、legacy bridge 或 Whiteboard renderer 的可达加载。
- capability/create-options/submission 未开放：create-options 中 infographic 项的 `available` 取 capability 的 `supported`（`commands.py:240-270`，当前 P3a public supported 仍为 false）；创建 infographic 还要求 `internal_test_only`、`internal-test` actor 与 bootstrap ready，任一不满足即 `CAPABILITY_NOT_AVAILABLE`（:152-158）。原生公共 API 未传递该 internal-only 参数（`webapp/mountain_task_api.py:82-101`）。
- 上述命令均为 pytest、AST/依赖守卫或导入探针；没有调用 renderer、Node/Remotion render 或任何 submission 执行路径。
