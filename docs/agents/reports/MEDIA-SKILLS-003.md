# MEDIA-SKILLS-003 Delivery

- Base: `7bc8af9`
- Delivery commit: recorded after this report is committed.
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
Skill directories, six canonical mappings, Artifact keys, canonical run/retry syntax, persistent
Task/Run/relative-path language, forbidden legacy tokens, and the unimplemented external Gate
disclosure. `tests/test_skill_contracts.py` executes it as a subprocess for the repository and for
`tests/fixtures/skill-contracts/bad/`; the latter has a legacy reference flag and exits non-zero.

| Command | Result |
| --- | --- |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/validate_skill_contracts.py` | exit 0, passed |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_skill_contracts.py` | exit 0, `2 passed in 0.36s` |
| forbidden-token `rg` gate | exit 0 (no matches) |
| `git diff --check` | exit 0 before commit |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | started twice at 2026-09-02; neither process produced a terminal result before delivery. This is a known gate incompleteness, not a pass claim. |

## Known gap

The Skills deliberately do not mention future Work Order/import/accept CLI commands as executable:
the approved contract is still not implemented. PM review must decide whether the non-terminating
full-suite runs require a follow-up environment/test investigation before merge.
