# M09 Round 3 — WBS-3 Backend Receipt

**Date:** 2026-09-05
**Scope:** WBS-3 — RemotionRendererAdapter / RendererPort

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `csboard/adapters/remotion/renderer_adapter.py` | ~230 | RemotionRendererAdapter implementing RendererPort |
| `tests/test_remotion_renderer_adapter.py` | ~370 | 19 tests covering all required scenarios |

## Implementation Summary

### RemotionRendererAdapter (`csboard/adapters/remotion/renderer_adapter.py`)

**Implements:** `RendererPort` protocol (`render()` + `capabilities()`)

**Flow:**
1. Read timeline / storyboard / illustration-manifest JSON artifacts
2. Convert to domain `InfographicStoryboard` via `voice_units_to_pages()`
3. Convert to Remotion props via `InfographicStoryboardAdapter.to_remotion_props()`
4. Write props to temp JSON file
5. Invoke `node video_renderer/render.mjs <props.json> <output.mp4> <public_dir>` via `subprocess.run`
6. Validate output, clean up temp file, return `RenderResult`

**Error handling:**
- `ARTIFACT_NOT_FOUND` — input file doesn't exist
- `ARTIFACT_READ_ERROR` — JSON parse failure
- `ARTIFACT_DIR_NOT_FOUND` — can't resolve artifacts directory
- `EMPTY_STORYBOARD` — no pages after conversion
- `NODE_NOT_FOUND` — node binary missing
- `RENDER_TIMEOUT` — subprocess exceeded timeout
- `RENDER_FAILED` — non-zero exit (stderr sanitized)
- `NO_OUTPUT` / `EMPTY_OUTPUT` — render succeeded but no file

**Sanitization:**
- `_sanitize_error()` strips absolute Windows/Unix paths and API keys/tokens from stderr
- All error messages are in Chinese with no path/secret leakage

**Injectable dependencies:**
- `render_mjs` path
- `node_bin` path
- `timeout` seconds
- `subprocess_run` callable (for testing)

### Tests (`tests/test_remotion_renderer_adapter.py`) — 19 tests

| Category | Tests | What's verified |
|----------|-------|-----------------|
| Command construction | 3 | Correct `node render.mjs <props> <output> <dir>` args, props written to temp file, props contains required keys |
| Output directory | 2 | Output dir created, output path inside run directory |
| Failure sanitization | 3 | No absolute paths in errors, error codes are known constants, missing artifact errors don't leak paths |
| Timeout handling | 2 | Timeout raises `RENDER_TIMEOUT`, temp file cleaned up on timeout |
| Non-zero exit | 3 | Exit 1/137 raise `RENDER_FAILED`, temp file cleaned up on failure |
| No side effects | 3 | subprocess not called on bad input, no orphaned output on failure, empty storyboard fails before subprocess |
| Success path | 2 | All RenderResult fields populated correctly, capabilities includes infographic-remotion |
| Import guard | 1 | AST scan confirms no webapp imports in adapter module |

## Test Results

```
tests/test_remotion_renderer_adapter.py  19 passed in 0.43s
Full WBS suite (73 + 19)                92 passed in 3.59s
```

## Exclusions Respected

- ❌ No `webapp.server` imports
- ❌ No frontend changes
- ❌ No VoiceProfile changes
- ❌ No real Remotion execution (all subprocess.run mocked)
- ❌ No git commit

## Integration Points

- **Consumes:** `InfographicStoryboardAdapter.to_remotion_props()` (WBS-2)
- **Consumes:** `voice_units_to_pages()` from `csboard.domain.infographic` (WBS-1)
- **Implements:** `RendererPort` protocol from `csboard.ports.providers`
- **Returns:** `RenderResult` from `csboard.domain.provider_types`
- **Next:** WBS-6 (CLI `--engine` parameter) can now wire this adapter via ProviderFactory
