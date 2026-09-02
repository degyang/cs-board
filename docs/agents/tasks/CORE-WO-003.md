# CORE-WO-003：Stage Work Order v1 后端骨架

- Owner: CORE
- Status: DISPATCHED
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
