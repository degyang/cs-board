# M09-INFRA-ADAPTER-002-R-V-R — P2 verifier gate补证

状态：dispatch_pending
Owner：verification（Claude Code `mimo-v2.5-pro / medium`，`%60`）
模式：一次性只读补证；不重跑 P2 产品门禁

## Gap and goal

`M09-INFRA-ADAPTER-002-R-V` 的 JSON/回执将结果写为 PASS，却明确记录
`./scripts/workmates verify` 因模型临时不可用而**未完成**。该命令是原票硬门禁，故先前 PASS 无效，P2 和 P4 均不能推进。

只补齐这一项：先确认 backend worktree 的 P2 scoped `git diff --name-only` 仍为空；创建一个此前不存在的新本地 JSON evidence 文件；运行一次：

```bash
./scripts/workmates verify --role verification --evidence <new-json-path>
```

## Boundaries and verdict

不修改 P2 实现/测试/依赖、P3a、服务、配置、看板或先前回执；不重跑 pytest/build，不执行真实 render/任务创建/提交。只允许写新 JSON 和
`docs/workmates/receipts/M09-INFRA-ADAPTER-002-R-V-R.md`。

若命令 PASS 且 P2 scoped diff 仍为空，回执可写 PASS（仅补齐原独立验证门禁，仍由 PM 消费）。若命令无法完成、失败或范围漂移，写 BLOCKED/FAIL 与精确输出；不要重试、不要降级或自我接受 P2/P4。写完停止。
