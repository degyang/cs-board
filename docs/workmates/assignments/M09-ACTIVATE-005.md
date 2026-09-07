# M09-ACTIVATE-005 — native backend activation gate wiring

状态：assigned

Owner：`backend`，工作区 `/mnt/d/workstation/projects/cs-board-worktrees/backend`；PM 集成；verification 独立复验。

你不是代码库中的唯一执行者。只修改本任务列出的 backend glue、直接测试和 backend 工作区回执；保留所有既有 M09/服务/资产改动，不改服务设置、Secrets、pointer、frozen outputs、frontend、主看板，不提交/合并/push。

## 现场根因

8000 由 `scripts/run_mountain_backend.py` 导入 `backend.mountain_server`。`backend.mountain_server` 计算了 `project_root`，但调用 `mountain_capability_router(service_registry)` 时未传入；`backend/mountain_capability_api.py` 也未注入 `accepted_v3_gate(root)`。因此 activation verifier 能用默认根读取 pointer，但 bootstrap 的 `external_stage_gate` 永远缺失/false。旧 `webapp/mountain_capability_api.py` 有正确语义，但不是当前运行入口。

## 目标与范围

1. 让 native `backend.mountain_capability_api` 接收显式 `project_root`，规范化为 `Path.resolve()`，并用同一 root 同时构造 `CapabilityService(project_root=root, external_stage_gate=lambda: accepted_v3_gate(root))`。
2. `backend.mountain_server` 将其已计算的 `project_root` 显式传入 capability router。
3. 增加直接回归，证明 data dir 与 project root 不同时：pointer 只从 project root 读取，external gate 与 activation verifier 使用同一 root；pointer 缺失/无效仍 fail closed。
4. 不更改 capability/pointer/fingerprint 算法，不创建 task/render，不调用 provider。

可修改：`backend/mountain_capability_api.py`、`backend/mountain_server.py`、直接相关 tests、backend 回执 `docs/workmates/receipts/M09-ACTIVATE-005.md`。

## 验收

- focused backend capability/activation/server/create-options tests PASS；`git diff --check` PASS。
- 回执列出文件 hash、命令、exit、数量和 `READY_FOR_VERIFY / CHANGES_REQUIRED`。
- 完成后保持客户端 idle，等待 PM/verification 消费，不退出成空壳。
