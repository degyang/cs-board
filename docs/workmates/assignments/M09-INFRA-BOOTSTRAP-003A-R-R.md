# M09-INFRA-BOOTSTRAP-003A-R-R — P3a API 门禁限时诊断

状态：dispatch_pending
Owner：`worker_runtime_p3a`（可见 runtime owner，`%54`）
模式：一次性只读诊断；不改实现

## Gap and goal

P3a 回执正确记录 `tests/test_capabilities_api.py` 未完成，但此前重复启动了多个长期 pytest。PM 已仅终止本票识别出的六个 PID；不得恢复或并行启动它们。

在当前 P3a diff 不变的前提下，做**一次**有外部时限的 API 门禁诊断：

```bash
timeout 45s .venv/bin/python -m pytest -q tests/test_capabilities_api.py -x
```

将 stdout/stderr、退出码和耗时记录到 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R.md`。运行前后核对 P3a scope diff。若通过，记录 PASS（仅 API gate补齐）；若超时/失败，记录 FAIL/BLOCKED、首个失败或 timeout 事实及进程已退出的证据。不要后台运行、不要 nohup、不要重试、不要启动额外 pytest。

## Boundaries

不得修改任何代码、测试、依赖、服务、配置、看板或原回执；不执行 real render、adapter、任务创建、activation 或 P4/P6/P3b。此票不接受 P3a，也不解锁 P4；完成新回执后停止，等待 PM。
