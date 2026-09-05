---
status: active
updated: 2026-09-05
mode: recover-evolve
---

# CS Board WebUI → Dynamic Infographic Team Contract

## Stage goal

第一阶段先完成并稳定展示 `http://127.0.0.1:5182/settings/voice-alignment`：名称为“本地服务”，Whisper 仅属于工具链，页面采用预置音色式左侧列表/右侧预览，并可真实新增、编辑和探测。其他 WebUI 基准对齐由用户驱动，不自行扩展。第一阶段由用户可见验收后，团队将工作重点切换到动态信息图规划与门禁收敛。

## Source of truth

- Requirements: `docs/Mountain/29-voice-provider-and-infographic-plan.md` §§5–6
- Work breakdown: `docs/Mountain/29-m09-infographic-work-breakdown.md`
- Shared board: `docs/workmates/board.md`
- Assignments: `docs/workmates/assignments/`
- Evidence: `docs/workmates/agent-receipts/`

## Team

| Role | Runtime | Capability | Authority | Availability |
| --- | --- | --- | --- | --- |
| supervisor | deterministic tmux/status script | n/a | detect stale state, never implement or accept | active |
| pm | Codex | standard | assign, consume verifier evidence, accept | active, non-blocking |
| worker_frontend | Claude Code | standard | finish the bounded WebUI outcome | active only with a ticket |
| tester_frontend | Codex | standard | independently verify browser-visible behavior and gates | after worker receipt |
| worker_env | Claude Code | standard | keep exactly one backend and one WebUI service | active only with a ticket |
| worker_backend | Codex | standard | dynamic infographic planning/implementation after WebUI acceptance | deferred |

## Workflow

`backlog → working → verification → acceptance → done`

- A worker owns exactly one `working` item.
- A worker may not validate or accept its own result.
- No new worker is created while an executable item lacks an owner.
- A ticket without a board update or receipt for 15 minutes is stale and must be stopped, split, or reassigned.
- Three repeated failures of the same ticket enter `arbitration`; no automatic scope expansion.
- Codex and Claude Code use project-scoped bypass/skip permissions only in this tmux session, with medium effort. High or above requires user approval.

## Definition of done for WebUI stage

- 5182 serves the current `web-v2` workspace from exactly one Vite process; 8000 uses the project `.venv` and exactly one backend process.
- The local-services page visibly provides list/detail preview, add, edit and real probe; Whisper is absent there and remains in toolchain.
- Frontend focused tests, full frontend tests and build exit 0 without skip.
- A Codex tester writes an independent PASS / FAIL / BLOCKED receipt.
- PM records acceptance and opens the dynamic infographic planning task. No commit or push without user instruction.

## Boundaries

- Do not broaden WebUI baseline work beyond the user-listed local-services outcome.
- Do not open the dynamic-infographic submission UI before its own gates.
- Do not delete assertions, add skip markers, or claim pre-existing failures close a gate.
- Do not change product requirements, secret policy, model capability, branch/merge state, or external services without user direction.
