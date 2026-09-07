# M09-INFRA-BOOTSTRAP-003A-R-R4 — corrected P3a/TestClient discriminator

状态：**BLOCKED — shared TestClient/app lifecycle**

Owner：`worker_runtime_p3a`。本票只执行一次前台只读诊断；未修改产品文件。

## Import and command integrity

临时脚本的第一段按任务要求设置了 `PROJECT_ROOT` 为集成区、断言 `backend/mountain_server.py` 是常规文件，并将该根目录插入 `sys.path`；随后 imports 成功，证明 import assertion 通过。唯一运行的命令为：

```bash
PYTHONPATH=/mnt/d/Workstation/Projects/cs-board timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-rootcause-r4.py > /tmp/m09-p3a-rootcause-r4.log 2>&1
```

- shell exit：`124`
- wall time：`19.942s`
- 无终端 stdout/stderr（按任务要求写入 `/tmp/m09-p3a-rootcause-r4.log`）。

## Markers and attribution

| Marker | Result |
| --- | --- |
| `direct-capability-start` | reached |
| `direct-capability-result` | reached: `supported=False bootstrap_ready=False` |
| `testclient-health-start` | reached |
| `testclient-health-result` | not reached |
| `testclient-capabilities-start/result` | not reached |

10 秒 faulthandler stack 显示主线程在 `starlette.testclient.TestClient.__enter__()` 等待 AnyIO blocking portal；portal event-loop 线程在 selector 等待。health GET 尚未发出，故不存在 health 或 capabilities response status。

精确归因：**`shared TestClient/app lifecycle`**。直接 P3a snapshot 已完成，排除 `direct P3a`；capabilities HTTP marker 从未到达，排除 `capabilities HTTP composition`。

## Scope and process checks

命令后使用 `ps -eo pid=,args= | rg '[p]ython.*m09-p3a-rootcause-r4|[p]ytest.*test_capabilities_api\\.py'` 核对，无 residual Python/pytest。P3a scope diff 在运行前后保持：

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

运行前后 scoped `git diff --check` 均通过。仅写入任务允许的两个 `/tmp` 诊断文件和本回执；未重试、未修改产品代码/测试/配置、未重启服务、未执行 P4/P6/P3b/activation/render/task 创建。

P3a/P4 仍未接受，停止等待 PM。
