# MEDIA-SKILLS-003：七 Skills 执行契约纠偏与机器校验

- Owner: MEDIA
- Status: DISPATCHED
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
