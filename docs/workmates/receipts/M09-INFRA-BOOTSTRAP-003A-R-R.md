# M09-INFRA-BOOTSTRAP-003A-R-R — P3a API gate timed diagnostic

状态：**BLOCKED**

Owner：`worker_runtime_p3a`。

## Single diagnostic

执行前 P3a scope diff 为：

- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

执行命令（仅此一次，前台，无 nohup、后台或重试）：

```bash
timeout 45s .venv/bin/python -m pytest -q tests/test_capabilities_api.py -x
```

结果：执行通道在 **30.002 秒**时中断命令，早于该命令的 45 秒外部 timeout；stdout/stderr 均为空，未返回 pytest/`timeout` 退出码。因此不能将 API gate 记为 PASS 或 FAIL，首个 pytest 测试也没有产生可归因的失败输出。

命令后以 `ps -eo pid=,args= | rg '[p]ytest.*test_capabilities_api\\.py'` 核对：无匹配进程，已退出，无残留 API pytest。P3a scoped diff 在前后完全相同，且前后 scoped `git diff --check` 均通过。

没有修改代码、测试、依赖、服务、配置、看板或原回执；本票仅新增本回执。未执行 render、adapter、任务创建、activation、P3b、P4 或 P6。

等待 PM 决定可提供完整 45 秒前台命令生命周期的验证环境；P4 仍锁定。
