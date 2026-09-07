# M09-INFRA-ADAPTER-002-R — P2 Storyboard/Remotion adapter

状态：dispatch_pending
Owner：backend（Codex `gpt-5.6-terra / medium`，tmux `%59`）
工作目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`
目标基线：`workmates/backend@e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`；保留其中既有 Asset Provenance 差异

## Authority and dependency

- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` P2
- `docs/workmates/receipts/M09-INFRA-PLAN-002-R-V.md` PASS
- `docs/workmates/receipts/M09-INFRA-CONTRACT-001-R-V.md` PASS

P1 已独立接受，故 P2 可与 P3a 并行。本票不拥有 P3a bootstrap/capability 代码；只消费计划中冻结的 prerequisite contract，不自行 probe、计算 `bootstrap_ready` 或设置 `supported`。

## Scope

只写 `csboard/adapters/remotion/`、必要的 adapter port types、直接 P2 tests/fixtures 与本工作树自己的新回执 `docs/workmates/receipts/M09-INFRA-ADAPTER-002-R.md`。开始时记录范围 diff，保留既有 Asset Provenance 和其他 owner 的差异；不得重置、覆盖或格式化不相关文件。

以 P1 `InfographicStoryboard v1`/`DynamicInfographicPropsV1` 为唯一输入边界，实现或收口：domain→props 翻译；run-private 临时 props；锁定 render script 的安全 argv；只有非空候选 MP4 通过 ffprobe 容器/视频流/时长/尺寸校验后才返回成功 `RenderResult`。命令、绝对路径、原始 stderr、环境变量与 secret 均不得进入结果、trace 或 manifest。

## Required tests and exit

覆盖 mock subprocess success/non-zero/timeout、坏 props/缺 Node、cleanup、probe failure fail-closed、path/secret redaction、无 legacy `webapp.*` import；不得执行真实 render、创建任务、修改 capability/commands/API/CLI/legacy/webapp/前端、开放 submission、commit 或 push。

运行 focused P2/affected tests 与 `npm --prefix video_renderer run build`；回执记录实际命令、退出码、pass/fail/skip、范围 diff 和未覆盖风险。完成时仅写 `READY_FOR_INDEPENDENT_P2_VERIFICATION` 并停止；P4 必须等待 P2 与 P3a 各自独立 PASS。
