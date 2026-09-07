# M09-INFRA-PLAN-002-R — P3a 职责单一真源修订

状态：working
Owner：backend（Codex `gpt-5.6-terra / medium`）
工作目录：`/mnt/d/Workstation/Projects/cs-board`

## Authority

- `docs/workmates/assignments/M09-INFRA-PLAN-002.md`
- `docs/workmates/receipts/M09-INFRA-PLAN-002-V.md` (FAIL)
- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`

## Goal and scope

Resolve only the recorded P3a contradiction. Make the plan's P3a definition,
its entry/exit criteria, reason-code ownership, P4 merge inputs, P6 entry, DAG
and next queue agree on one executable contract. P3a must actually diagnose
the bootstrap/toolchain items named by the plan (Node/script/locked
dependencies/browser/FFmpeg/ffprobe plus declared service/config readiness),
be read-only/fail-closed, perform no render, and never itself make the public
capability available. Keep P3b exclusively evidence activation after P6.

May write only `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`
and `docs/workmates/receipts/M09-INFRA-PLAN-002-R.md`. Do not change product
code/tests/config, run real render, create a task, open submission, alter
voice UI, commit, or push. Preserve all unrelated diffs.

## Done predicate

The updated text must eliminate every require/prohibit conflict identified in
the FAIL receipt and retain the existing fail-closed reason codes and queue:
P1 only after a new independent plan PASS; P2/P3a only after P1 PASS;
P4→P5→P6→P3b thereafter. Run `git diff --check`; receipt maps each verifier
finding to exact plan text and stops at READY_FOR_INDEPENDENT_PLAN_VERIFICATION.
