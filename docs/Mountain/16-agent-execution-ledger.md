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

## 3D. CCF Checker 可执行性最终纠偏

> 状态：已被 §3E 的小粒度指令取代，不再执行。原因：本节同时混合 checker、请求竞态和报告整改，不符合单一垂直切片原则。

### 3D.1 指令编号与起点

```text
instruction: CCF-ASSET-SETTINGS-07
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
implementation base: c7695e2
report commit: bdb37ba
result: rejected; tests exercise copies/source strings instead of production checker
```

只处理本节问题，不返工已通过的页面、DTO 和基础交互。

### 3D.2 必须完成

1. 把 checker 核心拆成可导入模块，例如 `scripts/contract-checker-core.mjs`；CLI 脚本只负责读取环境、调用核心和设置退出码。测试必须直接 import 生产核心，删除测试文件中复制的 `extractInterfaceFields`、`verifyFieldsBidirectional`、`validateJsonType` 等实现。
2. 生产 `verifyResponse/verifyNested` 必须实际调用类型验证，遍历所有存在的顶层字段和嵌套字段；当前 `validateJsonType()` 定义但从未调用必须修复。
3. 类型验证必须区分 array、plain object 和 null；`items` 为对象、Record 为数组、复杂对象为字符串等必须失败。数组元素必须递归校验对应 DTO。
4. HTTP checker 测试必须通过受控本地 HTTP server 或注入的真实 fetch transport 执行生产 `checkRealBackend()`，验证请求 method/path、响应解析和 violations；禁止通过 `toContain("method: 'POST'")` 等源码字符串断言代替行为。
5. 自动化测试必须让以下生产行为失败：Probe 使用 GET、空 Registry、网络错误、缺必填字段、未知字段、顶层类型错误、嵌套类型错误、数组元素错误、404 非 JSON；并验证缺可选字段允许。
6. 请求生命周期必须选择一种真实方案：
   - 将 AbortSignal 从 AssetManagementPage 传入 `fetchStyles/fetchVoices` 并最终传入 fetch；或
   - 删除无效 AbortController，使用 generation + mounted ref，并在 cleanup 中递增 generation、禁止完成后的任何 setState。
   测试必须验证生产 API 收到 abort signal，或验证卸载后生产 guard 确实阻止状态更新，不能仅以“控制台没 warning”作为断言。
7. 报告必须位于约定路径：`docs/Mountain/m07-ccf-asset-settings-07-report.md`，不得写入 `web-v2/docs`。旧的错误位置文件保留历史，不改写提交。
8. 未运行真实 CCB checker 时整体状态写“执行中”；不得使用 Closeout/Done/全部完成措辞。

### 3D.3 门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
MOUNTAIN_API_BASE=http://127.0.0.1:<CCB_PORT>/api/v1 MOUNTAIN_CONTRACT_SERVICE_ID=<service_id> node web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

先形成实现提交：

```text
fix(mountain-web): execute real contract validation paths
```

再形成报告提交：

```text
docs(mountain): report CCF checker execution status
```

报告记录 implementation commit；不要求记录报告提交自身 hash。先本地提交，不推送。

### 3D.4 完成报告

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-asset-settings-07-report.md
```

报告列出 3D.2 八项结果、直接 import 生产核心的测试名称、本地 HTTP server 行为测试、请求生命周期测试、implementation_commit、build、tests、warning、fixture checker、真实 checker、clean status 和未完成事项。

## 3E. CCF 单一垂直切片：可执行 Contract Checker

### 3E.1 指令编号

```text
instruction: CCF-CONTRACT-CHECKER-01
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
base: bdb37ba
scope: contract checker only
```

本轮禁止修改 React 页面、资产请求生命周期、业务 DTO、样式和其他功能。目标只有一个：生产 checker 必须真实执行字段、类型和 HTTP 契约验证，且其测试直接调用同一份生产实现。

### 3E.2 唯一交付结果

执行下面命令时，checker 必须对受控测试服务器完成真实 HTTP 校验：

```bash
npm --prefix web-v2 run test:contract-checker
```

该命令必须启动或连接测试进程内的受控 HTTP server，并验证：

- GET Service detail；
- GET Service secrets；
- POST Service probe；
- 404 `body.error`；
- 顶层和嵌套必填字段；
- 可选字段允许缺失；
- 未知字段拒绝；
- object/array/string/number/boolean/null 类型；
- `items[]` 元素 DTO；
- 空 Service Registry、网络错误和非 JSON 响应均失败。

### 3E.3 实现边界

1. checker 核心必须是唯一生产模块，例如 `contract-checker-core.mjs`；CLI 与测试都 import 它。
2. 测试目录不得复制 checker 算法；不得读取 checker 源码后使用 `toContain` 证明行为。
3. `verifyResponse()` 必须在生产调用链中实际执行类型校验。未被调用的验证函数视为未实现。
4. 测试 HTTP server 必须记录 method/path 并返回真实 JSON；测试断言最终 violations/exit result，不能只断言 mock 被调用。
5. 测试不得依赖 CCB、网络或现有用户数据，因此每次可确定性重复执行。
6. 本轮不要求真实 CCB checker 通过；它属于后续联合验收，不得阻塞这个独立切片。

### 3E.4 预定义机器门禁

CCF 不得改变或弱化以下验收含义：

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
git diff --check
```

验收要求：

- 所有命令退出码为 0；
- 0 warning、0 unhandled rejection；
- checker 专项测试至少包含一个完整成功场景和上述每类失败场景；
- fixture mode 必须明确声明不是真实 API；
- 不允许 `expect(true)`、源码字符串断言、复制生产算法或“状态码不是 400”式断言。

### 3E.5 提交与报告

先提交实现：

```text
fix(mountain-web): make contract checker executable and testable
```

得到 implementation commit 后，创建：

```text
docs/Mountain/m07-ccf-contract-checker-01-report.md
```

再提交报告：

```text
docs(mountain): report CCF contract checker slice
```

报告只记录：implementation commit、五条门禁原始摘要、专项成功/失败场景、git clean 状态。执行者只能写“门禁已执行”，不得写“最终验收通过”；最终通过由审核者判定。先本地提交，不推送。

## 3F. CCF 单点修复：复杂嵌套类型守卫

### 3F.1 指令编号

```text
instruction: CCF-CONTRACT-CHECKER-02
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
base: cf8ff79
scope: nested complex type guard only
```

`CCF-CONTRACT-CHECKER-01` 的五条门禁均已通过，但审核者用生产 `verifyResponse()` 复现：把合法 Service fixture 的 `config_status` 整体替换为字符串 `"wrong-string"` 后，violations 仍为空。原因是复杂 DTO 类型被 `tsTypeToJsonTypes()` 跳过，而 `verifyNested()` 遇到非对象也静默跳过。

### 3F.2 唯一修改目标

修复生产 checker，使 `NESTED_STRUCTURES` 声明的字段在非 null 时必须满足容器类型：

- `Foo` 必须是 plain object，不能是 string/number/boolean/array；
- `Foo[]` 必须是 array，不能是 plain object 或其他类型；
- 数组每个元素必须是 plain object，再递归校验字段；
- 只有 DTO 明确允许 null 时才接受 null。

只新增针对生产核心的最小回归测试，至少覆盖：

1. `ServiceDefinition.config_status = "wrong-string"` 失败；
2. `ServiceListResponse.items = {}` 失败；
3. `ServiceListResponse.items = ["wrong-string"]` 失败；
4. 合法嵌套对象和数组仍通过。

禁止修改页面、HTTP endpoint、DTO、fixture 内容和其他业务测试；禁止复制生产算法或源码字符串断言。

### 3F.3 固定门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
git diff --check
```

提交：

```text
fix(mountain-web): reject invalid nested contract containers
```

本轮无需新增长篇报告。在 `docs/Mountain/m07-ccf-contract-checker-02-report.md` 记录 implementation commit、四个回归测试、五条门禁摘要和 clean status，再形成独立文档提交。执行者只报告门禁结果，最终通过由审核者判定。

## 3G. CCF 未交付纠偏：完成复杂嵌套容器守卫

### 3G.1 指令状态

```text
instruction: CCF-CONTRACT-CHECKER-03
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed HEAD: cf8ff79 docs(mountain): report CCF contract checker slice
result: rejected; no implementation or report commit for §3F exists
```

审核者已确认工作树干净且仍停在 §3F 的起点 `cf8ff79`。旧门禁当前为 build 通过、checker tests `44/44`、全量前端 tests `251/251`、fixture checker 通过；这些结果不包含 §3F 要求的四个新行为，因此不得视为交付。

### 3G.2 唯一任务

完整执行 §3F.2 的复杂嵌套容器守卫修复，不得修改页面、DTO、HTTP client、fixtures 或其他业务功能。生产 `verifyResponse()` 必须实现：

- 非 nullable 的嵌套对象字段收到 string/number/boolean/array/null 时产生 violation；
- 嵌套对象数组字段收到 plain object 或其他非数组值时产生 violation；
- 对象数组中的非 plain-object 元素产生 violation；
- 合法嵌套对象和对象数组继续通过。

测试必须直接调用生产导出的 checker 核心，不复制实现，并明确包含以下四例：

1. `ServiceDefinition.config_status = "wrong-string"` 失败；
2. `ServiceListResponse.items = {}` 失败；
3. `ServiceListResponse.items = ["wrong-string"]` 失败；
4. 对应合法 fixture 通过。

### 3G.3 固定门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

先形成实现提交：

```text
fix(mountain-web): reject invalid nested contract containers
```

再将实际 implementation commit、四例名称、五条门禁原始摘要和未完成项写入：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-contract-checker-03-report.md
```

形成独立报告提交：

```text
docs(mountain): report nested contract guard status
```

先本地提交，不推送。最终回复必须给出两个 commit hash；没有 commit hash 等同未交付。执行者不得自行宣布审核通过。

## 3H. CCF 单一垂直切片：移除固定 Provider 前端遗留

### 3H.1 指令编号与已验收基线

```text
instruction: CCF-DYNAMIC-SERVICES-CLEANUP-04
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: f4aeecb fix(mountain-web): reject invalid nested contract containers
accepted report: fa7b254 docs(mountain): report nested contract guard status
```

审核者已复现：build 通过、contract checker `48/48`、前端全量 `255/255`、fixture checker 和 diff check 通过。复杂嵌套容器守卫本轮验收通过。

### 3H.2 唯一目标

前端模型服务域只允许使用动态 Service Registry。删除当前不可达但仍残留的固定 Provider 页面、路由辅助、DTO、API client 和对应旧测试，防止后续误接 `/providers`。不得修改后端，不得重做动态 Service 页面样式或添加新功能。

必须完成：

1. 删除不再由 Router 使用的 `ProvidersPage.tsx`、`ProviderDetailPage.tsx` 及其专属样式、测试和导入。
2. 删除前端生产代码中的 `fetchProviders/fetchProvider/updateProviderConfig/fetchProviderSecrets/setProviderSecret/deleteProviderSecret` 等 `/providers` client，以及只服务于旧 Provider API 的 DTO。
3. 保留并锁定唯一入口：`/settings/models`、`/settings/models/new`、`/settings/models/:serviceId`、`/settings/models/:serviceId/edit` 均使用动态 Service 页面与 `/services` API。
4. `VoiceAlignmentPage` 跳转服务详情仍使用 `/settings/models/:serviceId`，不得引入 Provider 名称或固定 provider_type 分支。
5. 如果通用 CSS 类仍被动态 Service 页面使用则保留；只有通过引用搜索证明专属旧 Provider 的样式才可删除。
6. 更新测试，验证设置导航和四条模型服务路由只落到动态 Service 组件；生产代码和有效测试中不得残留 `/api/v1/providers` 或以 `/providers` 为 endpoint 的调用。

### 3H.3 边界与机器门禁

允许删除真正不可达的旧代码，不得顺带调整资产、任务、工作台、checker 算法或后端契约。删除前先使用引用搜索确认无生产消费者。

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "(/api/v1)?/providers|fetchProviders|fetchProviderSecrets|ProviderDetailPage|ProvidersPage" web-v2/src web-v2/tests web-v2/scripts
git diff --check
git status --short
```

若 fixture/checker 中存在为确认后端禁止旧路径而保留的明确负向断言，可以保留，但报告必须逐项解释；不得用宽泛排除掩盖生产残留。

### 3H.4 提交与报告

实现提交：

```text
refactor(mountain-web): remove fixed provider frontend legacy
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-dynamic-services-cleanup-04-report.md
```

报告提交：

```text
docs(mountain): report dynamic services frontend cleanup
```

先本地提交，不推送。报告给出删除清单、引用搜索结果、实际 implementation commit、门禁摘要和保留的负向断言；执行者不得自行宣布最终审核通过。

## 3I. CCF 单一垂直切片：预置风格浏览与主预览

### 3I.1 指令编号与基线

```text
instruction: CCF-PRESET-STYLE-BROWSER-05
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: 66daa43 refactor(mountain-web): remove fixed provider frontend legacy
accepted report: 733395d docs(mountain): report dynamic services frontend cleanup
```

审核者已复现 build、contract checker `48/48`、全量前端 `222/222`、fixture checker、动态 Service 四路由和生产残留扫描，本轮固定 Provider 清理验收通过。

最新视觉与资产基准位于独立 main 文档工作树，CCF 必须直接读取以下绝对路径，不得假设这些文件已经合并到 CCF 分支：

```text
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/asset-management/
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/public/styles/
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/preset-style-assets.md
```

### 3I.2 唯一目标

只完成资产管理“预置风格”Tab 的浏览与详情视觉闭环。数据必须来自现有 `/api/v1/assets/styles?kind=preset`；不得把原型的 `SEED_PRESETS`、localStorage、图片路径映射或提示词硬编码复制进生产前端。

要求：

1. 列表按最新原型基准展示预置风格主缩略图、名称、短描述/description、标签和 badge（只有后端 DTO 提供时才展示）；无图时显示明确占位，不伪造图片。
2. `preview_asset_id` 非空时，使用类型化 helper 构造 `/api/v1/assets/blobs/{asset_id}` URL 并显示真实图片；必须 URL encode，不展示 asset_id 或物理路径给普通用户。
3. 详情区展示大图、名称、description、engine、tags、完整 `prompt_text`、可选 `negative_prompt` 和只读状态；长提示词可复制但不可直接编辑 preset。
4. preset 只允许“复制为自定义”，不得出现编辑、删除、启停或新增 preset 操作；复制成功后给出反馈，并切换到/定位对应 custom 条目，不能让用户误以为修改了原 preset。
5. 图片加载失败显示可访问的错误占位，不能让整页崩溃；快速切换条目时旧图、旧详情和旧请求不得覆盖新选择。
6. 多参考图及语义路由目前后端 `StyleTemplate` 尚无正式字段。本轮不得从静态基准硬编码补齐；在报告中记录明确 API gap，等待后端后续提供逻辑 asset ID 列表与路由参数。
7. 不修改自定义风格、音色库、设置、任务页、checker 核心或后端。

### 3I.3 强制行为测试

至少覆盖：

- preset 列表对真实 DTO 渲染缩略图、description、tags；
- blob URL 使用 encode 后的 `preview_asset_id`；
- preview 为空及图片 onError 的占位行为；
- 详情显示完整 prompt/negative prompt，复制按钮可用，但不存在编辑/删除/启停按钮；
- copy API 成功后的反馈与 custom 定位行为，失败时保持当前 preset 且显示结构化错误；
- 快速选择两个 preset 时最终详情始终对应最后选择；
- custom 与 voice 既有回归测试继续通过。

禁止复制 `assetStore.ts` 的 localStorage/seed 算法，禁止在测试中复制生产 URL 算法，禁止只断言组件文本存在而不触发真实交互。

### 3I.4 门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "mountain\.assets|SEED_PRESETS|localStorage" web-v2/src/pages/AssetManagementPage.tsx web-v2/src/lib/api/assets.ts
git diff --check
git status --short
```

实现提交：

```text
feat(mountain-web): complete preset style browsing experience
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-preset-style-browser-05-report.md
```

报告提交：

```text
docs(mountain): report preset style browser status
```

先本地提交，不推送。报告列出实际 implementation commit、视觉基准映射、行为测试、门禁和多参考图 API gap；执行者不得自行宣布审核通过。

## 3J. CCF 单一垂直切片：系统工具链只读状态页

### 3J.1 指令编号与已验收基线

```text
instruction: CCF-TOOLCHAIN-STATUS-06
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: b91d051 feat(mountain-web): complete preset style browsing experience
accepted report: 862a4e0 docs(mountain): report preset style browser status
```

审核者已复现 build、contract checker `48/48`、前端全量 `239/239`、fixture checker、禁止项扫描和 clean status；预置风格浏览切片验收通过。

本轮视觉基准必须读取：

```text
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/SystemStatusTabs.tsx
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/types.ts
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/screenshots/settings/03-toolchain-normal.png
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/screenshots/settings/04-toolchain-unavailable.png
```

### 3J.2 唯一目标

只整改 `/settings/toolchain`，使用现有真实 `GET /api/v1/settings/toolchain` DTO，落实最新原型的信息层级与只读边界。不得修改 Storage、Diagnostics、Voice Alignment、Models、Assets、Task 页面、checker 核心或后端。

要求：

1. 页面标题为“系统工具链”，明确说明这是运行环境探测结果、只读展示，不是可保存配置。
2. 每个工具以状态卡呈现 component 的用户可读名称、用途说明、可用/不可用状态、可选版本，以及不可用时的 `error_code` 和 `suggestion`。
3. 名称和用途可以使用纯展示映射（Codex Skills、IndexTTS、Whisper、FFmpeg、FFprobe、白板渲染器等）；未知 component 必须回退显示后端 component，不得被过滤或伪造状态。
4. 页面不得展示后端可能返回的 `path`、可执行命令、参数、环境变量、绝对目录、API Key 或 Secret。不得为了 UI 方便把这些字段加入 DTO。
5. 不提供保存、编辑、选择引擎或伪刷新/伪 Probe 按钮。数据只在路由进入时真实请求一次；失败提供明确错误和真实“重新加载”动作时，按钮必须重新调用该 GET，而不是只改本地状态。
6. loading 使用与卡片同构的骨架；空 tools 显示“未探测到工具链组件”，不能显示“未找到配置”。
7. 请求失败、组件不可用和页面空状态是三种不同状态；快速卸载/重进时旧请求不得写回新页面。
8. 不复制原型 fixture，不使用 localStorage/sessionStorage/mock fallback。

### 3J.3 强制行为测试

至少覆盖：

- available 工具显示名称、用途和版本；
- unavailable 工具显示真实 error_code/suggestion；
- 未知 component 仍可见且状态来自 DTO；
- 响应即使含 `path`、command、token 等额外字段，DOM 中也不存在其值；
- loading 骨架、空列表和 request error 分别渲染；
- retry 会再次调用真实 API，成功后清除旧错误并显示卡片；
- unmount 后延迟响应不会产生状态更新警告或污染下一实例；
- 页面不存在任何保存、编辑、引擎下拉或伪 Probe 控件。

测试必须触发生产组件和 API adapter；禁止复制状态映射算法或只检查源码文本。

### 3J.4 门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/ToolchainPage.tsx
git diff --check
git status --short
```

实现提交：

```text
feat(mountain-web): align toolchain status with readonly design
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-toolchain-status-06-report.md
```

报告提交：

```text
docs(mountain): report readonly toolchain status
```

先本地提交，不推送。报告列出视觉映射、真实 DTO 字段、敏感字段不渲染测试、门禁、两个 commit hash 和 API gap；执行者不得自行宣布审核通过。

## 3K. CCF 单一垂直切片：运行时存储只读状态页

### 3K.1 指令编号与已验收基线

```text
instruction: CCF-STORAGE-STATUS-07
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: 7b0f35c feat(mountain-web): align toolchain status with readonly design
accepted report: 68166e0 docs(mountain): report readonly toolchain status
```

审核者已复现：build 通过、contract checker `48/48`、前端全量 `244/244`、fixture checker、禁止项扫描、diff check 和 clean status。系统工具链只读页验收通过。

视觉与契约基准：

```text
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/SystemStatusTabs.tsx
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/types.ts
```

当前真实后端契约是 `GET /api/v1/settings/storage`，字段为：`writable`、`assets_available`、`tasks_available`、`temp_available`、`free_bytes`、`used_bytes`、`cleanup_policy`、`error_code`、`suggestion`。原型提出“五类逻辑存储”，但后端目前只能证明资产、任务、临时三类；不得伪造另外两类。

### 3K.2 唯一目标

只整改 `/settings/storage` 为“运行时存储状态”只读页，不修改 Diagnostics、Voice Alignment、Models、Assets、Task、checker 核心或后端。

1. 标题和说明明确这是全局运行时存储健康，不是某个 Task 的目录或可保存配置。
2. 使用真实 `fetchStorageSettings()`；分别展示资产存储、任务存储、临时存储三类逻辑状态。`true` 显示正常，`false` 显示不可用；不得把目录尚未创建误写成“数据丢失”。
3. 单独展示整体可写状态。`writable=false` 时显示后端真实 `error_code`、`suggestion`；字段为空时使用中性说明，不伪造错误码或修复命令。
4. `free_bytes`、`used_bytes` 仅在非 null、有限且非负时格式化展示；异常值显示“未统计”，不得产生 `NaN`、负容量或崩溃。两者都有效时可展示用量比例，但必须清楚标为当前存储卷统计，不暗示 Mountain 独占空间。
5. `cleanup_policy` 只作为后端返回的只读策略摘要展示。不得提供配额、保留天数、自动清理开关、立即清理、目录选择或保存按钮；当前后端没有这些写 API。
6. 不展示或推导绝对路径、目录树、文件名、Task ID、命令、环境变量和 Secret。响应即使额外含这些字段，DOM 也不得出现。
7. loading 使用同构骨架；请求失败显示独立错误和真实“重新加载”；响应成功但所有统计为 null 仍是正常响应，不得显示“未找到配置”。
8. 使用与已验收 Toolchain 页同等级的请求生命周期保护：卸载或后发请求后，旧响应不得写回。不得使用 runtime fixture、mock fallback、localStorage 或 sessionStorage。

### 3K.3 强制行为测试

- 三类逻辑存储分别覆盖正常/不可用，不得只测全为 true；
- writable false 展示真实 error_code/suggestion；
- null、负数、`NaN`/非有限容量安全显示“未统计”；有效容量单位和可选比例正确；
- cleanup_policy 只读展示，页面不存在保存、编辑、目录选择、立即清理、配额/保留配置控件；
- 响应携带 path、directory、filename、task_id、command、token 时 DOM 中均不存在其值；
- loading、成功但未统计、request error 是三个不同状态；retry 确实再次调用生产 API adapter；
- unmount 及先后两次请求竞态不会由旧响应污染最新页面；
- 测试触发生产组件与 API adapter，不复制格式化/状态映射算法，不用源码字符串断言代替行为。

### 3K.4 固定门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/StoragePage.tsx
git diff --check
git status --short
```

实现提交：

```text
feat(mountain-web): align runtime storage readonly status
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-storage-status-07-report.md
```

报告列出 implementation commit、真实 DTO 映射、三类存储状态、容量异常测试、敏感字段不渲染测试、请求生命周期、门禁原始摘要、API gap 和 clean status。报告提交：

```text
docs(mountain): report runtime storage status
```

先本地提交，不推送。执行者只报告门禁结果，不得自行宣布审核通过。

## 3L. CCF Storage 行为证据与语义收口

### 3L.1 指令编号与审核结论

```text
instruction: CCF-STORAGE-STATUS-08
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed implementation: 1539e95 feat(mountain-web): align runtime storage readonly status
reviewed report: c8e274d docs(mountain): report runtime storage status
result: rejected narrowly; UI direction is correct, race test is inert and test output has act warnings
```

审核者复现 build、contract checker `48/48`、全量 `270/270` 和 fixture checker；但全量输出含两条 `The current testing environment is not configured to support act(...)` warning。生产页面仅做窄语义修正，不扩大其他设置页。

### 3L.2 唯一任务

1. 将三类逻辑存储卡文案从“存储目录正常，可读写”改为与 DTO 一致的中性语义，例如“逻辑存储已就绪”；`*_available=false` 表达“尚不可用”。三类 boolean 不证明单目录可读写，且不能与整体 `writable=false` 矛盾。不得展示“请检查运行环境”等后端未返回的修复建议。
2. 重写名为 `second request wins when first arrives after second` 的测试。当前测试只 unmount 第一实例，未发起第二请求、未 resolve 第二 Promise，也未断言新页面，必须删除这种假覆盖。
3. 新竞态测试必须真实产生两个页面生命周期或两个请求：第一实例请求悬挂后卸载/路由重进，第二实例发起并完成请求，页面先显示第二响应；随后解析第一响应，断言 DOM 仍保持第二响应且不出现第一响应的 cleanup policy/error/state。两个 Promise 都必须实际 resolve，两个 API 调用都必须断言。
4. 修复 retry 测试的两条 act warning。使用 Testing Library 的用户交互与 `waitFor` 正确等待，不得嵌套不必要的 `act`，不得屏蔽 `console.error` 或 warning。
5. 增加测试保证当 `writable=false` 而三类 available=true 时，三类只显示“已就绪/可用”类中性状态，不出现“可读写”；整体卡单独显示不可用和后端错误。
6. 不修改 API DTO、checker、其他页面或后端，不降低既有 270 个测试覆盖。

### 3L.3 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/StoragePage.tsx
git diff --check
git status --short
```

要求全量输出 0 act warning、0 Router warning、0 unhandled rejection。实现提交：

```text
fix(mountain-web): close storage status behavior evidence
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-storage-status-08-report.md
```

报告列出真实双请求时序、两个 Promise 的解析顺序与 DOM 断言、act warning 原始结果、语义修正、门禁和 clean status。报告提交：

```text
docs(mountain): report storage status correction
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 3M. CCF 系统诊断只读摘要页

### 3M.1 指令编号与已验收基线

```text
instruction: CCF-DIAGNOSTICS-SUMMARY-09
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: 879482d fix(mountain-web): close storage status behavior evidence
accepted report: 69fa143 docs(mountain): report storage status correction
```

审核者已复现 build、contract checker `48/48`、全量 `271/271`、0 act/Router warning、fixture checker、禁止项和 clean status。Storage 只读状态页验收通过。

视觉基准：

```text
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/SystemStatusTabs.tsx
/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/source/src/features/settings/systemStatus/types.ts
```

真实接口为 `GET /api/v1/settings/diagnostics`，现有 DTO 只有 API、动态服务汇总、工具链汇总、存储汇总、遥测状态、日志错误计数和脱敏 recent_errors。后端没有原型所示“系统能力矩阵”，本轮不得伪造。

### 3M.2 唯一目标

只整改 `/settings/diagnostics` 为系统级只读诊断摘要，不修改 Toolchain、Storage、Voice Alignment、Models、Assets、Task、checker 或后端。

1. 标题为“系统诊断”，说明这是当前运行环境的系统级摘要；具体 Task/Run 的事件、日志、Trace 和产物诊断仍进入任务工作台查看。
2. 展示 API、动态服务、工具链、存储、遥测、近期错误六类摘要。服务和工具链用后端真实计数；空注册表 `0/0/0` 是有效状态，不显示加载失败。
3. API status 对 `healthy/ok` 显示正常，对 `degraded` 显示降级，对 `failed/down/unavailable` 显示不可用；未知字符串必须原样可见并使用中性状态，不得过滤或假定正常。
4. 存储容量采用与已验收 Storage 页一致的安全格式化语义；null、负数、NaN、Infinity 显示“未统计”，不得产生 NaN 或负容量。不得复制一份容易漂移的算法：提取并复用纯展示 helper，或以同一共享函数服务两个页面并保留既有测试。
5. telemetry 只显示 enabled/disabled；logs 只显示 `recent_errors` 计数。系统摘要页不展示 `api.endpoint`、`telemetry.endpoint`、`logs.log_path`，也不展示 recent_errors 的任意 message/details/path；任务级错误详情由运行诊断页负责。
6. 增加明确的脱敏/隐私说明，并提供真实链接 `/tasks` 前往任务队列；不得硬编码具体 task_id 或假诊断入口。
7. 不实现原型能力矩阵。页面可不显示该区，报告记录 API gap；不得用固定 engine/visualSource 列表伪造。
8. loading 使用同构骨架；请求失败显示错误与真实“重新加载”。刷新/重新加载必须再次调用真实 GET，不得只更新时间或本地状态。
9. 使用请求生命周期保护：卸载/重进的旧响应不能污染新页面；复用 Storage 已验收的真实双生命周期测试模式，不得提交未解析 Promise 的假竞态测试。
10. 响应额外包含绝对路径、命令、token、secret、credential 时不得渲染；不得使用 localStorage/sessionStorage/runtime fixture/mock fallback。

### 3M.3 强制行为测试

- 六类摘要对完整真实 DTO 渲染，空服务/工具链计数正常；
- API healthy/degraded/down/未知状态分别映射；
- 服务与工具链不一致计数原样显示，不在前端重算或修正；
- 存储容量有效和异常边界，共享 helper 与 Storage 既有测试继续通过；
- telemetry/logs 为 null 与非 null 两组；只显示安全摘要，不显示 endpoint/log_path/recent error message/details；
- 页面包含脱敏说明和 `/tasks` 链接，不包含伪能力矩阵；
- loading、error、retry、真实双生命周期旧响应晚到测试；
- 敏感额外字段不进入 `container.textContent`；
- 0 act warning、0 Router warning、0 unhandled rejection。

### 3M.4 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 run test:contract-checker
npm --prefix web-v2 test -- --run
node web-v2/scripts/check-api-contract.mjs
! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/DiagnosticsPage.tsx
git diff --check
git status --short
```

实现提交：

```text
feat(mountain-web): align system diagnostics summary
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-diagnostics-summary-09-report.md
```

报告列出六类 DTO 映射、状态映射、共享容量 helper、敏感字段不渲染、双生命周期时序、能力矩阵 API gap、门禁与 clean status。报告提交：

```text
docs(mountain): report system diagnostics summary
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 3N. CCF 任务队列真实列表基线

### 3N.1 指令编号与已验收基线

```text
instruction: CCF-TASK-QUEUE-10
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: 7218eb5 feat(mountain-web): align system diagnostics summary
accepted report: 77837b0 docs(mountain): report system diagnostics summary
```

审核者已复现 `npm run build`、前端全量 `300 passed`，并使用真实 CCB uvicorn 与加密 SecretStore 运行本分支生产 checker，结果为 `All contracts aligned against real backend`。系统诊断摘要验收通过；旧报告中“真实 CCB checker 未运行”已由审核者补齐，无需改写旧报告。

### 3N.2 唯一目标

结束资产与设置阶段，依据仓库内现行 WebUI 原型基准，将 `/tasks` 收口为读取真实 `GET /api/v1/tasks` 的任务队列入口。只实现列表、筛选、游标翻页和合法导航，不修改任务工作台、创建任务流程、后端 API、DTO 契约或 Pipeline。

1. 页面和导航统一使用“任务队列”“新建任务”，不得重新引入 Project/项目作为业务概念。
2. 通过现有 `fetchTasks({limit,cursor,status,q})` 获取数据；搜索同时表达标题或 Task ID，状态筛选只发送后端支持的真实值。不得下载全量数据再伪装服务端筛选。
3. 每项只展示真实 DTO：`task_id`、`title`、Task 状态、`updated_at`，以及存在时的 `active_run.status/current_stage/retryable/final_available`。不得用固定阶段、随机进度、假百分比或推测性成果数量填充。
4. `active_run` 不存在时显示“尚未运行”。当前阶段通过统一阶段名称映射显示；未知阶段保留安全可读原值，不能崩溃。
5. 提供进入任务工作台的主操作；仅在 `active_run` 存在时提供运行诊断导航，仅在 `final_available=true` 且 run id 存在时提供成片入口。不得伪造尚无 API 支撑的取消、暂停、重试或逐工序控制。
6. 实现 loading skeleton、请求失败与重试、无任务、筛选无结果四种可区分状态。重试调用真实 adapter。
7. 分页严格使用响应 `next_cursor`；切换 `q/status` 必须清空旧 items 和 cursor。后发请求胜出，卸载后不得 setState；不得用延时猜竞态。
8. 不在 localStorage/sessionStorage 保存业务数据；不展示路径、命令、Secret、日志内容或错误内部详情。
9. 原型中若有现行 DTO 不提供的逐阶段状态、成果缩略图或批量控制，不得伪造；在报告 API gap 表逐项记录，供后续 CCB 切片处理。

### 3N.3 强制行为测试

- 首次请求参数、`q/status` 切换后 cursor 重置、`next_cursor` 翻页及无下一页行为。
- running、failed、completed、无 active run、未知状态和未知阶段的真实渲染。
- diagnostics/final 链接分别受 active run 与 `final_available` 约束，URL 编码 Task/Run ID。
- loading、请求错误后重试、空队列、筛选无结果。
- 两个可控 Promise 证明后发请求胜出；unmount 后旧请求完成不更新状态且无 act/unhandled rejection。
- 注入额外 `path/command/token/secret/logs` 字段，断言页面不渲染。
- 生产 API adapter 的 HTTP 边界测试；不得以源码字符串或只检查 mock 次数代替行为断言。

### 3N.4 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
npm --prefix web-v2 run test:contract-checker
MOUNTAIN_API_BASE=http://127.0.0.1:<动态端口>/api/v1 node web-v2/scripts/check-api-contract.mjs
! rg -n "\b(project|projects|Project|Projects)\b|localStorage|sessionStorage|Math\.random" web-v2/src/pages/TasksPage.tsx web-v2/tests/task*
git diff --check
git status --short
```

真实 checker 需要 CCB 后端已启动；若无法访问，只能如实标记 blocked，不能用 fixture 冒充。其余门禁必须完成。

实现提交：

```text
feat(mountain-web): establish real task queue
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-task-queue-10-report.md
```

报告列出原型映射、DTO 字段表、状态/阶段映射、操作显示条件、请求时序、API gap、门禁原始摘要、implementation commit 和 clean status。报告提交：

```text
docs(mountain): report real task queue
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 3O. CCF 任务队列生产导航与分页纠偏

### 3O.1 指令编号与审核结论

```text
instruction: CCF-TASK-QUEUE-11
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed implementation: ba2fc19 feat(mountain-web): establish real task queue
reviewed report: 29ad93a docs(mountain): report real task queue
result: rejected; tests pass but final action targets a test-only SPA route
```

审核者已复现 build 和前端全量 `327 passed`。拒绝原因是生产行为错误而非门禁失败：

1. `TasksPage` 将“成片”实现为 React Router `Link` 到 `/tasks/:taskId/runs/:runId/final`，但生产 `src/app/router.tsx` 没有该路由；点击进入 404。
2. `task-queue.test.tsx` 自行注册了该虚假 Route，因此测试证明的是测试路由，不是生产 Router。
3. “进入工作台”使用 `navigate(`/tasks/${t.task_id}`)`，没有编码 Task ID；同一页面其他操作却编码了 ID。
4. 加载更多期间没有独立 pending 状态或禁用按钮；连续点击会发出相同 cursor 的并发请求，两个响应都可 append，造成重复任务。
5. 当前报告的 DTO 映射遗漏了 `active_run.status/retryable/final_available` 的实际表现，未完整对应 §3N。

### 3O.2 唯一修复目标

只纠正任务队列生产导航、运行摘要和 cursor 分页行为；不修改后端、DTO、创建任务、任务工作台或 Pipeline。

1. “成片”必须使用生产 `getFinalUrl(task_id, run_id)` 指向后端媒体 endpoint，以普通 `<a>` 打开/下载；不得创建没有页面语义的 SPA `/final` 路由。
2. “进入工作台”和“运行诊断”的 Task/Run 参数全部编码。优先用小型集中 URL helper，避免各按钮各自拼接不一致。
3. 测试必须挂载生产 `router` 或复用生产 route definition 验证导航；不得在测试中注册生产不存在的 `/final` 页面来让断言通过。
4. active run 存在时显示真实运行状态；`retryable=true` 只显示“可重试”提示，不增加重试按钮；`final_available` 由成片入口的显示条件表达。未知 run 状态安全显示原值。
5. 将首次/筛选加载与“加载更多”状态分离。分页请求 pending 时按钮禁用且文案明确；同一 cursor 不得并发请求或重复 append。
6. 每次网络请求拥有唯一 generation/request token。筛选改变、重试、分页之间后发请求胜出；过期分页响应不得追加到新筛选结果。
7. 分页失败保留已经显示的 items 和 cursor，显示局部错误并允许重试该页；不得把整个队列替换成全页错误。
8. append 时按 `task_id` 防御性去重，同时保持服务端返回顺序；不得用客户端重新排序改变后端队列语义。

### 3O.3 强制生产行为测试

- 使用真实 `getFinalUrl`，断言成片是 API `<a href>`，不是 Router Link；生产 Router 下点击不进入 404。
- 工作台、诊断 URL 对包含 `/ + 空格` 的 Task/Run ID 正确编码。
- 双击/连续点击加载更多只发出一个该 cursor 请求，按钮 pending 时 disabled。
- 可控 Promise：旧筛选分页挂起后切换筛选，新响应先完成、旧分页后完成，旧 items 不得进入新列表。
- 分页失败保留第一页，点击局部重试仍使用原 cursor，成功后只追加一次。
- 后端跨页重复 task_id 时页面只出现一次且顺序稳定。
- active run 的 known/unknown status、retryable true/false 和 final_available true/false 均有 DOM 行为断言。
- 删除测试专用 `/final` Route；不得以源码字符串或只断言 mock 次数代替生产导航行为。

### 3O.4 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
npm --prefix web-v2 run test:contract-checker
! rg -n "path=.?[\"']?/tasks/:taskId/runs/:runId/final|<Route.*final" web-v2/src web-v2/tests
! rg -n "localStorage|sessionStorage|Math\.random" web-v2/src/pages/TasksPage.tsx web-v2/tests/task-queue.test.tsx
git diff --check
git status --short
```

纠偏提交：

```text
fix(mountain-web): correct task queue navigation and paging
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-task-queue-11-report.md
```

报告列出生产 Router 验证、成片 API URL、编码案例、分页状态机、旧响应隔离、去重行为、运行摘要映射、门禁和 clean status。报告提交：

```text
docs(mountain): report corrected task queue behavior
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 3P. CCF 任务队列 Router 证据与零 Warning 收口

### 3P.1 指令编号与审核结论

```text
instruction: CCF-TASK-QUEUE-12
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
reviewed implementation: d8a2ce8 fix(mountain-web): correct task queue navigation and paging
reviewed report: cc08193 docs(mountain): report corrected task queue behavior
result: implementation accepted; test/report rejected because full suite emits act warnings while report claims zero
```

审核者已复现 build、`329 passed` 和 checker `48 passed`。生产成片 API `<a>`、ID 编码、分页互斥、旧响应隔离、局部失败恢复和去重实现均正确。唯一收口问题：`production router has no /final route` 测试没有断言，也没有等待页面异步请求完成，稳定输出两条 React act warning；报告却写 `act warnings: 0`。

### 3P.2 唯一任务

只修复测试证据和报告，不修改已验收的 `TasksPage` 业务行为，不扩展新功能。

1. 删除“无断言即证明 absence”的测试。测试不得通过注释声明成功。
2. 将生产 child route definitions 提取为可导出的 `RouteObject[]` 常量并由 `createBrowserRouter` 直接复用，或采用等价的不重复生产路由定义方式。
3. 使用 React Router `matchRoutes()` 对真实生产 route definitions 做行为断言：工作台和 diagnostics 能匹配对应页面；`/tasks/:taskId/runs/:runId/final` 不得匹配一个 final 页面，只能落入生产 wildcard/404。
4. 成片按钮测试继续断言真实 `getFinalUrl()` API href、`target=_blank`、`rel=noopener noreferrer`，且元素为 `<a>` 而非 Router navigation。
5. 所有渲染测试必须等待请求 settle 或在 act 内完成；全量测试 stderr 中必须 0 act warning、0 Router warning、0 unhandled rejection。
6. 不得修改后端、DTO、TasksPage 分页状态机、创建任务、工作台或 Pipeline。
7. 新建纠偏报告，明确上一报告的 warning 声明错误以及本轮真实结果；不得改写旧报告掩盖审计历史。

### 3P.3 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-task-queue-12-test.log
! rg -n "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection" /tmp/ccf-task-queue-12-test.log
npm --prefix web-v2 run test:contract-checker
! rg -n "No assertion needed|absence.*proof|it\([^)]*production router[^)]*,\s*\(\)\s*=>\s*\{\s*\}\)" web-v2/tests
git diff --check
git status --short
```

纠偏提交：

```text
test(mountain-web): prove production task routes without warnings
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-task-queue-12-report.md
```

报告提交：

```text
docs(mountain): report warning-free task route evidence
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 3Q. CCF 新建任务核心输入真实保存

### 3Q.1 指令编号与已验收基线

```text
instruction: CCF-CREATE-TASK-13
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web
branch: feat/mountain-assets-settings-web
accepted implementation: 41041dd test(mountain-web): prove production task routes without warnings
accepted report: 685787d docs(mountain): report warning-free task route evidence
```

审核者已复现 build、全量 `332 passed`、checker `48 passed`，并扫描确认 0 act warning、0 Router warning、0 unhandled rejection。任务队列前端阶段验收完成。

### 3Q.2 唯一目标

将 `/tasks/new` 从“只创建空 Task、丢弃用户文案”的占位页，改为能够真实完成 `createTask → uploadInputs` 的标准白板任务输入保存。只覆盖任务名称、完整文案、文案整理规则、参考音频、画面锚定开关和字幕开关；不实现资产选择、选择性手动阶段、启动 Run 或其他引擎。

1. 当前页面的 `script` 已采集却从未提交，这是阻断缺陷。本轮保存成功的定义必须同时满足：`POST /tasks` 成功且随后 `POST /tasks/{task_id}/inputs` 成功。
2. 标准流程本轮固定 `engine=whiteboard`，不得继续展示尚未完成的动态信息图选择。Task 创建请求只发送后端真实支持的 `title/engine/pipeline_id`。
3. 文案必填，使用原始完整文本提交；不得在前端自行实现另一套分割算法或把预览结果当权威数据。
4. 提供 `target_chars/min_chars/max_chars` 三个明确的整数输入，默认分别为 `80/35/140`；校验 `1 <= min <= target <= max`，并设置合理上限。将三项原样写入 FormData。
5. 提供 `visual_anchor_enabled` 和 `include_subtitles` 开关，按真实布尔字符串写入 FormData。其余现有必需字段使用明确、可见的标准默认值：`style`、`pen_text`、`stroke_detail`；不得秘密从 localStorage 读取。
6. 提供可选参考音频文件输入，只接受后端支持的 `.wav/.mp3/.m4a/.ogg/.flac`；FormData 字段名为 `reference`。浏览器不得读取、打印、缓存或 base64 化文件内容。
7. 创建 Task 成功而 input 保存失败时，不得再次点击就重复创建 Task。组件保留本次响应的 `task_id/run_id`，显示“任务已创建、输入保存失败”，提供“重试保存输入”和“进入任务工作台”两个明确选择。
8. 重试保存只调用 `uploadInputs(existingTaskId, form)`；成功后跳转编码后的 `/tasks/{task_id}`。首次两步均成功也跳转工作台。
9. 防止重复提交：create 和 upload 任一步 pending 时主按钮 disabled；双击只产生一次 create。卸载后请求完成不得 setState/navigate。
10. API 错误只展示 `MountainApiError` 的安全 message/code；不得渲染响应中的 path、command、token、secret、traceback 或参考音频内容。
11. “执行策略”本轮不得伪造保存。页面明确说明当前仅保存任务输入，Run 在任务工作台启动；选择性手动阶段等待后端正式契约。不得把产品 `manual` 偷换成内部 `gated`。

### 3Q.3 强制行为测试

- 空标题、空文案、规则逆序/非整数/越界均不会发送请求，并显示对应字段错误。
- 正常路径严格先 create 后 upload；断言 create JSON 和 FormData 每个字段的真实值，FormData 无手工 Content-Type。
- 有/无 reference 两条路径；验证只传 File 对象，不读取内容。
- create 失败不调用 upload；upload 失败保留真实 task_id/run_id，不导航、不重复 create。
- upload 失败后点击重试只调用 upload；成功跳转编码 Task ID。
- 双击提交只调用一次 create；pending 状态禁用。
- unmount 后 create 或 upload 完成不更新状态、不导航，0 act warning/unhandled rejection。
- 注入敏感扩展错误字段，页面不渲染。
- HTTP 边界继续验证 `POST /api/v1/tasks` JSON 与 `/inputs` multipart；不得只断言 mock 次数。

### 3Q.4 门禁、提交和报告

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run 2>&1 | tee /tmp/ccf-create-task-13-test.log
! rg -n "not wrapped in act|React Router Future Flag|Unhandled|unhandled rejection" /tmp/ccf-create-task-13-test.log
npm --prefix web-v2 run test:contract-checker
! rg -n "localStorage|sessionStorage|FileReader|readAsDataURL|infographic-remotion|execution_strategy.*manual|policy.*gated" web-v2/src/pages/CreateTaskPage.tsx web-v2/tests/create-task.test.tsx
git diff --check
git status --short
```

实现提交：

```text
feat(mountain-web): persist core task inputs
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/docs/Mountain/m07-ccf-create-task-13-report.md
```

报告列出两步请求时序、字段/FormData 映射、校验矩阵、partial failure 状态机、reference 安全边界、执行策略 API gap、门禁和 clean status。报告提交：

```text
docs(mountain): report core task input persistence
```

先本地提交，不推送。执行者不得自行宣布审核通过。

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

## 4C. CCB 可复现运行基线纠偏指令

### 4C.1 指令编号与审核结论

```text
instruction: CCB-RUNTIME-BASELINE-07
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation commit: b79291a fix(mountain): harden production runtime and task API boundaries
reviewed report commit: 391fe40 docs(mountain): report CCB runtime closeout status
result: rejected
```

保留上述提交，只允许形成增量 follow-up；不得 amend、squash、reset 或开始新功能。

### 4C.2 审核者复现实证

- 使用项目约定解释器 `/mnt/d/workstation/projects/cs-board/.venv/bin/python` 执行全量测试，实际结果为 `12 failed, 329 passed, 10 skipped, 80 errors`，不是报告中的 `426 passed, 5 skipped`。
- 同一解释器执行 `import cryptography` 得到 `ModuleNotFoundError`，默认加密 `create_app()` 无法启动。
- `cryptography` 虽写入两个 requirements 文件，但尚未形成“从项目安装入口安装后即可运行”的可复现闭环。
- `webapp/mountain_task_api.py` 仍直接使用 `repository.task_dir/run_dir`，读取 `request.json/task.json/index.json/JSONL` 并拼接 `final.mp4`；因此报告中的“Task Router 不直接读取这些文件”不成立。该架构债留给下一个独立切片，本轮不得继续宣称已关闭。
- 完成报告中的真实 HTTP 摘要显示 start 返回 `VALIDATION_ERROR`，不能作为“缺能力返回 CAPABILITY_NOT_AVAILABLE”的证明。

### 4C.3 本轮唯一目标

建立一条任何审核者都能在指定解释器中复现的后端运行基线。只处理依赖安装、默认加密启动、测试环境隔离和报告真实性，不改 Task Router 架构、不新增 API/业务功能。

必须完成：

1. 明确项目后端唯一安装入口，并保证执行该安装入口后，指定解释器可成功 `import cryptography`。不得依赖 CCB 自己终端中未记录的另一个 venv 或全局 site-packages。
2. 保持默认 fail-closed：未设置 `CSBOARD_ALLOW_PLAINTEXT_SECRETS` 时，`create_app(temp_dir)` 成功且 `/api/v1/health` 返回 `secret_store.encrypted=true`；只有明确 scoped 测试才可启用明文。
3. 修复因移除全局明文环境变量暴露出来的测试隔离问题。需要明文的旧测试逐个显式使用 fixture；验证默认加密行为的测试不得使用该 fixture。禁止重新引入全局环境变量或 autouse 明文 fixture。
4. `webapp.mountain_server:app` 在依赖正确安装后必须是 FastAPI 实例，不能是 `None`；依赖缺失时必须给出明确启动错误，不能静默生成不可用 app。
5. 在同一指定解释器中完整执行全量测试、compileall 和真实 TestClient/HTTP 冒烟；报告必须原样记录结果。任何失败都只能标记“执行中”。
6. 报告必须明确保留的下一阶段债务：Task Router 仍有直接文件/目录访问，`CAPABILITY_NOT_AVAILABLE` 的真实 start 行为尚需独立审核（除非本轮不改业务代码即可真实证明），FastAPI 框架 422 尚未统一 `body.error`。

### 4C.4 机器门禁

所有命令必须在本指令指定 worktree 执行：

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pip install -r requirements-dev.txt
/mnt/d/workstation/projects/cs-board/.venv/bin/python -c "import cryptography; from webapp.mountain_server import app; assert app is not None; print(cryptography.__version__)"
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

另增加/保留一个行为测试，使用 `monkeypatch.delenv(..., raising=False)` 和临时 data dir 创建 app，断言 health 的 `encrypted is True`。不得用源码字符串、`hasattr` 或 mock 替代。

### 4C.5 提交与报告

实现提交：

```text
fix(mountain): make encrypted runtime baseline reproducible
```

报告提交：

```text
docs(mountain): report reproducible runtime baseline
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-runtime-baseline-07-report.md
```

先本地提交，不推送。报告只写命令实际输出，并列出所有未关闭债务；执行者不得自行宣布审核或联合验收通过。

## 4D. CCB 单一垂直切片：Task 输入与启动边界

### 4D.1 指令编号与已验收基线

```text
instruction: CCB-TASK-INPUT-START-08
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
accepted implementation: 5c3deff fix(mountain): make encrypted runtime baseline reproducible
accepted report: 89626a7 docs(mountain): report reproducible runtime baseline
```

审核者已在指定共享解释器中复现：`cryptography 50.0.1`、模块 app 为 FastAPI、`427 passed, 5 skipped`、compileall 与 clean status。本轮基线通过。

审核者还真实复现了 `create task -> multipart save inputs -> start`：输入保存返回 200，缺少 Service 时 start 返回 `400` 且 `body.error.code=CAPABILITY_NOT_AVAILABLE`。该行为不得返工或改回 `detail`。

### 4D.2 唯一目标

只收口 Task 的“保存输入、读取输入、启动运行”这一条垂直链。Router 负责 HTTP 解析/响应和受控上传 staging；Application command/query 负责领域校验、输入状态和启动前置条件；Repository 负责持久化。不得同时重构 artifacts、events、logs、diagnostics、final 或其他 Router。

完成后，`webapp/mountain_task_api.py` 的以下三个 endpoint 不得出现 `repository.task_dir/run_dir`、`request.json/task.json`、`Path.read_text/write_text` 或自行解释 input manifest：

- `POST /api/v1/tasks/{task_id}/inputs`
- `GET /api/v1/tasks/{task_id}/inputs`
- `POST /api/v1/tasks/{task_id}/runs/{run_id}/start`

具体要求：

1. Router 将上传文件分块写入受控临时 staging，设置大小上限，并在成功或失败后清理；不得先写入任务正式目录。
2. `MountainCommands.save_inputs(...)` 接收 staging 引用，由 Application 校验 Task、音频类型/非空、制作参数和规则，并通过 Repository/输入存储接口原子提交 manifest 与 reference。
3. `MountainCommands.get_inputs(task_id)` 返回稳定、非敏感 DTO；Router 不读取或合并 JSON。
4. 启动前的“输入是否已保存”及所需 capability 计算进入 Application command/service；Router 只调用一个启动入口，不读取 request 文件、不遍历阶段映射。
5. 缺输入继续返回 `400 body.error.code=VALIDATION_ERROR`；有输入但缺服务继续返回 `400 body.error.code=CAPABILITY_NOT_AVAILABLE`，并在单一位置返回非重复的 `unavailable` 详情。不得同时出现顶层空 `unavailable` 和 `details.unavailable`。
6. 更新输入未提供新 reference 时保留旧 reference；失败时旧 manifest/reference 完整保留且 staging/partial 为零。
7. CLI 与 Web 必须复用同一 Application 输入/启动语义；本轮不改变公开 CLI 参数。

### 4D.3 强制行为测试

至少覆盖：

- 真实 multipart 分块上传后 GET 回读一致，DTO 不泄漏绝对路径、staging 路径或 Secret；
- 超限、空文件、非法扩展/媒体、任务不存在均返回稳定 `body.error`，且无正式目录 partial；
- 更新不带 reference 保留旧文件，更新失败也保留旧 manifest 和 sha256；
- 缺输入 start 为 VALIDATION_ERROR；保存输入后缺 Service 为 CAPABILITY_NOT_AVAILABLE，`unavailable` 只出现一次且包含 stage/capability；
- 注入 fake Application/Repository 时证明三个 endpoint 不绕过端口访问磁盘，并同时具有真实 HTTP 行为测试；
- CLI 与 Web 对同一 Task 读取相同输入状态。

禁止只用源码字符串、`hasattr`、mock 调用次数或宽松的“不是 500”断言替代行为验证。架构边界静态检查可作为附加门禁，但不能代替上述行为。

### 4D.4 固定门禁与提交

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

实现提交：

```text
refactor(mountain): move task input and start semantics into application
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-start-08-report.md
```

报告提交：

```text
docs(mountain): report task input and start boundary status
```

先本地提交，不推送。报告必须给出 implementation commit、具体测试名、门禁原始摘要、三个 endpoint 的生产调用关系和仍未收口的 Router 债务；执行者不得自行宣布最终审核通过。

## 4E. CCB Task 输入边界单点纠偏

### 4E.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-ATOMIC-09
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 98f4061 refactor(mountain): move task input and start semantics into application
reviewed report: c383467 docs(mountain): report task input and start boundary status
result: rejected; 430 tests pass but upload safety and atomicity requirements are not implemented
```

保留两个提交，只形成增量 follow-up。不得开始 artifacts/events/logs/final 等后续收口。

### 4E.2 审核实证

1. Router 使用 `await reference.read()` 将完整上传一次性读入内存，没有分块 staging、没有大小上限；报告将其描述为完成，与 §4D.2.1 不符。
2. `MountainCommands.save_inputs()` 先 `save_input_file()`、再 `save_request()`，最后才运行 `prepare_script()`。如果规则或文案整理失败，新音频及 request 已覆盖，违反“失败保留旧 manifest/reference 且无 partial”。
3. Repository 的 `save_input_file()` 与 `save_request()` 分别原子替换单文件，但二者和 Task preparation 不是一个原子提交单元；单文件原子不等于业务事务原子。
4. 新测试只验证成功更新不带 reference；没有验证上传新 reference 后发生校验/提交失败时旧音频 sha256、旧 request 和旧 Task preparation 均保持不变。

### 4E.3 唯一修复目标

只修复 Task 输入上传的有界 staging 和业务原子提交：

1. Router 使用固定 chunk 循环将 `UploadFile` 写入由安全临时目录创建的唯一 staging 文件；设置明确的最大字节数。超过上限立即返回 `400 body.error.code=VALIDATION_ERROR`，关闭上传并清理 staging。禁止 `await reference.read()` 无参数，禁止把完整音频 bytes 传入 Application。
2. Application 接收只读 staging descriptor/path 加原始文件名/媒体信息。先完成 Task 存在性、脚本、规则、扩展名、非空、大小等全部校验，并完成 `prepare_script()`，然后才允许进入持久化提交。
3. 在 Repository/专用输入存储 port 增加一个业务级原子提交接口，一次提交 request、Task preparation 和可选 reference。可使用同目录临时文件、备份与锁，但必须保证任一 replace/write/save 失败时恢复原 request、Task 和 reference，并清理所有临时/备份文件。
4. 不上传新 reference 时保留旧 reference；上传不同扩展的新 reference 成功后，旧 reference 文件不得被元数据误选。不要通过扫描目录猜当前 reference，必须以 manifest/request 指向的相对路径读取元数据。
5. Router `finally` 清理 staging；Application/Repository 成功或失败均不得留下 `.partial`、`.tmp`、`.bak` 或 staging 文件。
6. 保持已经通过的 GET inputs 与 start 错误契约，不改公开 DTO 和 CLI 参数。

### 4E.4 强制行为测试

必须新增真实行为测试：

- 使用会记录 `read(size)` 参数的 UploadFile/HTTP 上传证明分块读取，且不存在无参全量 read；
- 恰好上限成功、超过上限失败，失败后 staging 与任务正式目录无新文件；
- 初次输入成功后，记录 request 内容、Task preparation、reference sha256；随后上传新 reference 并给出非法规则导致 `prepare_script` 失败，三者完全不变；
- 注入 Repository 在第二/第三个 replace 时失败，验证全部旧状态恢复且临时文件为零；
- 成功用 `.mp3` 替换旧 `.wav` 后，GET inputs 只报告当前 `.mp3` 的 filename/size，不能扫描命中旧 `.wav`；
- 缺输入 start 和缺 Service start 的既有测试继续通过。

不得用源码字符串、只检查文件存在、mock 调用次数或“状态码不是 500”替代上述最终状态断言。

### 4E.5 门禁与提交

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

实现提交：

```text
fix(mountain): make task input upload bounded and atomic
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-atomic-09-report.md
```

报告提交：

```text
docs(mountain): report bounded atomic input status
```

先本地提交，不推送。报告必须明确 staging 上限、事务策略、故障注入测试和两个 commit hash；执行者不得自行宣布审核通过。

## 4F. CCB 原子输入生产路径纠偏

### 4F.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-ATOMIC-10
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 349c954 fix(mountain): make task input upload bounded and atomic
reviewed report: 0728c2d docs(mountain): report bounded atomic input status
result: rejected
```

保留上述提交，只形成增量 follow-up。本轮仍只处理 Task 输入事务，不开始其他 Router 或新功能。

### 4F.2 审核实证

1. 报告明确承认 §4E 强制要求的第二/第三步故障注入测试未完成，因此不能通过。
2. `test_chunked_upload_with_size_limit` 只上传 1KB 并断言 200；它没有验证分块 read 参数、恰好上限、超过上限或清理，测试名与证据不符。
3. Router 用系统默认 `/tmp` 创建 staging，Repository 用 `Path.rename()` 移入 `/mnt/d` 数据目录。审核者在 `/mnt/d/workstation/projects/cs-board` 临时 data dir 真实复现：有效小文件上传返回 `400 INTERNAL_ERROR`，错误为 `[Errno 18] Invalid cross-device link`。
4. 回滚逻辑在“无旧 request”时失败不会删除新 request；新旧 reference 扩展不同时，失败可能恢复旧 reference 但留下新扩展文件。
5. 固定 `request.json.bak/task.json.bak/reference.wav.bak` 不是唯一事务备份，遇到陈旧备份或并发/崩溃恢复存在覆盖风险。
6. `get_inputs()` 仍通过 `repository.task_dir()` 拼路径读取元数据，没有使用正式 Repository/输入存储 port。

### 4F.3 唯一修复目标

建立在 Windows/WSL 实际数据盘上也成立、可故障注入证明的 Task 输入事务：

1. staging 必须由 Repository/专用 InputStore 创建在目标 Task 文件系统内的受控 staging 目录，Router 只能通过 port 获取写入句柄或 staging descriptor。禁止系统默认 `/tmp` 加跨设备 rename，禁止 Router 自行知道任务正式路径。
2. 上传上限和 chunk size 必须可在测试中安全注入为小值；生产默认仍为 50MB/1MB。Router 对 UploadFile 只调用 `read(CHUNK_SIZE)`，并在 finally 中关闭上传和释放 staging。
3. Repository 使用唯一 transaction ID/目录准备所有新文件；验证完成后在 Task lock 内提交。事务失败必须根据提交前快照恢复“存在”和“不存在”两种状态，并删除本事务产生的所有新 reference/request/task/temp/backup。
4. 同扩展和跨扩展 reference 替换均须正确；成功后只保留 manifest 当前指向的 reference，失败后只保留旧 reference，不得留下孤儿新文件。
5. 用 Repository/InputStore 正式接口读取当前 reference 元数据；Application 和 Router 不调用 `task_dir/run_dir`，不拼物理路径。
6. 内部 I/O 错误返回稳定、已脱敏的 `body.error.code=INTERNAL_ERROR`，不得把绝对 staging/data 路径或 Python errno 原文暴露给客户端。

### 4F.4 强制行为测试

测试必须操作生产实现并覆盖：

- data dir 明确位于 `/mnt/d`，小 WAV 上传成功，证明无跨文件系统错误；
- 记录 UploadFile read 调用，全部带固定 size，恰好注入上限成功、上限加 1 字节失败；
- 超限、Application 校验失败、Repository 第 1/2/3 个提交动作失败后，staging/transaction/`.bak/.tmp/.partial` 为零；
- 已有输入场景记录 request、Task preparation、旧 reference sha256；新同扩展及新跨扩展提交分别在每个故障点失败，三者完全保持；
- 首次保存在每个故障点失败后，request/reference 不存在，原 Task 原样存在；
- 成功跨扩展替换后旧 reference 被清除，GET 只返回 manifest 当前文件；
- HTTP INTERNAL_ERROR 响应不含 `/tmp`、`/mnt/`、反斜杠绝对路径、`Errno` 或异常原文；
- 既有 start 契约测试继续通过。

禁止源码字符串测试、只上传小文件却声称验证上限、只 mock 调用次数或仅断言状态码。

### 4F.5 门禁、提交与报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

实现提交：

```text
fix(mountain): make task input transaction production safe
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-atomic-10-report.md
```

报告提交：

```text
docs(mountain): report production safe input transaction
```

先本地提交，不推送。报告必须包含 `/mnt/d` 实测、每个故障点的最终状态断言、两个 commit hash 和所有未关闭事项；执行者不得自行宣布审核通过。

## 4G. CCB 输入事务最终行为纠偏

### 4G.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-TRANSACTION-11
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 7db67d6 fix(mountain): make task input transaction production safe
reviewed report: 0ce3ba2 docs(mountain): report production safe input transaction
result: rejected; 435 tests pass but mandatory transaction behavior is unproved and rollback is incorrect
```

保留已有提交，仅形成增量 follow-up。本轮禁止开始其他 Router、FastAPI 422 或新功能。

### 4G.2 已确认问题

1. 报告再次明确承认“每个提交动作故障注入测试”缺失，违反 §4F.4。
2. `test_staging_on_same_filesystem` 注释称使用 `/mnt/d`，实际 `data_dir = tmp_path`，默认路径为 `/tmp/pytest-*`；没有覆盖真实数据盘。
3. `test_chunked_read_verification` 只上传 10KB，没有记录 `UploadFile.read(size)`，没有注入上限，也没有测试上限加 1 字节。
4. 回滚判断 `backup exists && target exists -> unlink backup` 会在新 target 已安装后删除旧备份，留下新 request/task/reference，恰好违背回滚目的。
5. 跨扩展 reference 失败时可能恢复旧文件但不删除新扩展 target；首次提交失败且没有 backup 时，新 request/reference 也不会被删除。
6. 无新 reference 时 `txn_dir=None`，request 与 task 顺序直写，不属于业务级原子提交。
7. Router 在验证 Task 存在前调用 `create_staging(task_id)`，不存在的 task_id 可能被创建空任务目录。
8. 工作树存在未跟踪 `docs/Mountain/mountain-engineering-debt.md`，报告中的 clean status 不真实。不得直接删除；应将其内容合并进本轮报告的未完成项后纳入报告提交，或作为独立、说明清楚的文档提交。

### 4G.3 唯一目标

使所有输入保存（有无 reference）都走同一、可故障注入、最终状态正确的事务：

1. Application 在创建事务前先通过 Repository 验证 Task 存在；不存在时不得产生 task 目录、`.staging` 或任何文件。
2. 每次 save_inputs 都创建唯一 transaction，包括仅更新文案且不上传 reference；在 transaction 中准备完整的新 request 和 task，以及可选 reference。
3. 将所有目标安装动作收口到一个可在测试 Repository 中按序失败的生产方法（例如 `_replace_for_commit`）。不得为测试复制事务算法。
4. 回滚必须先删除本事务已安装的新 target，再恢复旧 backup；提交前不存在的 target 在失败后必须重新不存在。不能根据“target 当前存在”推断它是旧文件。
5. 成功提交后清除旧 reference（跨扩展时）、所有 backup、transaction 文件和空 staging 父目录；失败也同样清零事务垃圾。
6. 上传限制作为 Router factory/config 的显式参数注入，生产默认 50MB/1MB；测试使用小上限，不得分配 50MB 才能验证边界。
7. 使用真实 `/mnt/d/workstation/projects/cs-board` 下的 `TemporaryDirectory` 做至少一个 HTTP 上传测试；测试自行清理且不得把运行数据提交 Git。
8. 保持 INTERNAL_ERROR 脱敏和既有 GET/start 契约。

### 4G.4 强制测试矩阵

必须基于生产事务实现验证：

- 不存在 Task 上传：404/稳定错误，磁盘无该 task 目录；
- 无 reference 的首次保存与更新保存，在每个 target 安装动作失败时均恢复提交前状态；
- 有 reference 的首次保存：第 1/2/3 个安装动作分别失败后，request/reference 不存在，Task 原样；
- 已有同扩展 reference 更新：每个故障点后 request、Task、reference sha256 与旧值一致；
- 已有跨扩展 reference 更新：每个故障点后只有旧扩展文件且 sha256 一致，新扩展不存在；
- 所有上述失败和成功场景后，递归扫描 `.staging/*.bak/*.tmp/*.partial` 为零；
- 注入 `max_bytes=8, chunk_size=4`，8 字节成功、9 字节返回 VALIDATION_ERROR，并用记录型 UploadFile/生产上传函数证明每次 `read(4)`，无无参 read；
- `/mnt/d` TemporaryDirectory 的真实 HTTP 小文件上传返回 200；
- INTERNAL_ERROR 响应不含路径、Errno 和注入异常文本。

测试不得使用源码字符串、虚假注释、只检查 mock 次数或宽松状态码。

### 4G.5 门禁和提交

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

实现提交：

```text
fix(mountain): prove and restore task input transactions
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-transaction-11-report.md
```

报告提交：

```text
docs(mountain): report verified task input transactions
```

先本地提交，不推送。报告逐行列出故障矩阵结果、真实 `/mnt/d` 路径类别（隐藏随机目录名）、两个 commit hash和 clean status；任何矩阵未完成只能标“执行中”。

## 4H. CCB 输入事务并发与真实故障注入纠偏

### 4H.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-TRANSACTION-12
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 45d7b97 fix(mountain): prove and restore task input transactions
reviewed report: c201d4e docs(mountain): report verified task input transactions
result: rejected; tests pass but production serialization and fault-injection evidence are invalid
```

保留上述提交，只形成增量 follow-up commit；不得 amend、squash、reset 或扩大到其他 Router、资产、设置功能。审核者已复现专项 `20 passed`、全量 `455 passed, 5 skipped`；拒绝原因不是门禁失败，而是门禁没有证明生产实现。

### 4H.2 已确认阻断问题

1. `FilesystemTaskRepository.commit_inputs()` 在 `45d7b97` 中移除了原有 `with self.task_lock(task_id)`。同一 Task 的两个并发保存可交错 rename、backup 和 rollback，破坏 request/task/reference 一致性。
2. `FaultInjectRepository._install_target()` 完整复制生产算法。故障测试运行的是测试副本，不是生产算法；生产代码回归时测试仍可能全绿。
3. 当前故障只在步骤开始前抛出，没有覆盖旧文件已备份、新文件已安装后的半提交状态。
4. `MountainCommands.save_inputs()` 在 Repository 锁外读取旧 request 来保留 reference；并发时，无新音频的后写事务可能用过期快照覆盖刚提交的新 reference。

### 4H.3 唯一修复目标

1. 对同一 `task_id` 的完整输入提交恢复 Repository 级串行化。锁覆盖读取当前 request/task/reference、形成最终提交数据、备份、安装、回滚和清理；不同 Task 不得共用全局事务锁。
2. “未上传新 reference”必须在锁内从当前已提交状态保留 reference。可通过显式 `preserve_reference`、Repository 内合并或等价清晰接口实现；不得依赖 Application 锁外旧快照，也不得用空字符串猜三态。
3. 在生产 Repository 中增加最窄、默认 no-op 的故障注入 seam，例如 `_input_txn_checkpoint(name, context)`。测试子类只能覆盖该 hook 抛错，不得覆盖或复制 `commit_inputs()`、`_install_target()`、回滚或清理算法。
4. checkpoint 至少覆盖 request/task/reference 各自的 `after_backup` 和 `after_install`；首次保存无 backup 时仍覆盖对应 `after_install`。
5. 任一 checkpoint 抛错后，提交前 request、task、reference 内容和文件集合完全恢复；本事务 `.bak`、`.tmp`、`.partial`、staging 和跨扩展新文件为零。
6. 成功并发保存产生自洽状态：`request.script`、`task.script_preparation` 和 reference 指向属于一个已完成事务。明确并测试以取得 Task 事务锁后的提交顺序为准。

### 4H.4 强制生产行为测试

- 测试子类只覆盖生产 checkpoint hook；测试中不得存在第二份 `_install_target` 或 rollback 实现。
- 首次无 reference：request/task 的 `after_install` 故障后恢复空状态。
- 首次有 reference：request/task/reference 的 `after_install` 故障后恢复空状态。
- 已有同扩展 reference：request/task/reference 的 `after_backup`、`after_install` 故障后，三个旧对象 sha256/JSON 均不变。
- 已有跨扩展 reference：相同矩阵后只存在旧扩展 reference，内容与 manifest 指向一致。
- 并发测试用 Barrier/Event 或等价同步原语让事务 A 停在生产 checkpoint，再启动事务 B；断言 B 在 A 释放前不能进入同一 Task 提交区。不得用 `sleep` 猜竞态。
- 覆盖“事务 A 上传新 reference、事务 B 不上传 reference”的确定顺序，证明 B 保留 A 最新 reference，而非锁外旧快照。
- 增加不同 Task 可并行测试，证明没有退化为全局锁。
- HTTP 404、大小上限、`/mnt/d` 上传和 INTERNAL_ERROR 脱敏继续通过。

禁止源码字符串断言替代行为测试。`rg` 只能作为额外禁止项门禁。

### 4H.5 固定门禁、提交和报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_input_transaction_11.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
! rg -n "def _install_target|installed_request|old_request_bak" tests/test_input_transaction_11.py
git diff --check
git status --short
```

实现提交：

```text
fix(mountain): serialize and prove input transactions
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-transaction-12-report.md
```

报告列出 implementation commit、生产 checkpoint 名称、故障矩阵测试、并发同步方式、最终一致性断言、所有门禁原始摘要、clean status 和未完成项。报告提交：

```text
docs(mountain): report serialized input transaction status
```

先本地提交，不推送。执行者只报告门禁结果，不得自行宣布审核通过。

## 4I. CCB 同一 Task 真并发验收纠偏

### 4I.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-CONCURRENCY-13
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 353a773 fix(mountain): serialize and prove input transactions
reviewed report: 6fbfc3a docs(mountain): report serialized input transaction status
result: rejected; production direction is correct, required same-Task concurrency behavior was not tested
```

审核者已复现专项 `22 passed`、全量 `457 passed, 5 skipped`、compileall、禁止项和 clean status。生产 checkpoint、锁内 reference 保留和回滚矩阵方向正确；本轮只补齐缺失的并发行为证据，除非新测试暴露真实缺陷，否则不得修改生产代码。

### 4I.2 拒绝原因

1. `test_same_task_lock_serializes` 只断言两次 `task_lock(task_id)` 返回同一个对象，没有运行 `commit_inputs()`，无法证明事务 A 持锁时事务 B 被阻塞。
2. `test_concurrent_ref_preservation` 是 A、B 顺序请求，不是并发请求，无法证明 B 等待 A 后读取最新 reference。
3. 报告称“TestClient 是同步的，无法直接测试真正并发”，但同一文件已用两个线程和 TestClient 验证不同 Task 并行；该理由不成立。
4. §4H 明确要求使用 Barrier/Event 让 A 停在生产 checkpoint，再启动同一 Task 的 B，并证明 B 在释放前不能进入提交区；当前未交付。

### 4I.3 唯一任务

以现有生产 `_input_txn_checkpoint()` 为同步点，新增或重写同一 Task 真并发测试：

1. 使用共享的生产 Repository 实例和同一个 Task；事务 A、B 在两个真实线程执行生产 `MountainCommands.save_inputs()` 或真实 HTTP `/inputs` 路径。
2. A 上传新的 reference，并在持有 Task 锁期间停在 `request.after_install`（或更能证明锁覆盖提交区的 checkpoint）。测试 hook 通过 Event/Barrier 通知主线程 A 已进入。
3. 主线程确认 A 已停住后启动 B；B 不上传 reference，并提交不同 script。必须有确定信号证明 B 已开始调用保存，而非尚未获得调度。
4. A 未释放时，B 不得到达任何生产 transaction checkpoint，也不得返回成功。使用 Event 的有界 `wait(timeout)` 和线程存活状态证明；不得使用 `sleep` 猜竞态。
5. 释放 A 后，两线程必须在有界时间内结束且无死锁，两个保存均成功。最终状态按锁获取顺序属于 B：`request.script` 是 B，`task.script_preparation.voice_units` 拼接后等于 B 的规范化 script，`request.reference_audio` 仍指向 A 上传的新 reference，文件 sha256 等于 A 上传内容。
6. 最终 `.staging`、`.bak`、`.tmp`、`.partial` 和孤儿 reference 为零。
7. 保留并继续通过不同 Task 真并行测试。该测试与同一 Task 串行测试必须共享生产事务算法，只允许 checkpoint hook 提供同步，不得覆盖 `_install_target()`、commit 或 rollback。
8. 测试若暴露生产缺陷，做最小修复并补充对应断言；若没有暴露，不要为了形成 diff 修改生产代码。

### 4I.4 门禁、提交和报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_input_transaction_11.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
! rg -n "def _install_target|installed_request|old_request_bak|time\.sleep" tests/test_input_transaction_11.py
git diff --check
git status --short
```

测试/最小修复提交：

```text
test(mountain): prove same-task input serialization
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-concurrency-13-report.md
```

报告必须说明线程同步时序、A/B checkpoint 证据、A 未释放时 B 的观测、最终 request/task/reference 一致性、垃圾文件扫描、门禁原始摘要、implementation/test commit 和 clean status。报告提交：

```text
docs(mountain): report same-task concurrency proof
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4J. CCB 同一 Task 并发证据最终收口

### 4J.1 指令编号与审核结论

```text
instruction: CCB-TASK-INPUT-CONCURRENCY-14
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed test commit: 66bf570 test(mountain): prove same-task input serialization
reviewed report: 65744bd docs(mountain): report same-task concurrency proof
result: rejected narrowly; real two-thread path exists, three required assertions remain
```

审核者已复现专项 `22 passed`、全量 `457 passed, 5 skipped`、compileall、禁止项和 clean status。生产事务实现不再修改；只补测试证据和如实报告。

### 4J.2 唯一任务

仅修改 `tests/test_input_transaction_11.py` 中两个同一 Task 并发测试：

1. 增加 `b_started` Event。B 在线程内、紧邻调用真实 POST/save 之前设置；主线程必须先 `assert b_started.wait(timeout=...)`，再观察 A 未释放时 `b_entered` 为 false。避免把“B 尚未调度”误判为“B 被锁阻塞”。
2. A 释放且两个线程结束后，必须断言 `b_entered.is_set()`，证明 B 后续确实经过同一个生产 checkpoint，而非逻辑线程标识失效或绕开 hook。
3. 两个测试都捕获 A/B 的 HTTP 状态或异常。不得丢弃线程函数返回值；线程异常必须使主测试失败。明确断言两个响应均为 200。
4. reference 并发测试读取最终 `task.json`，按 `source_range`/顺序拼接 `script_preparation.voice_units[].text`，断言与最终 `request.script`（B 文案）完全一致，并验证 unit 范围连续覆盖全文。
5. 保留最终 reference 路径和 sha256、垃圾文件清零、线程有界结束及不同 Task 并行断言。
6. 不修改生产代码、不新增睡眠、不复制事务算法、不扩大其他测试。

### 4J.3 门禁、提交与报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_input_transaction_11.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
! rg -n "def _install_target|installed_request|old_request_bak|time\.sleep" tests/test_input_transaction_11.py
git diff --check
git status --short
```

测试提交：

```text
test(mountain): close same-task concurrency evidence
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-task-input-concurrency-14-report.md
```

报告只记录新增四类证据、实际 test commit、门禁原始摘要和 clean status。报告提交：

```text
docs(mountain): report final concurrency evidence
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4K. CCB 后端门禁与并发证明最终清场

### 4K.1 指令编号与审核结论

```text
instruction: CCB-BACKEND-PREINTEGRATION-15
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed test commit: 6d40b27 test(mountain): close same-task concurrency evidence
reviewed report: 67d78a3 docs(mountain): report final concurrency evidence
result: rejected narrowly; blocking observation is still instantaneous and full suite has a stable legacy-server failure
```

审核者复现：专项 `22 passed`；全量 `1 failed, 456 passed, 5 skipped`。失败项 `tests/test_mountain_v1_api.py::test_v1_provider_configuration_enables_start` 单独运行也稳定失败，原因是该文件测试旧 `webapp.server` 和固定 `/api/v1/providers`，不属于新 Mountain Server。生产事务代码不修改。

### 4K.2 唯一任务

1. 两个同一 Task 并发测试均保留 `b_started.wait(...)`，随后使用有界观察 `assert not b_entered.wait(timeout=<合理短值>)`；不得用紧接着的 `is_set()` 代替等待窗口。A 释放后继续断言 `b_entered.is_set()`、A/B=200、最终 Task/request/reference 一致。
2. 删除现行测试文件 `tests/test_mountain_v1_api.py`。该文件唯一导入旧 `webapp.server`，测试固定 `/providers`、Provider Profile 和旧启动逻辑；新架构已明确不兼容旧项目，新 `webapp.mountain_server` 已有负向测试保证 `/api/v1/providers` 返回 404。不要通过 monkeypatch 可用性、放宽断言或 skip 继续维持旧契约。
3. 保留 `tests/test_mountain_server.py` 对新组合根、动态 `/services`、旧 `/providers` 404、加密 SecretStore 和 Task API 的测试。
4. 扫描现行测试：`from webapp.server import app` 必须为零。对其他直接构造 `mountain_v1_router` 的历史单元测试本轮不扩大清理，但必须在报告列出数量和后续债务；不得让它们访问网络或影响全量确定性。
5. 连续执行两次完整 pytest，均须 0 failed；不得仅复跑失败测试后宣布通过。

### 4K.3 门禁、提交与报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_input_transaction_11.py tests/test_mountain_server.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
! rg -n "from webapp\.server import app|import webapp\.server" tests
! rg -n "def _install_target|installed_request|old_request_bak|time\.sleep" tests/test_input_transaction_11.py
git diff --check
git status --short
```

实现/测试提交：

```text
test(mountain): stabilize new server preintegration gate
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-backend-preintegration-15-report.md
```

报告必须列出：有界阻塞观察、删除旧测试的契约依据、新 Server 覆盖、两次全量 pytest 原始摘要、剩余直接 `mountain_v1_router` 测试数量、所有门禁和 clean status。报告提交：

```text
docs(mountain): report backend preintegration gate
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4L. CCB 新 WebUI 联调后端运行切片

### 4L.1 指令编号与已验收基线

```text
instruction: CCB-REAL-RUNTIME-CONTRACT-16
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
accepted implementation/test: d90e405 test(mountain): stabilize new server preintegration gate
accepted report: b22dad3 docs(mountain): report backend preintegration gate
```

审核者已复现专项 `42/42`、全量 `427 passed, 5 skipped`、compileall、旧 Server import 清零及 clean status。输入事务与新 Server 后端基线正式验收通过，不再追加该领域测试。

### 4L.2 唯一目标

把当前分支的 `webapp.mountain_server:app` 作为真实独立进程启动，并让 CCF 工作树的生产 contract checker 对它通过，为后续新 WebUI 集成提供可复现后端。不得合并或修改 CCF 分支，不得启动旧 `webapp.server`。

1. 使用项目指定解释器和临时 `CSBOARD_DATA_DIR` 启动真实 uvicorn；默认加密模式，禁止设置 `CSBOARD_ALLOW_PLAINTEXT_SECRETS=1`。端口使用未占用的测试端口，不写用户正式 `~/.csboard`。
2. 轮询 `/api/v1/health` 等待就绪，验证 `secret_store.encrypted=true`、storage writable、service registry 正常。启动失败必须输出可操作错误并非零退出。
3. 通过真实 HTTP 创建一条仅用于契约检查的动态 Service，取得确定的 `service_id`；不得直接写 registry JSON。Service 可以不可用，但 list/detail/secrets/probe DTO 必须结构完整且脱敏。
4. 从以下绝对路径运行 CCF 的生产 checker，不复制 checker 或 fixture：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
```

环境必须同时设置真实 `MOUNTAIN_API_BASE=http://127.0.0.1:<port>/api/v1` 和 `MOUNTAIN_CONTRACT_SERVICE_ID=<service_id>`。输出必须是 `All contracts aligned against real backend`；fixture mode 不算通过。
5. 若 checker 发现后端 DTO 不一致，只在 CCB 分支做最小后端契约修复和行为测试；不得修改前端 types、fixtures 或 checker 来迁就后端。
6. 增加一个可重复执行的后端 runtime/contract smoke 自动化入口（Python 脚本或 pytest 集成测试），负责：创建临时数据目录、选择/接收端口、启动 uvicorn、等待 health、创建契约 Service、调用外部生产 checker、在 finally 终止子进程并清理临时目录。不得残留后台进程、正式数据或 Secret。
7. 自动化还要真实请求 `/api/v1/services`、`/api/v1/assets/styles?kind=preset`、`/api/v1/settings/toolchain`、`/api/v1/settings/storage`、`/api/v1/settings/diagnostics` 和不存在 API，确认状态码及统一 `body.error`。不得访问 `/api/v1/providers` 作为正向能力。
8. 本轮不构建/托管 WebUI，不修改启动器；静态 SPA 和统一启动属于后续集成切片。

### 4L.3 门禁、提交和报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
<新增的真实 runtime/contract smoke 命令>
! rg -n "webapp\.server:app|from webapp\.server import|/api/v1/providers" <新增生产脚本及测试>
git diff --check
git status --short
```

实现提交：

```text
test(mountain): prove real backend frontend contract
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-real-runtime-contract-16-report.md
```

报告必须包含：实际 uvicorn 命令（隐藏随机路径）、端口、health 摘要、契约 Service 非敏感字段、生产 checker 原始成功输出、API smoke 表、进程和临时目录清理证据、pytest/compileall/diff/clean status。报告提交：

```text
docs(mountain): report real backend contract runtime
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4M. CCB 可移植后端启动与 Smoke 加固

### 4M.1 指令编号与已验收基线

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-17
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
accepted implementation: 97be79b test(mountain): prove real backend frontend contract
accepted report: 7d4869b docs(mountain): report real backend contract runtime
```

审核者已复现真实 uvicorn、默认加密 health、动态 Service HTTP 创建、CCF 生产 checker `All contracts aligned against real backend`、API smoke、全量 `427 passed, 5 skipped` 和 clean status。真实后端契约联调验收通过。

保留一个 follow-up 缺陷：smoke 成功路径在 `cleanup_process(proc)` 后立即 `proc = None`，随后 `if proc is not None` 永远不执行；临时目录使用 `ignore_errors=True` 后也没有检查路径消失。因此清理实际执行了，但脚本没有证明它。

### 4M.2 唯一目标

将真实后端启动和 smoke 做成仓库内可移植入口，为后续集成新 WebUI 使用；不得修改业务 API、DTO、前端或 Pipeline。

1. 新增正式前台启动脚本，例如 `scripts/run_mountain_backend.py`。必须使用当前 `sys.executable`/当前环境导入 `webapp.mountain_server:app`，支持 `--host`、`--port`、`--data-dir`、`--log-level`；默认 host 为 `127.0.0.1`、port 为 `8000`，data dir 遵循 `CSBOARD_DATA_DIR`/现有默认语义。
2. 启动脚本不得导入或启动 `webapp.server`，不得创建明文 SecretStore，不负责后台 daemon、浏览器和 WebUI 构建。依赖缺失、端口占用、app 为 None 时给出可操作错误并非零退出。
3. `smoke_real_backend_contract.py` 改用 `sys.executable`，Node 使用 `shutil.which("node")`；不得硬编码 `/mnt/d/workstation/.../.venv` 或 mise 版本目录。
4. checker 默认优先使用当前仓库 `web-v2/scripts/check-api-contract.mjs`；允许 `--checker-path` 或 `MOUNTAIN_CONTRACT_CHECKER` 覆盖。文件不存在时打印明确路径和解决方式，非零退出；不得静默切 fixture。
5. smoke 必须通过新增正式启动脚本拉起后端，而不是另写一套 uvicorn 命令，确保测试的就是用户启动入口。
6. 修复清理证明：保留原 `Popen` 引用/PID，终止后断言 `poll() is not None`；删除临时目录后断言 `not Path(tmp_dir).exists()`。清理失败必须非零，不能 `ignore_errors=True` 后无条件打印成功。
7. stdout/stderr 不得因 PIPE 无人消费导致长时间运行阻塞。可使用临时日志文件或 communicate/受控日志策略；启动失败时在错误输出中带最后有限行日志，不泄漏 Secret。
8. 增加行为测试覆盖参数解析、当前解释器、默认加密环境、启动失败、checker 缺失、子进程终止和临时目录清理。测试不得真的杀无关进程或使用固定端口。
9. 更新后端开发启动说明，只引用新脚本；明确这是前台后端入口，新 WebUI 仍将在后续集成切片启动。

### 4M.3 门禁、提交和报告

```bash
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
! rg -n "/mnt/d/|mise/installs|webapp\.server|CSBOARD_ALLOW_PLAINTEXT_SECRETS.*1" scripts/run_mountain_backend.py scripts/smoke_real_backend_contract.py
git diff --check
git status --short
```

实现提交：

```text
feat(mountain): add portable backend runtime entry
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-17-report.md
```

报告列出正式启动命令、跨平台路径策略、smoke 复用关系、失败行为测试、PID/临时目录清理断言、真实 checker、门禁和 clean status。报告提交：

```text
docs(mountain): report portable backend runtime
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4N. CCB 可移植启动入口真实行为纠偏

### 4N.1 指令编号与审核结论

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-18
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: efe746c feat(mountain): add portable backend runtime entry
reviewed report: 58c98ab docs(mountain): report portable backend runtime
result: rejected; launcher fails outside repository cwd and tests do not prove the promised behavior
```

审核者已复现专项 `18 passed`、原有仓库 cwd smoke 与真实 CCF checker 成功；但从 `/tmp` 执行绝对脚本：

```bash
cd /tmp
python /absolute/repo/scripts/run_mountain_backend.py --port <free-port> --data-dir <temp-dir>
```

进程立即退出并返回 `ModuleNotFoundError: No module named 'webapp'`。原因是启动器把字符串 `webapp.mountain_server:app` 交给 uvicorn，却没有把 repository root 加入实际 import path。smoke 通过是因为它额外注入了 `PYTHONPATH=PROJECT_ROOT`，因此没有测试独立启动器的真实行为。

此外，现有 18 个测试中多项只读取源码搜索字符串；`test_temp_dir_cleanup_proven` 只测试 Python 自带 `shutil.rmtree()`，没有执行 smoke 的清理路径。报告中的“可移植”和“清理证明”因此证据不足。

### 4N.2 唯一修复目标

只纠正正式启动入口和 smoke 的真实行为证据，不修改业务 API、DTO、前端、Pipeline 或 SecretStore 语义。

1. `run_mountain_backend.py` 必须能从任意 cwd 通过绝对脚本路径启动。由脚本自身解析 repository root，并显式建立可靠 import 条件；不得依赖调用者 cwd、外部 `PYTHONPATH` 或安装 editable package。
2. `--data-dir` 必须在导入/创建 `webapp.mountain_server` app 之前写入环境，避免 import-time 默认目录先被冻结。实际导入 app 并验证非 None；导入失败输出简洁可操作错误并非零退出，不打印完整内部路径 traceback。
3. smoke 启动正式入口时移除 `PYTHONPATH=PROJECT_ROOT` 注入，确保它不再掩盖启动器缺陷。
4. 所有路径都关闭 uvicorn 日志文件句柄后再删除临时目录，包含 health 超时、Node 缺失、checker 非零、API smoke 失败和异常路径；兼容 Windows 打开文件不能删除的语义。
5. 成功与失败路径都必须证明子进程已停止、临时目录已消失。finally 清理失败必须导致最终非零并给出目标类别，不得吞异常或无条件打印成功。
6. 保留动态端口，不得 kill 无关进程；错误输出和最后日志不得包含 Secret。

### 4N.3 强制真实行为测试

- 在 pytest 临时 cwd（不在仓库内）用绝对脚本路径、动态端口和临时 data dir 启动正式入口；轮询真实 `/api/v1/health`，断言 `status=ok`、加密 SecretStore、响应 data dir 对应本次目录，然后终止并证明 PID 消失。
- 调用环境显式移除 `PYTHONPATH` 和 `CSBOARD_ALLOW_PLAINTEXT_SECRETS`，证明成功不是测试环境泄漏。
- 用包含空格的临时 cwd/data-dir 重复至少一次启动验证。
- smoke 成功路径运行真实 checker，并由测试掌握 temp root/PID，返回后断言无残留目录和进程。
- 构造 checker 非零退出的失败路径，断言 smoke 非零，同时无残留目录、进程和未关闭日志句柄。
- 构造 health/startup 失败路径，断言错误可操作、无 traceback/Secret，并完成相同清理证明。
- 参数默认值等纯解析可做单元测试；“可启动、加密、失败清理、跨 cwd”不得再用 `read_text()`/`inspect.getsource()`/字符串存在性代替行为测试。

### 4N.4 门禁、提交和报告

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_backend_runtime_17.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
! rg -n "/mnt/d/|mise/installs|webapp\.server|CSBOARD_ALLOW_PLAINTEXT_SECRETS.*1|PYTHONPATH" scripts/run_mountain_backend.py scripts/smoke_real_backend_contract.py
git diff --check
git status --short
```

纠偏提交：

```text
fix(mountain): prove portable backend launch behavior
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-18-report.md
```

报告必须列出仓库外 cwd 与含空格 cwd 的真实启动命令摘要、health 加密结果、成功/失败清理证据、移除的伪行为测试、全部门禁和 clean status。报告提交：

```text
docs(mountain): report proven portable backend runtime
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4O. CCB 启动测试挂起与伪清理证据纠偏

### 4O.1 指令编号与审核结论

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-19
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed working tree: uncommitted changes over 58c98ab
result: rejected; delivery is uncommitted, report absent, targeted test fails and leaks a backend process
```

审核时 worktree 有三个未提交文件，HEAD 仍为上一轮 `58c98ab`，`m07-ccb-portable-runtime-18-report.md` 不存在。审核者运行 §4N 专项测试后看到 `.F.......`，随后 pytest 挂起并遗留 `run_mountain_backend.py --port 48585` 子进程；审核者已只终止本次审核创建的 pytest 与该子进程。

已确认的代码问题：

1. `test_launch_script_port_occupied` 在启动 subprocess 前已退出 socket `with`，端口被释放，测试实际启动长期运行的后端并在 `subprocess.run(timeout=10)` 后泄漏进程。
2. `test_import_failure_cleanup` 函数体是 `pass`，没有任何验收价值。
3. `test_health_timeout_cleanup` 只由测试手动 kill launcher、手动 rmtree，未运行 smoke health 失败路径。
4. 没有按 §4N 测试 smoke 的真实 checker 成功路径、checker 非零失败路径及其 PID/临时目录清理。
5. 多个异常清理仍使用 `ignore_errors=True`，与要求相反；多个 Popen 使用无人持续消费的 PIPE。
6. `test_script_error_no_secret_leak` 的布尔断言近似恒真，且没有向环境注入可识别的 canary Secret 来证明脱敏。
7. 当前修改虽然可能修复仓库外 import，但尚未形成可审计提交和报告，不能验收。

### 4O.2 唯一任务

在当前未提交修改上完成 §4N，不新增业务功能。先确保所有本轮测试创建的进程和目录均由 `try/finally` 所有权模型清理，再运行门禁。

1. 修正端口占用测试：监听 socket 必须保持打开直到 launcher 已返回；使用有界 Popen/communicate 或等价方式，finally 无条件终止仍存活的测试子进程。
2. 删除空 `pass` 测试。若需要验证 import/startup failure，提供最窄的可注入 app target/factory seam 或测试专用环境变量，默认生产路径不变；真实运行失败并断言非零、可操作错误、无 traceback/canary Secret。
3. health 失败测试必须执行 `smoke_real_backend_contract.py` 自身的失败路径，不能由测试复制 kill/rmtree 算法冒充。
4. 为 smoke 提供最窄的可观测测试接口，例如可选 `--temp-parent` 和 PID marker，或将 main 分解为返回运行上下文的可调用函数。生产默认不变；测试必须能在 smoke 返回后证明它创建的 PID 不存在且该 parent 下无工作目录。
5. 分别真实执行：checker 成功、checker 返回非零、health/startup 失败。三条路径都断言进程消失、目录消失、日志句柄可删除；不得 `ignore_errors=True`。
6. 测试 Popen 日志使用临时文件或持续消费策略，禁止无人消费 PIPE；每个 Popen 在创建后立刻进入 try/finally 所有权范围。
7. 脱敏测试在环境/失败 checker 输出中放入唯一 canary（例如 `ccb-runtime-secret-canary`），断言 smoke stdout、stderr 和启动失败尾部日志均不含 canary；不得使用近似恒真的复合条件。
8. 保留并通过仓库外 cwd、含空格 cwd、移除 PYTHONPATH、默认加密 health 的真实行为测试。
9. 完成后必须形成纠偏实现提交和独立报告提交；提交前 worktree 只能有预期报告，报告提交后 clean。

### 4O.3 固定门禁与泄漏门禁

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_backend_runtime_17.py
! pgrep -af "scripts/run_mountain_backend.py" | grep -v "pgrep -af"
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
! rg -n "pass$|ignore_errors=True|stdout=subprocess\.PIPE|stderr=subprocess\.PIPE|PYTHONPATH" tests/test_backend_runtime_17.py scripts/smoke_real_backend_contract.py
git diff --check
git status --short
```

`pgrep` 门禁执行前先确认没有用户原本启动的 Mountain 后端；不得为了过门禁杀不属于本轮测试的进程。若存在外部进程，在报告中记录并使用测试 PID 清单逐个证明，不得运行广泛 kill。

纠偏实现提交：

```text
fix(mountain): close portable runtime process leaks
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-19-report.md
```

报告必须列出三个 smoke 路径各自的 exit code、PID 消失、temp parent 清空、canary 脱敏、仓库外与空格 cwd health、专项/全量门禁、两个 commit 和 clean status。报告提交：

```text
docs(mountain): report leak-free portable runtime
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4P. CCB 非空 PID 与脱敏证据收口

### 4P.1 指令编号与审核结论

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-20
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 3155369 fix(mountain): close portable runtime process leaks
reviewed report: ae220a1 docs(mountain): report leak-free portable runtime
result: rejected; runtime works and 12 tests pass, but PID and secret-redaction assertions are vacuous
```

审核者已复现专项 `12 passed in 22.03s` 且 worktree clean。运行入口的跨 cwd 修复方向正确。本轮拒绝只针对下列证据缺陷：

1. smoke 将 `pid.marker` 写在 `csboard-smoke-*` 内，成功清理后 marker 同目录一起消失；测试断言 `len(marker) == 0 or PID 已死`，所以只要目录删除就永远通过，未证明 PID 消失。
2. checker failure 测试只证明目录剩余项为空，完全没有保存或检查真实 PID。
3. canary 仅注入环境变量 `CSBOARD_CONTRACT_CANARY`，没有进入 checker stdout/stderr 或启动日志；`CANARY not in output` 因此是空证明。
4. `CCF_CHECKER` 在后端 pytest 中硬编码 sibling worktree `/mnt/d/Workstation/...`；一个新 clone 或 CI 没有该目录时全量测试失败，违反可移植目标。
5. report 把上述空断言写成 PID 和 canary 已验证，与实际测试不符。

### 4P.2 唯一任务

只修复上述验收证据，不扩展业务功能。

1. smoke 增加可选的外部 PID 观测方式，例如 `--pid-marker /path/file`。marker 必须位于 smoke 自有临时工作目录之外，启动成功后原子写 PID；smoke 不负责删除调用者提供的 marker。默认生产调用不创建 marker。
2. 三条 smoke 测试都从外部 marker 读取一个确定的非空 PID；smoke 返回后逐个断言该 PID 不存活，再由测试删除 marker。禁止 `marker 不存在 OR PID 已死` 形式。
3. checker 成功路径、checker 非零路径、health/startup 失败路径分别断言 PID。若启动失败前未创建子进程，则必须有明确 lifecycle 结果证明 `spawned=false`；不得把 marker 缺失当作通用成功。
4. 构造失败 checker，令其在 stdout 和 stderr 输出真实敏感形态，例如 `Authorization: Bearer ccb-runtime-secret-canary-...` 与 `?api_key=...`。smoke 在回显 checker stdout/stderr 前必须使用现有 `DefaultRedactor` 或等价统一脱敏器；测试断言原 canary 不出现且 `[REDACTED]` 出现。
5. 启动失败尾部日志走同一脱敏函数。测试通过最窄、明确的测试 seam 让日志包含 Bearer/query secret，再断言原值不出现、替代值出现；不得仅把 canary 放进无人输出的环境变量。
6. 后端 pytest 不得硬编码 CCF sibling worktree。进程生命周期单测使用测试创建的 checker 文件；真实 CCF checker 只保留在独立 smoke 门禁参数中。若仓库将来包含生产 checker，可通过 repo-relative 路径使用。
7. `run_mountain_backend.py` 捕获 app import 异常时不得直接打印未经脱敏的 `str(exc)`；输出稳定错误码/建议，详细异常只经脱敏后进入受控日志。
8. 修正报告，逐条列出外部 marker 的实际 PID、原始 canary 输入形态、脱敏输出摘要及独立真实 CCF checker 门禁，不能继续复用空证明表述。

### 4P.3 固定门禁

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_backend_runtime_17.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
! rg -n "/mnt/d/Workstation|len\(marker\).*== 0|CSBOARD_CONTRACT_CANARY| or all\(" tests/test_backend_runtime_17.py
! rg -n "print\(.*str\(exc\)|print\(f.*\{exc\}" scripts/run_mountain_backend.py scripts/smoke_real_backend_contract.py
git diff --check
git status --short
```

纠偏实现提交：

```text
test(mountain): prove runtime pid cleanup and redaction
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-20-report.md
```

报告提交：

```text
docs(mountain): report proven runtime cleanup and redaction
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4Q. CCB Health 失败路径与日志句柄最终收口

### 4Q.1 指令编号与审核结论

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-21
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: a16e622 test(mountain): prove runtime pid cleanup and redaction
reviewed report: f1ab52f docs(mountain): report proven runtime cleanup and redaction
result: rejected; success/checker-failure PID proof works, required health/startup failure test is explicitly skipped
```

审核者复现结果：`11 passed, 1 skipped in 13.24s`。skip 原文为 `health timeout requires complex subprocess mocking; covered by checker failure test`，但 checker failure 发生在 health 成功之后，不能覆盖 launcher/health 失败。报告却将“仓库外 cwd”列为第三条 smoke 路径，错误声称三条均完成。

同时确认：

1. `test_startup_failure_log_redaction` 在测试里复制三条正则自行脱敏，没有执行生产 `smoke.redact_text()` 或生产失败输出。
2. `test_launcher_no_raw_exception_output` 又退化为读取源码字符串，且断言表达式不能可靠定位异常输出。
3. smoke 的 checker/health 异常路径在 finally 中未先关闭 `log_fd` 就 `rmtree(tmp_dir)`；Linux 可能通过，Windows 会因打开文件句柄无法删除。
4. 测试重新引入多个无人消费的 `stdout=subprocess.PIPE` 和 `ignore_errors=True`，与可移植、无泄漏目标冲突。

### 4Q.2 唯一任务

这是启动入口纠偏的最后一个收口切片；只修复 health/startup 失败与跨平台句柄清理，不增加业务能力。

1. 给 smoke 增加最窄 `--launcher-path` 覆盖参数，默认仍为仓库正式 `scripts/run_mountain_backend.py`。仅用于以真实子进程替换 launcher；路径不存在时明确非零退出。
2. `wait_for_health` 在轮询期间同时观察 launcher `proc.poll()`；launcher 已退出时立即判定 startup failure，不等待完整 30 秒。
3. 测试创建一个临时 launcher：向 stdout/stderr 写入 `Authorization: Bearer <canary>` 和 `?api_key=<canary>` 后非零退出。通过 smoke 的 `--launcher-path` 和外部 `--pid-marker` 真实执行。
4. 上述测试必须断言：smoke 非零、marker 是确定非空 PID、PID 已死亡、输出含 `[REDACTED]` 且不含原 canary、smoke 临时目录已删除。
5. 删除 health skip，不得用 checker failure 替代；删除复制正则的测试和源码字符串异常测试。所有脱敏断言必须观察生产 smoke 的真实 stdout/stderr。
6. `log_fd` 在 finally 中无论成功、checker 失败、launcher 失败或异常都先 flush/close，再删除目录。关闭和删除失败均使 smoke 非零；不得吞异常。
7. 所有测试 Popen 使用临时日志文件或 `communicate()` 的短命进程；长期后端不得挂无人消费 PIPE。每个临时目录用正常 `rmtree` 并断言消失，不得 `ignore_errors=True`。
8. 外部 PID marker 写入采用 temp file + `os.replace` 原子替换；父目录不存在时给出明确错误并在 finally 停止已启动进程。
9. 报告如实列出 success、checker failure、launcher/startup failure 三条 smoke，不得用仓库外 cwd 替代第三条；专项测试必须 0 skipped。

### 4Q.3 固定门禁

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q -rs tests/test_backend_runtime_17.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
! rg -n "pytest\.skip|ignore_errors=True|stdout=subprocess\.PIPE|stderr=subprocess\.PIPE|read_text\(.*LAUNCH_SCRIPT|_BEARER =|_QUERY_SECRET =" tests/test_backend_runtime_17.py
git diff --check
git status --short
```

实现提交：

```text
fix(mountain): prove startup failure cleanup
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-21-report.md
```

报告提交：

```text
docs(mountain): report startup failure cleanup
```

先本地提交，不推送。执行者不得自行宣布审核通过。

## 4R. CCB 后端测试去除 sibling worktree 依赖

### 4R.1 指令编号与审核结论

```text
instruction: CCB-PORTABLE-BACKEND-RUNTIME-22
worktree: /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend
branch: feat/mountain-assets-settings-backend
reviewed implementation: 1930c0b fix(mountain): prove startup failure cleanup
reviewed report: 94fb655 docs(mountain): report startup failure cleanup
result: runtime behavior accepted; backend test portability rejected due hardcoded CCF sibling worktree
```

审核者已复现专项 `14 passed in 19.85s`、真实 CCF checker、三条 smoke、加密 health、PID 终止与临时目录清理。startup failure 和日志句柄问题已关闭。

唯一剩余阻断：`tests/test_backend_runtime_17.py` 重新定义 `CCF_CHECKER = Path('/mnt/d/Workstation/.../mountain-assets-settings-web/...')`，成功与 startup failure 测试均依赖该文件预先存在。新 clone、CI 或单独后端 worktree 无此 sibling 路径，全量后端测试不可运行。这违反 §4P 已明确的“后端 pytest 不得硬编码 CCF sibling worktree”；真实 CCF checker 只能属于独立集成门禁。

### 4R.2 唯一任务

只删除后端测试对外部 worktree 的依赖，不再改启动器和 smoke 生命周期生产逻辑。

1. 从 `tests/test_backend_runtime_17.py` 删除 `CCF_CHECKER` 绝对路径及所有 `/mnt/d/Workstation` 引用。
2. lifecycle 成功测试在 pytest 临时目录生成最小成功 checker，输出 smoke 所需的精确成功标记；它只证明 smoke 生命周期，不冒充 CCF 契约测试。
3. checker failure 继续使用临时失败 checker；startup failure 使用任意存在的临时 checker，因为 launcher 在 checker 执行前失败。三个测试不得依赖 sibling repo。
4. 报告明确区分：pytest lifecycle checker 是测试 fixture；真实 CCF production checker 由固定独立门禁命令验证。不得把 fixture 结果写成契约对齐。
5. 模拟 CCF checker 文件被移除/重命名后专项测试仍须全部通过。可在隔离环境通过只检出本 worktree或显式 monkeypatch 外部环境验证，不得实际改动 CCF worktree。
6. 保留真实集成 smoke 门禁，路径仅出现在本节命令/报告执行记录，不得进入后端生产代码或 pytest。
7. 新建纠偏报告，不改写旧报告；专项必须 0 skipped，worktree clean。

### 4R.3 门禁、提交和报告

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q -rs tests/test_backend_runtime_17.py
! rg -n "/mnt/[a-zA-Z]/|mountain-assets-settings-web|CCF_CHECKER" tests/test_backend_runtime_17.py scripts/run_mountain_backend.py scripts/smoke_real_backend_contract.py
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --checker-path /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs
git diff --check
git status --short
```

实现提交：

```text
test(mountain): remove sibling worktree dependency
```

报告路径：

```text
/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend/docs/Mountain/m07-ccb-portable-runtime-22-report.md
```

报告提交：

```text
docs(mountain): report standalone backend runtime tests
```

先本地提交，不推送。执行者不得自行宣布审核通过。此切片通过后不再继续启动脚本工作，下一后端切片回到任务队列/新建任务契约。

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
