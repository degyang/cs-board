# M09-ACTIVATE-002-V — independent probe-timeout verification

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`，只读检查当前集成区）；PM 负责消费结论。

不得修改产品实现、测试、服务定义、Secrets、pointer、outputs 或看板；只可写全新 `/tmp` 证据和 `docs/workmates/receipts/M09-ACTIVATE-002-V.md`。

## 目标与冻结值

- 原任务：`docs/workmates/assignments/M09-ACTIVATE-002.md`；worker 回执：`docs/workmates/receipts/M09-ACTIVATE-002.md`。
- `csboard/adapters/filesystem/service_registry.py` SHA-256 `0ed986c938e53fef78d4cf43491bd32de9c982c2897043c8989f5c7e221739b2`。
- `tests/test_service_registry.py` SHA-256 `5f662827d220fa1cf0280403fb8e5eee10a8e9b84085112d7355fe5265ef54a8`。
- 集成后 PM 已观察：50 focused tests PASS；8000 现由 tmux pane `%15` / PID `132790` 托管。修正后 MiMo-TTS 与 MiMo-TTS-Codeplan 真实 probe 均 available，不再是 `OPENAI_PROBE_ERROR`；local-indextts 明确为 `TTS_UNREACHABLE`。

## 验证

1. 复核 diff 只包含四类有界 timeout 和无网络回归，不掩盖错误。
2. 重跑 `tests/test_service_registry.py tests/test_mountain_service_api.py tests/test_capabilities_api.py`，运行 scoped `git diff --check`。
3. 只读复核 8000 health/services/capabilities，只记安全状态；不再 POST probe。
4. 运行全新 `./scripts/workmates verify --role verification --evidence /tmp/m09-activate-002-v-evidence-<timestamp>.json`。
5. 回执给出 `PASS / FAIL / MISSING EVIDENCE / BLOCKED`，明确 timeout 修正是否可接受，并分开记录 activation 仍被文本/图片 secret 阻断的事实。
