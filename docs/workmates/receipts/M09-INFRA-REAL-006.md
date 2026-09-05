# M09-INFRA-REAL-006 — P6 controlled real smoke receipt

Status: `READY_FOR_VERIFY`

## Scope and execution

- Executed only PLAN-004 P6's controlled real smoke. No capability, create-options, submission, API, CLI, webapp, or product-source changes were made.
- Verified and used only the approved Linux Chrome executable:
  `/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome`
  (`Google Chrome for Testing 152.0.7977.54`). Windows `chrome.exe` was not used.
- Created the controlled package:
  `outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3/`.
- Rendered through `RemotionRendererAdapter` with the locked `video_renderer/render.mjs`; it produced a real MP4, not a placeholder, timeout-only result, or empty file.

## Result

- MP4: `artifacts/render/infographic.mp4`
- SHA-256: `18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a`
- Size: `9872` bytes
- Independent `ffprobe`: H.264 video stream, `1920x1080`, duration `2.000000` seconds, container `mov,mp4,m4a,3gp,3g2,mj2`.
- Artifact index: 8 artifacts; its recorded SHA-256 matched the final `artifacts/index.json`.

## Inputs, manifests, and evidence

- Minimal valid 1x1 RGBA PNG was generated as the smoke input and stored in the same run at `artifacts/assets/smoke.png` (68 bytes); source and SHA-256 are recorded in evidence and the artifact index.
- Recorded artifacts include storyboard, timeline, illustration manifest, persisted props, MP4, ffprobe JSON, and P1 render manifest.
- Evidence: `evidence/remotion-real-smoke.json`.
  It records sanitized argv, props hash, artifact index and manifest hashes, MP4 hash, tool versions, render-script and lockfile hashes, browser policy, and UTC freshness.
- Freshness: verified `2026-09-05T14:29:14Z`; expires `2026-09-06T14:29:14Z` (fixed 24 hours, UTC).
- Toolchain: Node `v24.20.0`; npm `11.12.1`; Remotion `4.0.515`; Chrome `152.0.7977.54`; FFmpeg/ffprobe `6.1.1-3ubuntu5`; render-script SHA-256 `ce5596d1b77884cf9bd51c1702832c42de24f3d2d42850b0204eb527477f095c`; lockfile SHA-256 `b85a51f84e1b50c7aeb7668c32f315214eeda39764994256a7fb2963a5cf24fa`.

## Failure preservation and rework

- The first controlled package, `outputs/p6-real-smoke-2e6bfb1381e8/runs/run-p6-2e6bfb1381e8/`, was retained with `evidence/remotion-real-smoke-failed.json`.
- Its failure was a one-shot driver defect that supplied an empty Node executable path (`Permission denied: ''`), before Remotion started; it was corrected in the temporary driver by using the verified absolute Linux Node path. No product source was changed.

READY_FOR_VERIFY
