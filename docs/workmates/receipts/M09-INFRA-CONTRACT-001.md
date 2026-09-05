# M09-INFRA-CONTRACT-001 — P1 实现回执

状态：`READY_FOR_INDEPENDENT_P1_VERIFICATION`

本回执仅报告 P1 实现与门槛结果；**不是**独立验证或验收，不授权 P2、P3a 或任何后续工单。

## 已交付的 P1 契约

- `InfographicStoryboard v1` 是纯 domain DTO：`schema_version=1`、`engine=infographic-remotion`、稳定 page/node/cue ID，以及绝对毫秒的 start-inclusive/end-exclusive 页面与 cue 语义。
- Voice Unit 页面策略固定为 `exactly_one_page_per_voice_unit`：一个 Voice Unit 恰好一个 page；多 visual 作为该 page 的 nodes/cues，拒绝缺少或重复的 catalog/timing visual ref。该策略消除了“每 unit 1–2 页”的实施歧义，未来拆页必须提升 schema version。
- `DynamicInfographicPropsV1` 固化 `schemaVersion: 1`、帧坐标及 run-relative asset reference 语义。毫秒 cue 坐标转为零基 frame；时长 frame count 为 `ceil(duration_ms * fps / 1000)`，区间 end 为 exclusive。保留 `InfographicVideoProps` 兼容别名仅服务既有 local default props；新的 adapter/task-package 必须生成严格 V1。
- manifest/evidence 均为 V1、hash-only、run-relative 的最小 P2/P6 输入：manifest 有 output relative path、output/probe hashes、size、duration、frames；evidence 有 UTC verification time、renderer/lockfile/props/service/index/manifest/MP4 hashes 与工具版本。domain 拒绝绝对路径、父目录逃逸与 secret 字段。
- 新增黄金 JSON：空 storyboard（应拒绝）、单 visual、同 Voice Unit 多 visual/跨 Voice Unit 时序，以及 1050ms@30fps 的 props/frame conversion；相同 props 有严格 TypeScript checked companion。

## 执行门槛

| 命令 | 退出码 | 结果 | 耗时 |
| --- | ---: | --- | ---: |
| `pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py` | 0 | PASS — 66 passed | 0.59s |
| `npm run build`（`video_renderer/`） | 0 | PASS — `tsc --noEmit`，包括 `DynamicInfographicPropsV1` fixture | 3.0s |
| real render / MP4 / ffprobe | SKIP | 不属于 P1，未执行 | — |
| task creation / submission / capability activation | SKIP | 不属于 P1，未执行 | — |

## 文件边界

- `csboard/domain/infographic.py`
- `video_renderer/src/types.ts`
- `video_renderer/src/fixtures/dynamic-infographic-props-v1.ts`
- `tests/test_infographic_domain.py`
- `tests/fixtures/infographic/{storyboard-empty-v1,storyboard-single-visual-v1,storyboard-multi-visual-v1,dynamic-infographic-props-v1}.json`
- 本回执

未修改 pipeline、commands/API/CLI、renderer adapter、capabilities、legacy/webapp、任何动态信息图 WebUI 或预置音色内容；未创建 render、MP4、任务、提交、commit 或 push。

## 未授权项

- P2 adapter/render validation：须独立 P1 PASS 后由 PM 派发。
- P3a bootstrap readiness：须独立 P1 PASS 后由 PM 派发；本 P1 未探测或激活工具链。
- P4+、P6 real smoke、P3b activation、`create-options.available` 与任何用户/API/WebUI submission：均未授权。

## Rework：独立验证 FAIL 修复

原因总结：原 `_relative()` 只依赖 `PurePosixPath` 的绝对路径判断，因而未拒绝 `C:/...`、`C:relative` 与 URI scheme；原 `_no_secret()` 只检查 mapping key，嵌套 list/dict 中的显式凭据字符串可穿透。

修复（仍严格位于 P1 domain/test 边界）：

- `_relative()` 现拒绝所有 URI/Windows-drive 前缀、反斜杠、POSIX 绝对路径、`..` 逃逸及 `./` 路径；只保留 run-relative POSIX 路径。
- `_no_secret()` 递归检查任意嵌套字符串值，拒绝显式 `api_key`/`secret`/`password` 赋值、带 token/key 形式的 token-like 值，以及 token-like Bearer 值；普通叙事文本（例如 `Token economics and bearer market dynamics.`）不匹配，避免误伤。
- 增加并保留稳定断言矩阵：`C:/`、`C:relative`、`file://`、反斜杠、`..` 都是 `ABSOLUTE_PATH_FORBIDDEN`；嵌套 api key/password/token/Bearer 值都是 `SECRET_FORBIDDEN`。

复跑门禁（项目根目录）：

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py` | 0 | `76 passed in 0.62s` |
| `npm --prefix video_renderer run build` | 0 | `tsc --noEmit` |

本工作树中该两模块当前共有 76 项（原先回执的 66 项基数已被后续 P1 fixture/contract 覆盖扩展）；实际结果如上，未将计数写成 63 而掩盖当前测试集合。**READY_FOR_REVERIFY**。
