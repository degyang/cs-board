# M09-INFRA-BOOTSTRAP-003A-R-R5 — P3a alternate ASGI API contract evidence

状态：dispatch_pending
Owner：`worker_runtime_p3a`（`%54`）
模式：一次、只读、in-process API evidence；不使用 `TestClient`

## Authority and rationale

R-R4 已证明 direct `CapabilityService.snapshot()` 完成，阻塞位于共享 `TestClient.__enter__`/AnyIO portal，早于 health 请求。这不是 P3a 实现失败。为了取得 P3a API 合同证据，本票使用现有 `httpx.ASGITransport`，不创建 blocking portal、不重启 live service、不修复共享生命周期。

## Exact one-shot evidence

创建 `/tmp/m09-p3a-asgi-r5.py`，第一段验证并插入项目根到 `sys.path`（同 R-R4）。脚本只用新的 `TemporaryDirectory`，设置 `faulthandler.dump_traceback_later(10)`，并输出 marker：

1. `direct-capability-start/result`：对临时根的 `FilesystemServiceRegistry` + `PlaintextSecretStore` + `CapabilityService(...).snapshot()` 直接调用；记录 infographic item 的 `supported` 与 `bootstrap_ready`。
2. `asgi-capabilities-start/result`：对 `create_app(temp_root)` 使用 `httpx.ASGITransport(app=app, raise_app_exceptions=True)` 和 `httpx.AsyncClient(base_url='http://test')`，以 `asyncio.run()` 精确请求一次 `/api/v1/capabilities`；断言 HTTP 200、`items/providers` 顶层形状、infographic item 仍 `supported=false`，且响应文本没有 secret、`http://` 或 `https://`。

只运行一次，且不得使用 `TestClient`：

```bash
PYTHONPATH=/mnt/d/Workstation/Projects/cs-board timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-asgi-r5.py > /tmp/m09-p3a-asgi-r5.log 2>&1
```

回执 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R5.md` 记录 shell exit、所有 marker/status、direct 与 ASGI contract facts、任何 stack、无 residual Python/pytest 及未变 P3a scoped diff。若 ASGI 失败/超时，真实记录 BLOCKED/FAIL；不得将 TestClient lifecycle 问题计为 P3a 实现失败。

## Boundary

只可写两个 `/tmp` 文件与新回执。不得修改产品代码/测试/依赖/服务/配置/看板/旧回执；不重启服务、不重试、不启动后台进程、不执行 P4/P6/P3b/activation/render/task 创建。即使 PASS 也只交 PM 派发独立 P3a 验证，绝不自行接受 P3a/P4。
