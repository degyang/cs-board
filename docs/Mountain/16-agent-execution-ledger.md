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

## 3B. CCF 二次审核收口指令

### 3B.1 指令编号与起点

```text
instruction: CCF-ASSET-SETTINGS-05
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed commit: ee18ccc fix(mountain-web): close CCF asset settings review gaps
result: rejected; implementation improved, verification incomplete
```

保留 `ee18ccc`，只形成增量 follow-up commit；不得重做已经通过的实现，不得 amend、squash 或 reset。

### 3B.2 本轮唯一范围

1. 将 `m07-ccf-asset-settings-04-report.md` 恢复为与已提交历史一致；不要通过提交事后修改旧报告来制造 clean 状态。新结论只写入 3B.5 指定的新报告。
2. 清除测试输出中的全部 React Router Future Flag warning 和 `No routes matched location` warning。通过正确配置测试 Router/future flags 和补全目标路由解决，不得 mock 或屏蔽 `console.warn/error`。
3. 将真实 contract checker 扩展到 Service list/detail/secrets/probe、Style list、Voice list、Voice Alignment、Toolchain、Storage、Diagnostics 和统一错误响应。
4. Contract checker 必须双向验证字段：后端不得出现 DTO 未声明字段，DTO/fixture 的必填字段也不得从后端缺失；必须递归验证关键嵌套结构及 JSON 类型，至少覆盖 `config_status`、`secret_status`、`availability`、`items[]` 和 `error`。
5. 真实模式只能访问 `MOUNTAIN_API_BASE`，网络失败或任何 endpoint/字段/type 不一致必须非零退出；fixture 模式只能作为本地静态检查，输出不得使用“All contracts aligned”冒充真实后端通过。
6. 补齐 FormData 三种调用方 Header 大小写形式的行为测试：`Content-Type`、`content-type`、`CONTENT-TYPE` 均必须在最终 fetch headers 中不存在。
7. 补齐风格预览完整行为测试：选择文件 -> `uploadAsset(file)` -> 获得 `asset_id` -> `createStyle/updateStyle` 请求携带同一 `preview_asset_id`；上传失败不得提交 style。
8. 补齐 style/voice 筛选与 cursor 分页测试，包括 query 参数、追加下一页、跨页去重、tab/filter 重置，以及旧请求晚返回时不能污染新筛选结果。生产实现使用 request generation、AbortController 或等效机制消除竞态。
9. 使用与 `app/router.tsx` 等价的 route tree 验证 `/settings/models`、new、detail、edit、voice-alignment、toolchain、storage、diagnostics；不得以手工传入单个组件代替生产路由验证。
10. 完成后工作树必须真实干净；报告中的 commit、status、测试数、warning 数和 checker 状态必须与最终命令输出一致。

### 3B.3 验收门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
MOUNTAIN_API_BASE=http://127.0.0.1:<CCB_PORT>/api/v1 node web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

要求：0 failed、0 act warning、0 Router warning、0 unhandled rejection。若 CCB 服务尚未就绪，真实 checker 可标记 `blocked`，但整项状态仍为“执行中”，不得宣布完成。

形成新提交：

```text
fix(mountain-web): finish CCF contract and verification gates
```

先本地提交，不推送远端。

### 3B.4 禁止事项

- 不扩大范围重构已通过的页面功能；
- 不修改主台账；
- 不通过吞掉 console、删除断言或降低类型严格度清除 warning；
- 不用源码字符串断言代替用户交互和 HTTP 行为；
- 不把 fixture checker 结果写成真实 API 验证通过。

### 3B.5 完成报告

只在 CCF worktree 创建：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-asset-settings-05-report.md
```

逐项报告 3B.2 的 10 项结果及测试名称，附最终 commit、clean status、build、tests、warning 数、fixture checker、真实 checker、已知 gap 和未完成事项。真实 checker 未通过时，报告状态只能是“执行中”。

## 3C. CCF 最终契约与竞态收口指令

### 3C.1 指令编号与起点

```text
instruction: CCF-ASSET-SETTINGS-06
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed commit: 1377675 fix(mountain-web): finish CCF contract and verification gates
result: rejected; UI gates pass, checker and stale-request requirements remain
```

保留 `1377675`，只处理本节列出的剩余问题。

### 3C.2 已通过且不得返工

- build 通过；
- 202 个前端测试通过；
- 0 act warning、0 Router warning、0 unhandled rejection；
- Service 页面、结构化 DTO、Secret UI、Probe UI、删除流程；
- FormData Content-Type 清理实现；
- 风格预览上传入口及基础筛选、分页界面。

### 3C.3 本轮必须完成

1. 修复 contract checker 的 HTTP method：Service detail/secrets 使用 GET，Service probe 必须使用 POST；endpoint 定义必须显式包含 method，不能全部经 GET helper。
2. 动态 Service 校验不得在服务列表为空时 `SKIP` 后成功。支持 `MOUNTAIN_CONTRACT_SERVICE_ID`；未提供时使用列表第一项；两者都不存在时以非零退出并清楚提示先准备测试 Service，不得由 checker 擅自修改生产数据。
3. 404 错误响应的 HTTP status 必须作为 checker 元数据处理，不能把 `_status` 注入响应 body 后参与 DTO 字段校验。
4. 实现真实 JSON 类型校验，而不仅是字段名比较。至少校验 object/array/string/number/boolean/null 联合、`items[]` 元素类型，以及 Service/Settings/Error 的关键嵌套字段。期望类型应来自显式 contract schema 或可测试的结构定义，不得用脆弱正则假装完整解析 TypeScript。
5. 正确区分 DTO 必填字段和 `?` 可选字段。后端缺少必填字段失败，缺少可选字段允许；后端未知字段仍失败。
6. 为 checker 增加自动化行为测试，至少覆盖：GET detail、GET secrets、POST probe、空 Registry 失败、网络失败、缺必填字段、缺可选字段、未知字段、嵌套类型错误、数组元素错误和统一错误响应。
7. 修复 AssetManagementPage stale-request 竞态。使用 AbortController、request generation token 或等效机制，确保旧 tab/filter/page 请求晚返回时不会覆盖或追加到新状态；组件卸载后不得 setState。
8. 增加竞态行为测试：先发请求 A，改变 tab/filter 后发请求 B，B 先返回、A 后返回，最终页面只能显示 B；同时覆盖 load-more 旧页响应不能污染重置后的列表。
9. 新报告不得声称真实 checker 已通过，除非实际连接 CCB 服务且命令为零退出；阻塞时明确写执行中。

### 3C.4 门禁与提交顺序

先完成代码和测试，形成实现提交：

```text
fix(mountain-web): harden contract checker and asset request lifecycle
```

取得实现 commit hash 后，再创建报告并形成独立文档提交：

```text
docs(mountain): report CCF contract closeout status
```

报告记录 `implementation_commit`，不要求记录包含报告自身的 commit hash，从而避免 Git 提交哈希的循环依赖。最终必须 `git status --short` 为空。

门禁：

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
MOUNTAIN_API_BASE=http://127.0.0.1:<CCB_PORT>/api/v1 MOUNTAIN_CONTRACT_SERVICE_ID=<service_id> node web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

先本地提交，不推送远端。

### 3C.5 完成报告

只在 CCF worktree 创建：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-asset-settings-06-report.md
```

报告包含 3C.3 九项结果、checker 测试名称、竞态测试名称、implementation_commit、build、tests、warning 数、fixture checker、真实 checker、clean status、已知 gap 和未完成事项。真实 checker 未通过时状态只能为“执行中”。

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

## 4A. CCB 审核纠偏指令

### 4A.1 指令编号与起点

```text
instruction: CCB-BACKEND-INTEGRATION-05
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed commit: 70c9d5f fix(mountain): close secure runtime and asset integration gaps
result: rejected
```

本轮只能在上述 worktree 和分支形成 follow-up commit，不得 amend、squash、reset 或删除 `70c9d5f`。

### 4A.2 已验证基线

- Python 门禁：`403 passed, 10 skipped, 4 warnings, 3 subtests passed`；通过不等于功能验收通过。
- `compileall` 和 `git diff --check` 通过。
- TestClient 可以启动路由，但默认环境的 `/api/v1/health` 实测返回 `secret_store.encrypted=false`，违反默认加密和 fail-closed 要求。
- 完成报告仍标记真实 HTTP 和 CCF contract checker 为“执行中”，不能宣布完成；报告记录的 commit `520a139` 与实际 HEAD `70c9d5f` 不一致。

### 4A.3 必须关闭的阻断项

1. 修复 SecretStore fail closed：`create_secret_store(encrypted=True)` 不得捕获加密依赖错误后静默降级明文。只有显式 `CSBOARD_ALLOW_PLAINTEXT_SECRETS=1` 才能构造 PlaintextSecretStore；默认无法加密时服务启动必须失败。增加默认失败、显式明文、加密成功三个行为测试。
2. 真正建立唯一组合根：`create_app()` 只创建一次 Repository、ArtifactStore、Telemetry、SecretStore、ServiceRegistry、ServiceResolver、ProviderFactory 和 MountainCommands/Application service，并显式作为参数注入 Router。禁止通过给 `APIRouter` 动态挂 `state_set_dependencies` 属性注入，禁止 Router 内重新创建 MountainCommands 或基础设施。
3. 收口 `mountain_task_api.py`：Router 不得遍历 `tasks/*/task.json`，不得直接读写 `task.json`、`request.json`，不得直接改变 RunStatus/StageStatus，不能直接写 Telemetry 或拼接 `final.mp4`。这些行为必须移动到 Application Commands/Query Service 和 Repository/ArtifactStore 正式接口。
4. Task 列表必须在 Application 层执行 `filter -> priority sort -> cursor -> limit`，修复当前先 cursor 后 sort/filter 的错误顺序；分页必须在过滤结果上稳定、无重复、无漏项。
5. Task 输入保存必须使用 Application command 和 Repository 的原子 input-manifest 接口；更新未上传 reference 时必须保留原有相对路径，禁止把 `reference_audio` 覆盖为 null；失败不得留下 partial、半写 request 或 task 状态。
6. Pipeline 生产路径必须 fail closed：ServiceResolver 缺失时不得回退到 `create_text_model/create_tts/create_image_model/...` 固定 Provider 路径。CLI 与 Web 都必须显式注入 Resolver 和 Factory，并通过 `ServiceDefinition -> create_adapter()`。
7. ProviderFactory 动态生产入口不得自行创建 SecretStore，不得依赖 `PROVIDER_PROFILES` 或 `.profiles`。旧 Provider 兼容代码必须隔离到 legacy 模块，不能从新 Mountain composition root、CLI 或 Pipeline 可达。
8. Settings DTO 与 §3/§3A 的前端契约统一：voice-alignment 必须返回 `speech_synthesis`、`speech_alignment`、`indextts`、`whisper`；每个服务包含 service_id/display_name/capability/adapter_type/endpoint/model/timeout/availability。Toolchain 顶层字段、Storage cleanup_policy、Diagnostics 结构须与共享 fixture 完全一致。
9. Diagnostics 不能通过截断日志 message 假装脱敏。必须复用 Redactor，对 message、details 和嵌套字段进行结构化脱敏；增加包含 API key、Bearer token、service secret 原文的日志测试，确认响应与磁盘诊断包均不存在原文。
10. Service availability 不得在每次 list/detail 时执行可能昂贵的实时 probe。Probe 只由显式 endpoint 或受控缓存刷新；list/detail 返回最近一次 ProbeResult。无历史结果时返回结构化 unknown/unavailable 状态。
11. Service 创建/更新必须校验未知字段、service_id 路径安全、revision conflict、required/optional secret key；不得让 Secret 混入 config。所有错误统一返回 `body.error`，不得混用 FastAPI 字符串 `detail`。
12. Voice multipart 与通用 upload 必须以行为测试证明：分块写入且有上限、MIME/扩展名/文件签名一致、临时文件必清、FFprobe 元数据真实、sha256 正确、HEAD/206/416 正确、不泄漏 storage_path/绝对路径。不得只检查函数存在。
13. 修正完成报告：实际 HEAD、干净状态、真实 HTTP 命令和结果必须一致；CCF contract checker 尚未能运行时明确写 blocked，不能写“完成”。

### 4A.4 强制生产行为测试

至少新增或重写测试证明：

- 默认加密不可用时 create_app 失败，而显式明文开关才允许降级；
- 四类 Router 使用同一组注入实例；
- Task Router 源层面不再承担文件和状态机职责，并通过 HTTP 行为验证 Application 调用；
- Web 和 CLI 执行同一 Stage 时解析同一个默认 Service，切换默认服务后下一次构造的 Adapter 改变；
- 任何生产执行入口缺少 Resolver/Factory 都返回结构化 `CAPABILITY_NOT_AVAILABLE`；
- Task 列表过滤、排序、cursor、limit 顺序正确；
- input-manifest 更新保留 reference，相对路径且原子；
- Settings 所有 DTO 与共享 fixtures 对齐；
- Secret/Token 在 API、日志、事件、diagnostics 和磁盘扫描中均为零明文；
- 真实 WAV 上传、FFprobe、Range 全链路。

禁止使用 `hasattr`、`inspect.getsource`、`expect status != 400` 或只断言 mock 被调用来代替最终行为验证。必要的架构边界可使用依赖身份断言，但必须同时有 HTTP/CLI/Pipeline 行为测试。

### 4A.5 门禁、真实启动与提交

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
```

必须使用临时 data dir 启动真实 `uvicorn webapp.mountain_server:app`，逐项验证 §4.11 中的端点，并保存状态码与安全裁剪后的响应摘要。随后运行 CCF 的：

```bash
MOUNTAIN_API_BASE=http://127.0.0.1:<port>/api/v1 node <CCF-worktree>/web-v2/scripts/check-api-contract.mjs
```

若 CCF checker 尚未完成，只能将本项标记 blocked，其他工作继续完成。

形成新的提交：

```text
fix(mountain): close CCB runtime integration review gaps
```

先本地提交，不推送远端。

### 4A.6 完成报告

只在 CCB worktree 创建或更新：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-backend-integration-05-report.md
```

报告逐项列出 4A.3 的 13 项处理结果、生产文件和行为证据，并包含实际 commit、git status、pytest、compileall、真实 uvicorn/HTTP、CCF checker、Secret 明文扫描、已知 gap 和未完成事项。未全部完成时只能写“执行中”。

## 4B. CCB 生产运行时最终收口指令

### 4B.1 指令编号与起点

```text
instruction: CCB-BACKEND-INTEGRATION-06
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed commit: 5007a5b fix(mountain): close CCB runtime integration review gaps
result: rejected; unit gates pass, real start path fails
```

保留 `5007a5b`，只形成增量 follow-up，不返工 4B.2 已通过内容。

### 4B.2 已通过且不得返工

- 421 个 Python 测试通过；
- SecretStore 工厂不再静默从 encrypted=True 降级；
- Service probe cache 基础实现；
- Service 创建/更新基础校验；
- Voice multipart、HEAD、Range 基础行为；
- Settings DTO 的本轮基础调整。

### 4B.3 本轮必须关闭

1. 修复真实 start 500：`mountain_task_api.start_run()` 不得引用不存在的 `_service_resolver`。上传输入后调用 start，在服务缺失时必须返回结构化 `CAPABILITY_NOT_AVAILABLE`，绝不能抛 NameError/500。
2. 唯一组合根必须注入同一个 `MountainCommands`/Application service 实例。Task Router 直接接收 commands/query service，不得每次请求 `_get_commands()` 新建实例；Router 参数不得使用 `repository or Filesystem...` 等生产回退创建基础设施。
3. 完成 Task Router 收口：`get_task/get_inputs/start/artifacts/content/events/logs/trace/metrics/final/diagnostics` 均委托 Application Query/Command 与 Artifact/Telemetry port。Router 不得直接读取 `task.json`、`request.json`、`index.json`、JSONL、`final.mp4`，不得拼接运行目录或解释领域状态。
4. 输入上传采用明确的 staging/application 边界：Router 只流式接收至受控临时文件并校验 HTTP 输入；Application command 负责校验任务、媒体、保留既有 reference、原子提交 input-manifest 和清理。任一步失败不得覆盖旧 reference，不得留下 partial。
5. ProviderFactory 新生产构造必须强制注入 SecretStore；删除无注入时 `encrypted=False` 的危险默认。若 legacy 确需自建，迁入明确 legacy factory，新 Mountain Server/CLI/Pipeline 不可达。
6. 加入可安装的运行时加密依赖。当前项目环境实测没有 `cryptography`，默认服务无法启动。将依赖写入项目实际安装清单并更新启动/安装文档；默认缺依赖时抛出明确可操作错误，不得让模块级 `app` 变成 `None`。
7. 删除根级 `conftest.py` 对全部测试全局设置 `CSBOARD_ALLOW_PLAINTEXT_SECRETS=1` 的做法。明文模式只在明确需要的 scoped fixture 中设置并恢复；必须有未设置开关的真实默认加密启动测试。
8. 所有 HTTP 错误统一 `body.error`。清除 Task Router 的字符串或 dict `HTTPException.detail` 输出；测试覆盖 validation/not-found/capability/internal boundary，确认没有 FastAPI `detail` 泄漏。
9. Diagnostics/Logs/Events/Artifact content 返回前复用 `DefaultRedactor`，不仅返回计数。增加 API key、Bearer token、查询参数 secret、嵌套敏感键和真实 Service secret 的响应及磁盘扫描测试。
10. 真实启动门禁必须覆盖：默认加密模式启动、health encrypted=true、创建 Task、保存输入、start 缺能力返回结构化 4xx、注册测试 Service 后动态解析到 adapter、旧 `/providers` 404，以及 Service/Asset/Settings/Task 查询端点。
11. 对接 CCF `CCF-ASSET-SETTINGS-06` 完成后的 checker。后端自身先用共享 fixtures/契约测试保证 DTO；不得把 checker failure 描述为通过。
12. 修正报告真实性：状态不得写“全部通过”同时附带 checker violation；报告必须记录实际 implementation commit、真实 HTTP 结果、clean status 和未完成项。

### 4B.4 强制回归测试

至少覆盖：

- upload inputs 后 start 不产生 500；
- 缺 Service 返回 `body.error.code=CAPABILITY_NOT_AVAILABLE`；
- Router 多次请求使用同一 commands/repository/telemetry/resolver/factory 实例；
- ProviderFactory 无 SecretStore 构造失败；
- 默认加密启动与显式明文开发启动相互隔离；
- input 更新失败保留旧 reference 且无 partial；
- Task 查询全部通过 Application/Port 行为完成；
- Task/日志/事件/产物/诊断响应中 secret 原文为零；
- CLI 与 Web 切换默认 Service 后下一次 Stage 使用同一新 Adapter。

禁止只用 `hasattr`、源码字符串或 mock 调用次数替代真实 HTTP/Application 行为。

### 4B.5 门禁与提交顺序

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
```

使用临时 data dir 启动真实 uvicorn，保存安全裁剪后的请求/响应摘要。随后运行可用的最新 CCF checker；未通过只能标记执行中。

先形成实现提交：

```text
fix(mountain): harden production runtime and task API boundaries
```

取得 implementation commit 后，再形成报告提交：

```text
docs(mountain): report CCB runtime closeout status
```

先本地提交，不推送。最终 `git status --short` 必须为空。

### 4B.6 完成报告

只在 CCB worktree 创建：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-backend-integration-06-report.md
```

报告逐项记录 4B.3 十二项结果及测试名称，包含 implementation_commit、pytest、compileall、默认加密启动、真实 HTTP、CCF checker、Secret 扫描、clean status、已知 gap 和未完成事项。任一真实门禁未完成时状态只能为“执行中”。

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
