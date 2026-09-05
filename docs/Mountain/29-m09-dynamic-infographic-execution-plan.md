# M09 动态信息图实施执行计划

状态：实施前收敛；**本文件不授权实现或开放提交**。
日期：2026-09-05
依据：`29-voice-provider-and-infographic-plan.md` §§5–6、`29-m09-infographic-work-breakdown.md`，以及本工作树检查。

## 0. 决策与范围

目标是把 `engine=infographic-remotion` 作为 Mountain 原生六阶段流水线中的独立引擎，而不是旧信息图服务的别名。它可以共享 Task/Run/Artifact/Trace、Voice Unit、Timeline、插图和媒体能力；它必须拥有自己的 `InfographicStoryboard` 变换和 `RemotionRendererAdapter`。在下列所有门禁均通过前，任何能力出口均须返回 `supported=false`，且不得创建该引擎任务或展示可提交入口。

本阶段不包括：动态信息图 WebUI 提交、旧 `webapp/server.py` 删除/迁移、旧任务重跑、参考风格、真实 Provider/音色交付。真实短文案渲染只是最终验证门禁，不是本次规划授权的实现动作。

## 1. 经核验的现状：计划、代码和未提交差异不能混同

### 1.1 已具备的基础

| 项目 | 核验事实 | 状态及含义 |
| --- | --- | --- |
| 引擎标识 | `csboard/domain/enums.py` 已有 `INFOGRAPHIC_REMOTION = "infographic-remotion"`。 | 可作为稳定 Task 引擎值。 |
| 原生任务包 | `FilesystemTaskRepository` 已将新任务放在 `outputs/<task_id>/runs/<run_id>/`，含 locator、原子 artifact index、Run/Stage 状态和恢复基础。 | 可复用；仍需规定信息图产物契约。 |
| 六阶段编排 | `PipelineOrchestrator` 有固定六阶段；现有 artifact store 有下游失效图。 | 可复用，不可借此推断信息图已通。 |
| Remotion 工程 | `video_renderer/render.mjs`、`src/*`、锁定的 Remotion `4.0.515` 和 `DynamicInfographic` composition 已存在。 | 有候选 renderer，不等于真实机器可渲染。 |
| 本机基础命令 | 检查到 Node `v24.20.0`、`ffmpeg`、`ffprobe`，`video_renderer/node_modules` 存在。 | 仅说明部分二进制/依赖在场；未执行 real render。 |
| 旧任务识别 | `LegacyJobBridge._is_infographic()` 以 `reference_mode == infographic` 或 `job_type == infographic` 识别，并投影为 `infographic-remotion-v8`。 | 旧信息图可读投影已存在，不能进入新执行路径。 |
| M09 形状的未提交工作 | 新增 `domain/infographic.py`、`adapters/remotion/*` 和相应测试；`capabilities.py`、`commands.py`、CLI 有未提交改动。 | 是待审实现，不是本计划可宣布的完成项。 |

### 1.2 缺失、冲突和待澄清事实

| 类别 | 事实/风险 | 计划处理 |
| --- | --- | --- |
| 真实工具链 | 当前 capability 检测仅检查 PATH 中常见 Chromium 名称及少数 Windows 路径；`render.mjs` 本身又交给 Remotion 管理浏览器。尚无真实最小 MP4、probe 记录或浏览器来源的可复现证据。 | 单列工具链/real-render 门禁；不能由 Node、`node_modules` 或 mock 测试把 capability 置真。 |
| Capability 语义 | 未提交实现把 `rendering` 当作普通服务要求，并以粗粒度 reason code 覆盖多项缺失；`REMOTION_NOT_INSTALLED` 已声明却无对应探测。图像阶段仍被外部 gate 永久阻断。 | 先定义 engine-aware、逐项可解释的 readiness contract 和优先级；只在全条件及真实 smoke 证据有效时支持。 |
| Renderer 契约 | 未提交 adapter 由 JSON 重建 storyboard，直接写 `render/infographic.mp4`，而 application manifest 又对 repository root 取相对路径。该路径/元数据与 canonical artifact path、最终 compose 输入的契约没有冻结。 | 先冻结 artifact/path/manifest schema，再实现 adapter；渲染成功必须通过媒体 probe 和 artifact commit。 |
| Storyboard 语义 | 当前草案的纯函数按每 Voice Unit 一页，空 timing 可产生 0 时长；WBS 写的是每 unit 1–2 页。Remotion 类型、cue 相对/绝对 frame 语义和图片 public-dir 解析未形成版本化契约。 | 以领域 schema、时序不变量和 fixtures 定稿；禁止 renderer 猜测/二次生成 storyboard。 |
| 入口不一致 | CLI 已有 `--engine`；原生 `/api/v1` create-options/task 路径存在；旧 `webapp/mountain_api.py` 仍有静态 capability 与白板 renderer 路径，`mountain_v1_api.py` 也含静态信息图条目。 | 只确定唯一原生读/写入口和 legacy read-only 规则；本阶段不得开放 WebUI submission。 |
| 选择 renderer | `ServiceResolver` 是 capability→ServiceDefinition 的单值解析，`ProviderFactory.create_renderer()` 历史上硬连白板。未提交 command 绕过 resolver 直接构造 Remotion adapter。 | 引入显式 engine renderer selection port/registry；不能以任意 `rendering` 服务代表 Remotion。 |
| 恢复与失败 | 通用 Run/Artifact 失效机制存在，M09 fake E2E 已覆盖部分 resume；但未证明 renderer 部分输出、超时、probe 失败、重复运行和 cleanup 具有统一状态转换。 | 通过任务包规则和专门恢复测试验收。 |
| 安全 | adapter 草案尝试清洗 stderr，但 Task/Trace/manifest/CLI/API 的统一 error envelope 和命令行/绝对路径脱敏责任尚未冻结。 | application 仅记录稳定 code + 安全摘要；adapter 负责子进程原始输出不外泄；SecretStore 的值永不进入任一包。 |

已运行的只读测试证据：M09 相关的 8 个测试模块共 `115 passed`。它们使用 fake/mocked subprocess 或 monkeypatch；不构成真机渲染、浏览器可用或外部 Provider 成功的证据。

## 2. 目标架构与边界

```
CLI / 原生 API（只读 capability；提交以后续门禁开放）
                   ↓
MountainCommands ── CapabilityService ── Toolchain/Service probes + evidence
       ↓                       ↓
Task / Run / Trace / ArtifactStore ← stable error envelope
       ↓
Pipeline stages → InfographicStoryboardPort → InfographicStoryboard (domain)
       ↓                                         ↓
RendererPort ← RemotionRendererAdapter ← versioned Remotion props
       ↓
outputs/<task>/runs/<run>/artifacts + evidence (atomic index)
```

依赖方向只能由外向内：delivery (CLI/API) → application → domain/ports；adapter → domain/ports；`video_renderer` 只消费 props。domain 不得 import Remotion、subprocess、webapp 或 Provider；application 不得 import legacy webapp；Remotion adapter 不得 import `webapp.*`。旧 bridge 是唯一可知晓 legacy job 形状的隔离点。

领域对象为版本化的 `InfographicStoryboard`（pages、nodes、cues、total duration、schema/version、非敏感 metadata）。`InfographicPage` 的时间区间、每个 node/cue 的稳定 ID 与 cue frame 坐标必须可验证；从 VoiceUnit + Timeline + storyboard visual 的转换必须是纯函数。它输出 domain JSON，不输出 JSX、命令行或绝对路径。

`InfographicStoryboardAdapter` 是唯一的 domain→Remotion props 翻译层。其输入是已提交的 storyboard、timeline、插图 artifact references 和 run-relative asset map；输出是符合锁定 `DynamicInfographic` props schema 的版本化 JSON。`RemotionRendererAdapter` 是唯一允许执行 Node 的 `RendererPort`：写 run-private props 临时文件、执行锁定脚本、验证候选 MP4、返回结构化结果，绝不读旧 job 或调用旧服务。

Capability 是同一份 engine+visual source projection 的只读事实，但分为两个不可混用的工作包：(1) **P3a bootstrap readiness** 是唯一的 bootstrap/toolchain 诊断真源：只读、fail-closed 地检查 Node、render script、锁定依赖、由 Remotion 实际使用的 browser、FFmpeg/ffprobe、服务配置与 secret presence、服务 probe 及 external-stage gate，输出“可进行受控 smoke”的诊断；即使 `bootstrap_ready=true`，也始终不能把 engine 标为 `supported=true`。(2) **P3b evidence activation** 只读取 P6 产生且经独立复核、未过期的 real-smoke evidence，并连同当前 P3a/P4 合流 readiness 决定 `supported`。创建 Task、CLI 显示、API `create-options` 均只消费 P3b activation projection；不得由 UI 或 task create 自己复算。P3a/P3b 的诊断或读取均不得创建任务、渲染、联网或泄露配置。

错误责任：adapter 将原始 stderr、命令、绝对路径和环境变量归约为分类错误；application 映射为稳定 `reason_code`、安全摘要和可恢复性；observability 可保留受访问控制的关联 ID/哈希，不能保留 secret。SecretStore 只在 provider adapter 内取值；不得进入 props、task/request snapshot、artifact、trace、日志、HTTP 或 CLI 输出。

## 3. 可独立验收的工作包

### P1 — 契约冻结：领域、props 与任务包

- 目的：冻结 `InfographicStoryboard v1`、`DynamicInfographicProps v1`、render-manifest/evidence schema 和 ID/时序不变量，解决现有 1–2 页与 1 页草案差异。
- 允许边界：`csboard/domain/infographic.py`、domain schema/validation、`video_renderer/src/types.ts`、测试 fixtures；不改 pipeline、API、CLI、旧 webapp。
- 输入/输出：输入为已版本化 VoiceUnit/Timeline/visual refs；输出为纯 domain JSON 与 run-relative props，不含本机路径/secret。空/重叠/零时长、未知 node kind、丢失 visual ref 均为确定错误。
- 测试：round-trip、空/单/多 visual、frame 坐标、schema compatibility、props fixture TypeScript typecheck。
- entry gate：取得现有 fixture 和 renderer props 的差异清单。exit gate：schema 命名、版本、绝对/相对时间语义和 max limits 经评审冻结。
- 验收证据：测试报告、黄金 JSON fixture、schema 变更说明。禁止项：在 domain 中 import adapter/Remotion；以 prompt 文本推断 asset 路径。

### P2 — Storyboard 与 renderer adapter

- 目的：实现两个 ports，并只通过 P1 契约交接。
- 允许边界：`csboard/adapters/remotion/`、相应 port types、adapter tests；不改 legacy、delivery 入口或产品 WebUI。
- 输入/输出：adapter 输入为 P1 domain/artifact refs；输出 props JSON 与 `RenderResult`。renderer 的成功前提是非空候选 MP4 **且** ffprobe 的容器/视频流、时长和尺寸符合 contract。
- 测试：mock subprocess 成功/非零/超时/缺 node/坏 JSON、temp cleanup、路径与 secret 脱敏、probe 不通过即失败、无 legacy import 的 AST test。
- entry gate：P1 exit，且 render.mjs 参数和 public asset 策略已冻结。exit gate：所有 fake adapter tests 通过；P2 消费并遵守 P3a 已定义的 renderer/toolchain prerequisite contract（Node、render script、锁定 Remotion/lockfile、由 Remotion 实际使用的 browser、FFmpeg/ffprobe、renderer/tool versions），但不自行探测或宣告其就绪；没有输出或 probe 失败绝不返回 success/manifest。P4 合流的是 P2 adapter 契约完成与 P3a bootstrap 诊断，P2 不反向成为 P3a 输入。
- 验收证据：命令 argv（脱敏）、props 黄金 fixture、result/错误矩阵、测试报告。禁止项：直接构造旧 renderer、`webapp.*` import、把 raw stderr 写入 Trace。

### P3a — Bootstrap probes：bootstrap/toolchain 基础就绪诊断

- 目的：把不依赖 P2 adapter、P6 evidence 或 activation 的基础条件做成唯一、可解释且保守的 bootstrap/toolchain probe。本包检查工具链的存在、锁定关系和安全可用性诊断，绝不执行真实 render；它不负责 activation。
- 允许边界：`application/capabilities.py`、`runtime/toolchain.py`（必要时）、service probe read model、capability tests；不创建任务、不执行 render。
- 输入/输出：输入为 P1 已冻结的 prerequisite/evidence contract；Node、render script、锁定依赖、Remotion/browser 定位、FFmpeg/ffprobe 的只读检查；SecretStore presence、各 stage service 的 cache probe、external-stage gate 与 UTC probe timestamp。输出为 `bootstrap_ready`、每项检查结果、稳定 reason code、检查时间和安全诊断（不含路径）。公开 activation projection 在本包完成后仍为 `supported=false`，不得因工具存在、`node_modules` 或 mock 证据变为 true。
- 测试：每个 Node/script/lockfile/Remotion/browser/FFmpeg/ffprobe、服务/secret、external gate 缺项和多缺项优先级；bootstrap ready 但仍 unsupported；白板不回归；CLI/API 读模型一致。断言 `bootstrap_ready=true` 与 `supported=false` 可并存，所有 probe 异常均 fail closed。
- entry gate：仅 P1 exit；该票可与 P2 并行。exit gate：仅当全部上述工具链、服务/secret/probe 与 external-gate 条件满足时 `bootstrap_ready=true`；任何 probe 异常或缺项均为 false。P3a 只报告 bootstrap 诊断，不得运行 adapter、渲染、创建任务、读取 P6 evidence 或宣告 `supported=true`。
- 验收证据：逐项 bootstrap 检查报告、reason-code matrix 和 mocked capability tests。禁止项：读取/要求 P2 或 P6 产物/evidence，执行真实渲染、创建任务、activation 或开放提交，返回 secret/本机绝对路径。

### P4 — 原生 Task/Run/Stage 路由与输出提交

- 目的：让已获准的原生 engine 在同一 Task/Run/Trace 和 artifact index 内按 engine 选 storyboard/renderer，且绝不误选白板。
- 允许边界：`application/commands.py`、engine renderer selection/ports、artifact/repository（仅为 P1 contract 必要改动）、`mountain_task_api.py`、CLI；不改旧 `mountain_api.py` 为新实现，不做 WebUI submission。
- 输入/输出：输入为 `engine=infographic-remotion`、Capability snapshot、Task snapshot 和 P1 artifacts；输出为 engine 写入 Task、render manifest、stage/run state 与 trace。失败必须是 FAILED/可重试状态，不得留 SUCCESS。
- 测试：create capability reject/accept、engine persistence、stage routing spy、artifact index path、failed-render resume、白板完全回归。
- entry gate：P1、P2、P3a exit；P4 在此合流 P3a 的唯一 bootstrap/toolchain 诊断与 P2 的 adapter 契约完成，缺任一方均不得进入受控通道。exit gate：新 engine 不可回落到 `WhiteboardRendererAdapter` 或 generic rendering service；所有输入 artifact 被索引、校验且在同一 run。即使合流成功，P4 也只允许受控 internal/test 的真实任务通道：它不得让 `create-options` 返回 available，也不得打开用户/API/WebUI 提交入口。
- 验收证据：fake 六阶段 E2E、任务包树、manifest/trace fixture。禁止项：直接写 output root 外部路径、绕过 artifact store、自动开启用户可见动态信息图提交。

### P5 — Legacy separation 与入口收敛

- 目的：将旧 `infographic-remotion-v8` 保持只读，消除/隔离静态旧 capability 与旧 renderer 入口对新引擎的歧义。
- 允许边界：legacy classification/read adapter、native route composition、CLI/API contract tests、import/route tests；旧 `webapp/server.py` 功能不得改写。
- 输入/输出：输入为 legacy job 的两个识别字段或 pipeline id；输出仅 legacy read projection。新 Task 只能为 `mountain-av-v1 + infographic-remotion`，不得以 legacy run id 运行/恢复。
- 测试：legacy read works、legacy stage invoke rejected、AST import boundary、route inventory、new engine render spy 断言不触发旧 renderer/module。
- entry gate：P4 exit。exit gate：每个公开入口只有一个 native capability 真源；legacy static route 明确弃用/隔离并有测试。
- 验收证据：路由清单、reject response fixtures、subprocess module-isolation test。禁止项：把旧结果迁移成新任务、为兼容而调用 `webapp.server`、把 legacy supported 当 native supported。

### P6 — 真实短文案 smoke 与 evidence 生成

- 目的：以受控的真实渲染证明 P2–P5 的工具链和输出，并生成供后续 activation 复核的 evidence；它不是普通 E2E 的替代，也不自行改变 capability。
- 允许边界：受控验证脚本/fixture、`outputs/` 忽略的验证任务包、evidence 读模型和测试；不提交生成媒体、不开放 WebUI。
- 输入/输出：最小无 secret 文案、固定 props/assets、锁定 Node/Remotion、可定位 browser、FFmpeg/ffprobe；输出带哈希的 MP4、probe JSON、工具版本、props/renderer hash、耗时和脱敏日志。
- 测试：fake E2E 仍覆盖每次 CI；真实 smoke 仅在显式环境/标记下执行，验证 MP4 可由 ffprobe 读取、非零时长/尺寸、manifest hash 一致。
- entry gate：P1、P2、P3a、P4、P5 全部 exit；P3a 必须报告 `bootstrap_ready=true`；真实工具链已显式安装/定位且操作者被授权执行。P6 不依赖 P3b activation 结果。
- exit gate：一次成功的完整 evidence，供 P3b 独立读取；失败保持 `supported=false`，不伪造 manifest 或 success。
- 验收证据：受控任务包中的 evidence 文件和独立复核记录。禁止项：以 mock、空文件、浏览器语音或静态占位物替代；将 API key 写入 evidence。

依赖图：

```
                 ┌─→ P2 ─┐
P1 ──────────────┤        ├─→ P4 ─→ P5 ─┐
                 └─→ P3a ┘              ├─→ P6 ─→ P3b/P7
                    (bootstrap)          │  (real evidence) (activation)
                                          └───────────────────
```

P2 与 P3a 都只依赖 P1，故可并行；P3a 自行检查完整 bootstrap/toolchain contract，但不读取或依赖 P2 的 adapter 产物。P4 同时依赖两者，并在 P4 entry 合流 P3a bootstrap/toolchain 诊断与 P2 adapter 契约完成；P5 依赖 P4；P6 同时依赖 P1/P2/P3a/P4/P5；P3b/P7 的唯一上游工作包是 P6 的独立复核成功 evidence，并在 activation 时重新读取当前 P3a 和 P4 合流结果。不存在 P3a/P3b 对 P6 的反向依赖，也不存在循环。

### P3b/P7 — Evidence activation 与发布判定

- 目的：独立复核 P6 evidence，并把 P3a bootstrap readiness 与已验证 smoke 结果合成为唯一的 `supported` activation projection；将是否开放提交保留为 PM/security 的显式决定。
- 允许边界：capability activation/read model、evidence verifier、CLI/API capability contract tests、发布决策记录；不改 renderer/domain，不实现 WebUI submission。
- 输入/输出：输入为 P3a 的 current bootstrap/toolchain readiness、P4 的 current adapter-and-routing 合流结果、P6 的完整 evidence 与独立复核结果；输出为 `supported=true` 或下列稳定 reason code。`create-options` 对 `infographic-remotion` 返回 `available=true`（等同 `supported=true`）**当且仅当**：pre-smoke readiness 为真；真实 MP4 存在且非空；ffprobe 结果有效；task-package 的 artifact index、render manifest 与各自声明的 hash 一致；evidence 未过期；且 P3b 独立复核通过。任何一项不成立一律 false/unavailable，绝不以 Node、node_modules、mock 或 stale evidence 伪造可用。
- 测试：上述每个必要条件逐项为真/假、过期/篡改/缺字段 evidence、bootstrap 或 renderer readiness 回退、CLI/API 同源、无 evidence 不可 create。
- entry gate：P6 success evidence、P3a 当前 `bootstrap_ready=true`、P4 current adapter-and-routing merged readiness=true；另需 PM/security 明确授权进行 activation review。exit gate：独立验证人逐项复核 MP4、ffprobe、artifact index、manifest、hash、freshness 与当前 readiness；仅在全部通过后可标 true，且仍不自动开放 WebUI submission。
- 验收证据：evidence verifier 报告、activation snapshot、PM/security 决策记录。禁止项：把 P6 自测视作独立复核、仅凭 Node/测试通过 activation、顺带开放提交入口。

## 4. Real-render 的硬门禁

真实渲染前必须同时满足：锁定且可执行的 Node；`video_renderer/package-lock.json` 对应依赖已安装；`render.mjs` 与 composition ID 通过 build/typecheck；可定位且由 Remotion 实际使用的 headless browser；`ffmpeg` 与 `ffprobe`；所有原生 stage services 已配置、有 secret presence 且近期 probe 成功；图像外部 stage gate 已真正解除；最小 props 和 asset fixture 已通过 P1。

real smoke 必须产生一个真实、非空的 MP4，随后用 ffprobe 验证可解析的视频流、codec/尺寸和非零时长。evidence 记录工具版本、renderer/lockfile/props 哈希、匿名任务/run ID、probe 摘要和时间；不记录完整命令、绝对路径、环境或 secret。仅 `render.mjs` 退出 0 不足以成功；不存在输出、0 字节、probe 失败、时长/尺寸不符、manifest 写入失败均为失败，Run/Stage 标记 FAILED 或可恢复的失败，Capability 继续 false。P6 成功也只生成 evidence；只有 P3b 的独立复核可 activation。

`create-options` 的 `available=true` 必须逐项等价于 P3b 的 `supported=true`，且必须同时满足：真实非空 MP4；有效 ffprobe；task-package artifact index、render manifest 与哈希一致；当前 pre-smoke readiness；未过期 evidence；独立复核。所有比较用 UTC 时钟；freshness 固定为 `verified_at` 起 **24 小时**，超过或无法解析即过期。

P3a 的 bootstrap reason-code matrix 必须采用 fail-closed 的稳定首个缺项优先级：`NODE_NOT_FOUND` → `RENDER_SCRIPT_MISSING` → `LOCKFILE_INVALID` → `REMOTION_NOT_INSTALLED` → `BROWSER_UNAVAILABLE` → `FFMPEG_NOT_FOUND` → `FFPROBE_NOT_FOUND` → `SERVICE_SECRET_MISSING` → `SERVICE_PROBE_FAILED` → `EXTERNAL_STAGE_BLOCKED`；多缺项只公开优先级最高的一项，同时在安全的内部诊断中保留逐项结果。P3b activation/create-options 则固定为：`READINESS_FAILED`（P3a bootstrap 或 P4 adapter-and-routing 合流不成立）、`EVIDENCE_MISSING`、`EVIDENCE_EXPIRED`、`MP4_MISSING`、`FFPROBE_INVALID`、`MANIFEST_INVALID`、`HASH_MISMATCH`、`TOOLCHAIN_CHANGED`、`SERVICE_PROBE_CHANGED`。实现不得以 P3a 附加诊断替换 P3b activation/create-options code。失效、缺失或 P6 失败时必须返回 `available=false/supported=false`，并禁止用户创建；只有受控 internal/test 通道可在 P4/P6 明示门禁下运行。

evidence 的 binding 至少包括 renderer hash、lockfile hash、props hash、Node/Remotion/browser/FFmpeg/ffprobe 工具版本、服务 probe snapshot、MP4 artifact、artifact index 和 render manifest。renderer、lockfile、props、任一工具版本、任一 service probe、artifact、index 或 manifest 任一变化，均立即使 evidence 无效；工具版本变化返回 `TOOLCHAIN_CHANGED`，服务 probe 变化返回 `SERVICE_PROBE_CHANGED`，artifact/index/manifest 结构不合法返回 `MANIFEST_INVALID`，声明哈希不一致返回 `HASH_MISMATCH`。无证据返回 `EVIDENCE_MISSING`，无法取得非空 MP4 返回 `MP4_MISSING`，probe 缺失/不可解析/不符合契约返回 `FFPROBE_INVALID`。

分层原则：单元测试和 fake E2E mock ports/subprocess，验证 schema、路由、恢复和脱敏；real E2E 只验证一个受控最小产物和工具链，不调用生产 WebUI。两层都必须通过，任何一层都不能替代另一层。

## 5. Legacy separation、兼容决策与反回落测试

旧信息图的识别键是 legacy job 的 `reference_mode/job_type=infographic`，以及 bridge 所写 `infographic-remotion-v8` pipeline id；新路径的唯一身份是 Task 的 `pipeline_id=mountain-av-v1` 加 `engine=infographic-remotion`。名称相似不是兼容依据。

默认迁移决策是“不迁移、只读”：旧记录继续由 `LegacyJobBridge` 投影、展示和下载；没有 native stage 执行、resume 或重新渲染。若未来要求迁移，须单独决定是否创建全新 native Task、如何获得输入/许可证/哈希证据、以及如何标记不可验证的旧 artifact；不得隐式转换。

P5 的回归测试必须在 new task 中 monkeypatch/spy `WhiteboardRendererAdapter` 与 legacy module import，使任何被调用/import 即失败；同时断言实际构造的 renderer 为 Remotion adapter，Task pipeline id 不是 v8，legacy run 的 stage invoke 以稳定错误拒绝。静态 AST 扫描覆盖 new adapter/application 目录，路由测试确认旧静态 API 不被 native API 的 capability 真源采用。

## 6. 输出任务包规则

每个新任务的根为 `outputs/<task_id>/`；每次 Run 固定为 `runs/<run_id>/`。仅 `artifacts/` 内、经 `FilesystemArtifactStore` 原子提交并在 `artifacts/index.json` 注册的文件可作为后续 stage 输入或成功证据。建议固定键/相对位置：

| artifact key | 位置 | 必需元数据 |
| --- | --- | --- |
| `planning.storyboard` | `artifacts/planning/storyboard.json` | schema version、engine、输入 artifact hashes、时序/ID 校验结果 |
| `illustrations.manifest` | `artifacts/planning/illustration-manifest.json` | run-relative image refs、hash、producer |
| `render.props` | `artifacts/render/remotion-props.json`（或受控 evidence 副本） | props schema、renderer/version hash；不得含绝对路径/secret |
| `render.manifest` | `artifacts/render/render-manifest.json` | engine、输出 artifact key/hash、duration/frames/probe 摘要、producer、status |
| `render.video` | `artifacts/render/infographic.mp4` | SHA-256、size、probe digest；临时文件使用 `.partial` |
| `render.evidence` | `evidence/remotion-smoke.json` | 仅 real smoke：版本/hash/时刻/脱敏结果 |
| `output.final-manifest` | 既有最终成片契约位置 | 指向已验证的 final artifact，不重复复制 renderer 输出 |

Task metadata 保存 engine、pipeline、非敏感 request/input snapshots；Run 保存 entrypoint、trace、stage attempts、状态和安全错误 code。成功必须为 artifact index 提交和 Run stage success 都完成；任一前置失败则没有 success manifest。可恢复性以 artifact hash + producer stage + stale dependency graph 决定：上游变更使 storyboard/render/final stale；同一 run 的 retry 可复用校验仍有效的上游 artifact，但不得复用失败/未 probe 的 MP4。保留已成功或诊断所需的 artifact/evidence 至产品保留期；临时 props、partial 文件和安全允许的失败中间物可在 finally/清理任务删除，清理必须不删已索引成功物。绝不把绝对输出路径、secret、原始 stderr 或浏览器 profile 写入包。

## 7. Next queue（规划完成不等于授权实现）

| 顺序/工单 | 严格依赖 | 独立验证角色与出口 |
| --- | --- | --- |
| M09-INFRA-CONTRACT-001：P1 schema/fixture | PLAN-002 独立 PASS | 实现者 worker_backend；Domain reviewer 独立验证 schema+golden fixture+typecheck，PASS 才可派下一票。 |
| M09-INFRA-ADAPTER-002：P2 ports/render validation | CONTRACT-001 独立 PASS | 实现者 worker_backend；Adapter/test reviewer 独立验证 mock subprocess、probe failure、脱敏、legacy-import tests。 |
| M09-INFRA-BOOTSTRAP-003A：P3a bootstrap readiness | CONTRACT-001 独立 PASS（与 P2 并行） | 实现者 worker_backend；Runtime reviewer 独立验证 reason matrix、fail-closed、多缺项、bootstrap-ready 仍 unsupported、白板回归。 |
| M09-INFRA-ROUTING-004：P4 task/run/artifact wiring | ADAPTER-002、BOOTSTRAP-003A 均独立 PASS | 实现者 worker_backend；Application reviewer 独立验证 fake six-stage + retry、index、engine routing spy，以及仅 internal/test 通道、无用户提交。 |
| M09-INFRA-LEGACY-005：P5 boundary/route inventory | ROUTING-004 独立 PASS | 实现者 worker_backend；Migration reviewer 独立验证 legacy read/reject、module isolation、new path no-fallback。 |
| M09-INFRA-REAL-006：P6 controlled smoke/evidence | P1/P2/P3a/P4/P5 均独立 PASS，且 P3a 当前 `bootstrap_ready=true`；另需显式 real-render 授权 | 实现者 release/runtime worker；独立 runtime verifier 复核真实 MP4、ffprobe、hash/manifest/freshness；失败即不开放 capability。 |
| M09-INFRA-ACTIVATE-003B：P3b/P7 evidence activation/发布决策票 | REAL-006 成功且独立 evidence PASS；P3a 当前 readiness；另需 PM/security activation-review 授权 | 实现者 worker_backend；Independent runtime reviewer + PM/security 复核 evidence/current readiness，才可标记 supported；单独决定是否授权后续 WebUI/提交工作。 |

可自动派发的顺序为：PLAN-003 独立 PASS 后首票 CONTRACT-001（P1）；P1 独立 PASS 后同时派 ADAPTER-002（P2）与 BOOTSTRAP-003A（P3a）；两者 PASS 后依序 ROUTING-004（P4）→ LEGACY-005（P5）→ REAL-006（P6）→ ACTIVATE-003B（P3b/P7）→ create-options/task-submission 联调。最后一项仍需单独产品授权，且本计划绝不授权 WebUI submission。每张票均须由列出的实现者交付、独立验证者 PASS 后才可推进，不能以“已有未提交代码/测试通过”替代验收。
