# CORE-RUNTIME-007 test report

Status: FAIL

Validated delivery: `09009f103439d5d17e44fc6d30ebc1dfb1b1ec8e`  
Contract: `docs/agents/tasks/CORE-RUNTIME-007.md`  
Base: `de57fab`

## Contract gates

```text
$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
506 passed, 5 skipped, 4 warnings, 3 subtests passed in 96.19s (0:01:36)
exit: 0
```

This is a normal pytest exit and demonstrates that the reported full-suite
timeout is not present in this delivery. It does not satisfy Acceptance 2:
the contract requires the full suite to exit with **no skips**, while this run
has five skips.

```text
$ git diff --check de57fab...09009f103439d5d17e44fc6d30ebc1dfb1b1ec8e
docs/Mountain/25-ccb-execution-plan-final-correction.md:3: trailing whitespace.
docs/Mountain/25-ccb-execution-plan-final-correction.md:4: trailing whitespace.
docs/Mountain/25-ccb-execution-plan-final-correction.md:5: trailing whitespace.
docs/Mountain/25-ccb-execution-plan-final-correction.md:6: trailing whitespace.
docs/Mountain/25-ccb-execution-plan-final-correction.md:7: trailing whitespace.
docs/Mountain/27-ccb-execution-plan-recovery.md:3: trailing whitespace.
docs/Mountain/27-ccb-execution-plan-recovery.md:4: trailing whitespace.
docs/Mountain/27-ccb-execution-plan-recovery.md:5: trailing whitespace.
exit: 2
```

The required diff gate fails. The base-to-delivery diff also contains changes
outside the task's allowed runtime/test/report surfaces, including Work Order,
capability, CLI, webapp, schema, and Mountain documentation changes.

## Observed cleanup

Immediately after the full suite, `pgrep -af 'pytest|run_mountain_backend.py'`
reported only the shell executing that inspection; there was no test-owned
pytest or `run_mountain_backend.py` process. Listener inspection found no
listener on ports 8765--8768. `/tmp` contained no `csboard-sequential-*` or
`csboard-backend-*` directory.

## Verdict

FAIL. Do not resume `MEDIA-PREFLIGHT-004` from this validation. The full-suite
hang appears recovered, but the delivered commit fails two explicit CORE-RUNTIME-007
contract conditions: no-skips full pytest evidence and a clean required diff
gate.
