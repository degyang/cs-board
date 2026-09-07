# M09-INFRA-BOOTSTRAP-003A-R-R2 — P3a API lifecycle hang diagnosis

状态：dispatch_pending
Owner：`worker_runtime_p3a`（`%54`）
模式：一次、前台、只读诊断；不修改实现

## Why this ticket exists

`R-R` 被执行通道在 30.002 秒截断，早于外部 45 秒 timeout，未获得 pytest 退出码或输出。该票只需要获得一个在通道限制内结束的完整生命周期，并定位卡在何处；它不重跑 P3a 实现或补齐验收。

## Exact one-shot command

从集成区执行一次以下命令。它的 25 秒上限低于通道上限；pytest 在 15 秒时应输出 faulthandler 线程栈。不得用 `nohup`、`&`、管道、重试或第二次 pytest。

```bash
timeout --kill-after=5s 25s .venv/bin/python -X faulthandler -m pytest -vv -x -o faulthandler_timeout=15 tests/test_capabilities_api.py > /tmp/m09-p3a-api-lifecycle-r2.log 2>&1
```

随后只读取该日志并记录：开始/结束 UTC、shell exit code（包括 124/137）、最后启动的 test/fixture、任何 faulthandler stack、以及 `ps` 确认无 residual `test_capabilities_api.py` pytest。运行前后记录 P3a scope diff 和 `git diff --check`，但绝不编辑它。

## Boundary

只可写 `/tmp/m09-p3a-api-lifecycle-r2.log` 与
`docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R2.md`。不得修改代码、测试、依赖、服务、配置、看板或先前回执；不得重启产品服务，执行 render/adapter/任务创建/activation 或 P4/P6/P3b。无论诊断结果，P3a/P4 都不被接受；写完回执立即停止。
