# M09-V1-CORRIDOR-002-V-R — corrected frozen-hash verification

状态：`working`

verification，请复验 M09-V1-CORRIDOR-002。上一轮唯一 blocker 是 PM 错把 backend worktree 中格式不同的 test 文件 hash 写成集成区 hash；实现文件没有在验证期间变化。先读取 `M09-V1-CORRIDOR-002-V.md`。

工作目录：`/mnt/d/Workstation/Projects/cs-board`
回执：`docs/workmates/receipts/M09-V1-CORRIDOR-002-V-R.md`

当前集成区冻结 hash：

- `video_renderer/render.mjs`: `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593`
- `video_renderer/browser-resolver.mjs`: `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec`
- `video_renderer/browser-resolver.test.mjs`: `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca`
- `video_renderer/package.json`: `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59`

必须独立核对全部 hash，重跑 3/3 resolver test、typecheck、25 个 Python focused tests。真实渲染必须直接使用 `tests/fixtures/infographic/dynamic-infographic-props-v1.json`，并复制 `assets/drawing-hand-clean.png` 到新 `/tmp` run root 的 `artifacts/planning/illustrations/visual-001.png`；publicDir 参数必须是该 run root。显式 unset 三个浏览器环境变量，要求 exit 0、非空 MP4、ffprobe H.264/1920×1080/非零时长、无残余进程、diff-check 与新的 workmates evidence PASS。

不得修改实现、测试、既有回执或看板；不得使用真实素材/provider/secret，不启动服务，不提交/合并/推送。出口 PASS/FAIL/BLOCKED，并明确能否解锁 V2。
