# M09-INFRA-REAL-006 — PLAN-004 P6 独立验证回执

结论：**PASS**

仅只读复核 `outputs/p6-real-smoke-51657b64d6d3/runs/run-p6-51657b64d6d3` 及失败保留包；未重新 render，未修改产品实现、capability、create-options 或 submission。

## 独立实测

- 亲自执行：`ffprobe -v error -show_entries format=duration,size:stream=codec_name,codec_type,width,height -of json .../artifacts/render/infographic.mp4`，exit 0。
- 结果：MP4 为非空 `9872` bytes；唯一视频流为 `h264`、`1920x1080`；format duration `2.000000` 秒。
- 重算并与 evidence 相同：
  - MP4：`18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a`
  - props：`aa01442aee747e425a7cc7e5e29594eb7bf49635ca14812dce052eaffa938f08`
  - render manifest：`6dffc18fac04d61eb6bfc1a742b1ac30d946ce5584492048c0cfa39b2bd5c86d`
  - artifact index：`c7915528ff3c4f432d221e3e95a250bfd799d052b0aab7015d75cd8c49db9245`
  - `video_renderer/render.mjs`：`ce5596d1b77884cf9bd51c1702832c42de24f3d2d42850b0204eb527477f095c`
  - `video_renderer/package-lock.json`：`b85a51f84e1b50c7aeb7668c32f315214eeda39764994256a7fb2963a5cf24fa`。

## Evidence、包边界与状态

- 用 `RemotionEvidenceV1` 构造并调用 `validate_remotion_evidence` 成功。`verified_at=2026-09-05T14:29:14Z` 为可解析 UTC；复核时证据年龄约 124 秒，满足 `<=24h`，并且声明的 expiry 为 `2026-09-06T14:29:14Z`。
- `artifact index` 8 个条目均为 run-relative、无绝对路径或 `..` 逃逸；逐个复算文件大小与 SHA-256 均匹配。MP4、props、manifest、probe 均在该 Task 的该 Run 下；task/package/run 的 task ID 均为 `p6-real-smoke-51657b64d6d3`、run ID 均为 `run-p6-51657b64d6d3`。
- `task.json`、`run.json` 和 `render-visuals` stage 均为 `succeeded`；manifest 也声明 2000 ms、60 frames、同一 MP4 hash/size。
- 当前工具版本与 evidence 一致：Node `v24.20.0`、npm `11.12.1`、Remotion `4.0.515`、FFmpeg/ffprobe `6.1.1-3ubuntu5`；当前可执行 browser 路径 `/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome` 存在且输出 `Google Chrome for Testing 152.0.7977.54`，与 evidence 一致。
- 失败保留包 `outputs/p6-real-smoke-2e6bfb1381e8/runs/run-p6-2e6bfb1381e8` 存在 `evidence/remotion-real-smoke-failed.json`，含 `status=FAILED`、`reason_code=RENDER_FAILED`；相应 task/run/stage 均为 `failed`，没有伪造成功 evidence。

## 门禁仍关闭

当前 capability projection 对 `infographic-remotion` 固定 `supported=False`（`csboard/application/capabilities.py:79-91`）；create-options 仅将该值映射为 `available`（`csboard/application/commands.py:240-270`）。故 P6 evidence 本身没有开放 capability 或 create-options。

本验证只调用 ffprobe、哈希、JSON/领域 evidence 解析及版本/路径读取；没有执行 Node render、Remotion render 或任务提交。
