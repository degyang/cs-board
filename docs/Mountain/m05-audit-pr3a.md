# M05 审计报告 — PR-3a: 类型统一 + VoiceUnitService 重构 + CLI 接线

日期: 2026-08-29
分支: `feat/mountain-m07-project-api-web-v2`

---

## 变更摘要

### 修改文件（5 个）

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `csboard/domain/av_timing.py` | 重构 | 删除本地 `AlignmentResult`，统一使用 `provider_types.AlignmentResult` |
| `csboard/application/voice_units.py` | 重写 | `VoiceUnitService` 改用 M02 端口（`TextToSpeechPort` + `AlignmentPort` + `MediaPort`）；删除 `VoiceSynthesizer`/`VoiceAligner` 本地 Protocol；添加向后兼容适配器 |
| `csboard/application/commands.py` | 扩展 | 新增 `clone_voice()` 方法（~60 行） |
| `cli/csboard.py` | 扩展 | `stage run clone-voice` 从 stub 改为真实调用；新增 `--reference`/`--tts-url`/`--tts-mode` 参数 |
| `webapp/mountain_stages.py` | 适配 | `clone_voice()` 使用 `_LegacySynthesizerAdapter`/`_LegacyAlignerAdapter`/`_NoOpMedia` 适配新签名 |

### 测试文件（2 个修改）

| 文件 | 变更 |
|------|------|
| `tests/test_voice_units.py` | 重写 — 使用 `FakeTTS` + `FakeAlignment` + `FakeMedia` 替代旧的 `FakeSynthesizer`/`FailingAligner` |
| `tests/test_cli_csboard.py` | 更新 — stub 测试改用 `plan-storyboard`（`clone-voice` 已是真实命令） |

---

## 设计决策

### 1. AlignmentResult 统一

**问题**：`domain/av_timing.py` 和 `domain/provider_types.py` 各自定义了 `AlignmentResult`，字段相同但类型不同。

**方案**：删除 `domain/av_timing.py` 中的定义，从 `provider_types` 导入。`__all__` 导出保持不变，下游代码无感。

**偏离**：无。两个类字段完全一致，只是合并为一个。

### 2. VoiceUnitService 重构

**旧接口**：
```python
VoiceUnitService(repo, synthesizer: VoiceSynthesizer, aligner: VoiceAligner)
```

**新接口**：
```python
VoiceUnitService(tts: TextToSpeechPort, alignment: AlignmentPort, media: MediaPort, repository, reference_audio)
```

**关键变更**：
- `_synthesize_unit()` — 构建 `TTSRequest`，调 `self.tts.synthesize()`，用 `self.media.probe()` 探测时长
- `_align_unit()` — 写音频到临时文件，构建 `AlignmentRequest`，调 `self.alignment.align()`
- 删除 `SynthesizedVoice`，用 `TTSResult` 替代（别名 `SynthesizedVoice = TTSResult` 保留兼容）

### 3. 旧桥接兼容

`webapp/mountain_stages.py` 使用旧的 `VoiceSynthesizer`/`VoiceAligner` 接口。通过三个适配器桥接：
- `_LegacySynthesizerAdapter` — 包装旧 `VoiceSynthesizer` 为 `TextToSpeechPort`
- `_LegacyAlignerAdapter` — 包装旧 `VoiceAligner` 为 `AlignmentPort`
- `_NoOpMedia` — 空操作 `MediaPort`（旧桥接不需要媒体操作）

### 4. CLI clone-voice 实现

默认使用 `FakeTTS` + `FakeAlignment` + `FakeMedia`。当 `--tts-url` 不是默认值时，切换为 `IndexTTSAdapter`。Whisper 适配器待 PR-3b 补全。

---

## 测试覆盖

- **133 个测试全部通过**（4 个因 `cryptography` 未安装跳过）
- `test_voice_units.py` — 3 个测试：重用已有音频、异常对齐回退、成功对齐路径
- `test_cli_csboard.py` — stub 测试更新为 `plan-storyboard`

---

## 遗留问题

1. **CLI 默认用 Fake 适配器** — `clone-voice` 默认跑 FakeTTS，不产生真实语音。真实 TTS 需要指定 `--tts-url`。
2. **无 Whisper 适配器** — `FakeAlignment` 返回的 `starts_ms` 用字符作 key，无法通过 whisper 验证（key 应为 visual_id）。所有单元都会走 equal_fallback。真实 Whisper 适配器在 PR-3b 实现。
3. **临时文件清理** — `_synthesize_unit()` 和 `_align_unit()` 使用 `tempfile`，在异常时可能残留。可考虑使用 `RuntimePaths.temp_dir`。
4. **`mountain_stages.py` 适配器是临时方案** — 旧桥接的三个适配器（`_Legacy*`）是过渡代码，M03 跳过后应随旧桥接一起移除。

---

## 签收

- [x] 代码审查通过
- [x] 测试全部通过（133/133，4 skipped）
- [x] 文档已更新（本文件）
