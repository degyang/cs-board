# M09-INFRA-BOOTSTRAP-003A-R-R4 — corrected P3a/TestClient discriminator

状态：dispatch_pending
Owner：`worker_runtime_p3a`（`%54`）
模式：一次、只读诊断；不修改产品文件

## Harness correction

R-R3 在任何产品代码执行前因 `/tmp` 脚本不含仓库根而 `ModuleNotFoundError: backend` 退出。该 harness 错误不代表 P3a 或 TestClient 结论。本票只修正 import bootstrap，保留 R-R3 的相同直接/health/capabilities marker 与 20 秒上限。

## Exact requirements

临时脚本 `/tmp/m09-p3a-rootcause-r4.py` 的第一段必须：

```python
from pathlib import Path
import sys
PROJECT_ROOT = Path('/mnt/d/Workstation/Projects/cs-board').resolve()
assert (PROJECT_ROOT / 'backend' / 'mountain_server.py').is_file()
sys.path.insert(0, str(PROJECT_ROOT))
```

仅在上述断言通过后 import `FilesystemServiceRegistry`、`PlaintextSecretStore`、`CapabilityService`、`create_app` 和 `TestClient`。在一个新的 `TemporaryDirectory` 中，以 `print(..., flush=True)` 依次发出 `direct-capability-start/result`、`testclient-health-start/result`、`testclient-capabilities-start/result` marker；先 direct snapshot，再 health GET，health 成功才 capabilities GET。设置 `faulthandler.dump_traceback_later(10)`。

只运行一次：

```bash
PYTHONPATH=/mnt/d/Workstation/Projects/cs-board timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-rootcause-r4.py > /tmp/m09-p3a-rootcause-r4.log 2>&1
```

回执 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R4.md` 必须记录 import assertion、shell exit、最后 marker、所有可得 status、任何 stack 和精确归因（direct P3a / shared TestClient-app lifecycle / capabilities HTTP composition）；并证明无 residual Python/pytest、P3a scope diff 未变。

## Boundary

只可写两份 `/tmp` 诊断文件和新回执。不得编辑产品代码、测试、依赖、配置、服务、看板或旧回执；不重启服务、不重试、不启动后台进程、不执行 P4/P6/P3b/activation/render/task 创建。无论结果均不接受 P3a/P4，完成后停止。
