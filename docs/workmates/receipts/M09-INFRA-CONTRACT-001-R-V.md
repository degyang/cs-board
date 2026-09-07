# M09-INFRA-CONTRACT-001-R-V — P1 契约独立复验回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、服务、配置或看板。P2/P3a 未推进。

## 验证范围

P1 scoped files only：
- `csboard/domain/infographic.py`
- `video_renderer/src/types.ts`
- `tests/test_infographic_domain.py`
- `tests/test_infographic_storyboard_adapter.py`
- `tests/test_infographic_contract_fixture.py`

## Diff 状态

| 检查点 | 结果 |
| --- | --- |
| Pre-check `git diff --name-only`（P1 scoped） | 空——P1 scoped 文件无变更 |
| Post-check `git diff --name-only`（P1 scoped） | 空——验证期间无写入 |
| `git diff --check` | exit 0 |

P1 scoped 文件在验证前后完全相同，无漂移。

## 门禁独立复验

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py` | 0 | **77 passed**, 0.77s, 0 skipped |
| `npm --prefix video_renderer run build` | 0 | `tsc --noEmit` 通过 |
| `git diff --check` | 0 | 通过 |
| `./scripts/workmates verify --role verification --evidence /tmp/m09-contract-001-r-v-evidence.json` | 0 | PASS |

与实现回执声称的 77 passed 一致。

## P1 语义逐项核验

| 不变量 | 代码位置 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| V1 versioning | `infographic.py:11` `INFOGRAPHIC_SCHEMA_VERSION=1`；`types.ts:66` `schemaVersion: 1` required | 两端均为 V1 常量/required 字段 | PASS |
| 稳定 ID | `infographic.py:22` `_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")`；`:42` `_id()` 校验 | page/node/cue/visual/unit 全部经 `_id()` | PASS |
| Exactly one page per Voice Unit | `infographic.py:21` `VOICE_UNIT_PAGE_STRATEGY = "exactly_one_page_per_voice_unit"`；`:196` `voice_units_to_pages` 逐 unit 生成一页 | V1 固定策略，不拆分 | PASS |
| 毫秒/frame start-inclusive/end-exclusive | `infographic.py:69-78` `milliseconds_to_frame`: `ms * fps // 1000`（floor）；`:81-85` `duration_frames`: `(ms * fps + 999) // 1000`（ceil） | floor 用于 cue start（start-inclusive），ceil 用于总帧数（不丢尾帧） | PASS |
| Run-relative-only artifact refs | `infographic.py:46-51` `_relative()`: 拒绝绝对路径、`..`、Windows drive、URI scheme、`./` 前缀 | 覆盖所有逃逸模式 | PASS |
| 拒绝空 storyboard | `infographic.py:149` `not storyboard.pages → EMPTY_STORYBOARD` | PASS |
| 拒绝重叠 | `infographic.py:159` `page.cue_start_ms < last_page_end → OVERLAPPING_TIMELINE` | PASS |
| 拒绝零时长 | `infographic.py:151` `total_duration_ms <= 0 → INVALID_DURATION`；`:158` `cue_end_ms <= cue_start_ms → INVALID_PAGE_TIMING` | PASS |
| 拒绝未知 node | `infographic.py:105-106` `kind not in INFOGRAPHIC_NODE_KINDS → UNKNOWN_NODE_KIND` | PASS |
| 拒绝缺 visual | `infographic.py:188+` `voice_units_to_pages` 要求 `visual_id` 存在于 `storyboard_visuals` | PASS |
| 拒绝 secret | `infographic.py:24-31` `_SECRET` + `_SECRET_VALUE` regex；`:54-66` `_no_secret()` 递归扫描 key/value | PASS |
| TS strict props | `types.ts:65-77` `DynamicInfographicPropsV1`: `schemaVersion: 1`, `totalDurationFrames: number` 均 required | PASS |
| Manifest hash-only | `types.ts:89-98` `RenderManifestV1`: sha256/size/duration/frames/probe，无路径 | PASS |
| Evidence hash-only | `types.ts:101-112` `RemotionEvidenceV1`: 全 sha256 字段，无原始路径/secret | PASS |

## 证据文件

- `/tmp/m09-contract-001-r-v-evidence.json`（machine-readable）

---

**最终判定：PASS**

所有77项测试通过、TS build 通过、P1 scoped diff 验证前后为空、14项 P1 不变量均由代码确认。P2/P3a 未推进，等待 PM 授权。
