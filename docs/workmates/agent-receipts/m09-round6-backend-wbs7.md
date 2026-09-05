# WBS-7: Infographic E2E Tests — Receipt

## Deliverable

`tests/test_infographic_e2e.py` — 7 tests across 4 test classes.

## Tests Implemented

### 1. TestInfographicPipelineFakeE2e
- **test_infographic_pipeline_fake_e2e**: Creates a task with `engine=INFOGRAPHIC_REMOTION`, mocks all 6 pipeline stage executors, runs the full pipeline via `PipelineOrchestrator.run_pipeline`, verifies all stages complete. For `render-visuals`, lets the real `_exec_render_visuals` code run to verify it constructs `RemotionRendererAdapter` (not `WhiteboardRendererAdapter`). Pre-creates timeline, storyboard, and illustration-manifest artifacts. Verifies `render.manifest` artifact is committed.

### 2. TestInfographicCapabilityMissingNode (2 tests)
- **test_infographic_capability_missing_node**: Patches `_detect_remotion_readiness` to return `(False, NODE_NOT_FOUND)`, verifies `CapabilityService.snapshot()` reports `supported=False` with `reason_code=NODE_NOT_FOUND`.
- **test_infographic_capability_missing_node_create_task**: Verifies `create_task` raises `DomainError` with `CAPABILITY_NOT_AVAILABLE` code containing `NODE_NOT_FOUND`.

### 3. TestInfographicErrorSanitization (2 tests)
- **test_infographic_error_sanitization**: Creates an infographic task, pre-creates artifacts, constructs a real `RemotionRendererAdapter` with a mocked `subprocess.run` that returns stderr containing absolute Windows/Unix paths and API keys. Runs through the pipeline orchestrator. Verifies the error message in the pipeline result does NOT contain `C:\Users`, `admin`, `/home/user`, `.ssh`, `sk-abc123secretvalue`, or `tok_xyz789`.
- **test_remotion_adapter_sanitizes_stderr**: Unit-tests `RemotionRendererAdapter._sanitize_error` with various dirty strings containing paths and secrets.

### 4. TestWhiteboardStillWorks (2 tests)
- **test_whiteboard_still_works**: Creates a whiteboard task, pre-creates artifacts, calls `_exec_render_visuals` with mocked `service_resolver` and `provider_factory`. Verifies `service_resolver.resolve("rendering")` was called and `provider_factory.create_adapter` was used (whiteboard path). Verifies `task.engine == Engine.WHITEBOARD`.
- **test_whiteboard_full_pipeline_unaffected**: Runs the full 6-stage whiteboard pipeline with mocked executors and whiteboard adapter routing. Verifies all stages complete and the whiteboard adapter (not RemotionRendererAdapter) was used.

## Verification

```
$ python -m pytest tests/test_infographic_e2e.py -v
7 passed in 1.12s

$ python -m pytest tests/test_infographic_task_creation.py tests/test_remotion_renderer_adapter.py tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_capability.py tests/test_create_options_infographic.py tests/test_no_legacy_imports.py tests/test_cli_capabilities.py tests/test_infographic_e2e.py -v -q
109 passed, 1 warning in 5.08s
```

No regressions. No existing files modified. No webapp imports. No real subprocess/Node/Remotion execution.

## Constraints Met

- ONLY `tests/test_infographic_e2e.py` created
- ALL subprocess/Remotion calls mocked — no real execution
- Not committed
- No webapp.server imports
- No VoiceProfile or frontend touched
- Tests pass without external dependencies
