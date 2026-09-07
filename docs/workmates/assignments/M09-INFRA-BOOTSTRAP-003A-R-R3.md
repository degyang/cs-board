# M09-INFRA-BOOTSTRAP-003A-R-R3 — P3a vs TestClient root-cause discriminator

状态：dispatch_pending
Owner：`worker_runtime_p3a`（`%54`）
模式：一次、只读诊断；不修改产品文件

## Question

R-R2 已将卡点缩小到首个 `TestClient.get()`/AnyIO blocking portal。现在只区分：

1. P3a `CapabilityService` 的直接、无 HTTP 调用是否自行卡住；
2. 共享 `create_app` + `TestClient` 的 health 请求是否已经卡住；
3. 若 health 完成，capabilities 请求是否才是首个卡点。

## One bounded reproduction

只在 `/tmp/m09-p3a-rootcause-r3.py` 写入临时脚本，并运行一次（20 秒低于通道 30 秒限制）：

```bash
timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-rootcause-r3.py > /tmp/m09-p3a-rootcause-r3.log 2>&1
```

该临时脚本必须使用单个新的 `tempfile.TemporaryDirectory()`，按序 `print(..., flush=True)` 以下 marker：`direct-capability-start/result`、`testclient-health-start/result`、`testclient-capabilities-start/result`。它先通过 `FilesystemServiceRegistry`、`PlaintextSecretStore`、`CapabilityService` 对该临时根直接调用 `snapshot()`；再以 `TestClient(create_app(temp_root))` 请求 `/api/v1/health`，仅当 health 完成才请求 `/api/v1/capabilities`。脚本在 10 秒时调用 `faulthandler.dump_traceback_later(10)`。

回执必须记录 shell exit、最后一个 marker、response status（若有）、faulthandler stack（若触发）及精确归因：`direct P3a`、`shared TestClient/app lifecycle` 或 `capabilities HTTP composition`。同时检查无 residual Python/pytest，且 P3a scope diff 未变。

## Boundary

只允许写两个 `/tmp` 诊断文件和 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R3.md`。不得编辑任何产品代码/测试/依赖/配置/服务/看板/先前回执；不重启服务，不执行 P4/P6/P3b/activation/render/task 创建，不重试。无论结论都不得接受 P3a/P4；停止等待 PM。
