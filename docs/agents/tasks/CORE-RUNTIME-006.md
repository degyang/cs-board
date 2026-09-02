# CORE-RUNTIME-006：后端全量门禁、冷启动边界与进程清理

- Owner: CORE
- Status: DISPATCHED
- Priority: P0
- Depends on: `CORE-CAP-005=APPROVED`
- Worktree: `/mnt/d/workstation/projects/cs-board-core-cap-repair`
- Branch: `fix/mountain-capability-secret-contract`
- Base commit: `7ac3cb003327110d58c7d48cf75131d207018d5f`

## Goal

在当前已批准 CORE 集成基线上建立一次可重复的后端发布前门禁：全量 pytest 必须在 180 秒内自行正常
退出，fresh data dir 的 Mountain 组合根必须可反复冷启动并满足关键 API/NotFound/error contract，测试和
smoke 结束后不得残留 uvicorn、子进程或监听端口。定位并修复真实挂起、skip 或生命周期缺陷；不得只延长
timeout 或把“未观察到失败”写成通过。

## Allowed surfaces

- `tests/` 中聚焦全量退出、真实 launcher、冷启动、API 错误边界和进程清理的测试；
- `scripts/run_mountain_backend.py`、`scripts/smoke_real_backend_contract.py` 及必要的聚焦 helper；
- 只有门禁复现出生产缺陷时，才可最小修改 `webapp/mountain_server.py`、Mountain `/api/v1` 路由组合、
  runtime/process supervisor 或 repository 生命周期代码；报告必须逐项关联复现；
- `docs/agents/reports/CORE-RUNTIME-006.md`。

## Forbidden surfaces

- `web-v2`、Dashboard、媒体 Skill/adapter、Stage Work Order 语义或执行、selective 编排；
- 修改 API DTO 或持久化格式来绕开既有契约；读取、打印或提交 Secret 值；
- skip/xfail、新增外层 sleep、删除断言、只提高 timeout，或用 watchdog 的 124/信号退出冒充门禁通过；
- 合并、领取其他任务或修改其他 Owner 状态。

## Acceptance

1. `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS ... pytest -q` 全量在 180 秒内由 pytest 自身 exit 0，
   `0 failed` 且 `0 skipped`；外层 watchdog 仅作失败清理，exit 124/137/信号均为失败；
2. 使用两个不同 fresh data dir 连续启动真实 `scripts/run_mountain_backend.py`，每轮健康检查与
   `/api/v1/tasks`、`/api/v1/services`、`/api/v1/capabilities`、settings/assets 代表性读取均进入明确终态；
3. 非法 task/run/asset/service ID、未知路由和缺失实体返回既有结构化 4xx error contract，不泄露绝对路径、
   traceback、Secret 或完整输入；不得把 NotFound 变成 500；
4. 端口已占用、启动导入失败或健康检查超时必须有界非零退出并清理子进程；负向行为由测试进程观察真实
   child return code，不能依赖测试超时判定成功；
5. 每轮停止后验证 launcher/uvicorn child 已退出、临时目录可删除且测试端口可立即重新 bind；不得按
   模糊进程名误杀用户其他服务；
6. 报告列出全量用例数、退出码与墙钟耗时、冷启动矩阵、NotFound/error 矩阵、发现的挂起根因与修复、
   清理证据；若无挂起也必须写明定位方法和最慢测试，不得虚构根因。

## Gates

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s 180s \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py
git diff --check 7ac3cb0...HEAD
```

首个命令只有 pytest 自身 exit 0 且摘要无 skipped 才通过；`timeout` 仅是 180 秒硬上限。若 smoke 的真实
参数与脚本 help 不同，先以 `--help` 固定命令并记录，不得删除真实 launcher/API/cleanup 行为。

## Stop condition

提交并推送当前 CORE 分支；报告记录逐门禁真实终态。全部 acceptance 满足才置为 `REVIEW_READY` 并通知
PM；若真实环境或缺陷阻止正常门禁，置为 `BLOCKED` 并提交可复现证据。不得自行批准或等待 Reviewer。

