# M09-V2-OUTPUT-001 — final MP4 validation and atomic registration

状态：working（2026-09-07；M09-V1-CORRIDOR-002-V-R PASS 已由 PM 接受）
Owner：`backend`；独立验证：`verification`。

仅消费冻结的 V1 输出。验证最终 MP4 非空并用 ffprobe 校验视频流、时长和尺寸；原子登记 `render.video`、render manifest、SHA-256 和 artifact index，并使 Task/Run/Stage 准确标为 success、failure 或 retry。任何 timeout、非零退出、空文件、probe 或登记失败都不得 SUCCESS。

不增加中间图片观测，不公开提交，不写 secret、raw stderr 或绝对路径。回执给出脱敏的验证与登记证据。

## 本轮执行边界

- 工作目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`；保留全部既有 dirty state，不回滚或吸收无关改动。
- 使用新的匿名 synthetic task/run ID；输入只允许 checked-in golden props 等价数据和 synthetic 图片。不得消费 `/tmp` V1 文件作为长期 artifact，也不得使用真实任务、用户素材、provider 或 secret。
- 必须通过当前 `RemotionRendererAdapter`/领域契约或等价的正式边界生成候选，不能复制旧 MP4。浏览器必须由已验收 resolver 自动发现，调用环境显式不设置三项浏览器变量。
- 输出登记在该 worktree 的 `outputs/<new-task>/`：`task-package.json`、`task.json`、`run.json`、输入 storyboard/timeline/illustration manifest、持久 props、最终 `artifacts/render/infographic.mp4`、ffprobe JSON、render manifest 与 artifact index。禁止建立第二份未绑定 MP4。
- 所有 JSON 先写同目录临时文件再 `os.replace`/等价原子替换；MP4 先保留 run-private candidate，经 ffprobe 成功后原子移动到最终位置。登记失败时 run/stage/task 不得为 succeeded。
- manifest/index 每个 path 必须 run-relative、hash/size 与实际文件一致；Task、Run、`render-visuals` 必须在全部写入成功后才标 `succeeded`。
- 最窄相关测试、renderer tests/typecheck、`git diff --check`、无残余进程及新 workmates evidence 必须通过。回执写入 `docs/workmates/receipts/M09-V2-OUTPUT-001.md`。
- 不修改 capability/create-options/public submission，不启动 8000/5182，不创建 activation pointer/evidence，不提交、合并或推送。完成只写 `READY_FOR_INDEPENDENT_V2_VERIFICATION`；V3 仍等待独立 V2 PASS。
