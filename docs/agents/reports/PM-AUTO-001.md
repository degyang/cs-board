# PM-AUTO-001 Delivery

- Delivery: `fa840d7`
- Implementer: PM (`/root/pm`)
- Verdict claimed: none; waiting for `/root` review

## Delivered

- PM 注册从用户入口 `/root` 分离为 `/root/pm`；MEDIA 注册信息修正为实际 worktree/branch；
- CORE/MEDIA 首轮正式裁决、CORE attempt 2 和三个依赖化后续 BACKLOG 已提交；
- Dashboard Skill 使用 PM 120 秒、Worker 600 秒默认有限租约，过期写 `idle + lease_expired`；
- 项目事件探针只对 review、dispatch、依赖满足三类新事件输出 JSON；ack 后不重复；
- 恢复 wrapper 以 flock 防重叠，只有新事件加真实 `codex_cli` UUID 才调用一次模型；
- 当前 orchestrator PM 不冒充 CLI UUID，wrapper 返回 `not-configured`；五分钟 systemd 模板未安装。

## Verification

```text
python3 -m unittest discover -s .agents/coordination/scripts/tests -v
Ran 4 tests ... OK

npm --prefix .../team-dashboard test
3 passed

skill-creator quick_validate.py .../pos-magents
Skill is valid!

git diff --check
clean
```

Dashboard Skill 修复提交为 POS 分支 `7f816b9`（有限租约）和 `496218f`（显式 BACKLOG lane），
均已推送。当前团队 Dashboard 继续运行在 `http://127.0.0.1:4317`。

## Honest boundary

orchestrator `followup_task` 是当前事件驱动主路径，可唤醒空闲 `/root/pm`。若线程树失效，只有注册
真实 Codex CLI session UUID 后，外部 timer 才能恢复；当前未注册、未安装 timer，也没有后台模型
调用。用户已授权的边界保留为最多每五分钟检查一次、无事件零模型调用。
