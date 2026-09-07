# M09-ACTIVATE-006 — truthful create-options reason projection

状态：assigned

Owner：`backend`，工作区 `/mnt/d/workstation/projects/cs-board-worktrees/backend`；PM 集成；`verification` 独立复验。

你不是代码库中的唯一执行者。只修改本任务列出的后端投影、直接测试和 backend 工作区回执；保留他人改动，不修改服务配置、Secrets、activation pointer、frozen outputs、frontend、主看板，不提交/合并/push。

## 现场事实

`M09-ACTIVATE-005-V` 已记录：真实 create-options 对 `infographic-remotion` 返回 `available=true`，同时因 `reason_code=null` 的 `or "能力未就绪"` fallback 返回误导性的 `reason`。按钮门禁正确，但响应语义自相矛盾。

## 目标与范围

1. `available=true` 时不返回不可用原因（字段省略或明确 `null`，优先与既有 API 约定一致）。
2. `available=false` 时保留稳定、非空、脱敏的 reason code；缺失 reason code 时仍 fail closed 并给稳定 fallback。
3. 增加直接回归，覆盖 supported true、supported false with reason、supported false without reason。
4. 不改变 capability、pointer、fingerprint、task creation 或 frontend 逻辑；不创建 Task/render，不调用 provider。

可修改：`csboard/application/commands.py`、直接相关 tests、backend 工作区 `docs/workmates/receipts/M09-ACTIVATE-006.md`。

## 验收

- focused create-options/capability/activation tests PASS；`git diff --check` PASS。
- 回执列出修改文件 hash、命令、exit、测试数量和 `READY_FOR_VERIFY / CHANGES_REQUIRED`。
- 完成后客户端保持 idle，等待 PM 消费；不要退出固定客户端。
