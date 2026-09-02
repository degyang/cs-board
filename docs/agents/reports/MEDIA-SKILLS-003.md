# MEDIA-SKILLS-003 Delivery

- Base: `7bc8af9`
- Attempt 1 delivery: `eb2a985`; attempt 2 delivery: recorded after this report is committed.
- Scope: only seven `skills/*/SKILL.md`, a deterministic contract linter, its executable tests and
  static failing fixture. No production core, CLI, API, Schema, WebUI or media adapter changed.

## Skill correction

| Skill | Before | After |
| --- | --- | --- |
| `video-workflow` | Created/selected a Project and accepted request-file/provider details. | Starts from WebUI-persisted Task/Run and only coordinates the six stage IDs. |
| `visual-anchor-generator` | Took a full script CLI value and described a direct API start. | Uses only persisted preparation and canonical Stage CLI. |
| `voice-cloner` | Took reference file and TTS endpoint/mode flags. | Uses persisted audio/service settings; retry is Unit-scoped. |
| `storyboard-planner` | Retained old Skill upstream naming. | Declares canonical AV/timeline/style inputs and storyboard output. |
| `illustration-generator` | Described normal image output as immediately formal. | States the external candidate Gate is not implemented and cannot be claimed executable. |
| `visual-renderer` | Did not state accepted-artifact boundary. | Consumes accepted illustrations and persisted timing only. |
| `av-compositor` | Included optimistic success-shaped output. | Requires structured `validation.passed=true` before reporting success. |

Every Stage example is now `stage run --task --run --stage --json`; only voice, illustration and
render retries add their allowed Unit/Visual scope. All Skills say that persisted parameters,
run-root relative paths, structured results/events/Artifacts are the source of truth.

## Linter and test evidence

`scripts/validate_skill_contracts.py` parses frontmatter and command text. It checks exactly seven
Skill directories, six canonical mappings, explicit declared inputs versus outputs, canonical
run/retry syntax, persistent Task/Run/relative-path language, forbidden legacy tokens, and the
unimplemented external Gate disclosure. `tests/test_skill_contracts.py` executes it as a subprocess
for the repository and three negative fixtures: legacy reference flag, visual-anchor self-cycle,
and an unimplemented illustration retry.

| Command | Result |
| --- | --- |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/validate_skill_contracts.py` | exit 0, passed |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_skill_contracts.py` | attempt 2 exit 0, `4 passed in 0.54s` |
| forbidden-token `rg` gate | exit 0 (no matches) |
| `git diff --check` | exit 0 before commit |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | not a pass claim: PM had already observed it exceed 176.99s after 223 passed/4 skipped. Attempt 2 isolated the long group with `timeout 25`: `tests/test_asset_repository.py` exit 0 (6 passed), `tests/test_av_timing.py` exit 0 (5 passed), and `tests/test_backend_runtime_17.py` exit 124 after 9/14 tests. Verbose evidence identifies `test_smoke_startup_failure_path` as the current hang point. |

## Known gap

The Skills deliberately do not mention future Work Order/import/accept CLI commands as executable:
the approved contract is still not implemented. The unrelated full-suite blocker is now localized to
`tests/test_backend_runtime_17.py::test_smoke_startup_failure_path`; this task does not modify its
production/runtime surface.
