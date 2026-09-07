# M09-ACTIVATE-003 receipt

Verdict: **READY_FOR_VERIFY**

Target commit: `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21` (working tree intentionally contains concurrent, uncommitted M09 work).

## Changes

- Added `csboard/application/service_capabilities.py`: interprets only the primary capability plus a non-empty string-only `config.capabilities` list; it de-duplicates entries and keeps `audio_generation` compatible with `speech_synthesis`.
- `CapabilityService` uses that same declaration for provider and infographic-bootstrap checks. The infographic bootstrap no longer checks an automatic image service; its existing external-stage gate remains fail-closed. Whiteboard retains its image-service requirement.
- `ServiceResolver` uses the same declaration and projects a secondary match onto the requested `ServiceDefinition.capability`, so the factory builds a text adapter for the Codeplan text capability.
- Added the direct multi-capability regression coverage and adjusted the existing infographic-bootstrap diagnostics fixture to omit the now-external image prerequisite.

No service settings, Secrets, activation pointer, frozen outputs, frontend, board, real provider request, renderer, or real task was changed or run.

## Checks

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_m09_activate_003.py tests/test_service_resolver.py tests/test_dynamic_provider_factory.py tests/test_infographic_capability.py tests/test_infographic_activation_projection.py tests/test_capabilities_api.py` | 0 | 64 passed |
| `.venv/bin/python -m pytest -q tests/test_create_options_infographic.py tests/test_infographic_task_creation.py tests/test_task_create_contract_30.py tests/test_cli_engine_validation.py` | 0 | 58 passed (one dependency deprecation warning) |
| `.venv/bin/python -m compileall -q csboard/application/service_capabilities.py csboard/application/capabilities.py csboard/application/service_resolver.py` | 0 | compiled |
| `git diff --check` | 0 | no whitespace errors |
| `./scripts/workmates verify --role verification --evidence …/M09-ACTIVATE-003-workmates.json --timeout 60` | 0 | PASS; release/runtime guard 12 passed |

Workmates evidence: `.workmates-evidence/M09-ACTIVATE-003-workmates.json`.

The complete serial backend gate was not run: the targeted capability, activation, resolver, provider-factory, create-options, and task-creation suite is the relevant bounded gate in this concurrently modified worktree. Independent verification should target the frozen implementation diff.
