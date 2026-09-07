# M09-V2-OUTPUT-001-V — independent verification receipt

Verdict: **PASS**

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Frozen target hashes unchanged | ✅ | `artifacts.py` = `62071f0b…`, `commands.py` = `fdf30d21…`, `test_infographic_routing_p4.py` = `6a2f0a53…`, `test_infographic_e2e.py` = `0b2d2397…` — all match assignment |
| 2 | V1 renderer/resolver hashes unchanged | ✅ | `render.mjs` = `07e92a17…`, `browser-resolver.mjs` = `ef33bd05…`, `browser-resolver.test.mjs` = `37e7a73e…`, `package.json` = `8cda49b4…` — all match M09-V1-CORRIDOR-002-V-R |
| 3 | Accepted run identified correctly | ✅ | `run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63`; `task.json` `active_run_id` matches |
| 4 | Exactly one final indexed MP4 in accepted run | ✅ | `artifacts/render/infographic.mp4` = 9,872 bytes, SHA-256 `18e95359ac…`; `.remotion-private/candidate/` is empty |
| 5 | MP4 verified by real ffprobe | ✅ | H.264 High profile, 1920×1080, 2.0s, 60 frames, MP4 container, probe_score 100 |
| 6 | All indexed sizes/hashes match disk | ✅ | Recomputed SHA-256 and size for all 6 indexed files match artifact index exactly |
| 7 | Manifest bindings correct | ✅ | `render-manifest.json` `probe_sha256` = indexed `render.ffprobe` hash; `output_sha256` = indexed `render.video` hash; all paths run-relative |
| 8 | Task/Run/Stage status correct | ✅ | Accepted run: `run.json` status=succeeded, `render-visuals` stage=succeeded; `task.json` status=succeeded |
| 9 | Sibling run statuses | ✅ | 3 runs `failed`, 1 prior `succeeded` (`d7401b67`) with different input hashes — task `active_run_id` correctly points to accepted run; prior succeeded run is not claimed as V2 output |
| 10 | Input snapshots synthetic | ✅ | SVG = "Controlled synthetic corridor"; storyboard/timeline/illustration-manifest contain no real data |
| 11 | 37-test focused gate | ✅ | `pytest tests/test_infographic_routing_p4.py tests/test_remotion_renderer_adapter.py tests/test_infographic_contract_fixture.py tests/test_infographic_e2e.py` — 37 passed |
| 12 | Renderer tests/typecheck | ✅ | `npm test` 3/3 pass; `npm run build` (tsc --noEmit) pass |
| 13 | Scoped `git diff --check` | ✅ | No whitespace errors on frozen target files |
| 14 | No residual renderer processes | ✅ | `ps aux | grep video_renderer/render.mjs` — none found |
| 15 | Workmates representative gate | ✅ | Exit code 0, evidence `/tmp/m09-v2-output-001-v-evidence-1788719314.json` |
| 16 | No activation/capability/public-submission change by V2 | ✅ | `capabilities.py` diff is pre-existing committed state (1ce6f0c), not V2 work; no activation pointer or submission endpoint modified |
| 17 | P6 activation fixture | ℹ️ | `test_infographic_activation.py` collects 30 tests in main checkout; absent in backend worktree as stated — outside V2 scope, confirmed no V2 change to activation |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on 4 frozen targets | 0 — all match |
| `sha256sum` on 4 V1 renderer files | 0 — all match |
| `ffprobe -print_format json -show_format -show_streams <MP4>` | 0 |
| `pytest -q tests/test_infographic_routing_p4.py tests/test_remotion_renderer_adapter.py tests/test_infographic_contract_fixture.py tests/test_infographic_e2e.py` | 0, 37 passed |
| `npm --prefix video_renderer test` | 0, 3 passed |
| `npm --prefix video_renderer run build` | 0 |
| `git diff --check HEAD -- <frozen targets>` | 0 |
| `workmates verify --role verification --evidence <path>` | 0 |

## Observations

- Run `d7401b67` is also marked `succeeded` with a private candidate MP4 still present in `.remotion-private/candidate/`. This is a prior successful render attempt with different input hashes. The task's `active_run_id` correctly identifies the accepted run as the canonical V2 output. This does not block acceptance but is noted for PM awareness.

## Unverified scope

- Visual/video quality acceptance (reserved for user).
- PM stage acceptance (reserved for PM after this PASS).
- Public capability/submission remains closed as expected.
