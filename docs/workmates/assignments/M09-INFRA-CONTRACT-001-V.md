# M09-INFRA-CONTRACT-001-V — P1 领域契约独立验证

`tester_backend`（Codex terra medium），在 P1 回执完成后独立验证。

回执：`docs/workmates/receipts/M09-INFRA-CONTRACT-001-V.md`。

验证：严格 P1 文件边界；版本化 storyboard/props/manifest/evidence 契约；清晰的 1–2 页策略；时间/帧/ID/相对路径/secret 不变量；黄金 fixture 和 schema round-trip；TypeScript props typecheck；禁止 domain→Remotion/subprocess/webapp/provider 依赖。独立运行 focused P1 tests、受影响 domain suite和 TypeScript typecheck，记录精确证据。不得修改实现/计划、创建任务、render、打开 capability/submission。PASS 才授权 PM 同时派发 P2 与 P3a。
