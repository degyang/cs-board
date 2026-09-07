# M09-V1-CORRIDOR-002-V — verification receipt

Status: **BLOCKED**

## Hash verification

| File | Expected | Actual | Match |
|------|----------|--------|-------|
| `video_renderer/render.mjs` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` | ✓ |
| `video_renderer/browser-resolver.mjs` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` | ✓ |
| `video_renderer/browser-resolver.test.mjs` | `fc8dfe55d2dbd73c848bf46cfa15c5633d5efdb2590a6c85a5543c707b4f05cb` | `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca` | ✗ |
| `video_renderer/package.json` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` | ✓ |

**BLOCKED**: `browser-resolver.test.mjs` hash does not match frozen specification.

## Implementation review (completed before BLOCKED)

- ✓ Priority order: configured env vars → platform paths → Puppeteer/Playwright cache
- ✓ Only accepts executable files (`fs.accessSync(R_OK | X_OK)` + `isFile()`)
- ✓ Linux reuses `~/.cache/puppeteer/` and `~/.cache/ms-playwright/`
- ✓ Returns `null` to preserve Remotion fallback
- ✓ Same resolved path passed to both `selectComposition` and `renderMedia`

## Tests (completed before BLOCKED)

- `npm --prefix video_renderer test`: exit 0, 3/3 passed
- `npm --prefix video_renderer run build`: exit 0 (typecheck)
- `pytest tests/test_remotion_renderer_adapter.py tests/test_infographic_contract_fixture.py`: exit 0, 25/25 passed

## Real render (completed before BLOCKED)

- Environment: `REMOTION_BROWSER_EXECUTABLE`, `PUPPETEER_EXECUTABLE_PATH`, `CHROME_PATH` explicitly unset
- Input: `tests/fixtures/infographic/dynamic-infographic-props-v1.json` + `assets/drawing-hand-clean.png`
- Render exit: 0
- Output: `/tmp/corridor-002-verify-1158383/output.mp4`, 12,389 bytes
- ffprobe: H.264, 1920×1080, duration 1.066667s, non-empty

## Other checks

- No residual `node … video_renderer/render.mjs` processes
- `git diff --check -- video_renderer`: exit 0
- `./scripts/workmates verify --role verification`: PASS

## Conclusion

**BLOCKED** — cannot unlock V2. The `browser-resolver.test.mjs` file has diverged from the frozen hash. Backend must re-freeze or re-commit this file before verification can pass.
