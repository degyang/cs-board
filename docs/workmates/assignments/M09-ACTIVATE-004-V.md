# M09-ACTIVATE-004-V — current-browser V3 evidence re-freeze

状态：assigned

Owner：`verification`（Claude Code / `mimo-v2.5-pro` / medium）；PM 消费结果并签发 activation pointer。

你不是代码库中的唯一执行者。只读集成区实现与 frozen outputs；只允许在 `/tmp` 新建本轮验证目录/证据，并向既有 `docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md` 追加明确的 current-browser re-freeze 段。不得修改实现、测试、服务、Secrets、canonical outputs、activation pointer 或 board。

## 背景与目标

原 V3 PASS 的真实 smoke 使用 `Google Chrome for Testing 152.0.7977.54`；当前 `video_renderer/browser-resolver.mjs` 在三个 browser env var 均未设置时解析为 `152.0.7977.75`。`M09-ACTIVATE-003-V` 已判定不能直接改 pointer 绕过漂移。

在当前 `.75` browser 上对 accepted run 的 synthetic、run-contained `remotion-props.json` 做一次隔离的受控 renderer verification，证明当前 browser 与未变的 renderer/resolver/lockfile 能产生真实、非空、ffprobe-valid H.264 1920×1080 MP4。此任务不创建 Task/Run，不调用文本、TTS、图片 provider，不修改或替换 accepted MP4。

## 必须检查

1. 开始/结束重算 accepted task/run/MP4/index/manifest 与 renderer/resolver/lockfile hashes，确认无漂移。`commands.py` 在原 V3 后包含已验收的 activation 集成改动，不要求匹配原 V3 hash；应记录当前 hash，并引用 `M09-ACTIVATE-003-V` 的 focused PASS，禁止声称它未漂移。
2. 明确 unset `REMOTION_BROWSER_EXECUTABLE`、`PUPPETEER_EXECUTABLE_PATH`、`CHROME_PATH`，由 renderer resolver 自动选择 browser；记录安全版本字符串，不记录完整环境。
3. 输入只允许 accepted run 的 `input-snapshot/remotion-props.json` 与其引用的 synthetic SVG；先验证引用 run-contained、无 `..`、无绝对路径。
4. 输出仅写到新建 `/tmp/m09-activate-004-v-*`；运行既有 `video_renderer/render.mjs`，必须有有界 timeout。随后用真实 ffprobe 核对 H.264、1920×1080、duration>0，并记录 size/hash；确认无残留 renderer 进程。
5. 运行 renderer tests/typecheck、focused corridor/activation tests、scoped diff check，以及新的 `./scripts/workmates verify --role verification --evidence <不存在的新路径>`。
6. 若全部通过，向 `M09-V3-CORRIDOR-VERIFY-001.md` 追加 dated re-freeze 段，写当前 browser、命令/exit、临时 evidence 路径、pre/post hashes 与 `Verdict: PASS`；不得删除或改写旧证据。若任一失败，追加 `BLOCKED/FAIL` 并保持 activation 关闭。

完成后退出，不等待新任务，不停留空闲 shell。
