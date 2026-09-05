# M09-GATE-001 — PM corrective-path decision

## Inputs

- Worker receipt: `docs/workmates/receipts/M09-GATE-001.md`
- Work board: `docs/workmates/board.md`
- Existing dirty implementation only; do not discard unrelated changes.

## Decision required

Decide whether the proposed minimal production fix is safe:

> Prevent module-level/default `~/.csboard` startup from populating the process-global seed cache. Explicit `create_app(tmp_path)` callers must create/cache only a clean, deterministic seed.

The stale home-directory `mock-llm` must never contaminate test/app factory calls with an explicit data directory.

## Constraints

- Do not alter `web-v2`.
- Do not delete the user's `~/.csboard` files.
- Do not use test-only cache resets as the final production remedy.
- Do not commit.
- This is a decision/assignment task, not an implementation task.

## Required output

Write `docs/workmates/receipts/M09-GATE-001-DECIDE.md` with:

1. decision (`approve minimal fix` or `block`);
2. precise intended behavior and accepted file scope;
3. verification criteria for the tester;
4. next owner.

Then update only the matching row in `docs/workmates/board.md`.
