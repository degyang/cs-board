# 独立 PM 运行与恢复

## 当前真实运行方式

- 用户接口是 `/root`；独立 CEO/PM 是注册在 `.agents/coordination/agents.json` 的 Codex CLI UUID；
- 事件 wrapper 用 `codex exec resume <UUID>` 唤醒 CEO；每次只处理一个短协调周期；
- CEO 被唤醒后优先恢复 stale active work，再处理审核、依赖和派发，然后结束本轮；
- Dashboard 每三秒读取 Git 状态和 runtime 心跳。PM working 租约默认 120 秒，Worker 默认 600 秒；
  租约到期写成 `idle + lease_expired`，因此心跳不能长期伪造工作状态。

旧 orchestrator Agent 只能在原线程树仍存在时被直接唤醒，不能作为持久注册。Dashboard 本身只是观察器，
不能调用模型，也不能证明跨进程、跨会话自治。面板上的 `idle` 只有在事件探针没有待处理工作时才是
正常等待；stale `IN_PROGRESS` 会产生恢复事件。

## 外部 Codex CLI 恢复入口

`.agents/coordination/scripts/pm_event_probe.py` 是纯本地事件探针，只读取跟踪状态：

- 出现 `REVIEW_READY` 时产生 review 事件；
- 出现 `READY` 时产生 dispatch 事件；
- `BACKLOG` 的全部依赖变为 `APPROVED` 时产生 promote-ready 事件；
- `IN_PROGRESS` 的 runtime 缺失、idle/blocked、heartbeat 过期或 task_id 不匹配时产生 recover-stale 事件；
- 同一 Owner 已有 active task 时，抑制后续 `READY` 的并发 dispatch；
- 没有新事件或该事件已成功 ack 时不输出内容，也不调用模型。

`.agents/coordination/scripts/run_pm_if_needed.sh` 使用非阻塞 `flock` 防止重叠。只有探针输出新事件，
且 `.agents/coordination/agents.json` 中 PM 注册为 `transport=codex_cli`、`thread=<真实 CLI UUID>` 时，
才执行一次 `codex exec resume`；成功后才 ack，失败会保留事件供人工恢复。每次最多处理一个 PM 周期。

CEO 派发 CLI Worker 时只能调用 `.agents/coordination/scripts/dispatch_cli_agent.sh`。该脚本用独立
`cs-board-agent-<role>.service` 启动 Worker 并立即返回；unit active 时拒绝重叠启动。CEO 不得在自身
oneshot 中同步等待 Worker 的产品门禁，否则会再次阻塞调度入口。

当前 CEO 由 `codex exec --json` 启动，注册表保存其 `thread.started` 返回的真实 UUID；UUID 只用于
`codex exec resume`，不是在线心跳。由于当前项目位于 WSL `/mnt/d`，CLI 的 `workspace-write` sandbox
实际返回 `EROFS`；wrapper 因此用 CLI 的无 sandbox resume 模式恢复当前 CEO session。它的动作权限仍
受 Git 契约、单周期 prompt、非重叠锁和独立审核约束，systemd unit 也只允许执行项目内这一 wrapper。
用户级 timer 安装命令为：

```bash
mkdir -p ~/.config/systemd/user
cp .agents/coordination/systemd/cs-board-pm.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now cs-board-pm.timer
```

用户已授权的上限是每五分钟检查一次、无事件零模型调用。定时器没有 merge、删除、审批绕过或产品
决策权限；未注册 CLI UUID 前不应启用。运行证据只写 ignored runtime，不写 Secret 或用户素材。

## 当前 M1 全局瓶颈快照（2026-09-02）

本快照服从 `docs/agents/agreements.md` 最新 ACTIVE 节点：只推进人工 Codex Skills 视频闭环；新任务和
Reviewer 默认使用适中模型与 reasoning effort，未达到三次失败返工不申请升级。

### 首要瓶颈

`PROTOTYPE-GOLDEN-005 → WEB-PARITY-004 attempt 2 → WEB-WO-003 → MEDIA-E2E-003 → USER_ACCEPTANCE`
是当前最长且不可绕过的串行链。PROTOTYPE 正在以 `gpt-5.6-terra + medium` 恢复五页 immutable golden；
在其独立审核通过前，WEB 缺少合法验收输入，不能重派 parity，也不能越过 P0 去领取 Work Order。

### 次要瓶颈

`MEDIA-PREFLIGHT-004` 的检测器已交付，但 live readiness 仍报告 FFmpeg/ffprobe version failure、
IndexTTS timeout 和 Whisper model 缺失。即使 WEB 链先完成，MEDIA live readiness 未全绿也不能派发
`MEDIA-E2E-003`，因而无法生成最终可播放 MP4。

### 关键依赖与资源错配

- `CORE-RUNTIME-006` 与上述产品串行链并行，但它是正式 API 冷启动、零 skip 和清理的发布前可靠性门禁；
  当前唯一 Reviewer 正在审核其 attempt 2，MEDIA review 因 Reviewer WIP=1 排队。
- WEB Worker 当前 blocked/空闲，不是缺人，而是缺经审核的 immutable golden；提前派发只会重复失败。
- MEDIA Worker 已交付 preflight，当前阻塞来自本机工具/模型/服务环境，而非继续写媒体代码。
- PROTOTYPE Worker 是当前真正解除 WEB 空转的资源，已使用治理允许的适中配置；不得为了缩短等待越级提模。

### CEO 接下来三个最小动作

1. 等当前 `CORE-RUNTIME-006` 独立审核提交后，只记录 verdict 与任务状态，不并发启动第二个 Reviewer。
2. Reviewer 释放后：若 `PROTOTYPE-GOLDEN-005` 已 handoff，优先审核它以解除主链；否则先审核已排队的
   `MEDIA-PREFLIGHT-004`，同时保持 PROTOTYPE Worker 单独运行。
3. 只有 PROTOTYPE 获批后，才把同一 `WEB-PARITY-004` 有界 attempt 2 提交为 `DISPATCHED` 并异步唤醒
   WEB；继续冻结 `WEB-WO-003`。MEDIA 侧依据 preflight review 只做最小环境修复，live readiness 全绿前
   不派发 `MEDIA-E2E-003`。

以上均为工程协调判断，不代表用户验收、发布或合并通过。
