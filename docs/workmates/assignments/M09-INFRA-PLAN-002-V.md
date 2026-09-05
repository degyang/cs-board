# M09-INFRA-PLAN-002-V — P3/P6 依赖图独立验证

`tester_backend`（可见 tmux 5.2，Codex terra medium），在 `M09-INFRA-PLAN-002` 回执完成后，只读独立验证计划修订。

执行权：此前内部验证结果不作为本轮判定依据。只有可见 tmux `tester_backend` 可写本回执；PM 只监控并消费它。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`M09-INFRA-PLAN-002.md`、更新后的执行计划、`M09-INFRA-PLAN-002` 回执与既有 29 计划。

回执写入：`docs/workmates/receipts/M09-INFRA-PLAN-002-V.md`

必须独立检查：

- P3a 不依赖 P6 evidence，P6 依赖 P3a/P1/P2/P4/P5，P3b 只在 P6 独立成功 evidence 后 activation；依赖图和 next queue 没有循环或相互矛盾。
- create-options 的 `available/supported=true` 有真实 MP4 + ffprobe + task-package manifest/hash + freshness 的明确条件；缺失/过期/失败必为 unavailable，并有稳定 reason codes。
- P4 的受控 internal/test 通道不等于用户提交开放，WebUI submission 仍关闭。
- P1-first 自动队列、各票 entry/exit、实现/独立验证角色完整；P1 到 P5、legacy 分离和 task-package 规则未被削弱。

不得改产品代码、规划、测试或服务；不得运行 real render、创建任务或打开 WebUI submission。出口 PASS / FAIL / BLOCKED，附精确定位。只有 PASS 才可供 PM 自动派发 P1。
