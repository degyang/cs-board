# M09-INFRA-ROUTING-004 — P4 Routing Receipt

状态：READY_FOR_VERIFY
范围：P4 原生 `infographic-remotion` 的受控 internal/test 路由；未提交、未推送、未真实渲染。

## 实现

- `MountainCommands.create_task()` 对动态信息图默认 fail-closed。仅调用方显式传入 `internal_test_only=True` 且 `CommandContext.actor_type=internal-test`，并且 P3a snapshot 的 `bootstrap_ready=true` 时，才允许创建受控任务。HTTP API 与 CLI 都没有该参数，因此保持拒绝；`create-options` 没有被打开。
- P4 只消费 P3a 的 bootstrap 结果；没有把 Node、Remotion、browser、FFmpeg 或其他 toolchain probe 放回 P3a。
- engine 持久化到 Task，`_exec_render_visuals` 对该 engine 只选 `RemotionRendererAdapter`（或测试注入的同一专用 factory），不访问 generic `rendering` resolver/Whiteboard 路径。
- 三个 renderer 输入都必须在当前 Task/Run 的 artifact index 内、hash 有效、路径位于当前 run `artifacts` 根内，且文档 `task_id/run_id` 匹配；跨 run 输入返回 `ARTIFACT_RUN_MISMATCH`。
- 渲染输出只允许在当前 run `artifacts/render` 内。成功索引 `render.video` 和 `render.manifest`；manifest 包含 P1 所需的 run-relative output、hash、size、duration、frames 与 probe hash。renderer 失败或输出越界/无效会将 Run 与 `render-visuals` 置为 `FAILED`，可由既有 retry 路径重试，绝不留下 SUCCESS。

## 验证

- 新增 `tests/test_infographic_routing_p4.py`：公开拒绝/受控接受、engine persistence、Remotion-only spy、artifact index/manifest、failed-render FAILED、cross-run 输入拒绝，以及 fake 六阶段 E2E（同一 Task/Run/trace 和 artifact tree）。没有 Node 或真实 render。
- 专项：`pytest -q tests/test_infographic_routing_p4.py tests/test_task_engine_wiring.py tests/test_infographic_task_creation.py tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py` → **57 passed**, exit 0（1 个既有 Starlette deprecation warning）。
- `git diff --check` → exit 0。
- 未修改旧 `webapp/mountain_api.py`；其公开 dynamic infographic projection 仍是 `supported=false`。
