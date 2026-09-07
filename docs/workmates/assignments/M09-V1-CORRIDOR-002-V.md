# M09-V1-CORRIDOR-002-V — independent Remotion corridor verification

状态：`working`

verification，请独立验证 M09-V1-CORRIDOR-002。

工作目录：`/mnt/d/Workstation/Projects/cs-board`
输入：本任务、`M09-V1-CORRIDOR-002.md`、backend 回执 `../cs-board-worktrees/backend/docs/workmates/receipts/M09-V1-CORRIDOR-002.md`，以及当前集成区以下冻结实现：

- `video_renderer/render.mjs` SHA-256 `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593`
- `video_renderer/browser-resolver.mjs` SHA-256 `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec`
- `video_renderer/browser-resolver.test.mjs` SHA-256 `fc8dfe55d2dbd73c848bf46cfa15c5633d5efdb2590a6c85a5543c707b4f05cb`
- `video_renderer/package.json` SHA-256 `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59`

回执写入：`docs/workmates/receipts/M09-V1-CORRIDOR-002-V.md`；另使用一个全新 `/tmp` JSON 路径运行 `./scripts/workmates verify --role verification --evidence ...`。

必须验证：

1. 核对四个冻结 hash；不匹配立即 BLOCKED。
2. 只读审查 resolver 是否优先显式配置、只接受可执行文件、在 Linux 可复用当前 Puppeteer/Playwright cache，且同一路径同时传给 `selectComposition`/`renderMedia`。
3. 运行 resolver 3 tests、renderer typecheck、`tests/test_remotion_renderer_adapter.py` 与 `tests/test_infographic_contract_fixture.py`。
4. 新建 synthetic-only `/tmp` run root，显式 unset `REMOTION_BROWSER_EXECUTABLE`、`PUPPETEER_EXECUTABLE_PATH`、`CHROME_PATH`，真实调用 renderer；要求 exit 0、非空 MP4，并用 ffprobe 核对 H.264、1920×1080、非零时长。
5. 检查无残余 renderer 进程、`git diff --check -- video_renderer` 通过，并运行项目 workmates verification 入口。

不得修改实现、测试、既有回执、看板或公开 capability；不得使用真实素材/provider/secret，不启动服务，不提交/合并/推送。出口给出 PASS / FAIL / BLOCKED，并明确该 verdict 是否足以解锁 V2；测试产物保留在 `/tmp` 或清理，不登记为产品 artifact。
