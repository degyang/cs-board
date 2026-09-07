# M09-V1-CORRIDOR-001-R — diagnostic recovery and one conditional retry

状态：`blocked`（2026-09-07）：Phase B 的唯一诊断调用为 `composition selection` / exit `1`，不足以建立安全的最小修复；未进行 Phase C 重试。这不是 V2、V3 或 activation 授权。

## Owner、基线与预检

- Owner：`backend`，必须为全新 Codex `gpt-5.6-terra / medium` 会话；旧 `%71` 已退役，禁止向其注入任务或复用其上下文。
- 工作目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`；HEAD 必须仍为 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`，并保留既有 G0/baseline 与 ASSET-PROV dirty state，绝不回滚或吸收无关文件。
- 权威任务：集成区本文件；回执只写 worker worktree 的 `docs/workmates/receipts/M09-V1-CORRIDOR-001-R.md`。
- 开始前对以下冻结文件运行 SHA-256；任何不匹配均先 `BLOCKED`，不进行调用：

| 文件 | SHA-256 |
| --- | --- |
| `video_renderer/render.mjs` | `ce5596d1b77884cf9bd51c1702832c42de24f3d2d42850b0204eb527477f095c` |
| `video_renderer/package.json` | `0d85b259cf6916b3f2ff8bbc2fddf73f8571ab4d8d4bd59dc9010a9efbed318c` |
| `video_renderer/src/root.tsx` | `129597b180342f3be335f2b6dc6e3bc8f1f04691e18d05ecc2506265b00d78b5` |
| `video_renderer/src/index.tsx` | `c5b75179f527ffeaa3f368b152b344bb3d7d3ebe665f420d09a37e6ce3b2e426` |
| `video_renderer/src/video.tsx` | `9cf2911e5c3ffa3cd9681bf268885a8d7ba57dee09d2a25c57a4cd8155a7cb30` |
| `video_renderer/src/types.ts` | `709086bcb7e58f3ba05a50da7f3b9314cd45a02ff0031a0a83dd024d83a88429` |
| `video_renderer/src/fixtures/dynamic-infographic-props-v1.ts` | `5aafec4d7f39e74563daf6ce76bbeb62124d465f888ad9e793a35b04e97756f9` |

## Phase A — no-render static diagnosis

先只读核对并在回执给出结论：`render.mjs` 三参数顺序、props JSON 与 TypeScript schema（frame/duration/page/image/cue）、合成 SVG 相对路径相对于 `publicDir` 的可达性、`bundle/selectComposition/renderMedia` 的 public-dir 与输出定位、以及 browser executable 的 argv/存在性。不启动 Remotion，不调用 provider，不创建 MP4，也不保留原始 stdout/stderr。

若这一阶段已经能明确根因，可实施最小修复并为该修复添加/运行最窄测试；修复不得改变公开 capability、Task/Run/Stage、artifact 登记、V2/V3 或 renderer 内部业务设计。

## Phase B — only if static evidence is insufficient

若 Phase A 不能区分根因，允许恰好一次诊断性受控调用，使用全新隔离 synthetic-only run root。其 stdout/stderr 只能在进程内存中消费：写入回执的内容限于错误类别（browser argv / props schema / public asset / bundling / composition selection / render / timeout / unknown）和经路径、URL、token/secret 模式清洗后的最后一条安全摘要。禁止把原始流、绝对路径、secret、真实素材或完整命令行写到磁盘、回执、控制面或日志。

诊断调用必须有显式 timeout、退出码和无残余进程检查；它不构成 V1 成功、V2 证据或公开能力变更。若仍无法形成明确可修复根因，停止并写 `BLOCKED`，不重试。

## Phase C — minimal fix and one conditional retry

仅在 Phase A/B 已得到明确根因且最小修复及相关测试通过后，允许恰好一次新的受控本地 Remotion 重试。它使用新 run ID、版本化 props 和新的 synthetic-only asset；写明 props/asset SHA-256、timeout、退出码、run-relative 候选 MP4 路径与非空字节数。不得以诊断输出替代本次重试成功。

重试出现 timeout、非零退出或空文件时立即停止并如实 `FAIL`；不得再试。重试成功也只证明 V1-R 有一个真实非空候选 MP4：不得 ffprobe、不得 final MP4 hash/manifest/index 登记、不得声称 Task/Run/Stage success，且 V2 仍须等待独立 V1-R PASS。

## 共同禁止项与完成谓词

不得启动/重启 8000 或任一集成服务，不得使用真实用户素材、真实任务目录、密钥或外部图片/TTS provider，不得改 `available`/`supported`、create-options 或 public submission；不审计或重构 Remotion 内部图片生成。不要提交、合并或推送。

回执必须列出预检 hash、静态结论、是否/为何使用诊断调用、仅脱敏的类别/安全摘要、最小 diff 与测试、调用次数、每次受控结果、残余进程检查、禁止项检查和下一门禁。无论结果均不解锁 V2；只有独立 V1-R PASS 加上真实非空 MP4 才能使 PM 考虑派发 V2。
