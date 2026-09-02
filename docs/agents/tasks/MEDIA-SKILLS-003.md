# MEDIA-SKILLS-003：七 Skills 执行契约纠偏与机器校验

- Owner: MEDIA
- Status: CHANGES_REQUESTED
- Attempt: 2（返工）
- Priority: P0
- Depends on: `MEDIA-WO-002=APPROVED`, `CORE-EXEC-002=APPROVED`
- Worktree: `/mnt/d/workstation/projects/cs-board-media`
- Branch: `feat/mountain-media-work-orders`
- Base commit: `7bc8af9`

## Goal

把七个项目 Skills 从旧 Project/聊天参数/固定 Provider 说明纠正为“WebUI 已创建 Task，Skill 只用
task_id/run_id 和持久化输入执行”，并新增机器可运行的契约 linter，防止 `--script`、`--reference`、
`--tts-url` 等旧参数再次进入六工序说明。该切片不等待 Work Order 生产 DTO，也不虚构未实现命令。

## Authoritative references

- CORE CLI delivery `e1bc3d5` 的真实 `cli/csboard.py --help`；
- `docs/Mountain/05-skills-design.md`、`24-codex-six-stage-execution-contract.md`；
- `docs/agents/contracts/stage-work-order-v1.md`（已批准、尚未由生产代码实现）；
- 六阶段名称以 `csboard/application/pipeline.py` 为准。

## Allowed surfaces

- 七个 `skills/*/SKILL.md`；保留目录名 `script-segmenter`，本轮不做破坏性重命名；
- 新增 `scripts/validate_skill_contracts.py` 或等价确定性 linter；
- `tests/test_skill_contracts.py` 和仅供 linter 的小型静态 fixture；
- `docs/agents/reports/MEDIA-SKILLS-003.md`。

## Forbidden surfaces

- Python 生产内核、CLI、API、Schema、WebUI、Provider/媒体 adapter；
- 实际调用 LLM、IndexTTS、Whisper、imagegen、renderer、FFmpeg；
- 发明当前不存在的 work-order/import/accept CLI 并声称可执行；
- 把 API key、Provider URL、reference 绝对路径、完整文案或聊天路径写入 Skill；
- 合并、目录重命名或进入真实 E2E。

## Acceptance

1. 编排 Skill 明确起点是 WebUI 已保存的 `task_id/run_id`，不再创建 Project 或要求 request JSON
   携带 reference/TTS URL；
2. 六个 Stage Skill 的 stage_id、skill name、规范输入 Artifact、输出 Artifact 与当前代码/Schema一致；
3. 所有 stage run 示例统一为 `--task --run --stage --json`，retry 只额外传 unit/visual scope；
4. `visual-anchor-generator` 不传 `--script`；`voice-cloner` 不传 `--reference/--tts-url/--tts-mode`；
5. illustration Skill 如实说明当前 external candidate Gate 仍等待 CORE 实现，不得把候选文件当正式 manifest；
6. Skill 明确只读持久化参数/相对路径、结构化结果、事件和 Artifact，不从日志/聊天猜输入；
7. linter 解析 frontmatter 与命令块，验证 7 个 Skill、6 个规范 Stage、Artifact 映射、禁止词/旧参数、
   相对路径与“未实现能力不得宣称成功”；失败 fixture 必须证明 linter 会非零退出；
8. 测试必须执行 linter 行为，不得只用 `inspect.getsource` 或断言函数存在。

## Gates

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/validate_skill_contracts.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_skill_contracts.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check 7bc8af9...HEAD
! rg -n -- '--script|--reference|--tts-url|--tts-mode|创建或选择 Project|"reference_audio"\s*:\s*"/' skills
```

## Stop condition

提交并推送当前分支，报告列出逐 Skill 的 before/after、linter 规则、失败 fixture 证据和全量测试结果；
直接唤醒 `/root/pm` 后停止，不领取 MEDIA-E2E-003。

## Attempt 2 bounded correction

权威审核：`docs/agents/reviews/MEDIA-SKILLS-003.md`。保留七 Skills 已完成的 Task/Run、持久化输入、
旧参数移除和 linter 基础，只修正：

1. `visual-anchor-generator` 的输入是 persisted `script_preparation`、锚定开关和设置，不是自己的输出
   `planning.av-plan`；输出才是 `planning.av-plan`；linter 必须分开验证 inputs/outputs；
2. `illustration-generator` 在 external candidate Gate 未实现时不得展示或要求
   `stage retry ... --visual` 可执行；删除该命令并让 linter 在 Gate 未实现期间禁止它；
3. linter 的 Stage 映射使用明确 input/output 结构，不能仅以同一文件内出现 Artifact token 视为映射
   正确；至少新增两个失败 fixture 分别证明“自循环输入”和“未实现 retry”会非零；
4. 报告填入真实 delivery hash；全量 pytest 若超过合理时限，按测试目录分组运行并定位具体长耗时组，
   报告每组终态，不能只写“两次未结束”；
5. 不修改生产代码、CLI/API/WebUI，不进入 Work Order 实现或媒体调用。

门禁沿用 attempt 1，并额外要求：

```bash
! rg -n '输入 Artifact：`planning.av-plan`' skills/script-segmenter/SKILL.md
! rg -n 'stage retry .*generate-illustrations' skills/illustration-generator/SKILL.md
```

更新原报告并提交推送后，直接唤醒 `/root/pm`，停止。
