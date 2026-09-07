# M09-INFRA-CONTRACT-001-R — P1 契约冻结续作回执

状态：`READY_FOR_INDEPENDENT_P1_VERIFICATION`

本轮只检查并复跑当前集成区的 P1 契约；P1 允许范围内没有新的待修复 diff，因此未改 domain、props、fixture 或测试。唯一写入为本回执。未推进 P2/P3a，未改 pipeline、commands/API/CLI、renderer adapter、capability、legacy/webapp、配置或产品提交状态；未 render、创建任务、开放 capability/submission、commit 或 push。

## 当前 P1 契约核对

- `csboard/domain/infographic.py` 保持 V1 schema、稳定 page/node/cue ID、绝对毫秒 start-inclusive/end-exclusive 时序和 `exactly_one_page_per_voice_unit` 策略。
- domain validation 保持拒绝空 storyboard、重叠/零时长、未知 node、缺 visual/timing、非 run-relative 路径（含绝对/Windows/URI/父目录逃逸）和嵌套 secret 值；manifest/evidence 为 hash-only 输入。
- `video_renderer/src/types.ts` 保持严格 `DynamicInfographicPropsV1`、零基 frame 语义、end-exclusive frame span 及 `ceil(duration_ms * fps / 1000)` 总帧语义。
- golden fixtures 与 P1 测试覆盖空/单/多 visual、round-trip、时间/帧转换及 props contract；当前集成 diff 中这些 P1 文件均未出现新的变更。

## 本轮可复跑证据

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py` | 0 | `77 passed in 0.83s`，0 skipped |
| `npm --prefix video_renderer run build` | 0 | `tsc --noEmit` 通过 |
| `git diff --check` | 0 | 通过 |

历史 `M09-INFRA-CONTRACT-001.md` 仅作为线索，未替代本轮实际检查。以上是实现者自检，不构成独立验证或验收；P2/P3a 仍须待独立 P1 PASS 后由 PM 单独授权。
