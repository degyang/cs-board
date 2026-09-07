# M09-V2-OUTPUT-001-V-R — independent correction re-verification receipt

Verdict: **PASS**

## Pre/post hash verification

All frozen hashes verified from the main integration area
(`/mnt/d/workstation/projects/cs-board`), which is the canonical source of
truth. Backend worktree hashes are noted separately as non-target copy
differences.

| File | Pre (V receipt / V-R assignment) | Post (main integration area) | Match |
|------|----------------------------------|------------------------------|-------|
| `csboard/adapters/filesystem/artifacts.py` | `62071f0b2cb8dd6bfd980745f5a92e5fe1a40ef2fbbe0e48cf7a24eb1011187c` | `62071f0b2cb8dd6bfd980745f5a92e5fe1a40ef2fbbe0e48cf7a24eb1011187c` | ✅ |
| `csboard/application/commands.py` | `fdf30d215ddd134c829a1e611b2e44c16a38056eda11496c9b3d8ad7b586fcdd` | `fdf30d215ddd134c829a1e611b2e44c16a38056eda11496c9b3d8ad7b586fcdd` | ✅ |
| `tests/test_infographic_routing_p4.py` | `6a2f0a533b78c2c623869d3718686050709dd61e5cf047cf98eb6a3eb1b8f76d` | `6a2f0a533b78c2c623869d3718686050709dd61e5cf047cf98eb6a3eb1b8f76d` | ✅ |
| `tests/test_infographic_e2e.py` | `0b2d23979cbbdc7bb7d66e381b432aab23d48886789a5f8868cf4fc48ff1fb95` | `0b2d23979cbbdc7bb7d66e381b432aab23d48886789a5f8868cf4fc48ff1fb95` | ✅ |
| `video_renderer/render.mjs` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` | ✅ |
| `video_renderer/browser-resolver.mjs` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` | ✅ |
| `video_renderer/browser-resolver.test.mjs` | `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca` | `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca` | ✅ |
| `video_renderer/package.json` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` | ✅ |

All8 frozen hashes match exactly between the V receipt, the V-R assignment,
and the main integration area.

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Frozen target hashes unchanged (main integration area) | ✅ | `artifacts.py` = `62071f0b…`, `commands.py` = `fdf30d21…`, `test_infographic_routing_p4.py` = `6a2f0a53…`, `test_infographic_e2e.py` = `0b2d2397…` — all match V receipt and V-R assignment |
| 2 | V1 renderer hashes unchanged (main integration area) | ✅ | `render.mjs` = `07e92a17…`, `browser-resolver.mjs` = `ef33bd05…`, `browser-resolver.test.mjs` = `37e7a73e…`, `package.json` = `8cda49b4…` — all match V receipt |
| 3 | task.json hash | ✅ | `f02c10de8ca62ae458ec2f754fd5c4969264e515243c0ff85dc03465d32ba044` — matches V-R assignment |
| 4 | Accepted `dd3…` is the only succeeded run | ✅ | `dd3…` status=succeeded, render-visuals=succeeded. All four siblings (`987…`, `23a9…`, `d740…`, `eedf…`) status=failed, render-visuals=failed |
| 5 | Accepted `dd3…` is the active run | ✅ | `task.json` `active_run_id` = `run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63` |
| 6 | Sibling run hashes match V-R assignment | ✅ | `987…` = `0661196e…1415`, `23a9…` = `4c0aba80…5c0ac1`, `d740…` = `d9f67e48…91f3f0`, `dd3…` = `952437ed…04ae91e`, `eedf…` = `9550f000…63224` — all match |
| 7 | Zero `.remotion-private/candidate/*.mp4` across all siblings | ✅ | `find` across entire task root returns zero matches; all5 `.remotion-private/candidate/` dirs exist but are empty |
| 8 | All indexed artifacts present and hash/size-valid (all siblings) | ✅ | Recomputed SHA-256 and size for all indexed entries across all5 runs match disk exactly; zero missing or mismatched files |
| 9 | Manifest cross-references correct | ✅ | `manifest.output_sha256` = index `render.video.sha256` = `18e95359…d641a`; `manifest.probe_sha256` = index `render.ffprobe.sha256` = `a1ea882c…745b` |
| 10 | Accepted MP4 verified by real ffprobe | ✅ | H.264 High profile, 1920×1080, 2.0s, 60 frames, MP4 container, probe_score 100, 9,872 bytes |
| 11 | Accepted MP4 hash matches | ✅ | SHA-256 `18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a` — matches V-R assignment and manifest |
| 12 | Artifact index hash | ✅ | `47872bed9097e32271cd3a8ca6bd253e157f3bdc49b9c948b06513a39e60d188` — matches V-R assignment |
| 13 | Render manifest hash | ✅ | `75e30cccc87b8b802710d238e28d56f4430e28a12ca8bcf0d7edbeca66c37f15` — matches V-R assignment |
| 14 | 37-test focused gate | ✅ | `pytest -q tests/test_infographic_routing_p4.py tests/test_remotion_renderer_adapter.py tests/test_infographic_contract_fixture.py tests/test_infographic_e2e.py` — 37 passed |
| 15 | Renderer tests/typecheck | ✅ | `npm test` 3/3 pass; `npm run build` (tsc --noEmit) pass |
| 16 | Scoped `git diff --check` | ✅ | No whitespace errors on frozen target files |
| 17 | No residual renderer processes | ✅ | `ps aux \| grep video_renderer/render.mjs` — none found |
| 18 | Fresh Workmates verify evidence | ✅ | `./scripts/workmates verify --role verification --evidence /tmp/m09-v2-output-001-vr-evidence-1788741205.json` from project root — exit 0, status PASS |
| 19 | No new task/run/render | ✅ | Only pre-existing `task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f` and `temp` in outputs/ |
| 20 | No activation/capability/submission change | ✅ | `capabilities.py` diff is pre-existing committed state (1ce6f0c), not V2 work; no activation pointer or submission endpoint modified |
| 21 | Browser env vars absent | ✅ | `REMOTION_BROWSER_EXECUTABLE`, `PUPPETEER_EXECUTABLE_PATH`, `CHROME_PATH` all unset |

## Commands and exit codes

All commands executed from the main integration area
(`/mnt/d/workstation/projects/cs-board`) unless noted. Output verification
commands run against the backend worktree output at
`/mnt/d/Workstation/Projects/cs-board-worktrees/backend/outputs/task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f`.

| Command | Where | Exit |
|---------|-------|------|
| `sha256sum` on4 V2 frozen source/test files | main integration | 0 — all match |
| `sha256sum` on4 V1 renderer files | main integration | 0 — all match |
| `sha256sum` on task.json | backend worktree output | 0 — matches `f02c10de…` |
| `sha256sum` on all5 sibling run.json files | backend worktree output | 0 — all match V-R assignment |
| `sha256sum` on accepted MP4 | backend worktree output | 0 — `18e95359…d641a` |
| `ffprobe -print_format json -show_format -show_streams <MP4>` | backend worktree output | 0 |
| Index hash/size recomputation — accepted run (6 entries) | backend worktree output | 0 — all match |
| Index hash/size recomputation — all5 siblings | backend worktree output | 0 — all entries present and match |
| Manifest cross-reference check | backend worktree output | 0 — both match |
| `find <task-root> -path "*/.remotion-private/candidate/*.mp4"` | backend worktree output | 0 — zero matches |
| `pytest -q <4 focused test files>` | backend worktree | 0, 37 passed |
| `npm --prefix video_renderer test` | backend worktree | 0, 3 passed |
| `npm --prefix video_renderer run build` | backend worktree | 0 |
| `git diff --check HEAD -- <frozen targets>` | backend worktree | 0 |
| `ps aux \| grep video_renderer/render.mjs` | backend worktree | 1 (not found) |
| `./scripts/workmates verify --role verification --evidence <path>` | main integration (project root) | 0, PASS |

## Frozen hash table (main integration area — canonical)

| Artifact | SHA-256 |
|----------|---------|
| `artifacts.py` | `62071f0b2cb8dd6bfd980745f5a92e5fe1a40ef2fbbe0e48cf7a24eb1011187c` |
| `commands.py` | `fdf30d215ddd134c829a1e611b2e44c16a38056eda11496c9b3d8ad7b586fcdd` |
| `test_infographic_routing_p4.py` | `6a2f0a533b78c2c623869d3718686050709dd61e5cf047cf98eb6a3eb1b8f76d` |
| `test_infographic_e2e.py` | `0b2d23979cbbdc7bb7d66e381b432aab23d48886789a5f8868cf4fc48ff1fb95` |
| `render.mjs` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` |
| `browser-resolver.mjs` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` |
| `browser-resolver.test.mjs` | `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca` |
| `package.json` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` |

## Output artifact hash table (backend worktree)

| Artifact | SHA-256 |
|----------|---------|
| task.json | `f02c10de8ca62ae458ec2f754fd5c4969264e515243c0ff85dc03465d32ba044` |
| run `987…` | `0661196ee52cf36512f05f1d6f5c8e1b72f4ae0f001dd000d423404ddba01415` |
| run `23a9…` | `4c0aba809f8819b317ef5fb31b1e6eecf6d8a9e32bffe344587721f1d45c0ac1` |
| run `d740…` | `d9f67e488bf70cfa5e55a6041a215dae7d61e4b05c93f8eedbc6c52ae291f3f0` |
| run `dd3…` (accepted) | `952437ed60d68c6eba23cd9b5c32ed5b6d4b4a7ff89d373de65b1940f04ae91e` |
| run `eedf…` | `9550f00041e44a49b43c9753bbe03ee62c58b0d02ee1cf5283a987e4b8d63224` |
| MP4 | `18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a` |
| artifact index | `47872bed9097e32271cd3a8ca6bd253e157f3bdc49b9c948b06513a39e60d188` |
| render manifest | `75e30cccc87b8b802710d238e28d56f4430e28a12ca8bcf0d7edbeca66c37f15` |

## Observations

- **Backend worktree non-target copy divergence**: the backend worktree's
  `video_renderer/browser-resolver.test.mjs` has SHA-256
  `fc8dfe55d2dbd73c848bf46cfa15c5633d5efdb2590a6c85a5543c707b4f05cb`, differing
  from the canonical main integration area hash `37e7a73e…`. This file is
  untracked in the backend worktree (dirty state preserved per assignment). It
  is not a frozen V1/V2 target and does not affect verification; renderer tests
  pass3/3 in both locations. The backend worktree is not the canonical source
  for frozen source hashes.
- `d740…` has an indexed `artifacts/render/infographic.mp4` present on disk
  (hash matches accepted MP4) but its run status is `failed` with
  `render-visuals=failed`. This is correct per the R correction — the stale
  succeeded status was fixed, the unindexed private candidate was removed, and
  the indexed artifact was retained.
- `23a9…` also has indexed render artifacts on disk (ffprobe.json,
  render-manifest.json) despite being `failed`. These are retained indexed
  entries, not unbound candidates.

## Unverified scope

- Visual/video quality acceptance (reserved for user).
- PM stage acceptance (reserved for PM after this PASS).
- Public capability/submission remains closed as expected.
