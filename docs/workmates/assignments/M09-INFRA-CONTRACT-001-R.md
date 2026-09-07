# M09-INFRA-CONTRACT-001-R — P1 契约冻结续作

状态：dispatch_pending
Owner：backend（Codex `gpt-5.6-terra / medium`）
工作目录：`/mnt/d/Workstation/Projects/cs-board`

## Authority

- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` P1
- independent PASS: `docs/workmates/receipts/M09-INFRA-PLAN-002-R-V.md`
- historical implementation evidence: `docs/workmates/receipts/M09-INFRA-CONTRACT-001.md`

## Scope

Complete or reconcile only P1's current domain/props/fixture contract within
the plan's allowed P1 files: `csboard/domain/infographic.py`, immediately
adjacent domain schema/validation or port types, `video_renderer/src/types.ts`,
and direct P1 fixtures/tests. Preserve all unrelated diffs. Do not change
pipeline, commands/API/CLI, renderer adapter implementation, capabilities,
legacy/webapp, voice UI, services, configuration, task submission, or any
real-render behavior.

Use the existing P1 receipt only as evidence, not authority. Independently
inspect the actual current diff and ensure the P1 invariants are met: V1
versioning and stable IDs; exactly-one-page-per-Voice-Unit strategy; timing and
frame semantics; run-relative-only artifact refs; rejection of empty/overlap/
zero duration/unknown node/missing visual/absolute path/secret data; golden
fixtures; TypeScript props check; hash-only manifest/evidence inputs. Run
affected P1 tests and video-renderer typecheck. Write only
`docs/workmates/receipts/M09-INFRA-CONTRACT-001-R.md`; do not self-verify or
advance P2/P3a. Stop at `READY_FOR_INDEPENDENT_P1_VERIFICATION`.
