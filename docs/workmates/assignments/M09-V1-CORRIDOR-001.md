# M09-V1-CORRIDOR-001 — fixed-input controlled internal Remotion corridor

状态：`failed_controlled`（2026-09-07；G0 independent PASS 已消费；唯一一次本地调用以非零退出结束）。

## 目标与 owner

- Owner：`backend`，新鲜 Codex `gpt-5.6-terra / medium` 会话。
- 工作目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`；目标基线 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21` 加上已冻结的 G0/baseline capability diff。不要改动或回滚该工作树已有的无关改动。
- 独立验证：`verification`；V2 仍须等 V1 的独立 PASS。
- 回执：仅写 `docs/workmates/receipts/M09-V1-CORRIDOR-001.md`。

## 唯一交付

完成一次受控、本地、真实的 Remotion 调用。它消费一个新建的最小版本化 props JSON 与已知的本地非真实素材，记录其 SHA-256 和版本标识，并产生对应 run 目录中的候选 MP4（非空）或受控失败结果。Remotion 内部的图片与中间过程是黑盒，不审计、不扩展其治理范围。

执行前先从当前代码中定位既有 renderer/CLI 边界。若缺少使该单次调用可控的最小边界，可在本任务中实现，但只限固定输入、显式 timeout、退出码/脱敏失败摘要、run identity 和 run-relative 候选输出定位；为该行为补最窄测试。不得替换渲染器或重构其内部流程。

## 输入、运行与证据约束

- 固定 props 必须有明确 `schema/pipeline` 版本，内容与 SHA-256 写入回执；只使用本轮新建的本地合成素材，不读取真实素材、用户任务、密钥或集成运行目录。
- 使用本轮独立、可识别的数据/输出根（可用新建的 `/tmp` 测试夹具）；不得与 8000 或任一其他 worker 共用可写 data dir。记录相对路径，不能记录绝对路径或原始 stderr。
- 只可调用一次真实 Remotion；在调用前设置明确 timeout。超时、非零退出或空候选文件都必须真实记录为 failure，不得伪造或重试为 success。
- 成功仅代表 V1 的候选输出存在且与该受控 run 对应；不运行 ffprobe、不做 hash/manifest/artifact index 的正式登记、不宣称 Task/Run/Stage success（那些属于 V2）。

## 禁止项与停止条件

不得创建公开任务、不得改变 `available` 或 `supported`、不得激活 create-options/public submission、不得启动/重启集成服务、不得调用真实图片/TTS provider、不得写入或显示 secret、真实素材、原始 stderr 或绝对路径。不得开展 V2/V3/activation、ffprobe、最终登记、内部图片检查。

遇到 renderer 不可用、timeout、非零退出或空输出时停止并写 `BLOCKED`/`FAIL` 回执和脱敏事实；不扩大范围绕过。完成后不提交、合并或推送。

## 完成谓词

回执必须包括：冻结输入版本/hash、合成素材说明、真实 run ID、调用边界及 timeout、退出状态、候选 MP4 的 run-relative 路径和非空大小（或受控失败摘要）、涉及文件与测试命令/结果、无残余进程证明，以及明确声明未触碰所有禁止项。只有后续独立 verification PASS 才能解锁 V2。
