# Mountain 工程执行指令与验收回写台账

## 1. 文档用途

本文档是 Mountain 当前阶段 CCF（WebUI 前端）和 CCB（后端、CLI、服务入口）的唯一执行指令入口。执行结果写入各自代码分支的独立报告文件，避免多个 worktree 并发修改 `main`。

后续不再依赖聊天中的零散上下文。每位工程师开始工作前必须完整阅读：

1. 本文档的“共同规则”；
2. 分配给自己的“当前执行指令”；
3. 自己执行指令引用的架构文档；
4. 自己上一次审核结论和未关闭问题。

工程师不得修改本文件或另一位工程师的报告。任务完成后，只能在自己分支规定的报告文件中写入结果。

## 2. 固定位置与共同规则

### 2.1 本文档绝对路径

```text
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/16-agent-execution-ledger.md
```

### 2.2 代码仓库与工作区

主代码仓库：

```text
/mnt/d/workstation/projects/cs-board
```

CCF worktree：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
```

CCF 分支：

```text
feat/mountain-assets-settings-web
```

CCB worktree：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
```

CCB 分支：

```text
feat/mountain-assets-settings-backend
```

### 2.3 共同架构约束

- 现行业务概念统一为 Task、Run、Stage，不得恢复 Project 业务实体。
- WebUI 和 CLI 必须共享 Application Kernel、Repository、Artifact、Telemetry 和错误语义。
- 新 Mountain Server 不得依赖旧 WebUI、`webapp.server`、`LegacyJobBridge` 或旧 `JOBS`。
- 动态 Service Registry 是模型、语音、对齐、渲染、媒体和 Codex Skills 的统一注册入口。
- Service Registry 负责选择服务，ProviderFactory 负责构造 Adapter，SecretStore 负责 Secret，Application 层不得读取 Secret。
- Secret 不得进入任务文件、资产元数据、日志、事件、诊断包或 API 响应。
- 资产与设置先形成稳定基础，再继续 Task 主流程 WebUI。
- 不允许用 mock、fixture、localStorage 或静态业务数据冒充运行时能力。
- 测试必须验证行为，禁止使用 `expect(true)`、`hasattr`、源码字符串检查替代真实行为。

### 2.4 共同提交规则

- 只能在自己的独立 worktree 和分支工作。
- 不得 reset、清理或覆盖其他工作区。
- 每轮纠偏形成新的 follow-up commit，不得 squash 历史审核提交。
- 完成后先本地提交，不推送远端。
- 完成报告必须写入本指令指定的、位于自己 worktree 内的独立报告文件。
- 报告与代码放在同一个功能分支、同一个最终提交中；不得跨 worktree 修改 `main` 文档目录。

## 3. CCF 当前执行指令

### 3.1 指令编号

```text
CCF-ASSET-SETTINGS-03
```

### 3.2 起点

```text
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
base commits:
  ccdd83a feat(mountain-web): implement assets and settings foundation
  0bb7737 fix(mountain-web): complete assets settings contracts and interactions
```

### 3.3 本轮目标

CCF 必须交付真正可操作的资产管理和设置功能，而不是仅定义 API 函数或展示只读骨架：

1. WebUI 可以新建动态 Service；
2. 可以编辑 endpoint、model、priority 和非敏感 config；
3. 可以输入、保存、查看掩码状态和删除 LLM API Key；
4. 可以 Probe 服务并显示真实 ProbeResult；
5. 可以完整管理 custom style；
6. 可以上传、编辑、试听和管理 voice asset；
7. preset 严格只读，只允许查看和复制；
8. 设置页只有一套生产组件，测试必须覆盖实际 Router 使用的组件；
9. 建立可运行的 HTTP 契约检查脚本。

### 3.4 设置页面结构

消除当前两套重复实现，统一为：

```text
SettingsLayout
├── ModelServicesPage
├── ServiceDetailPage
├── VoiceAlignmentPage
├── ToolchainPage
├── StoragePage
└── DiagnosticsPage
```

生产路由：

```text
/settings                         -> redirect /settings/models
/settings/models                  -> ModelServicesPage
/settings/models/:serviceId       -> ServiceDetailPage
/settings/voice-alignment         -> VoiceAlignmentPage
/settings/toolchain               -> ToolchainPage
/settings/storage                 -> StoragePage
/settings/diagnostics             -> DiagnosticsPage
```

`SettingsLayout` 使用 `<Outlet />`。不得保留 SettingsPage 内部 Section 与独立 Page 两套实现。

### 3.5 Service 前端契约

`ServiceDefinition` 必须包含：

```text
schema_version, revision, service_id, display_name, capability,
adapter_type, endpoint, model, enabled, priority, is_default, config,
required_secrets, optional_secrets, config_status, availability,
secret_status, created_at, updated_at
```

其中：

- capability 和 adapter_type 是可扩展字符串，不是封闭枚举；
- availability 是结构化对象，包含 available、checked_at、latency_ms、component、error_code、suggestion；
- config_status 包含 configured、missing_fields、missing_secrets；
- secret_status 包含 configured、required、missing。

Service API：

```text
GET    /api/v1/services
POST   /api/v1/services
GET    /api/v1/services/{serviceId}
PATCH  /api/v1/services/{serviceId}
DELETE /api/v1/services/{serviceId}
POST   /api/v1/services/{serviceId}/activate
POST   /api/v1/services/{serviceId}/deactivate
POST   /api/v1/services/{serviceId}/default
POST   /api/v1/services/{serviceId}/probe
GET    /api/v1/services/{serviceId}/secrets
POST   /api/v1/services/{serviceId}/secrets
DELETE /api/v1/services/{serviceId}/secrets/{secretKey}
```

创建 Service 必须提供 service_id、display_name、capability、adapter_type，并可配置 endpoint、model、priority、enabled、required_secrets、optional_secrets 和非敏感 config。

### 3.6 Secret 页面要求

- Secret 列表响应统一使用 `items[]`，字段为 secret_key、configured、masked_value、updated_at。
- required secret 自动生成输入项，不让用户重复输入 key 名。
- Secret value 使用 password input。
- 保存成功后立即清空明文。
- 页面永不重新显示明文。
- 删除失败必须展示结构化错误。
- 不得写入 URL、localStorage、console 或页面诊断数据。

### 3.7 资产管理要求

页面标题统一为“资产管理”，包括：

#### 预置风格

- 列表、搜索、status/engine 筛选、分页、详情、revision、tags、提示词摘要、预览；
- 允许复制为 custom；
- 禁止编辑、删除、启用和停用。

#### 自定义风格

- 创建、查看、编辑、启用、停用、删除；
- 支持 name、description、engine、prompt_text、negative_prompt、tags、preview_asset_id 和 expected_revision；
- 预览文件先上传到 `/api/v1/assets/uploads`，再保存 preview_asset_id；
- 删除使用 React Dialog，不使用 `window.confirm`。

#### 音色库

- multipart 上传，字段为 file、name、tags；
- 展示 duration_ms、sample_rate、channels、format、revision；
- 编辑 name/tags，支持启用、停用、删除；
- 使用 `<audio controls>`；
- 播放 URL 固定为 `/api/v1/assets/voices/{voiceId}/content`。

### 3.8 HTTP 安全边界

- GET 不设置 Content-Type；
- JSON mutation 设置 application/json；
- FormData 合并用户 headers 后仍必须删除所有大小写形式的 Content-Type；
- 204 不调用 `json()`；
- 优先解析 `body.error`，兼容 FastAPI `detail`；
- 页面禁止直接 `JSON.stringify(error.details)` 或 `JSON.stringify(config)`；
- 错误详情只展示 capability、service_id、allowed、missing_fields、missing_secrets、suggestion、revision 等白名单字段。

### 3.9 契约 Fixtures 与检查脚本

在 `web-v2/tests/fixtures/contracts/` 建立唯一 fixture：

```text
service-list.json
service-detail.json
service-secrets.json
service-probe.json
style-list.json
voice-list.json
voice-alignment.json
toolchain.json
storage.json
diagnostics.json
error.json
```

组件和 HTTP 测试共用这些 fixture。

增加：

```text
web-v2/scripts/check-api-contract.mjs
```

通过 `MOUNTAIN_API_BASE` 连接真实后端，字段不一致时必须非零退出。

### 3.10 CCF 验收门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
git diff --check
```

要求：

- 0 failed；
- 0 React act warning；
- 0 unhandled rejection；
- 0 `expect(true)`；
- 0 Project/旧阶段回退；
- 0 旧 Provider、preset-styles、custom-styles、toggle、set-default 路径；
- 0 window.alert/window.confirm；
- 0 运行时 fixture/mock；
- 生产 Router 和测试组件一致。

完成后提交：

```text
fix(mountain-web): finish service secrets and asset management
```

### 3.11 CCF 完成报告

CCF 完成后必须在自己的 worktree 创建或更新：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-asset-settings-03-report.md
```

报告必须使用以下结构，不得修改本指令台账：

```markdown
#### CCF-ASSET-SETTINGS-03 完成报告 — <时间>

- worktree:
- branch:
- commit:
- git status:
- 生产路由:
- Service CRUD:
- Secret 配置流程:
- Style CRUD:
- Voice 上传与试听:
- 契约 fixture:
- check-api-contract 结果:
- build:
- tests:
- act warnings:
- 静态检查:
- 已知后端 gap:
- 未完成事项:
```

未完成时不得写“完成”；应明确写“执行中”及剩余问题。

## 3A. CCF 审核纠偏指令

### 3A.1 指令编号与起点

```text
instruction: CCF-ASSET-SETTINGS-04
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed commit: 1f1c529 fix(mountain-web): finish service secrets and asset management
result: rejected
```

本轮只能在上述 worktree 和分支形成 follow-up commit，不得改写、squash 或删除 `1f1c529`。

### 3A.2 必须关闭的阻断项

1. 新建 Service 必须输入并提交 `service_id`、`display_name`、`capability`、`adapter_type`；同时支持 `required_secrets`、`optional_secrets`、endpoint、model、priority、enabled 和非敏感 config。编辑页面必须正确回填并限制不可修改字段。
2. capability 与 adapter_type 保持可扩展字符串语义。可以提供推荐值，但必须允许用户输入注册表尚未预置的新值，不得只允许封闭 `<select>`。
3. `config_status` 改为结构化对象，至少包含 `configured`、`missing_fields`、`missing_secrets`；`secret_status` 改为结构化对象，至少包含 `configured`、`required`、`missing`。页面和测试同步使用真实结构。
4. Secret 列表统一解析 `{items: ServiceSecret[], total: number}`；保存成功清空明文；加载、保存、删除失败均显示结构化安全错误，不得静默吞错。
5. `probeService()` 返回并展示 `ServiceAvailability`，不得伪装成 `ServiceDefinition`；Probe 后按真实结果刷新详情。
6. 修复 Service 删除流程：删除失败不得关闭成功流程或离开页面；删除成功才导航到 `/settings/models`，不得读取异步旧 state 判断结果。
7. 删除旧的双轨 `SettingsPage` 生产功能及其旧测试，或将其收缩为无业务逻辑的兼容跳转；测试必须覆盖 Router 实际使用的 `SettingsLayout`、`ModelServicesPage`、`ServiceFormPage`、`ServiceDetailPage`。
8. 删除生产代码中的 `window.alert`、`window.confirm` 以及向 console 输出错误详情的行为。错误详情只能按白名单显示：`capability`、`service_id`、`allowed`、`missing_fields`、`missing_secrets`、`suggestion`、`revision`、`request_id`。
9. 修复 HTTP FormData header：合并调用方 headers 后，删除所有大小写形式的 `Content-Type`；增加传入 `content-type`、`Content-Type`、`CONTENT-TYPE` 的行为测试。
10. 自定义风格预览必须选择文件并先调用 `POST /api/v1/assets/uploads`，取得 `asset_id` 后再保存 `preview_asset_id`；不允许把“手工填写素材 ID”作为唯一流程。
11. 资产页面补全真实筛选和 cursor 分页：style 支持 kind/status/engine/q，voice 支持 status/q；提供加载下一页并保证不重复、不漏项。切换 tab/filter 时重置 cursor 和选中项。
12. `check-api-contract.mjs` 必须使用 `MOUNTAIN_API_BASE` 请求真实后端，不得仅比较本地 fixture 与 TypeScript 文本。至少验证 Service list/detail/secrets/probe、Style list、Voice list、Voice Alignment、Toolchain、Storage、Diagnostics 和统一错误响应；网络错误或字段不符必须非零退出。fixture 只作为期望契约，不得冒充服务器响应。
13. 清除全部 React `act(...)` warning、unhandled rejection 和 Router warning；不得通过屏蔽 `console.error` 掩盖 warning。完成报告必须逐字如实粘贴门禁摘要，不得把“tests passed”解释成“0 warning”。

### 3A.3 强制行为测试

至少新增或重写测试证明：

- 生产 Router 实际渲染所有 Settings 子路由；
- 创建 Service 请求包含全部必需字段和 Secret 声明；
- 自定义 capability/adapter_type 可以提交；
- Secret `{items,total}` 正常渲染，失败不被吞掉；
- Probe 使用 `ServiceAvailability`；
- 删除失败留在详情页，成功才导航；
- FormData 三种大小写 Content-Type 均被移除；
- 风格预览完成 upload -> asset_id -> style save 链路；
- style/voice 筛选与 cursor 翻页请求正确；
- production source 中不存在旧 Settings 双轨、`window.confirm`、`window.alert` 和错误详情 console 输出。

不得使用 `expect(true)`、源码字符串存在性断言或只断言 HTTP 状态不是 400 替代行为测试。

### 3A.4 门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:8000/api/v1 node web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

真实契约检查需要 CCB 服务时，不得伪造成功；在报告中标记 `blocked: waiting for CCB runtime`，其余前端工作和门禁继续完成。

形成新的提交：

```text
fix(mountain-web): close CCF asset settings review gaps
```

先本地提交，不推送远端。

### 3A.5 完成报告

只在 CCF worktree 创建或更新：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-asset-settings-04-report.md
```

报告逐项列出 3A.2 的 13 项处理结果、对应生产文件和行为测试，并包含：commit、git status、build、test 数量、warning 数量、真实 contract checker、已知 gap、未完成事项。未全部完成时只能写“执行中”。

## 4. CCB 当前执行指令

### 4.1 指令编号

```text
CCB-BACKEND-INTEGRATION-04
```

### 4.2 起点

```text
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
base commits:
  d8c81b6 feat(mountain): asset catalog, dynamic service registry, runtime status
  6a3e3c5 fix(mountain): complete dynamic services assets and server foundation
  af11727 fix(mountain): integrate dynamic services with task pipeline and secure assets
```

### 4.3 本轮阻断目标

CCB 必须关闭以下阻断项：

1. Service API、Settings API、CLI 和 ProviderFactory 使用同一个加密 SecretStore；
2. 动态服务不再只做启动前检查，而是真正决定六阶段使用的 Adapter；
3. Task API 不直接实现文件持久化和状态机；
4. 音色 API 真实接收 multipart 音频并通过 MediaPort/FFprobe 获取元数据；
5. Settings、CLI、Seed 和错误契约收口；
6. 输出与第 3 节 CCF 契约完全一致的 DTO。

### 4.4 唯一组合根与 SecretStore

`mountain_server.create_app()` 是唯一组合根。只在这里创建一次：

- SecretStore；
- FilesystemServiceRegistry；
- ServiceResolver；
- ProviderFactory；
- MountainCommands/Application service。

随后注入 Task、Service、Settings Router。Router 不得再次调用 `create_secret_store()`。

默认要求加密并 fail closed。只有显式 `CSBOARD_ALLOW_PLAINTEXT_SECRETS=1` 才允许开发明文模式，且 health/diagnostics 必须警告。

以下必须为零：

```text
create_secret_store(..., encrypted=False)
```

Secret 不得进入 Service JSON、Task 文件、request、manifest、日志、事件、诊断和错误信息。

### 4.5 动态服务进入 Pipeline

生产执行链必须为：

```text
Task API
  -> MountainCommands
  -> PipelineOrchestrator
  -> ServiceResolver.resolve_for_stage()/resolve(capability)
  -> ServiceDefinition
  -> ProviderFactory.create_adapter(service_definition)
  -> Stage Port
```

禁止仅在 `start_run` 中检查 capability 后继续使用旧无参 `create_text_model()`、`create_tts()` 等固定路径。

至少映射：

```text
generate-visual-anchors -> text_generation
clone-voice             -> speech_synthesis + speech_alignment
plan-storyboard         -> text_generation
generate-illustrations  -> image_generation 或 codex_skill
render-visuals          -> rendering
compose-video           -> media
```

切换默认 Service 后，下一次 Stage 必须实际构造并使用新 Service 的 Adapter。

### 4.6 ProviderFactory

- 动态生产路径只接受 ServiceDefinition；
- Adapter 至少支持 openai_compatible、indextts、whisper、ffmpeg、local_process；
- codex_skill 如果尚未实现，必须返回结构化 `UNSUPPORTED_ADAPTER`，不得假装成功；
- 未知 adapter 不得返回可用；
- Secret 由注入的同一个 SecretStore 获取；
- 新生产路径不得依赖 PROVIDER_PROFILES。

### 4.7 Task API 收口

`mountain_task_api.py` 只负责 HTTP DTO、鉴权边界和调用 Application Command。

以下逻辑必须移回 Application/Repository：

- 遍历和排序 task.json；
- 直接写 request.json/task.json；
- 直接修改 RunStatus；
- 直接拼 final.mp4；
- 直接维护 inputs；
- 直接写 telemetry event。

`reference_audio` 等持久化字段只保存相对路径，不得写绝对路径。

所有 Task 错误统一使用 `body.error` 契约。

### 4.8 Service API 目标 DTO

Service API 必须输出第 3.5 节定义的完整 ServiceDefinition View，包括：

- config_status；
- availability；
- secret_status。

Service secrets 响应必须为：

```json
{"items": [], "total": 0}
```

字段为 secret_key、configured、masked_value、updated_at。

Probe 返回 ServiceAvailability，而不是 ServiceDefinition。

列表 total 是过滤后总数，cursor 分页不得漏项或重复。

### 4.9 音色和通用上传

`POST /api/v1/assets/voices` 必须接收 multipart：

- file；
- name；
- tags。

要求：

- 分块写临时文件；
- 尺寸限制；
- 扩展名、MIME、文件签名校验；
- 使用 MediaPort/FFmpeg adapter 获取 duration_ms、sample_rate、channels、format；
- 计算 sha256；
- 原子写入；
- 成败均清理临时文件；
- Repository 正式方法更新 name、tags、revision、updated_at；
- Router 不调用 Repository 私有方法；
- `/content` 支持 HEAD、206 和无效 Range 416；
- 不返回 storage_path 或绝对路径。

通用 uploads 同样不得把完整文件累计在 bytearray 中。

### 4.10 Style、Settings、CLI、Seed

- preset 禁止 PATCH、DELETE、activate、deactivate，只允许查看和 copy；
- style 列表支持 kind/status/engine/q/cursor/limit；
- Toolchain 包含 Python、Node、FFmpeg、FFprobe、Codex CLI、Skills；
- Storage 包含 cleanup_policy；
- Voice Alignment 同时返回默认 TTS、Alignment、IndexTTS probe、Whisper probe；
- Diagnostics 包含 API、Service、Toolchain、Storage、Telemetry、Logs 和安全的最近错误；
- CLI 与 API 使用同一 Registry、AssetRepository 和 SecretStore；
- CLI Secret 默认 stdin/getpass，不把明文放命令行；
- Seed 使用 utc_now，禁止硬编码日期。

### 4.11 CCB 测试与真实门禁

必须有生产链测试证明：

```text
Task -> Pipeline -> Resolver -> ServiceDefinition -> create_adapter -> Stage
```

还必须覆盖：

- API 写入 Secret 后磁盘中不存在明文；
- Web/CLI/Pipeline 能读取同一 Secret；
- 切换默认服务改变下一次执行；
- Service 路径穿越、revision conflict、分页；
- 真实 WAV multipart 上传、元数据和 Range；
- preset 只读；
- Settings DTO；
- Task 文件没有绝对路径或 Secret。

门禁：

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
```

启动后验证：

```text
GET  /api/v1/health
POST /api/v1/tasks
GET  /api/v1/tasks
GET  /api/v1/providers -> 404
GET  /api/v1/services
GET  /api/v1/assets/styles
POST /api/v1/assets/voices
GET  /api/v1/settings/toolchain
GET  /api/v1/settings/storage
GET  /api/v1/settings/voice-alignment
GET  /api/v1/settings/diagnostics
```

必须额外运行 CCF 的真实契约检查脚本；字段不一致不得宣布完成。

完成后提交：

```text
fix(mountain): close secure runtime and asset integration gaps
```

### 4.12 CCB 完成报告

CCB 完成后必须在自己的 worktree 创建或更新：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-backend-integration-04-report.md
```

报告必须使用以下结构，不得修改本指令台账：

```markdown
#### CCB-BACKEND-INTEGRATION-04 完成报告 — <时间>

- worktree:
- branch:
- commit:
- git status:
- 唯一组合根:
- SecretStore 加密验证:
- 磁盘明文扫描:
- Pipeline 动态执行链:
- 六阶段 Service 映射:
- Task API 收口:
- Service API DTO:
- Style API:
- Voice multipart/metadata/Range:
- Settings API:
- CLI:
- Seed:
- pytest:
- compileall:
- 真实 uvicorn/HTTP 验证:
- CCF contract checker:
- 静态检查:
- 已知 gap:
- 未完成事项:
```

未完成时不得写“完成”；应明确写“执行中”及剩余问题。

## 5. 联合验收区

本节只由最终审核者填写。CCF 和 CCB 不得自行宣布联合验收通过。

### 5.1 联合验收条件

- CCF、CCB 各自门禁通过；
- CCF contract checker 对真实 CCB 服务通过；
- WebUI 可以创建 Service、保存 API Key、Probe；
- Secret 磁盘扫描无明文；
- WebUI 可以管理 custom style；
- WebUI 可以上传并试听 voice；
- CLI 能看到同一 Service 和资产；
- Task Pipeline 实际使用动态默认 Service；
- Task、Run、Stage、日志和诊断不泄漏 Secret；
- 新 Mountain Server 能同源托管构建后的 WebUI。

### 5.2 联合验收记录

尚未验收。
