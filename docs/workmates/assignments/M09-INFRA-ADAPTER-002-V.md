# M09-INFRA-ADAPTER-002-V — P2 Adapter 独立验证

`tester_backend`（Codex terra medium），独立验证 P2。

回执：`docs/workmates/receipts/M09-INFRA-ADAPTER-002-V.md`。

核验 P1 契约仅有入口、props/renderer 输出、mock subprocess success/nonzero/timeout、坏输入、cleanup、ffprobe failure不成功、path/secret redaction和无legacy import。独立运行 focused/affected P2/P1 adapter tests及 video_renderer TypeScript check。不得修改实现/计划、执行 real render、创建任务或打开 capability/submission。PASS 仅完成 P4 的另一半依赖。
