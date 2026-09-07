# SUBTITLE-TIMING-001 — Voice Unit scoped subtitle cues

状态：done（2026-09-07 PM 接受；独立 `SUBTITLE-TIMING-001-V` PASS）

Owner：`backend`；PM 集成；verification 独立行为复验。

工作目录：`/mnt/d/workstation/projects/cs-board-worktrees/backend`

回执：`docs/workmates/receipts/SUBTITLE-TIMING-001.md`

停止条件：完成实现与本任务有针对性的测试后写回执并停止；不得顺带修改或集成
`M09-ACTIVATE-005`，不得启动真实 provider、生成真实用户内容、提交、merge 或 push。

## 用户要求

当前字幕错误地把一个 Voice Unit 的整段文字作为单条字幕，覆盖该段语音全部时长。目标行为：一段语音内按可读短句逐条显示对应文字；Whisper 可用时使用真实文字时间；Whisper 失败时只在当前 Voice Unit 的实际语音时长内，按字幕文字有效字符长度比例分配时间。不得跨 Voice Unit 借用或累计时间。

## 参考与约束

- 当前缺口：`csboard/application/composition.py` 只为每个 unit 生成一个 full-text cue，忽略更细字幕时间。
- 可参考旧实现：`backend/server.py::_subtitle_chunks()` 与 `write_subtitles()`；它按标点/最大字符数切分，并在无有效 `subtitle_cues` 时按非空白字符长度加权分配 scene 时长。
- 新实现必须进入 Mountain 的 Voice Unit / `timing.timeline` / `compose-video` 共享内核，不得恢复旧 server 路由或建立第二套时间轴。
- 保持既有图片时间规则：Whisper 对齐失败时 Visual Item 仍按现行契约处理；字幕 fallback 是单元内字幕 cue 分配，不能改变 Voice Unit、Visual Item、音频或图片边界。

## 验收方向

1. 每个 Voice Unit 的字幕按中文标点和可读最大长度切成多条，输出文本顺序与原文一致、无遗漏、无跨 unit。
2. Whisper 有效时字幕 cue 使用单元内真实 char/caption 时间并校验覆盖、单调、边界；无效则整个 unit 采用 `text_length_fallback`，不混用真假时间。
3. fallback 使用该 unit 实际 voice `duration_ms`，按去除空白后的字符数比例分配；首条从 unit 起点开始，末条结束严格等于 unit 结束，零长度/舍入安全。
4. compose 阶段把各 unit 局部 cue 加上累计 voice offset 后写 SRT；任一 cue 不得早于本 unit 或晚于本 unit。
5. timeline/final manifest 明确记录 `timing_source` 与 fallback reason，Whisper 失败可见但不阻断成片。
6. 覆盖 Whisper success、低覆盖/异常 fallback、多 unit、长中文、标点、舍入、空白和 SRT 边界测试；对照旧实现行为测试，不读取真实素材、不调用 provider。

完成实现后需独立验证生成的 SRT 内容和时间区间；最终视频字幕视觉效果仍由用户验收。
