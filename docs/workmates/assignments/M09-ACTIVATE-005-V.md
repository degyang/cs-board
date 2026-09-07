# M09-ACTIVATE-005-V — native activation integration verification

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`）；只读验证当前主集成区与现有 8000/5182。

## 冻结目标

- 实现任务：`docs/workmates/assignments/M09-ACTIVATE-005.md`
- 实现回执：`docs/workmates/receipts/M09-ACTIVATE-005.md`
- 当前实现哈希：capability API `ea77eb4f…268b`；server `953d2ae7…544c`；test `0ffa866a…4796`。
- 当前 pointer：`docs/workmates/receipts/M09-ACTIVATE-001.pointer.json`，SHA-256 `c7fe49881f25d6904506a7bea9003103d6bb0c5fe89726ac2f1e094db8d987be`。
- 当前服务：8000 PID `208119`，5182 PID `124360`；只读观察，不重启。
- 回执：`docs/workmates/receipts/M09-ACTIVATE-005-V.md`
- 新证据：`.workmates-evidence/M09-ACTIVATE-005-V.json`

## 必须验证

1. 重算上述三项实现哈希和 pointer 哈希；检查 native `backend.mountain_server` 将同一 resolved project root 传给 capability router、`CapabilityService` 和 `accepted_v3_gate`，旧 webapp 不是运行入口。
2. 重跑 `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_m09_activate_005.py tests/test_capabilities_api.py tests/test_infographic_activation_projection.py tests/test_infographic_activation.py -k 'not browser_version_uses_renderer_resolver'`；记录 deselect 原因，不得扩大 skip。
3. 只读请求真实 8000 `/api/v1/capabilities`：`infographic-remotion + preset` 必须 `supported=true`、reason null、bootstrap ready，且全部 activation diagnostics ready。
4. 只读请求 8000 与 5182 `/api/v1/tasks/create-options`：该 engine 必须同时 `available=true`，证明 WebUI 消费同一投影。若浏览器工具可用，再核对 5182 新建任务页的信息图卡片可选择且不显示“暂未开放”；不得提交或创建任务。
5. 核对当前 provider/service 列表仍为 10 项，用户 MiMo 服务与 8 个去重预置音色未回退；不得输出 secret 或完整配置。
6. `git diff --check` 与 `./scripts/workmates verify --role verification --evidence .workmates-evidence/M09-ACTIVATE-005-V.json` PASS；末次复算冻结哈希。

## 边界与出口

- 不修改实现、既有测试、pointer、服务设置、Secrets、用户数据、frozen outputs、前端或看板；仅写指定新证据和验证回执。
- 不创建 task/run/render，不调用生成 provider，不把 HTTP/测试 PASS 说成最终视频视觉验收。
- 输出 `PASS / FAIL / BLOCKED`，列命令、exit、数量、真实 API/UI 观察、前后哈希与未验证范围，然后停止等待 PM 消费。
