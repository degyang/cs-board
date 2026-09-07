# M09-INFRA-BOOTSTRAP-003A-R-R3 — P3a vs TestClient root-cause discriminator

状态：**BLOCKED — diagnostic harness bootstrap**

Owner：`worker_runtime_p3a`。只执行了一次前台只读诊断，未修改产品文件。

## One-shot result

命令：

```bash
timeout --kill-after=3s 20s .venv/bin/python -X faulthandler /tmp/m09-p3a-rootcause-r3.py > /tmp/m09-p3a-rootcause-r3.log 2>&1
```

- shell exit：`1`
- wall time：`0.499s`
- 最后 marker：无；脚本在第一个 `direct-capability-start` 前失败。
- 日志中的唯一失败：从 `/tmp` 运行的临时脚本未能导入 `backend.mountain_server`（`ModuleNotFoundError: No module named 'backend'`）。
- response status：无；没有创建 `CapabilityService`、`create_app` 或 `TestClient`，因而无 health/capabilities HTTP 响应。
- faulthandler stack：未触发（进程在 10 秒阈值前退出）。

## Attribution

不能归因为 `direct P3a`、`shared TestClient/app lifecycle` 或 `capabilities HTTP composition` 中的任一项：失败发生在临时诊断 harness 的 Python import bootstrap，早于三种被区分的路径。这不是 P3a 或应用生命周期的运行结论。

## Integrity

运行后以 `ps -eo pid=,args= | rg '[p]ython.*m09-p3a-rootcause-r3|[p]ytest.*test_capabilities_api\\.py'` 核对，无 residual Python/pytest 进程。P3a scope diff 在前后均为：

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

前后 scoped `git diff --check` 均通过。仅写入任务允许的 `/tmp/m09-p3a-rootcause-r3.py`、`/tmp/m09-p3a-rootcause-r3.log` 与本回执；未重试、未重启服务、未执行 P4/P6/P3b/activation/render/task 创建。

P3a/P4 仍未接受，停止等待 PM。
