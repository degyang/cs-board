# M09-INFRA-BOOTSTRAP-003A-R-R5 — P3a alternate ASGI API contract evidence

状态：**BLOCKED — ASGI API request lifecycle**

Owner：`worker_runtime_p3a`。本票只执行一次前台、临时根目录诊断；未使用 `TestClient`，未修改产品文件。

## One-shot run

```bash
PYTHONPATH=/mnt/d/Workstation/Projects/cs-board timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-asgi-r5.py > /tmp/m09-p3a-asgi-r5.log 2>&1
```

- shell exit：`124`
- wall time：`19.945s`
- 命令输出依规定仅写入 `/tmp/m09-p3a-asgi-r5.log`。

## Marker and contract facts

| Marker | Observed result |
| --- | --- |
| `direct-capability-start` | reached |
| `direct-capability-result` | reached: `supported=False bootstrap_ready=False` |
| `asgi-capabilities-start` | reached |
| `asgi-capabilities-result` | not reached; no HTTP response status/body available |

仓库根 assertion 通过，`PYTHONPATH` 已设置，临时脚本 imports 成功。直接 `CapabilityService.snapshot()` 已完成，说明该 P3a read model 不自行卡住。随后 `httpx.ASGITransport` 的唯一 `/api/v1/capabilities` 请求未在 20 秒内返回，故 HTTP 200、top-level `items/providers`、`supported=false` 与敏感文本断言均未能执行完成，不计为 API contract PASS。

10 秒 faulthandler stack 显示主 asyncio event loop 在 selector 等待；一个 AnyIO worker 线程在队列等待。未得到应用 handler 内更细的栈或断言失败。该现象归于 **ASGI API request lifecycle**，而非 direct P3a 实现；也不把先前的 TestClient lifecycle 问题归咎于本票。

## Integrity

命令后以 `ps -eo pid=,args= | rg '[p]ython.*m09-p3a-asgi-r5|[p]ytest.*test_capabilities_api\\.py'` 检查，无 residual Python/pytest。P3a scoped diff 前后保持：

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

前后 scoped `git diff --check` 通过。只写入任务允许的 `/tmp` 脚本、日志和本回执；未重试、未启动后台任务、未重启服务、未执行 P4/P6/P3b/activation/render/task 创建。

P3a/P4 未接受。即使后续取得 API PASS，仍须独立 P3a verification，停止等待 PM。
