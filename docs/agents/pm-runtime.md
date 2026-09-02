# 独立 PM 运行与恢复

## 当前真实运行方式

- 用户接口是 `/root`；独立协调角色是 `/root/pm`；
- CORE/WEB/MEDIA 完成交付后，用 orchestrator `followup_task` 直接唤醒 `/root/pm`；
- PM 被唤醒后审核、提交裁决、计算依赖并派发下一项，然后结束本轮；
- Dashboard 每三秒读取 Git 状态和 runtime 心跳。PM working 租约默认 120 秒，Worker 默认 600 秒；
  租约到期写成 `idle + lease_expired`，因此心跳不能长期伪造工作状态。

orchestrator Agent 只能在当前线程树仍存在时被直接唤醒。Dashboard 本身只是观察器，不能调用模型，
也不能证明跨进程、跨会话自治。面板上的 `idle` 是正常等待事件，不代表队列丢失。

## 外部 Codex CLI 恢复入口

`.agents/coordination/scripts/pm_event_probe.py` 是纯本地事件探针，只读取跟踪状态：

- 出现 `REVIEW_READY` 时产生 review 事件；
- 出现 `READY` 时产生 dispatch 事件；
- `BACKLOG` 的全部依赖变为 `APPROVED` 时产生 promote-ready 事件；
- 没有新事件或该事件已成功 ack 时不输出内容，也不调用模型。

`.agents/coordination/scripts/run_pm_if_needed.sh` 使用非阻塞 `flock` 防止重叠。只有探针输出新事件，
且 `.agents/coordination/agents.json` 中 PM 注册为 `transport=codex_cli`、`thread=<真实 CLI UUID>` 时，
才执行一次 `codex exec resume`；成功后才 ack，失败会保留事件供人工恢复。每次最多处理一个 PM 周期。

当前 PM 是 orchestrator `/root/pm`，所以外部脚本会明确写入 `not-configured` 并退出，不产生模型调用。
不得把 `/root/pm` 字符串冒充 Codex CLI UUID。需要跨线程树恢复时，先由用户启动并确认一个独立 PM
CLI session，把真实 UUID 和 transport 写入注册表，再安装定时器：

```bash
mkdir -p ~/.config/systemd/user
cp .agents/coordination/systemd/cs-board-pm.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now cs-board-pm.timer
```

用户已授权的上限是每五分钟检查一次、无事件零模型调用。定时器没有 merge、删除、审批绕过或产品
决策权限；未注册 CLI UUID 前不应启用。运行证据只写 ignored runtime，不写 Secret 或用户素材。
