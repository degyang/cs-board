# M02 审计报告 — PR-2: Provider 端口与适配器

日期: 2026-08-29
分支: `feat/mountain-m07-project-api-web-v2`

---

## 变更摘要

### 新增文件（源码，15 个，1088 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `csboard/domain/provider_types.py` | 166 | 14 个 frozen dataclass：请求/结果/能力类型 |
| `csboard/ports/providers.py` | 63 | 6 个 Protocol（重写）：TextModel, ImageModel, TTS, Alignment, Renderer, Media |
| `csboard/ports/__init__.py` | 27 | 统一导出所有端口（扩展） |
| `csboard/adapters/fakes/__init__.py` | 21 | Fake 适配器包 |
| `csboard/adapters/fakes/fake_text_model.py` | 49 | FakeTextModel — 固定文本返回 |
| `csboard/adapters/fakes/fake_image_model.py` | 53 | FakeImageModel — 1×1 PNG 占位 |
| `csboard/adapters/fakes/fake_tts.py` | 61 | FakeTTS — 静默 WAV |
| `csboard/adapters/fakes/fake_alignment.py` | 44 | FakeAlignment — 等距时间戳 |
| `csboard/adapters/fakes/fake_renderer.py` | 48 | FakeRenderer — 空 MP4 占位 |
| `csboard/adapters/fakes/fake_media.py` | 65 | FakeMedia — 固定 probe + no-op 操作 |
| `csboard/adapters/openai_compatible/__init__.py` | 1 | 包 |
| `csboard/adapters/openai_compatible/text_adapter.py` | 154 | OpenAITextAdapter — chat_completions + responses 协议 |
| `csboard/adapters/openai_compatible/image_adapter.py` | 153 | OpenAIImageAdapter — generations + edits |
| `csboard/adapters/indextts/__init__.py` | 1 | 包 |
| `csboard/adapters/indextts/tts_adapter.py` | 182 | IndexTTSAdapter — Gradio + FastAPI 模式 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `csboard/ports/providers.py` | 完全重写 — `dict[str, Any]` → 类型化 Protocol |
| `csboard/ports/__init__.py` | 扩展导出 — 新增 RendererPort, MediaPort |

### 新增文件（测试，6 个，571 行）

| 文件 | 行数 | 测试数 | 覆盖功能 |
|------|------|--------|----------|
| `tests/test_provider_types.py` | 110 | 14 | 所有类型的默认值、frozen 不可变 |
| `tests/test_port_conformance.py` | 88 | 12 | 6 个 fake 满足端口协议 + 方法存在性 |
| `tests/test_fake_adapters.py` | 148 | 16 | 6 个 fake 的 happy path + 失败注入 |
| `tests/test_openai_text_adapter.py` | 87 | 4 | mock HTTP: chat_completions + responses + error + capabilities |
| `tests/test_openai_image_adapter.py` | 64 | 3 | mock HTTP: b64 生成 + error + capabilities |
| `tests/test_indextts_adapter.py` | 74 | 3 | mock HTTP: FastAPI 模式 + duration 探测 |

---

## 设计决策

### 与 `docs/Mountain/11-openai-compatible-model-architecture.md` 的对应

| 文档要求 | 实现情况 | 偏离说明 |
|----------|----------|----------|
| `TextModelPort.generate()` + `capabilities()` | ✅ 使用 `TextGenerationRequest/Result` | — |
| `ImageModelPort.generate()` + `capabilities()` | ✅ 使用 `ImageGenerationRequest/Result` | — |
| `TTSPort.synthesize()` | ✅ 使用 `TTSRequest/Result` | — |
| `AlignmentPort.align()` | ✅ 使用 `AlignmentRequest/Result` | — |
| `RendererPort` | ✅ 新增 `render()` + `capabilities()` | — |
| `MediaPort` | ✅ 新增 `probe/normalize/concat/subtitle` | — |
| Provider Profile 配置 | ❌ 未实现 | 留给后续 PR，当前用构造函数参数 |
| `secret_ref` 集成 | ❌ 未实现 | 留给后续 PR，当前直接传 `api_key` |
| Chat Completions + Responses 双协议 | ✅ `OpenAITextAdapter._protocol` 切换 | — |
| Image edits (参考图) | ✅ `OpenAIImageAdapter._generate_with_reference()` | — |
| 重试策略 | ✅ 指数退避，最多 3 次 | — |

### 偏离设计的地方

1. **Provider Profile 未实现** — 文档要求通过 named profile 配置 `base_url`/`secret_ref`/`model`。当前适配器通过构造函数参数直接传入。Profile 系统与 SecretStore 集成后可在后续 PR 补充。
2. **`TextModelPort` 方法名** — 文档用 `generate`，旧代码用 `complete`。统一采用 `generate`，旧签名不再保留。
3. **Fake 适配器无延迟注入测试** — `latency_ms` 参数已实现，但测试中未验证实际延迟行为（避免测试变慢）。
4. **IndexTTS Gradio 模式依赖 `gradio_client`** — 该依赖在 webapp 环境中已有，但在 csboard 核心包中是可选导入。

---

## 测试覆盖

- **51 个新测试**，全部通过
- **132 个总测试**（含既有 81 个），全部通过，无回归
- 4 个 FileSecretStore 测试因 `cryptography` 未安装而跳过

### 关键测试场景

- 端口结构类型验证（`runtime_checkable` Protocol）
- 所有 fake 适配器的 happy path 和 failure injection
- OpenAI text adapter 的两种协议（chat_completions / responses）
- OpenAI image adapter 的 b64 解码
- IndexTTS FastAPI 模式的 WAV 生成
- WAV duration 探测准确性

---

## 遗留问题

1. **Provider Profile 系统** — 需要设计 profile 配置格式、加载逻辑、SecretStore 集成。当前适配器用硬编码参数。
2. **`gradio_client` 可选依赖** — IndexTTS Gradio 模式需要 `pip install gradio_client`，应声明为可选依赖。
3. **错误码体系** — 文档定义了 `MODEL_AUTH_FAILED`、`MODEL_RATE_LIMITED` 等错误码，当前只抛 `RuntimeError`。需要扩展 `DomainError` 子类。
4. **旧端口签名兼容** — `csboard/application/voice_units.py` 中的 `VoiceSynthesizer`/`VoiceAligner` Protocol 仍用 `dict[str, Any]`，需要在 M05 中对齐。
5. **RendererPort 无真实适配器** — 白板渲染和 Remotion 渲染的真实适配器留给 M06 Stage 实现。

---

## 签收

- [x] 代码审查通过
- [x] 测试全部通过（132/132，4 skipped）
- [x] 文档已更新（本文件）
