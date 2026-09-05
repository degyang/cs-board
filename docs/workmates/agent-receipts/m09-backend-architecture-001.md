# M09 Backend Architecture Inventory 001

状态：只读盘点，未提交。
日期：2026-09-05
范围：Task/Run/Artifact/Trace/Capability 实际接入点、旧 webapp/server.py 耦合点、本地/模型服务边界。

---

## 1. Task / Run / Artifact / Trace 实际接入点

### 1.1 领域模型

| 实体 | 位置 | 关键字段 |
|---|---|---|
| `Task` | `csboard/domain/models.py` | task_id, title, engine (Engine enum), pipeline_id, status, active_run_id, revision |
| `Run` | `csboard/domain/models.py` | run_id, task_id, trace_id, entrypoint, status, stages (dict[str, StageState]) |
| `StageGate` | `csboard/domain/stage_gate.py` | task_id, run_id, trace_id, stage_id, status, revision, evidence (tuple) |
| `ExecutionPlan` | `csboard/domain/execution_plan.py` | mode (auto/selective), manual_stages |
| `Engine` | `csboard/domain/enums.py` | WHITEBOARD = "whiteboard", INFOGRAPHIC_REMOTION = "infographic-remotion" |

### 1.2 持久化层

| 组件 | 位置 | 职责 |
|---|---|---|
| `FilesystemTaskRepository` | `csboard/adapters/filesystem/repository.py` | Task/Run/Gate/Request CRUD；package locator；staging 事务；output root 解析 |
| `JsonlTelemetry` | `csboard/adapters/observability/jsonl.py` | Event/Log/Audit append-only JSONL；诊断 bundle 导出 |
| `FilesystemAssetRepository` | `csboard/adapters/filesystem/asset_repository.py` | 本地音频/风格资产文件管理 |

Task 包结构：`outputs/<task_id>/` 下含 `task.json`, `task-package.json`, `inputs/`, `runs/<run_id>/` (含 planning/audio/images/clips/subtitles/manifests/evidence/final/artifacts/)。

### 1.3 应用层

| 方法 | 位置 | 接入点 |
|---|---|---|
| `MountainCommands.create_task()` | `csboard/application/commands.py:111` | 创建 Task + Run，写入 output root |
| `MountainCommands.save_inputs()` | `commands.py:350` | 保存脚本/参考音频/执行计划到 inputs/ |
| `MountainCommands.start_run()` | `commands.py:634` | 启动 Run，触发 pipeline |
| `MountainCommands.pipeline_run()` | `commands.py:1163` | 按 ExecutionPlan 驱动六阶段 |
| `MountainCommands.stage_run()` | `commands.py:1078` | 单阶段执行入口 |
| `MountainCommands.generate_visual_anchors()` | `commands.py:710` | 阶段 1：视觉锚点 |
| `MountainCommands.clone_voice()` | `commands.py:902` | 阶段 2：语音克隆 (TTS + 对齐 + 媒体) |
| `MountainCommands.plan_storyboard()` | `commands.py:1314` | 阶段 3：分镜规划 |
| `MountainCommands.artifact_show()` | `commands.py:986` | 读取 Artifact 内容 |
| `MountainCommands.trace_run()` | `commands.py:692` | 读取 Trace (events) |
| `MountainCommands.export_diagnostics()` | `commands.py:706` | 导出诊断 bundle |

### 1.4 HTTP API 层

| Router | 位置 | 端点前缀 |
|---|---|---|
| `mountain_task_router` | `webapp/mountain_task_api.py` | `/api/v1/tasks`, `/api/v1/scripts`, `/api/v1/directories` |
| `mountain_asset_router` | `webapp/mountain_asset_api.py` | `/api/v1/assets` |
| `mountain_capability_router` | `webapp/mountain_capability_api.py` | `/api/v1/capabilities` |
| `mountain_service_router` | `webapp/mountain_service_api.py` | `/api/v1/services` |
| `mountain_settings_router` | `webapp/mountain_settings_api.py` | `/api/v1/settings` |
| `mountain_voice_profile_router` | `webapp/mountain_voice_profile_api.py` | `/api/v1/voice-profiles`, `/api/v1/voice-style-profiles` |

### 1.5 CLI 层

| 入口 | 位置 | 说明 |
|---|---|---|
| `cli/csboard.py:main()` | `cli/csboard.py:550` | 唯一 CLI 入口，通过 `execute()` 分派 |
| `cli/csboard.py:execute()` | `cli/csboard.py:263` | 构造 `MountainCommands` 实例，按 resource/action 分派 |

CLI 创建 `FilesystemTaskRepository(args.data_dir, project_root=ROOT)`，其中 `ROOT = Path(__file__).resolve().parents[1]`。未指定 `--output-root` 时，`resolve_output_root(None)` 返回 `project_root / "outputs"`。

---

## 2. Capability / Service / Provider 实际接入点

### 2.1 服务定义与注册

| 组件 | 位置 | 职责 |
|---|---|---|
| `ServiceDefinition` | `csboard/domain/service_definition.py` | 单 capability 的服务 DTO |
| `FilesystemServiceRegistry` | `csboard/adapters/filesystem/service_registry.py` | 服务 CRUD、健康探测、Secret 绑定 |
| `default_services.seed()` | `csboard/application/default_services.py` | 首次启动幂等安装 6 个默认服务 |

默认服务清单：

| service_id | capability | adapter_type | 说明 |
|---|---|---|---|
| `openai-compatible-text` | text_generation | openai_compatible | 文本模型 |
| `openai-compatible-image` | image_generation | openai_compatible | 图片模型 |
| `local-indextts` | speech_synthesis | indextts | 本地 TTS (IndexTTS) |
| `local-whisper` | speech_alignment | whisper | **本地对齐工具链** |
| `whiteboard-renderer` | rendering | local_process | 白板渲染器 |
| `local-ffmpeg` | media | ffmpeg | 媒体处理 |

### 2.2 服务解析

| 组件 | 位置 | 职责 |
|---|---|---|
| `ServiceResolver` | `csboard/application/service_resolver.py` | 按 capability/stage 选择最优服务 |
| `ServiceResolver._configured_services()` | `service_resolver.py:72` | 查询已配置且启用的服务；`speech_synthesis` 包含 `audio_generation` 别名 |
| `STAGE_CAPABILITY_MAP` | `service_resolver.py` | stage → capability 映射 |

### 2.3 Provider 工厂

| 方法 | 位置 | 适配器 |
|---|---|---|
| `ProviderFactory.create_adapter()` | `csboard/adapters/provider_factory.py:478` | 统一入口，按 ServiceDefinition 构造适配器 |
| `openai_compatible` + text_generation | `provider_factory.py:505` | `OpenAITextAdapter` |
| `openai_compatible` + image_generation | `provider_factory.py:513` | `OpenAIImageAdapter` |
| `openai_compatible` + speech_synthesis/audio_generation | `provider_factory.py:520` | `OpenAITTSAdapter` (**新增**) |
| `indextts` | `provider_factory.py:530` | `IndexTTSAdapter` |
| `whisper` | `provider_factory.py:537` | `WhisperAlignmentAdapter` |
| `ffmpeg` | `provider_factory.py:546` | `FFmpegMediaAdapter` |
| `local_process` | `provider_factory.py:550` | `WhiteboardRendererAdapter` |

### 2.4 Capability 投影

| 组件 | 位置 | 职责 |
|---|---|---|
| `CapabilityService.snapshot()` | `csboard/application/capabilities.py:35` | 只读可用性快照，不探测服务 |
| `WHITEBOARD_STAGE_REQUIREMENTS` | `capabilities.py:19` | 白板六阶段能力需求矩阵 |

`snapshot()` 中 `infographic-remotion` 条目硬编码 `supported=False`。

---

## 3. 本地服务 vs 模型服务边界

### 3.1 本地服务（工具链，无 SecretStore）

| 服务 | adapter_type | capability | 运行方式 | 说明 |
|---|---|---|---|---|
| Whisper 对齐 | whisper | speech_alignment | Node.js subprocess (`align.mjs`) 或本地 HTTP | **纯工具链**，不经过 SecretStore，不暴露 API Key |
| IndexTTS | indextts | speech_synthesis | 本地 Gradio HTTP (`127.0.0.1:7860`) | 本地 TTS 服务 |
| 白板渲染 | local_process | rendering | Python 进程内 | WhiteboardRendererAdapter |
| FFmpeg | ffmpeg | media | subprocess | 媒体处理 |

### 3.2 模型服务（远程，经 SecretStore）

| 服务 | adapter_type | capability | SecretStore 键 | 说明 |
|---|---|---|---|---|
| OpenAI 文本 | openai_compatible | text_generation | `<sid>_api_key` | 远程 API |
| OpenAI 图片 | openai_compatible | image_generation | `<sid>_api_key` | 远程 API |
| MiMo TTS | openai_compatible | speech_synthesis | `<sid>_api_key` | **新增**，远程 MiMo V2.5 TTS |
| MiMo TTS (audio_generation 别名) | openai_compatible | audio_generation | `<sid>_api_key` | 历史 capability 名，自动归一化为 speech_synthesis |

### 3.3 Whisper 不是模型服务

Whisper 在当前架构中是**本地对齐工具链**，不是模型服务：

- `adapter_type: "whisper"` → `WhisperAlignmentAdapter`
- 两种运行模式：`node` (调用 `align.mjs` 脚本) 或 `http` (调用本地 faster-whisper-server)
- 不需要 API Key，不经过 SecretStore
- ServiceRegistry 健康探测检查本地进程/端口可达性，不检查远程认证
- `capability: "speech_alignment"` 不出现在 model service UI 中

`provider_types.py` 中 `AlignmentResult.engine` 字段默认值为 `"whisper"`，但这只是标识对齐引擎来源，不表示 Whisper 是可配置的模型服务。

### 3.4 `audio_generation` → `speech_synthesis` 归一化

`audio_generation` 是早期持久化名称。归一化发生在三层：

1. **CapabilityService.snapshot()** (`capabilities.py:52`): `capability = "speech_synthesis" if service.capability == "audio_generation" else service.capability`
2. **ServiceResolver._configured_services()** (`service_resolver.py:74`): 查询 `speech_synthesis` 时自动包含 `audio_generation` 服务，`replace(service, capability="speech_synthesis")`
3. **ProviderFactory.create_adapter()** (`provider_factory.py:520`): `elif capability in {"speech_synthesis", "audio_generation"}`

**已修复 Bug:** `capabilities.py` 原先调用 `list_services()` (返回所有服务) 再 `+= list_services(capability="audio_generation")`，导致 `audio_generation` 服务在 `services_by_capability` 中出现两次。已改为 `seen` 集合去重。

---

## 4. 旧 webapp/server.py 耦合点

### 4.1 直接导入（必须迁移）

| 位置 | 行号 | 导入内容 | 用途 |
|---|---|---|---|
| `webapp/mountain_stages.py` | 27 | `from webapp import server` | `server.synthesize_voice()`, `server.load_config()`, `server.probe_duration()` |
| `webapp/mountain_api.py` | 262 | `from webapp.server import load_config` | 健康检查端点读取 TTS URL |

### 4.2 mountain_server.py 的隔离声明

`webapp/mountain_server.py` 模块文档明确声明：

> 不导入 webapp.server、LegacyJobBridge、JOBS。

`create_app()` 是唯一组合根，所有 Router 通过显式参数注入共享组件。新 Router (`mountain_voice_profile_api.py`) 遵循此模式。

### 4.3 旧端点

`mountain_api.py` 和 `mountain_stages.py` 包含旧端点：

- `mountain_stages.py`: `clone_voice()`, `submit_legacy_full_pipeline()`, `sync_legacy_state()` — 直接调用 `webapp.server`
- `mountain_api.py:262`: `/tasks/{task_id}/runs/{run_id}/health` — 调用 `load_config()` 检查 TTS URL

这些旧端点**不在** `mountain_server.create_app()` 中注册（新 Mountain Server 只注册 `mountain_task_router` 等新 Router）。它们仅通过旧 `webapp/server.py` 的 FastAPI app 暴露。

### 4.4 Legacy Bridge

`csboard/application/legacy_bridge.py` 提供旧任务只读兼容：

- `LegacyBridge.sync_legacy_state()`: 旧任务状态同步
- `_is_infographic()`: 按 `reference_mode/job_type` 检测旧信息图任务
- 不调用 `webapp.server`，只读文件系统

---

## 5. VoiceProfile 接入点（未提交进行中工作）

### 5.1 新增文件

| 文件 | 职责 |
|---|---|
| `csboard/domain/voice_profile.py` | `VoiceProfile` / `VoiceStyleProfile` 领域 DTO |
| `csboard/application/voice_profiles.py` | `VoiceProfileCatalog` 只读目录 + CRUD + 预览 |
| `csboard/adapters/openai_compatible/tts_adapter.py` | `OpenAITTSAdapter` + `preset_voice_profiles()` |
| `webapp/mountain_voice_profile_api.py` | REST API Router |
| `tests/test_voice_profiles_api.py` | 6 个测试，覆盖安全、CRUD、别名、预览 |
| `tests/test_openai_tts_adapter.py` | 2 个测试，覆盖 payload 和错误脱敏 |

### 5.2 安全契约

- API Key 仅由 `SecretStore` 保存，不进入 VoiceProfile DTO、API 响应、错误文本
- 预览调用 `provider_factory.create_adapter(service).synthesize(TTSRequest(...))`，通过 mock 验证
- `preset_voice_profiles()` 硬编码 MiMo 预置音色元数据（冰糖/茉莉/苏打/白桦/Mia/Chloe/Milo/Dean），不从 API Key 或远程 API 获取

---

## 6. 对 M09 动态信息图的影响

### 6.1 可直接复用的接入点

| 接入点 | 说明 |
|---|---|
| `FilesystemTaskRepository` | Task/Run/Gate 持久化，已支持 `Engine.INFOGRAPHIC_REMOTION` |
| `JsonlTelemetry` | Event/Log append，与引擎无关 |
| `MountainCommands.pipeline_run()` | 六阶段编排，与引擎无关 |
| `mountain_task_router` | Task CRUD API，`engine` 参数已通过 |
| `ServiceResolver` | 按 capability 解析服务 |
| `CapabilityService.snapshot()` | 只读可用性投影 |

### 6.2 需要新增/修改的接入点

| 接入点 | 当前状态 | M09 需求 |
|---|---|---|
| `ProviderFactory.create_renderer()` | 硬编码 `WhiteboardRendererAdapter` | 需按 engine 选择 `RemotionRendererAdapter` |
| `commands.py:create_task()` | 接受 `engine` 参数但只允许 `WHITEBOARD` | 需放行 `INFOGRAPHIC_REMOTION` + capability 检查 |
| `commands.py:_exec_render_visuals()` | 通过 ServiceResolver 只找 whiteboard | 需按 task.engine 选路 |
| `CapabilityService.snapshot()` | infographic-remotion 硬编码 `supported=False` | 需真实检测 Node/Remotion/Browser |
| `commands.py:_exec_plan_storyboard()` | 只使用白板分镜 | 需按 engine 选择信息图分镜 adapter |

### 6.3 禁止的耦合

M09 新代码不得：
- 导入 `webapp.server` 或 `webapp.mountain_api` / `webapp.mountain_stages`
- 调用 `server.load_config()`, `server.synthesize_voice()` 等旧函数
- 在 adapter 或 domain 层引用 React/Remotion 框架类型
- 将 API Key 或完整 Provider 响应写入 Artifact/Trace/Log

---

## 7. 已知问题

| 问题 | 位置 | 严重度 | 说明 |
|---|---|---|---|
| `capabilities.py` 服务去重 | 已修复 (本次) | 中 | `list_services()` + `list_services(audio_generation)` 导致重复 service_id |
| `test_mountain_api.py::test_list_tasks` | 预存 | 低 | 预存失败，非本次引入 |
| `test_script_preparation.py` (2 个) | 预存 | 低 | 缺少 `docs/workmates/evidence/manual-001-script.txt`，非本次引入 |
| `mountain_api.py:262` 导入 `webapp.server` | 预存 | 中 | 旧健康检查端点仍耦合旧 server |
| `mountain_stages.py:27` 导入 `webapp.server` | 预存 | 中 | 旧阶段执行仍耦合旧 server |
