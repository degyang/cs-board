# M09-INFRA-CONTRACT-001-V — P1 领域契约独立验证回执

状态：**PASS**

验证人：`tester_backend`。本次为只读独立验证：未修改实现、测试、计划或配置；未执行 real render、MP4/ffprobe、任务创建或 submission。

## 独立执行证据

| 命令 | 结果 |
| --- | --- |
| `pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py`（仓库根目录） | **PASS — 66 passed in 0.64s**, exit 0 |
| `npm run build`（`video_renderer/`） | **PASS — `tsc --noEmit`**, exit 0 |

## 七项验证结论

1. **版本化契约：PASS。** `InfographicStoryboard`、`DynamicInfographicPropsV1`、`RenderManifestV1` 与 `RemotionEvidenceV1` 均固定 V1/schema 字段；golden fixture 覆盖空（拒绝）、单 visual、多 visual 和 props 1050ms@30fps。
2. **页面策略：PASS。** `VOICE_UNIT_PAGE_STRATEGY` 明确为 `exactly_one_page_per_voice_unit`；多 visual 固定为同页 node/cue，并由 focused tests 覆盖。
3. **时间、帧、ID 不变量：PASS。** absolute-ms、start-inclusive/end-exclusive、start floor 与总帧 ceil、页面/cue 有序和稳定 ID 均经 domain suite 通过。
4. **相对路径与 secret：PASS。** 当前验证器拒绝 POSIX 绝对路径、Windows drive/URI、反斜杠与父目录逃逸；回归矩阵也拒绝显式 credential 值，同时允许普通叙述中的 `token` 一词。
5. **schema round-trip / TS props：PASS。** storyboard golden round-trip 与空 storyboard 拒绝通过；V1 typed fixture 被 `tsc --noEmit` 实际检查。
6. **依赖边界：PASS。** `csboard/domain/infographic.py` 仅依赖标准库及 `csboard.domain.enums`；未发现 domain 对 Remotion、subprocess、webapp、provider、adapter 或 application 的 import。
7. **P1 文件与禁止事项：PASS。** 核查未见 pipeline、CLI/API、capability、legacy/webapp 或 renderer 实施被 P1 改动；本验证也未触发 render、任务或 submission。

此前回执记录的 Windows 路径和 secret-value 拒绝缺口，现已由实现的 `_URI_OR_WINDOWS_DRIVE` / `_SECRET_VALUE` 规则及 `test_v1_rejects_non_posix_or_escaping_asset_path_matrix`、`test_v1_rejects_explicit_secret_value_matrix` 覆盖，并包含在本次 66 项通过证据中。

## 授权边界

本 PASS **仅**授权 PM 并行派发 **P2** 与 **P3a bootstrap readiness**。不授权 P3b/P4/P5/P6、real render、MP4/ffprobe、`create-options.available`、任务创建或用户/API/WebUI submission。

## Reverify — 路径与 secret rework

结论：**PASS**。本次仅复验 rework 与既有 P1 契约；未修改产品代码、测试、配置或规划，未执行 real render。唯一写入仍是本验证回执。

### `-B` 最小调用（exit 0）

以 `.venv/bin/python -B` 调用 `validate_infographic_storyboard()`，以下输入均稳定抛出所列错误码：

- `C:/render/infographic.mp4` → `ABSOLUTE_PATH_FORBIDDEN`
- `C:render/infographic.mp4` → `ABSOLUTE_PATH_FORBIDDEN`
- `file:///render/infographic.mp4` → `ABSOLUTE_PATH_FORBIDDEN`
- `render\\infographic.mp4` → `ABSOLUTE_PATH_FORBIDDEN`
- `render/../infographic.mp4` → `ABSOLUTE_PATH_FORBIDDEN`
- 嵌套 `api_key=...`、`password: ...`、`token=...`、`Bearer ...` 值 → 均为 `SECRET_FORBIDDEN`
- 普通叙事 `Token economics and bearer market dynamics.` → 接受。

实现依据：`csboard/domain/infographic.py:25-32,46-66`。URI/Windows drive 前缀、反斜杠、POSIX 绝对/父目录路径均由 `_relative()` 拒绝；`_no_secret()` 递归检查 Mapping/list/tuple，并仅对显式 credential 语法的字符串值拒绝，避免误伤普通叙事。新增参数化测试覆盖相同矩阵（`tests/test_infographic_domain.py:252-281`）。

### 必要门禁

```text
.venv/bin/python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_contract_fixture.py tests/test_infographic_storyboard_adapter.py
77 passed in 0.77s
exit 0

npm --prefix video_renderer run build
tsc --noEmit
exit 0
```

### P1 回归核验

**PASS** — v1 schema/round-trip、空/单/多 visual、绝对毫秒与 frame 语义、limits、确定错误码和缺 visual ref 校验仍在 `csboard/domain/infographic.py:11-23,69-85,128-225`；fixture/TS v1 契约仍在 `video_renderer/src/types.ts:59-112` 与 `tests/fixtures/remotion-smoke-props.json`，build 通过；domain 仍无 adapter/Remotion/subprocess/webapp import。P1 允许边界外的 pipeline/API/CLI/webapp 未被本次 rework 修改。

此前路径与 secret-value 拒绝缺口已由独立最小调用与专项门禁复证。P1 继续为 PASS；本结论不授权 real render 或 WebUI submission。
