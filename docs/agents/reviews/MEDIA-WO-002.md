# MEDIA-WO-002 Review

- Reviewer: PM (`/root/pm`)
- Delivery: `7bc8af9`
- Base: `8a59f86`
- Verdict: **APPROVED**

## 验收结论

交付完整覆盖六阶段共用 envelope、run-root 相对路径、结构化 argv、WO 独立状态机、fingerprint
与 stale、插画 candidate import/validate/accept/reject/retry、幂等语义、WEB 只读 DTO 和
Skills/CLI 消费边界。状态迁移均有明确退出动作；accept 前不会提交正式 `illustrations.manifest`。

契约中的规范 Stage、Artifact key 与当前 `csboard/application/pipeline.py`、
`csboard/adapters/filesystem/artifacts.py`、`schemas/mountain/` 及现行 Mountain 文档一致。
`illustrations.job`、`illustrations.candidates` 和 `style.snapshot` 是已声明但待实现的 additive
契约，文档已明确不冒充生产现状。

## 独立证据

```bash
git diff --check 8a59f86...7bc8af9
jq empty docs/agents/contracts/examples/illustration-work-order-v1.example.json
jq empty docs/agents/contracts/examples/illustration-visual-retry-v1.example.json
```

三项命令均通过；diff 只包含契约、两个 JSON 示例和交付报告，没有 Python、TypeScript、Schema
或运行时变更。本裁决不授权合并，后续实现仍受队列依赖约束。
