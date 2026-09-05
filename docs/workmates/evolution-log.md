---
status: trial
updated: 2026-09-05
---

# Workmates Evolution Log

## Candidate: ticketed control plane replacing prompt-driven tmux operation

- Date: 2026-09-05
- Scope: project
- Confidence: high
- Situation: long-lived PM/worker Claude sessions were asked to plan, implement, optimize full pytest, verify, and report through terminal text.
- Expected / actual: expected continuous dispatch; actual state repeatedly became stale inputs, duplicated polling panes, self-acceptance, and scope expansion from M09 into bootstrap caching.
- Evidence: M09 receipts stopped at 13:27; the `20-gate` worker remained active for hours without `m09-round9` receipt, repeatedly ran full pytest, and expanded to `webapp/mountain_server.py`/service probing.
- Occurrences / impact: repeated throughout the current session; user had to request progress and re-dispatch manually.
- Proposed narrow change: shared `board.md` is the only state source; short, file-backed assignments; one worker ticket; separate verifier; 15-minute stale threshold; deterministic supervisor only observes.
- Trial and metric: run M09-GATE-001; measure time from dispatch to worker receipt, verifier receipt, and number of manual user nudges. Target: each handoff has a board update and receipt within 15 minutes.
- Approval needed: none for this project-local trial; user approval remains required for permanent POS skill changes.
- Result: trial
- Rollback point: remove the three project-local control-plane files and return to manual operation.
