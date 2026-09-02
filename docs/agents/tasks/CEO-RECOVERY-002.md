# CEO-RECOVERY-002：恢复常驻调度与停滞队列

- Owner: PM（CEO 调度角色）
- Status: IN_PROGRESS
- Priority: P0
- Depends on: `PM-AUTO-001=APPROVED`
- Worktree: `/mnt/d/workstation/projects/cs-board-mountain-v2`
- Branch: `integration/mountain-v2`

## Goal

把现有只存在于旧 orchestrator 路径的 PM 恢复为真实、可按 UUID 唤醒的 Codex CLI 会话。CEO 每次只做
一次短协调周期：观察全队、识别失联或被阻塞的进行中任务、审核已交付工作、计算依赖并派发下一项，
然后退出本轮。长门禁留给 Worker 或 Reviewer，Dashboard 继续只做观察器。

## Current incident

- 注册表中的 `/root/pm`、`/root/web`、`/root/core`、`/root/media` 已不在真实会话树；
- `WEB-INTAKE-003` 仍标记 `IN_PROGRESS`，但 WEB heartbeat 已过期且没有可唤醒会话；
- `WEB-WO-003` 虽为 `READY`，同一 Owner 仍占用前项，不得重叠派发；
- 现有事件探针看不到 stale `IN_PROGRESS`，因此不能推动恢复。

## Allowed surfaces

- `.agents/coordination/agents.json`；
- `.agents/coordination/scripts/pm_event_probe.py`、`run_pm_if_needed.sh` 及其测试；
- `.agents/coordination/systemd/cs-board-pm.service`、`cs-board-pm.timer`；
- `docs/agents/status.md`、`docs/agents/pm-runtime.md`；
- 本任务的 report/review 文档；
- ignored runtime 状态与用户级 systemd 安装副本。

## Forbidden surfaces

- 产品代码、`web-v2`、媒体实现、Stage Work Order；
- Dashboard HTML/CSS/布局重做；
- 绕过 Reviewer、自行批准产品交付或自动 merge；
- 无事件时调用模型、无限模型循环、用心跳伪造在线；
- 覆盖或清理任一产品工作树中的用户改动。

## Acceptance

1. PM 注册为 `transport=codex_cli` 且 `thread` 是一次真实 `codex exec --json` 返回的 UUID；
2. 事件探针检测 `REVIEW_READY`、可派发 `READY`、依赖已满足的 `BACKLOG`，以及 heartbeat 过期、
   runtime 缺失、idle/blocked 的 `IN_PROGRESS` 恢复事件；
3. 同一 Owner 存在 `DISPATCHED`、`IN_PROGRESS` 或 `REVIEW_READY` 时，其后续 `READY` 不产生并发派发事件；
4. 探针无事件时 stdout 为空；成功 ack 后相同事件不重复；wrapper 使用非阻塞锁且失败不 ack；
5. 用户级五分钟 timer 已实际安装并 active；无事件路径用测试替身证明不会执行 `codex exec`；
6. `WEB-INTAKE-003` 的失联状态被实际恢复到一个真实可唤醒 Worker，会话注册和一次派发均有 runtime 证据；
7. 至少观察一轮 Worker → `REVIEW_READY` → 独立 Reviewer → CEO 裁决/下一队列计算；若产品门禁失败，
   保留真实失败并进入有界返工，不得伪称批准；
8. Dashboard 仍使用原面板和原端口，只通过既有 runtime/status 数据显示 CEO/队员状态。

## Gates

```bash
python3 -m unittest discover -s .agents/coordination/scripts/tests -p 'test_*.py' -v
python3 .agents/coordination/scripts/pm_event_probe.py probe --project .
systemctl --user is-enabled cs-board-pm.timer
systemctl --user is-active cs-board-pm.timer
git diff --check HEAD^
```

## Stop condition

实现提交、真实会话 UUID（可脱敏展示）、timer 状态、事件探针测试、WEB 恢复派发及闭环证据全部写入
`docs/agents/reports/CEO-RECOVERY-002.md`，提交后交给独立 Reviewer。实现者和 CEO 均不得自批。
