# M09-INFRA-CONTRACT-001-R-V — P1 契约独立复验

状态：dispatch_pending
Owner：verification（Claude Code `mimo-v2.5-pro / medium`）
模式：只读验证；目标为当前集成区

## Goal

独立复验 `M09-INFRA-CONTRACT-001-R` 的 P1 契约。消费其自检回执和
`M09-INFRA-PLAN-002-R-V` 的前置 PASS，但不以它们替代本轮复验。只给出
P1 PASS/FAIL/BLOCKED；P2、P3a、真实渲染、capability 或 submission 均不在本任务授权内。

## Target and scope

- 工作目录：`/mnt/d/Workstation/Projects/cs-board`（当前集成区；它是脏工作树，不能把全树 hash 当作冻结提交）。
- P1 范围仅限 `csboard/domain/infographic.py`、直接相邻的 domain schema/validation 或 port types、`video_renderer/src/types.ts`、以及直接 P1 fixtures/tests。
- 核对：V1 versioning 和稳定 ID；exactly-one-page-per-Voice-Unit；毫秒和 frame 的 start-inclusive/end-exclusive 语义；run-relative-only artifact refs；拒绝空、重叠、零时长、未知 node、缺 visual、绝对/逃逸路径和 secret；golden fixtures；strict TS props；manifest/evidence 仅 hash 输入。

## Required independent evidence

在开始和结束时记录 P1 scoped files 的 `git diff --name-only`/`git diff --check` 结果，确认本次验证没有写入目标实现，也没有发生 P1 范围漂移。独立运行：

```bash
.venv/bin/python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py
npm --prefix video_renderer run build
git diff --check
```

如发现缺口，给出最小可复现的具体反例、失败命令和受影响 P1 不变量。不得修改实现、测试、服务、配置、看板或既有回执；不创建 Task、不 render、不 commit/push。可只写新回执
`docs/workmates/receipts/M09-INFRA-CONTRACT-001-R-V.md`，并通过：

```bash
./scripts/workmates verify --role verification --evidence <本轮新建的本地 JSON 路径>
```

验收 predicate：仅当所有上述门禁通过、P1 语义逐项可由代码/fixtures证实，且 scoped diff 在验证前后相同，才可写 PASS。完成回执后停止，等待 PM 消费；绝不自行推进 P2/P3a。
