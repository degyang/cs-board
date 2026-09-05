# M09-INFRA-ROUTING-004-V 独立验证回执

结论：**PASS**。按当前执行计划 P4/PLAN-004 的受控 internal-test 边界完成独立验证。未修改实现、测试、配置或规划；未执行真实 Remotion render、未创建真实任务、未改变 capability activation 或开放 submission。唯一写入为本回执。

## 专项执行证据

```text
.venv/bin/python -m pytest -q \
  tests/test_infographic_routing_p4.py \
  tests/test_task_engine_wiring.py \
  tests/test_infographic_task_creation.py \
  tests/test_infographic_capability.py \
  tests/test_capabilities_api.py \
  tests/test_cli_capabilities.py
57 passed, 1 warning in 4.98s
exit 0

.venv/bin/python -m pytest -q tests/test_create_options_infographic.py
3 passed, 1 warning in 2.85s
exit 0
```

两次 warning 均为 Starlette `BlockingPortal` deprecation；合计 **60 passed**。P4 dedicated test 的所有 renderer 都写入 pytest 临时目录中的 fake bytes，不调用 Node、Remotion、ffprobe 或真实渲染。

## PLAN-004 P4 核验

1. **PASS — public/API/CLI/create-options 保持拒绝。** `MountainCommands.create_task()` 仅当 `internal_test_only=True`、`actor_type="internal-test"` 且 bootstrap ready 时才允许信息图任务（`csboard/application/commands.py:114-158`）；HTTP `/api/v1/tasks` 没有这个参数、固定 Web context（`webapp/mountain_task_api.py:57-103`）；CLI 也未暴露该非 HTTP seam。`create_options()` 直接投影 capability 的 `supported`（`commands.py:240-273`），而 P3a public item 恒 false。专用 create-options 3 项与 P4 public-reject test 均通过。
2. **PASS — 受控 internal-test 接受与 engine 持久化。** P4 test 证明普通信息图 create 抛 `CAPABILITY_NOT_AVAILABLE`，只有 internal-test context + `internal_test_only` 可创建；repository 回读为 `Engine.INFOGRAPHIC_REMOTION`（`tests/test_infographic_routing_p4.py:45-55`）。
3. **PASS — 六阶段 fake E2E 同一 Task/Run/trace。** fake pipeline 使用创建时同一 `task_id/run_id` 贯穿六阶段，所有 stage 最终 SUCCEEDED，render manifest 在该 run artifact tree 内（`:94-115`）；命令响应与 run state 均保留同一 trace，未创建第二个 Task/Run。
4. **PASS — Remotion-only，无 generic/Whiteboard 回落。** 信息图 `_exec_render_visuals()` 仅使用注入的 `infographic_renderer_factory` 或 `RemotionRendererAdapter`（`commands.py:1795-1813`）；generic resolver 只在 whiteboard branch 使用。P4 spy 使 generic resolver 调用即失败，而信息图 fake render 正常完成（`test_infographic_routing_p4.py:58-81`）；既有 whiteboard regression suites同批通过。
5. **PASS — 同 run artifact index/hash/路径边界。** 输入 artifact 必须索引、状态成功、hash 匹配且 resolve 在当前 run `artifacts/` 内（`commands.py:1640-1650`）；信息图输入文件再核验 `task_id/run_id`，跨 run 稳定报 `ARTIFACT_RUN_MISMATCH`（`:1661-1669`，P4 test `:84-91`）。输出仅写 `<run>/artifacts/render`，再以 artifact store 提交 `render.video`、`render.manifest` 及 SHA-256 metadata（`:1671-1714`）；P4 fake test 验证 index keys、相对 manifest 路径与 artifact tree。
6. **PASS — 失败态可重试且不残留 SUCCESS。** render 异常或输出非法时 run 和 `render-visuals` 均写为 `FAILED` 后重新抛出（`commands.py:1684-1695`）；P4 test 在 fake renderer failure 后断言二者 FAILED（`tests/test_infographic_routing_p4.py:76-81`）。既有 retry state 支持由同批 task-engine suite 覆盖。
7. **PASS — 未越界。** P4 实现限于 commands 路由/受控 seam、artifact commit 与任务测试；未修改旧 `webapp/mountain_api.py`，未打开 WebUI/API/CLI submission，未运行 real render。

P4 已满足 PLAN-004 的内部测试路由和 fail-closed public boundary，可作为 P5 的前置 PASS。此 PASS 不授权 P5 以外的实现、真实渲染、P6 evidence、activation 或任何用户/API/WebUI submission。
