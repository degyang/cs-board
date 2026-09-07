# M09-INFRA-BOOTSTRAP-003A-R-R2 — P3a API lifecycle hang diagnosis

状态：**BLOCKED**

Owner：`worker_runtime_p3a`。本票只执行一次、前台、只读诊断；未修改实现。

## Lifecycle

- 开始（UTC）：`2026-09-06T13:03:29Z`
- 结束（UTC）：`2026-09-06T13:04:07Z`
- 实际命令：

  ```bash
  timeout --kill-after=5s 25s .venv/bin/python -X faulthandler -m pytest -vv -x -o faulthandler_timeout=15 tests/test_capabilities_api.py > /tmp/m09-p3a-api-lifecycle-r2.log 2>&1
  ```

- shell exit：`124`（25 秒 timeout；工具报告 wall time 24.940s）
- stdout/stderr：写入 `/tmp/m09-p3a-api-lifecycle-r2.log`；该命令本身没有终端输出，因为按任务要求重定向。

## Diagnostic finding

- 已收集 6 个测试；最后启动且未完成的测试为 `test_capabilities_has_stable_sanitized_shape_without_probe`。
- 15 秒 faulthandler dump 显示主 pytest 线程在该测试的 `TestClient.get()` 中等待 AnyIO blocking portal；portal event-loop 线程处于 selector 等待。没有测试断言失败、异常或产品 API 响应可报告。
- 命令后以 `ps -eo pid=,args= | rg '[p]ytest.*test_capabilities_api\\.py'` 核对，无 residual `test_capabilities_api.py` pytest 进程。

## Scope integrity

运行前后 P3a scope diff 均为：

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

运行前后 scoped `git diff --check` 均通过。除本回执及任务指定的 `/tmp` 日志外未写文件；未重试、未启动后台作业、未重启服务，未执行 P3b/P4/P6、activation、render、adapter 或任务创建。

P3a 与 P4 均未接受，等待 PM 决定后续处理。
