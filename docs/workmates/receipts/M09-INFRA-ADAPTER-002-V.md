# M09-INFRA-ADAPTER-002-V — P2 Adapter 独立验证回执

结论：**PASS**。

验证人：`tester_backend_p2`。本次为只读独立验证；未修改产品代码、测试、计划或配置，未执行 real render、MP4/ffprobe、任务创建、capability activation 或 submission。唯一写入为本回执。测试中的 `subprocess` 与 ffprobe 均为 mock/fake，不会调用 Node、Remotion 或真实工具链。

## 独立执行证据

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_remotion_renderer_adapter.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py tests/test_no_legacy_imports.py` | **PASS — 74 passed in 1.09s**, exit 0 |
| `npm --prefix video_renderer run build` | **PASS — `tsc --noEmit`**, exit 0 |
| `git diff --check` | **PASS — 无输出**, exit 0 |

## 核验结论

1. **PASS — P1 是唯一结构性输入。** `RemotionRendererAdapter.render()` 仅读取提交的 `infographic_storyboard` 并以 `InfographicStoryboard.from_dict()`/`InfographicStoryboardAdapter` 转为 v1 props；timeline 与 illustration manifest 只提供已产出的 run-relative audio/image 引用，未见旧 planning fragments 重建 storyboard 的路径。`schemaVersion: 1`、fps、画布、总时长/帧数和 pages 已由 renderer/adapter focused tests 覆盖。
2. **PASS — 时间与 props 契约。** storyboard adapter 使用 P1 的 `milliseconds_to_frame()`（cue/page start floor）与 `duration_frames()`（duration/end/total ceil），并实际经 1050ms@30fps 等测试覆盖；坏 storyboard/坏 JSON 在启动 Node 前以稳定错误拒绝。
3. **PASS — mock subprocess 成功、nonzero、timeout 与 cleanup。** focused renderer suite 覆盖固定 argv、成功 `RenderResult`、nonzero `RENDER_FAILED`、timeout `RENDER_TIMEOUT`、缺 Node `NODE_NOT_FOUND`，以及 `.remotion-private` 中临时 props 在 success/nonzero/timeout 后清理。
4. **PASS — 输出及 probe fail-closed。** 输出仅允许当前 run 内；非空候选 MP4 仍必须通过 mock ffprobe 的 format/video stream/正 duration/正尺寸/props 尺寸校验。invalid ffprobe、尺寸不符、无输出或空输出不返回成功；probe failure 会删除候选文件。
5. **PASS — 路径、secret 和 legacy 隔离。** illustration/audio 只接受 run-relative POSIX 引用，拒绝绝对、drive/URI、反斜杠和 `..`；renderer stderr 的绝对路径及 credential/Bearer 文本会脱敏。AST/static test 通过，`csboard/adapters/remotion/` 与 application 扫描未发现 `webapp` legacy import。
6. **PASS — P2 readiness 边界未越权。** adapter 仅声明 `node`、render script、lockfile、Remotion、browser、FFmpeg/ffprobe、renderer/tool versions 的 prerequisite contract；未 probe、未宣布 readiness、未改 capability，符合 P2 仅供 P3a/P4 合流的边界。

## 授权边界

此 PASS 仅完成 P4 的一半前置条件（P2 adapter）。仍须 P3a bootstrap/readiness 的独立 PASS 后方可进入 P4；不授权 P4/P5/P6、真实渲染、MP4/ffprobe evidence、`create-options.available`、创建任务或任何用户/API/WebUI submission。
