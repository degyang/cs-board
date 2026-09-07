# SUBTITLE-TIMING-001-V — 独立字幕时间复验

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`）；只读检查主集成区。

## 冻结目标

- 工作目录：`/mnt/d/workstation/projects/cs-board`
- 原始任务：`docs/workmates/assignments/SUBTITLE-TIMING-001.md`
- 实现回执：`docs/workmates/receipts/SUBTITLE-TIMING-001.md`
- 实现文件哈希以回执六项为准；复验前后必须重新计算并一致。
- 回执：`docs/workmates/receipts/SUBTITLE-TIMING-001-V.md`
- 新 Workmates 证据：`.workmates-evidence/SUBTITLE-TIMING-001-V.json`

## 必须独立验证

1. 逐条映射原始六项验收标准，不复用实现者的 PASS 结论。
2. 重新运行：`.venv/bin/python -m pytest -q tests/test_subtitle_timing_001.py tests/test_av_timing.py tests/test_voice_units.py tests/test_composition_service.py tests/test_mountain_contracts.py`。
3. 使用合成输入独立调用共享内核，至少观察两个 Voice Unit：一段有效 Whisper 字符时间、一段低覆盖或异常时间的整单元 `text_length_fallback`；写出临时 SRT 后核对文本无遗漏、顺序、可读分段、累计 offset、单调无重叠、首尾严格落在各自 unit 边界。
4. 核对 fallback 按去空白字符权重使用该 unit 的实际 `duration_ms`，末 cue 严格等于 unit 结束；核对极短时长不会产生零长度 cue。
5. 核对 timeline/final manifest 可见 `subtitle_timing_source`、fallback reason 与 cue count；旧 timeline 缺少新字段时在 compose 处兼容回退，不能恢复旧 server 路由。
6. 运行 `git diff --check` 和 `./scripts/workmates verify --role verification --evidence .workmates-evidence/SUBTITLE-TIMING-001-V.json`。

## 边界与出口

- 不修改实现、既有测试、任务标准、服务、Secrets、真实素材、M09 pointer 或看板。
- 可新建上述验证回执和新证据；临时合成产物放独立 `/tmp` 并清理。
- 输出 `PASS / FAIL / BLOCKED`，列明命令、退出码、测试数量、逐项观察、目标前后哈希和未验证范围。完成后停止等待 PM 消费。
