# M09-INFRA-ADAPTER-002-R-V — P2 独立复验

状态：dispatch_pending
Owner：verification（Claude Code `mimo-v2.5-pro / medium`，tmux `%60`）
模式：只读验证；冻结目标为 backend worktree

## Target and authority

- 目标工作目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`
- 实现回执：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend/docs/workmates/receipts/M09-INFRA-ADAPTER-002-R.md`
- 前置：`M09-INFRA-CONTRACT-001-R-V` PASS；权威 P2 合同为 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` P2。

独立复验 P2 adapter 契约，不能以实现者的 101-test 自检替代本轮结论。目标 worktree 含既有 Asset Provenance 差异；只记录 P2 scoped diff，绝不把全树脏状态误报为本票变更。

## Scope and checks

P2 范围：`csboard/adapters/remotion/`、直接 adapter port types、`tests/test_remotion_renderer_adapter.py`、`tests/test_infographic_storyboard_adapter.py`、`tests/test_infographic_contract_fixture.py`、`tests/test_infographic_domain.py` 与 `video_renderer/src/`。在开始和结束记录该范围的 `git -C <worktree> diff --name-only`，并运行：

```bash
cd /mnt/d/Workstation/Projects/cs-board-worktrees/backend
.venv/bin/python -m pytest -q tests/test_remotion_renderer_adapter.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py tests/test_infographic_domain.py
npm --prefix video_renderer run build
git diff --check
```

确认：只消费 P1 v1 storyboard/props；run-private props 与 finally cleanup；安全 argv；非空 MP4 仍须 ffprobe 容器/视频流/正时长/正尺寸才成功；subprocess non-zero/timeout/缺 node/坏 JSON/坏 props/probe failure 一律 fail-closed；路径、原始 stderr、环境变量与 secret 脱敏；无 `webapp.*` import；P2 不探测 P3a 工具链、不计算 readiness/`bootstrap_ready`，不设置 capability `supported`。

不得修改实现、测试、依赖、服务、配置、看板或既有回执；不得执行真实 render/创建任务/提交/推送。唯一允许写入为新 JSON 证据（先确保路径不存在）和本集成区新回执 `docs/workmates/receipts/M09-INFRA-ADAPTER-002-R-V.md`。运行：

```bash
./scripts/workmates verify --role verification --evidence <本轮新建 JSON 路径>
```

只有全部门禁、契约核验及 P2 scoped pre/post diff 均通过才可 PASS。结论只能是 PASS/FAIL/BLOCKED；无论结果都不得接受 P2 或解锁 P4。完成回执后停止。
