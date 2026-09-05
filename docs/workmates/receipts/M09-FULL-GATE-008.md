# M09-FULL-GATE-008 — Full Gate Closure Receipt

状态：READY_FOR_VERIFY

## 已完成的 P8 收口

- `tests/test_cli_engine_validation.py` 的信息图接受案例改为直接调用受控 `MountainCommands` internal-test seam（`internal_test_only=True` + `actor_type=internal-test`）；产品 CLI 没有新增 bypass flag，公开提交仍关闭。
- `tests/test_infographic_e2e.py` 的信息图 fake 创建同样改走 internal-test seam；whiteboard mock renderer output 改为当前 run 的受控 `artifacts/render`，生产路径边界未放宽。
- 恢复 `NODE_NOT_FOUND` 兼容常量，但不恢复 P3a Node/toolchain 探测；旧测试已改为验证新的 fail-closed 语义。
- `RemotionRendererAdapter._sanitize_error` 已恢复并接入 renderer 错误路径，继续脱敏路径与 credential 文本。

## 已验证

- `pytest -q tests/test_cli_engine_validation.py tests/test_infographic_e2e.py`：**30 passed**，exit 0。
- `git diff --check`：exit 0。

## 独立全量门禁结果

- 主控以 `timeout 180s /usr/bin/time -p .venv/bin/python -m pytest -q` 运行独立全量门禁：exit 0。
- 结果：**914 passed，5 warnings，3 subtests passed**；pytest 用时 176.63s，wall-clock `real` 177.86s（在 180s 门禁内）。
- 主控同时确认 `git diff --check` exit 0。
