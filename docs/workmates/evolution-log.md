---
status: trial
updated: 2026-09-05
---

# Workmates Evolution Log

## Trial: fixed-role idle grace period and selective reclaim

- Date: 2026-09-07
- Scope: CS Board tmux runtime only.
- Trigger/evidence: user explicitly corrected two consecutive reclaim mistakes. Completed task clients were reclaimed immediately while empty launcher shells remained; after the empty shells were removed, a same-role verification client had to be recreated and repeat startup, permissions, and context loading.
- Root cause classification: reclaim policy did not distinguish fixed-role clients, launcher shells, temporary diagnostics, and product services; “task complete” was incorrectly treated as equivalent to “reclaim now.”
- Narrow mechanism: fixed frontend/backend/verification clients receive a 30-minute idle grace period and may be reused for same-role work; temporary/non-role diagnostics are reclaimed after receipt consumption; empty launcher shells are not retained; service panes are governed by exact PID/port ownership. Reclaim requires no pending task or confirmation and a consumed receipt.
- Trial metric: during the next collaboration cycle, count same-role cold starts, repeated permission prompts, idle shells left behind, and accidental service/user-session impact. Target: zero empty launcher shells, zero immediate fixed-role destroy/recreate cycles, and zero reclaim of active services or user sessions.
- Rollback: remove the 30-minute grace period if measured idle cost outweighs startup/context cost; retain the role/type distinction and exact-target safety checks.
- Result: trial; current `M09-ACTIVATE-004-V` verification client is the first application and will become fixed-role idle after completion rather than being immediately destroyed.

## Candidate: baseline-aware fresh-session dispatch preflight

- Date: 2026-09-06
- Scope: CS Board workmates runtime and task contracts.
- Trigger/evidence: `M09-G0-LIFECYCLE-001` was dispatched to an already-completed `%59` P2 client. Main and backend worktree both reported `e34ba6e`, but that commit tracks legacy `webapp/mountain_*`; the required main uncommitted `backend/` migration and assignment path were absent in the worktree. The inherited client consequently found legacy files and proposed a legacy diagnostic before PM stopped it. The canceled command is not evidence. The worker receipt records `BLOCKED — BASELINE_MISMATCH`.
- Root cause classification: baseline identity was inferred from HEAD alone; assignment reachability and target-file hashes were not checked; duplicate-role launcher rejection was worked around by reusing a completed client via terminal input.
- Proposed narrow mechanism: before every launch, a project-local preflight must (1) resolve the selected worktree, (2) require the assignment file to be reachable there, (3) require all declared target paths to exist and match an authority snapshot/hash, and (4) require the prior client for that role to be retired before a fresh launch. A failed check leaves the board `BLOCKED_BASELINE_AND_SESSION_REUSE`; it never falls back to legacy paths or `send-keys` reuse.
- Trial: apply this preflight to G0's baseline handoff snapshot before its next launch; verify assignment reachability, five recorded target hashes, a new pane ID, and an acknowledgement receipt before any command runs.
- Rollback: remove only the preflight wrapper/task-template requirement if a transactional launcher gains equivalent verified target binding; retain historical receipts and existing safety gates.

## Trial: one project-local product storage contract

- Date: 2026-09-06
- Scope: CS Board product runtime only; developer-tool directories are excluded.
- Trigger: user explicitly rejected ambiguous storage possibilities and required one durable rule.
- Previous failure: configuration and task state were split across `~/.csboard`, repository `.webapp`, `.task-packages` and output packages, making the active data root ambiguous and causing service data to appear missing after restart.
- Narrow mechanism: code, launcher, CLI and current runtime contract now use `settings/` for configuration/assets and `outputs/` for task data/results; legacy product roots are archived under `archive/legacy-runtime/` after copy and integrity checks.
- Trial evidence: encrypted key pair and nine service definitions migrated; backend gate passed all four shards with 914 tests and 3 subtests, frontend passed 447 tests and build, project verifier returned PASS, and live 8000 loaded nine services including both MiMo entries.
- Rollback: stop services, restore the prior directory/import diff, and recover the paired legacy data root from `archive/legacy-runtime/`; never restore only `secrets.enc` without its matching `master.key`.
- Limitation: this trial does not implement the separately recorded per-asset provenance and interactive regeneration requirement.

## Candidate: ticketed control plane replacing prompt-driven tmux operation

- Date: 2026-09-05
- Scope: project
- Confidence: high
- Situation: long-lived PM/worker Claude sessions were asked to plan, implement, optimize full pytest, verify, and report through terminal text.
- Expected / actual: expected continuous dispatch; actual state repeatedly became stale inputs, duplicated polling panes, self-acceptance, and scope expansion from M09 into bootstrap caching.
- Evidence: M09 receipts stopped at 13:27; the `20-gate` worker remained active for hours without `m09-round9` receipt, repeatedly ran full pytest, and expanded to `backend/mountain_server.py`/service probing.
- Occurrences / impact: repeated throughout the current session; user had to request progress and re-dispatch manually.
- Proposed narrow change: shared `board.md` is the only state source; short, file-backed assignments; one worker ticket; separate verifier; 15-minute stale threshold; deterministic supervisor only observes.
- Trial and metric: run M09-GATE-001; measure time from dispatch to worker receipt, verifier receipt, and number of manual user nudges. Target: each handoff has a board update and receipt within 15 minutes.
- Approval needed: none for this project-local trial; user approval remains required for permanent POS skill changes.
- Result: trial
- Rollback point: remove the three project-local control-plane files and return to manual operation.

## Trial: tmux dispatch acknowledgement and liveness checks

- Date: 2026-09-06
- Scope: CS Board `cs-board-team` runtime and supervisor monitoring only.
- Trigger: user twice identified that PM/worker instructions were visibly left in the TUI input box although the supervisor had reported them as dispatched or healthy.
- Expected / actual: expected `tmux send-keys ... Enter` to submit work; actual long pasted prompts remained unsubmitted in `%52`, `%58`, `%59`, and `%60`. PID presence and HTTP 200 heartbeats hid the stalled collaboration queue, while `./scripts/workmates status` without `--session cs-board-team` queried the wrong default session.
- Root causes: dispatch was considered successful after key injection rather than agent acknowledgement; monitoring checked process/service existence but not assignment consumption; board `working` rows were not reconciled with already-written receipts and pane output.
- Narrow mechanism under trial: always call status with the configured session; after every tmux dispatch, require a bounded post-check showing one of (a) agent response, (b) tool execution with changing output, or (c) a new task receipt. Text merely visible after the prompt marker is an unsubmitted dispatch and must be retried with `C-m`. A generic `Working` label is insufficient when the pane is actually waiting at an edit/permission confirmation; explicit confirmation prompts are monitored as blocked interaction. For each board `working` item, compare owner pane output and receipt existence; a live PID alone is not healthy evidence.
- Failure response: if acknowledgement is absent, retry the submit key once and recapture the pane; if still absent, report dispatch failure and recover the pane instead of changing board state or claiming progress.
- Trial evidence: the PM recovery instruction, backend `M09-INFRA-PLAN-002-R` dispatch, frontend recovery acknowledgement, and verifier `PRESET-VOICE-UX-004-V` dispatch initially remained at prompts; explicit `C-m` produced agent acknowledgements and concrete file/test reads in all observed Codex/Claude panes. Backend later stopped at an authorized file-edit confirmation despite showing `Working`; selecting the task-authorized edit resumed execution. PM also reconciled stale board rows and created bounded assignments.
- Metric: zero board transitions to `working` without post-dispatch acknowledgement; no stable heartbeat when any `working` owner lacks agent response/tool activity/receipt movement for the observation interval.
- Rollback: remove this project-local monitoring rule if the terminal client gains a transactional dispatch/acknowledgement API; do not weaken task, verification, or acceptance gates.
- Result: trial; current recovery remains under observation.
