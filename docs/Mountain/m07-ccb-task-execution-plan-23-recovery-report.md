# M07 CCB Task Execution Plan 23 Recovery Report

Implementation commit: `971494e150adf5321572505e85642687a3168487`

## Evidence

- `tests/test_task_execution_plan_23.py`: **40 passed**.  It has parameterized
  domain and HTTP invalid-input matrices; real temporary-dir API, reconstructed
  Repository/Application, and CLI `subprocess` readback; unsaved/old-request
  read-only SHA-256 snapshots; six production checkpoint failure injections;
  concurrent transaction-combination proof; start/NotFound directory snapshots;
  API/CLI/event/log/diagnostic redaction; error-contract details precedence; and
  required/optional/default/priority SecretResolver cases.
- `tests/test_service_registry.py tests/test_service_resolver.py`: **21 passed**.
- Required runtime canary
  `test_smoke_checker_failure_path`: **1 passed in 3.08s**.
- Final full gate: **484 passed, 5 pre-existing skipped, 0 failed, 4 warnings,
  3 subtests passed in 86.64s**.  It was run with the required `timeout 180s`
  and unset `PYTHONPATH` / `CSBOARD_ALLOW_PLAINTEXT_SECRETS` environment.
- `compileall csboard webapp cli scripts`, `git diff --check`, the execution-plan
  forbidden-string gate, and the Resolver-private-access gate completed normally.

## Resolver and safety correction

`ServiceResolver.resolve()` now returns only an enabled service whose required
Secrets are readable.  `resolve_configured()` is the explicit public selection
method for configuration views.  `MountainCommands` uses only the public
Resolver method and no longer reads `_registry`.  Secret-store errors fail
closed without exposing a secret or backend exception.  Diagnostic export no
longer copies script preparation, and telemetry redacts submitted script and
reference-byte fields.

## Runtime-hang investigation and cleanup

The mandated isolated failure-path test passed.  The complete runtime file was
then run in order (**14 passed in 27.84s**), followed by the exact success/failure
smoke pair (**2 passed in 11.36s**).  During a verbose full run, the observed
short-lived `smoke_real_backend_contract.py` and launcher PIDs were child
processes of the active test and exited through their existing cleanup path;
there was no remaining PID, port listener, altered environment, or temporary
runtime directory after completion.  A final independent full run reproduced a
normal 86.64-second exit, so there is no reproducible pytest hang or lifecycle
root cause left to mask with a timeout.  No skip was added and no assertion was
removed.

## Transaction / DTO matrix

Each request/task/reference backup-or-install checkpoint restores the exact old
directory SHA-256 revision, including script, reference bytes, preparation, and
execution plan.  Concurrent distinct script/reference/plan saves end with all
four facts belonging to one committed transaction.  POST, GET inputs,
reconstructed application, and real CLI JSON return the same canonical plan.

Working tree was clean after the implementation commit before this report was
added.  This report is submitted separately; it does not assert audit approval.
