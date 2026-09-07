# M09-V1-CORRIDOR-002 — Remotion browser recovery

状态：`working`

- Goal：修复真实 Remotion 调用在本机未显式设置 `REMOTION_BROWSER_EXECUTABLE` 时退出 1/无法产出 MP4 的问题。
- Owner：backend 独立 worktree；PM 维护看板并消费验证证据。
- Scope：`video_renderer` 浏览器解析边界、最窄自动化测试、synthetic-only 真实渲染与本轮回执。
- Constraints：不使用真实素材或 provider；不启动/重启集成服务；不改变 capability、公开提交、Task/Run/Stage 或 artifact 登记；不提交、合并、推送；保留无关 dirty state。
- Done Predicate：浏览器选择有确定性测试；renderer typecheck/相关测试通过；在不设置 `REMOTION_BROWSER_EXECUTABLE` 的干净子进程环境中，固定 synthetic props 真实调用退出 0，并生成可由 ffprobe 读取的非空 MP4；无残余 renderer 进程。
- Verification：实现者回执后，使用本轮新的 `./scripts/workmates verify --role verification --evidence ...` 证据，并逐条评估上述标准。验证通过只解锁后续 V2 决策，不自动开放公开能力。
