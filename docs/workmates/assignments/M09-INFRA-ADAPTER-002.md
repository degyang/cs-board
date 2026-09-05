# M09-INFRA-ADAPTER-002 — P2 Storyboard 与 Remotion Renderer Adapter

`worker_backend_p2`，仅实现 P2，依据独立 PASS 的 P1 契约。

回执：`docs/workmates/receipts/M09-INFRA-ADAPTER-002.md`。

范围：`csboard/adapters/remotion/`、必要 port types、直接 adapter tests。不得改 domain schema、capabilities、commands/API/CLI、legacy/webapp、前端或 real render 配置。

要求：只用 P1 版本化 storyboard/props 契约实现 domain→props 翻译与 renderer port；renderer 写 run-private 临时 props，执行锁定脚本，并且只有非空候选 MP4 经 ffprobe 容器/视频流/时长/尺寸验证后才成功。覆盖 mock subprocess success/nonzero/timeout、坏 props、缺 node、cleanup、probe failure、path/secret redaction、无 legacy import。不得执行真实 render/创建任务/开放 capability/submission。运行 focused + affected suite，记录证据；出口 READY_FOR_INDEPENDENT_P2_VERIFICATION。
