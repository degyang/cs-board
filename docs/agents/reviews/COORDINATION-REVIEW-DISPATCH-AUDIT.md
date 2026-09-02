# Reviewer 调度链全面审核

日期：2026-09-02

## 结论

重复出现“多个任务等待审核、Reviewer 却 idle”的原因不是单点心跳错误，而是 Reviewer 从未拥有确定性的
执行边界。PM 模型同时承担队列选择、注册表修改和会话启动意图，但 shell 层只验证 PM 自身 exit 0；真实
Reviewer 是否建立、是否仍存活、是否完成以及下一项是否接力均没有事务保证。

## 已复现缺陷

1. `pm_event_probe.py` 会枚举全部 `REVIEW_READY`，但没有 Reviewer WIP=1 的执行器；
2. PM 可以先修改 Reviewer thread/runtime，再尝试创建会话，启动失败后留下假 `working`；
3. PM 命令 exit 0 就 ack 事件，即使任务状态完全未改变，后续周期不会重试相同签名；
4. Reviewer 完成后没有确定性接力，下一项依赖下一次模型自行采取同样的一组非原子动作；
5. Dashboard 对超过 90 秒未刷新的 working 心跳显示 idle，这正确暴露了执行会话不存在，但与 Git 中
   `REVIEW_READY` 队列形成明显矛盾；
6. 旧方案混用 orchestrator 子会话、CLI UUID、runtime 文件和 systemd 服务，没有单一进程真相源；
7. PM oneshot 多次达到 180 秒 timeout；timeout 之前产生的局部注册/runtime 写入不会自动回滚。

## 修正

- `dispatch_review_agent.sh`：按事实表顺序选择一项 `REVIEW_READY`，用 flock 和单一 systemd unit 保证
  Reviewer WIP=1；已有服务运行时幂等退出；已完成 verdict 未被 PM 消费时不重复审核同一任务。
- `run_review_agent.sh`：systemd 监督的 wrapper 成为唯一 Reviewer 进程真相源；只有 wrapper 真正启动后
  才写 `working`，Codex 正常结束写 `idle` 并写独立 completed marker，异常退出写 `blocked`。Reviewer
  不使用 Worker 的 `review`（等待审核）状态，避免出现“Reviewer 等待审核”的自指语义。
- `run_pm_if_needed.sh`：每个周期先异步调用确定性 Reviewer dispatcher；PM 不再创建或预标 Reviewer。
  PM 返回后重新探测事件，事实状态未变化则不 ack 并非零退出，下一周期继续恢复。
- 所有新 Reviewer 固定使用治理允许的 `gpt-5.6-terra + medium`，不得自行升级。

## 回归矩阵

- 有 REVIEW_READY 且无 Reviewer 服务：启动队首，dispatcher 本身不预写 runtime；
- systemd 启动失败：非零退出且不产生假 working；
- Reviewer 已完成、PM 尚未消费：不重复启动同一审核；
- PM 模型 exit 0 但事实状态不变：不 ack，事件继续存在；
- shell 语法、原事件优先级和 stale recovery 测试全部保留。

本审核只修复协调与可观测性，不修改产品代码，也不构成任何任务批准。

## Worker 链补充审核与修正

PROTOTYPE attempt 2 随后复现完全相同的失败模式：CEO 预写 `working`，orchestrator 会话停在
`pending_init`，租约过期且工作树无变化。这证明缺陷属于所有动态 Agent，而非 Reviewer 特例。

- `run_worker_agent.sh` 成为 WEB、MEDIA、PROTOTYPE 及未来动态 Worker 的唯一受监督生命周期边界；
- `dispatch_cli_agent.sh` 只校验注册、契约 commit、Owner WIP 并启动 systemd wrapper，不再写 runtime；
- wrapper 真实启动才写 working，正常结束写 review，异常写 blocked；
- 同一 Owner 已有服务时仅允许同 task 幂等调用，其他 task 明确失败；
- 支持旧 `codex_cli` resume 和新 `codex_exec` fresh session；活动动态 Worker 全部迁移为后者，避免失效
  UUID、orchestrator thread limit 和 pending_init 成为隐式依赖；
- cycle/attempt 由派工显式传入，不再把所有返工错误显示为 attempt 1。

新增 Worker 回归覆盖：真实 wrapper 命令构造且 dispatcher 零预写、systemd 启动失败零假状态、受监督
runner 的 working → review 生命周期。至此 PM 只决定 Git 状态与调用执行器，不直接创建 Agent 或写心跳。

## PM 有界化补充

一次实际 PM 周期耗时 105 秒，却只完成两个机械状态归并。PM 现改为每轮最多消费一个 action，单次模型
调用硬上限 60 秒；超时或事实状态未变化均不 ack，保留事件供下一周期重试。Worker/Reviewer 的确定性
dispatcher 在 PM 模型调用前异步运行，因此 PM 变慢不会阻塞真实任务和审核接力。
