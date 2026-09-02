# CORE-WO-003：Stage Work Order v1 后端骨架

- Owner: CORE
- Status: CHANGES_REQUESTED
- Attempt: 3（返工）
- Priority: P0
- Depends on: `CORE-EXEC-002=APPROVED`, `MEDIA-WO-002=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- Branch: `feat/mountain-assets-settings-backend`
- Base commit: `e1bc3d5`

## Goal

按已批准 `stage-work-order-v1.md` 落地 WO 领域 DTO、持久化、状态读取和只读 API/CLI 骨架，使六阶段
都能从 persisted Task/Run/ExecutionPlan 生成确定性工作单，但不实现外部插画成果提交事务。

## Authoritative contract

- `/mnt/d/workstation/projects/cs-board-media/docs/agents/contracts/stage-work-order-v1.md`
- MEDIA contract commit: `7bc8af9`
- `docs/Mountain/24-codex-six-stage-execution-contract.md`
- `docs/agents/reviews/MEDIA-WO-002.md`

## Allowed surfaces

- `csboard/domain/`：新增 WO DTO、校验和状态转换；
- `csboard/ports/`、`csboard/adapters/filesystem/`：WO repository/持久化；
- `csboard/application/`：确定性生成、读取和状态投影；
- `webapp/mountain_*_api.py`：只读 WO API；
- `cli/csboard.py`：`work-order show` 只读命令；
- `schemas/mountain/`：仅本任务 DTO 必需的新 schema；
- 对应后端测试与 `docs/agents/reports/CORE-WO-003.md`。

## Forbidden surfaces

- `web-v2/`、`skills/`、Legacy API、Provider/TTS/Whisper/Renderer/FFmpeg；
- 外部 candidate import/validate/accept/reject/retry 的副作用实现；
- 图片生成、媒体执行、Secret 或绝对路径进入 WO；
- 合并、发布或顺手重构既有 Pipeline。

## Acceptance

- 六阶段 envelope、相对路径校验、fingerprint、revision 与状态机具备真实持久化和行为测试；
- Application 是唯一状态写入者，API/CLI 不复制决策；
- `work-order show` 可被 Skills 消费，响应不含 Secret、Provider URL、绝对路径或完整文案；
- 不修改 WebUI，不执行付费/本地媒体生成，不实现 candidate accept，不合并分支。

- 六个 Stage 在同一 Task/Run 下生成稳定且 schema-valid 的 WO；相同输入返回相同 work_order_id/fingerprint；
- 上游 revision/hash 或参数变化产生新 revision，并使旧 WO `stale`；
- 所有路径经 run-root 相对路径校验，argv 不经 shell；
- `work-order show --task --run --stage --json` 与只读 API 返回同一事实；
- 未实现的外部命令必须显式报告 capability/next action，不得假装成功。

## Gates

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_stage_work_orders.py tests/test_mountain_contracts.py tests/test_cli_csboard.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check e1bc3d5...HEAD
! rg -n '/mnt/|[A-Za-z]:\\\\|api[_-]?key|tts[_-]?url' tests/fixtures/stage-work-orders
```

必须新增真实行为测试，而不是 `inspect.getsource`/字符串存在性测试。报告记录 DTO 决策、路径树、
API/CLI 示例、定向与全量结果、已知未实现的 candidate Gate。

## Stop condition

完成上述后提交并推送当前分支，写 `docs/agents/reports/CORE-WO-003.md`，直接唤醒 `/root/pm`，
停止。不得进入 candidate Gate、WEB 或 E2E。

## Attempt 2 bounded correction

权威审核：`docs/agents/reviews/CORE-WO-003.md`。保留 attempt 1 的 DTO、filesystem 持久化、API/CLI
入口与安全投影，只修正以下行为：

1. `ready` 必须表示所需上游 Artifact 全部存在且 `succeeded`；缺失任一必需输入时，API/CLI 返回
   稳定 `DEPENDENCY_NOT_READY`（含缺失 artifact keys），不落盘一个伪 `ready` WO；不得临时扩展已
   冻结状态枚举；
2. 对当前真实可执行的非外部 Stage，`commands.run` 提供结构化 argv、idempotency key 和
   preconditions，`next_action` 精确表示 run 或 manual trigger；不得统一返回
   `CAPABILITY_NOT_AVAILABLE`；
3. `generate-illustrations` 在 candidate Gate 尚未实现期间必须明确保留 unavailable external action，
   不得把当前空 command 冒充可执行，也不得实现 candidate 副作用；
4. 插画 `output_directory` 必须是
   `manual/illustrations/candidates/<work_order_id>`，ID 与目录禁止使用两套 hash；
5. 强化 schema，使 identity、scope、input artifact、commands/argv、next_action 和相对路径约束能拒绝
   缺字段/错类型/绝对路径/额外未知字段，而不是只验证顶层字段存在；
6. 替换错误的六 Stage“全 ready”测试：逐阶段验证缺失依赖、补齐依赖后 ready/manual、结构化 run
   command、插画 ID/path 一致、API/CLI 错误一致和无副作用不落盘；
7. 继续禁止 WebUI、Skills、candidate Gate、媒体执行和架构扩张。Application 直连 filesystem
   repository 记为后续依赖倒置风险，本返工不要求顺手重构。

必须复现：

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_stage_work_orders.py tests/test_mountain_contracts.py tests/test_cli_csboard.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check e1bc3d5...HEAD
```

更新原报告追加 attempt 2 证据，提交并推送后直接唤醒 `/root/pm`，停止。

## Attempt 3 final bounded correction

Attempt 2 delivery `d6a73c0` 已修正缺失依赖、run command、插画 ID/path 与 schema；只剩两项：

1. `expected_outputs` 必须按规范输出集合：`clone-voice` 同时包含
   `audio.voice-manifest`、`timing.timeline`；`compose-video` 同时包含
   `output.final-video`、`output.final-manifest`；其余 Stage 保持规范 key。测试逐 Stage 断言完整集合；
2. 依赖消失使 current WO stale 后，恢复相同 hash 的 Artifact 不得返回旧 stale。必须创建可执行的新
   revision，并产生不复用旧 revision 副作用的 work_order/idempotency identity；测试覆盖
   `ready → dependency missing/stale → same artifact restored → new ready revision`。

不得修改其他语义，不进入 `CORE-CAP-004`。定向与全量门禁沿用 attempt 2；完成后追加报告、提交
推送并直接唤醒 `/root/pm`。
