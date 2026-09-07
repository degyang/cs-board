# M09-V3-CORRIDOR-VERIFY-001 — V3 independent boundary evidence verification receipt

Verdict: **PASS**

## Pre/post hash verification (main integration area — canonical)

All8 frozen implementation hashes reverified from `/mnt/d/workstation/projects/cs-board`.

| File | V2 V-R hash | V3 recomputed | Match |
|------|-------------|---------------|-------|
| `csboard/adapters/filesystem/artifacts.py` | `62071f0b…11187c` | `62071f0b…11187c` | ✅ |
| `csboard/application/commands.py` | `fdf30d21…86fcdd` | `fdf30d21…86fcdd` | ✅ |
| `tests/test_infographic_routing_p4.py` | `6a2f0a53…b8f76d` | `6a2f0a53…b8f76d` | ✅ |
| `tests/test_infographic_e2e.py` | `0b2d2397…f1fb95` | `0b2d2397…f1fb95` | ✅ |
| `video_renderer/render.mjs` | `07e92a17…45b593` | `07e92a17…45b593` | ✅ |
| `video_renderer/browser-resolver.mjs` | `ef33bd05…dbeec` | `ef33bd05…dbeec` | ✅ |
| `video_renderer/browser-resolver.test.mjs` | `37e7a73e…2d38ca` | `37e7a73e…2d38ca` | ✅ |
| `video_renderer/package.json` | `8cda49b4…cb59` | `8cda49b4…cb59` | ✅ |

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Frozen implementation hashes unchanged | ✅ | All8 files match V2 V-R receipt exactly |
| 2 | V1 renderer hashes unchanged | ✅ | `render.mjs`, `browser-resolver.mjs`, `browser-resolver.test.mjs`, `package.json` — all match |
| 3 | task.json hash | ✅ | `f02c10de…ba044` — matches V2 V-R receipt |
| 4 | Accepted `dd3…` is the only succeeded run | ✅ | `dd3…` status=succeeded, render-visuals=succeeded. All four siblings (987…, 23a9…, d740…, eedf…) status=failed, render-visuals=failed |
| 5 | Accepted `dd3…` is the active run | ✅ | `task.json` `active_run_id` = `run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63` |
| 6 | Sibling run hashes match V2 V-R receipt | ✅ | 987…=`0661196e…1415`, 23a9…=`4c0aba80…5c0ac1`, d740…=`d9f67e48…91f3f0`, dd3…=`952437ed…04ae91e`, eedf…=`9550f000…63224` |
| 7 | Zero `.remotion-private/candidate/*.mp4` | ✅ | All5 `.remotion-private/candidate/` dirs exist and are empty |
| 8 | All indexed artifacts present and hash/size-valid (all5 siblings) | ✅ | Recomputed SHA-256 and size for all indexed entries across all5 runs match disk exactly |
| 9 | Manifest cross-references correct | ✅ | `manifest.output_sha256` = index `render.video.sha256` = `18e95359…d641a`; `manifest.probe_sha256` = index `render.ffprobe.sha256` = `a1ea882c…745b` |
| 10 | Manifest `input_fingerprint` consistent | ✅ | Matches `_sha(f"{task_id}:{run_id}:render.manifest")` per `av_artifacts.py:84` |
| 11 | Accepted MP4 verified by real ffprobe | ✅ | H.264 High profile, 1920×1080, 2.0s,30fps,60 frames, MP4 container, probe_score100,9,872 bytes |
| 12 | Accepted MP4 hash matches | ✅ | SHA-256 `18e95359…d641a` — matches V2 V-R receipt and manifest |
| 13 | Artifact index hash | ✅ | `47872bed…d188` — matches V2 V-R receipt |
| 14 | Render manifest hash | ✅ | `75e30ccc…7f15` — matches V2 V-R receipt |
| 15 | Input snapshots match artifact inputs | ✅ | `storyboard.json`, `timeline.json`, `illustration-manifest.json` — byte-identical between `input-snapshot/` and `artifacts/input/` |
| 16 | Input references are run-contained and synthetic | ✅ | `remotion-props.json` image ref = `assets/synthetic-corridor.svg` (relative, run-contained); SVG exists at512 bytes |
| 17 | Browser auto-resolution with3 env vars absent | ✅ | `REMOTION_BROWSER_EXECUTABLE`, `PUPPETEER_EXECUTABLE_PATH`, `CHROME_PATH` all unset; `resolveBrowserExecutable()` falls through to platform/cached candidates |
| 18 | Bounded timeout | ✅ | `timeoutInMilliseconds:120000` on both `selectComposition` and `renderMedia` |
| 19 | ffprobe acceptance before publish | ✅ | `commands.py` routes infographic-remotion to `.remotion-private/candidate`; ffprobe verification produces `ffprobe.json` in artifacts |
| 20 |37-test focused gate | ✅ | `pytest -q tests/test_infographic_routing_p4.py tests/test_remotion_renderer_adapter.py tests/test_infographic_contract_fixture.py tests/test_infographic_e2e.py` —37 passed |
| 21 | Renderer tests/typecheck | ✅ | `npm test`3/3 pass; `npx tsc --noEmit` pass |
| 22 | Scoped `git diff --check` | ✅ | No whitespace errors on8 frozen target files |
| 23 | No residual renderer processes | ✅ | `ps aux \| grep video_renderer/render.mjs` — none found |
| 24 | Fresh Workmates verify evidence | ✅ | `./scripts/workmates verify --role verification --evidence /tmp/m09-v3-corridor-verify-001-evidence-1788742080.json` from project root — exit0, status PASS |
| 25 | No new task/run/render | ✅ | Only pre-existing `task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f` and `temp` in outputs/ |
| 26 | No activation/capability/submission change | ✅ | `capabilities.py` `supported: False` for infographic-remotion; diff is pre-existing committed state (1ce6f0c), not V2/V3 work |
| 27 | Ports8000/5182 not started | ✅ | `ss -tlnp` shows no listeners on8000 or5182 |
| 28 | V1 receipt hash | ✅ | V1 receipt exists at assigned path |
| 29 | V2 receipt hash | ✅ | SHA-256 `b0248d08…239f6` — matches assignment |

## Commands and exit codes

| Command | Where | Exit |
|---------|-------|------|
| `sha256sum` on8 frozen source/test files | main integration |0 — all match |
| `sha256sum` on task.json | backend worktree output |0 — matches `f02c10de…` |
| `sha256sum` on all5 sibling run.json | backend worktree output |0 — all match V2 receipt |
| `sha256sum` on accepted MP4 | backend worktree output |0 — `18e95359…d641a` |
| `ffprobe -print_format json -show_format -show_streams <MP4>` | backend worktree output |0 |
| Index hash/size recomputation — all5 siblings | backend worktree output |0 — all entries present and match |
| Manifest cross-reference check | backend worktree output |0 — both match |
| Input fingerprint verification | backend worktree output |0 — matches `_sha(task:run:artifact_key)` |
| Input snapshot vs artifact/input comparison | backend worktree output |0 — byte-identical |
| `.remotion-private/candidate` emptiness check | backend worktree output |0 — all5 dirs empty |
| `find <task-root> -path "*/.remotion-private/candidate/*.mp4"` | backend worktree output |0 — zero matches |
| `pytest -q <4 focused test files>` | main integration |0,37 passed |
| `npm --prefix video_renderer test` | main integration |0,3 passed |
| `npx --prefix video_renderer tsc --noEmit` | main integration |0 |
| `git diff --check HEAD -- <8 frozen targets>` | main integration |0 |
| `ps aux \| grep video_renderer/render.mjs` | main integration |1 (not found) |
| `ss -tlnp \| grep :8000\|:5182` | main integration |1 (not found) |
| `./scripts/workmates verify --role verification --evidence <path>` | main integration (project root) |0, PASS |

## Frozen hash table (main integration area — canonical)

| Artifact | SHA-256 |
|----------|---------|
| `csboard/adapters/filesystem/artifacts.py` | `62071f0b2cb8dd6bfd980745f5a92e5fe1a40ef2fbbe0e48cf7a24eb1011187c` |
| `csboard/application/commands.py` | `fdf30d215ddd134c829a1e611b2e44c16a38056eda11496c9b3d8ad7b586fcdd` |
| `tests/test_infographic_routing_p4.py` | `6a2f0a533b78c2c623869d3718686050709dd61e5cf047cf98eb6a3eb1b8f76d` |
| `tests/test_infographic_e2e.py` | `0b2d23979cbbdc7bb7d66e381b432aab23d48886789a5f8868cf4fc48ff1fb95` |
| `video_renderer/render.mjs` | `07e92a176a5d00ae09dcc95e6faf0592e2ff9df25106b15832a1d13e2445b593` |
| `video_renderer/browser-resolver.mjs` | `ef33bd05111b0e9cf87666250fefc81558d0f493cb113e68c83ff598c5adbeec` |
| `video_renderer/browser-resolver.test.mjs` | `37e7a73ec34a64276dc5016890320d1e497abb63d4153dba906694c3202d38ca` |
| `video_renderer/package.json` | `8cda49b4058e0980442ab297f39d67c5a49bd075c5cc79ed0d62ff360da4cb59` |

## Output artifact hash table (backend worktree — accepted run dd3…)

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

- **capabilities.py working-tree diff**: pre-existing uncommitted changes (from1ce6f0c lineage) that remove the `ActivationVerifier` import and keep `supported: False`. These are not V2/V3 work; the public infographic projection remains closed as expected.
- **commands.py working-tree diff**: pre-existing uncommitted changes adding the `.remotion-private/candidate` routing for infographic-remotion engine. Not V2/V3 work.
- **Renderer adapter contract**: `resolveBrowserExecutable()` checks3 env vars first, then platform-specific paths, then Puppeteer/Playwright caches. With all3 unset, it auto-resolves from cache — confirmed by the accepted run's successful render.
- **`input_fingerprint`**: computed as `_sha(f"{task_id}:{run_id}:{artifact_key}")` per `av_artifacts.py:84`, not as a content hash of remotion props. Verified consistent with manifest value `sha256:f49ba691…357c5`.

## Unverified scope

- Visual/video quality acceptance (reserved for user).
- PM stage acceptance (reserved for PM after this PASS).
- Public capability/submission remains closed as expected; activation ticket not yet issued.

## Evidence path

`/tmp/m09-v3-corridor-verify-001-evidence-1788742080.json`

---

## Current-browser V3 re-freeze (M09-ACTIVATE-004-V, 2026-09-07)

**Verdict: PASS**

### Context

Original V3 PASS used `Google Chrome for Testing 152.0.7977.54`. Current `browser-resolver.mjs` (with all three env vars unset) resolves to `152.0.7977.75`. This re-freeze proves the current browser produces byte-identical output from the accepted run's `remotion-props.json`.

### Pre/post hash verification (accepted artifacts — no drift)

| Artifact | V3 receipt hash | Re-freeze recomputed | Match |
|----------|----------------|---------------------|-------|
| `task.json` | `f02c10de…ba044` | `f02c10de…ba044` | ✅ |
| accepted run `dd3…` | `952437ed…04ae91e` | `952437ed…04ae91e` | ✅ |
| accepted MP4 | `18e95359…d641a` | `18e95359…d641a` | ✅ |
| artifact index | `47872bed…d188` | `47872bed…d188` | ✅ |
| render manifest | `75e30ccc…7f15` | `75e30ccc…7f15` | ✅ |

### Renderer/resolver/lockfile hashes (no drift)

| File | Hash |
|------|------|
| `video_renderer/render.mjs` | `07e92a17…45b593` |
| `video_renderer/browser-resolver.mjs` | `ef33bd05…dbeec` |
| `video_renderer/browser-resolver.test.mjs` | `37e7a73e…2d38ca` |
| `video_renderer/package.json` | `8cda49b4…cb59` |

### Post-V3 activation changes (recorded, not claimed frozen)

| File | Current hash | Note |
|------|-------------|------|
| `csboard/application/commands.py` | `75bbec82…e833` | Post-V3 activation integration; see M09-ACTIVATE-003-V focused PASS |
| `csboard/application/capabilities.py` | `ebdb2ea3…0065` | Post-V3 activation integration |
| `csboard/application/activation.py` | `34bffe07…6995` | Post-V3 activation integration |

### Browser resolution

- `REMOTION_BROWSER_EXECUTABLE`: unset
- `PUPPETEER_EXECUTABLE_PATH`: unset
- `CHROME_PATH`: unset
- Auto-resolved: `/home/ubuntu/.cache/puppeteer/chrome-headless-shell/linux-152.0.7977.75/chrome-headless-shell-linux64/chrome-headless-shell`
- Version string: `Google Chrome for Testing 152.0.7977.75`

### Isolated render verification

- Input: accepted run `dd3…` `input-snapshot/remotion-props.json` + `assets/synthetic-corridor.svg`
- Input path validation: relative, run-contained, no `..`, no absolute paths ✅
- Output dir: `/tmp/m09-activate-004-v-render-nehf0k`
- Render command: `timeout 180 node video_renderer/render.mjs <props> <output.mp4> <public-dir>`
- Render exit: 0
- Output hash: `18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a` — byte-identical to accepted MP4 ✅
- ffprobe: H.264 High, 1920×1080, 2.0s, 30fps, 60 frames, MP4, probe_score 100, 9,872 bytes ✅
- Residual renderer processes: none ✅

### Test gates

| Gate | Result |
|------|--------|
| Renderer tests (`npm --prefix video_renderer test`) | 3/3 pass ✅ |
| Renderer typecheck (`npx tsc --noEmit`) | pass ✅ |
| Focused corridor/activation tests (37 tests) | 37 passed ✅ |
| Scoped `git diff --check` on8 frozen targets | no whitespace errors ✅ |
| Workmates verify | PASS ✅ |

### Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on8 frozen source/test files | 0 — renderer/resolver/lockfile unchanged |
| `sha256sum` on task.json, run.json, MP4, index, manifest | 0 — all match V3 receipt |
| `resolveBrowserExecutable()` with3 env vars unset | resolved `152.0.7977.75` |
| `timeout 180 node video_renderer/render.mjs …` | 0 |
| `ffprobe -print_format json -show_format -show_streams <MP4>` | 0 |
| `ps aux \| grep video_renderer/render.mjs` | 1 (not found) |
| `npm --prefix video_renderer test` | 0, 3 passed |
| `npx tsc --noEmit` (from video_renderer/) | 0 |
| `pytest -q <2 focused test files>` | 0, 37 passed |
| `git diff --check HEAD -- <8 frozen targets>` | 0 |
| `./scripts/workmates verify --role verification --evidence <path>` | 0, PASS |

### Evidence paths

- Render output: `/tmp/m09-activate-004-v-render-nehf0k/output.mp4`
- Workmates evidence: `/tmp/m09-activate-004-v-evidence-1788754469.json`
