# Mountain 后续架构、资产与任务包规划

状态：近期执行规划。本文冻结优先级、后续方向和进入条件；尚未完成的设计项不等于已经实现或验收。

日期：2026-09-04

## 1. 共识

Mountain 应尽快停止在原有混合代码上继续叠加业务，尤其不得向旧 `webapp/server.py` 增加新工作流、领域规则、资产常量或新产品 API。迁移采用渐进式替换，不做一次性重写：先冻结契约和行为测试，再把业务能力逐块迁入共享内核，最后在所有调用和数据迁移完成后删除或归档旧实现。

同时，资产管理从“预置风格 / 自定义风格 / 音色库”扩展规划为四个一等目录：

1. 预置风格；
2. 自定义风格；
3. 音色库；
4. 前置条件。

这里必须区分“风格内人物约束”和“独立人物”。预置风格配方中规定的人物画法、默认角色和陪伴角色属于该预置风格的一部分；自定义风格上传时携带的人物组也属于该自定义风格资产包的一部分。二者不能被拆成“预置人物 / 自定义人物”两个独立资产目录。

旧 `webapp/server.py` 还包含脱离具体风格资产包的通用讲解者/主角 fallback，以及白板绘制手等运行前约束。它们统一以“前置条件”呈现在资产管理中，但后端必须保留明确类型和作用阶段。迁移前逐条判断 owner：风格专属约束留在 Style revision；讲解者进入视觉生成前置条件；绘制手进入渲染前置条件；原文明确的人物或动物仍来自 Task 内容，不能伪造为资产。

第三项共识是统一任务成果的物理归档边界。每个 Task 的输入快照、中间产物、人工候选、运行清单、验证证据和最终文件，最终都应能在当前项目根目录的 `outputs/<task_id>/` 下组成一个可识别、可搬运、可核验的任务包，而不是把正式成果长期散落在 `/tmp`、Provider 缓存、Skill 目录或多个不相关的运行目录中。

本项目前只记录需求，不立即迁移现有文件，也不在未讨论清楚 canonical storage、Run 版本和清理策略前修改 Repository 或 Artifact 契约。

## 2. 目标分层

| 层 | 职责 | 禁止事项 |
| --- | --- | --- |
| `webapp` HTTP 适配层 | FastAPI schema、route、鉴权/错误映射、composition root、SPA 托管 | 不实现文案整理、风格/人物规则、Stage 顺序、Provider 调用或文件事务 |
| `csboard/domain` | Task、Run、Voice Unit、Style、Voice、Precondition、Asset Revision、领域不变量 | 不依赖 FastAPI、React、文件系统或 Provider SDK |
| `csboard/application` | commands、queries、资产 CRUD、快照解析、失效、编排用例 | 不包含 HTTP request/response 和页面文案 |
| `csboard/stages` | 六阶段输入输出和幂等执行 | 不维护可变资产库或 UI 状态 |
| `csboard/ports` | Repository、Artifact、Asset、Provider、Renderer 等接口 | 不绑定具体本机目录或服务协议 |
| `csboard/adapters` | 文件系统、模型、TTS、渲染、遥测实现 | 不决定领域策略或工作流状态 |

新 `webapp.mountain_server:app` 最终只保留装配和生命周期；route 只调用 Application command/query。旧 `webapp/server.py` 是迁移输入和对照证据，不是可复用业务模块；新代码不得通过 import 它来“临时复用”业务。

## 3. 从旧代码迁出的能力清单

迁移前先对旧实现建立 inventory 和 characterization tests，至少覆盖：

- 旧 Job/Task 状态、恢复、队列和并发控制；
- 风格、人物、提示词和负面提示词常量；
- 文案、分镜、图片数量和时间线规则；
- Provider、TTS、Whisper、图片、FFmpeg 和渲染调用；
- 路径解析、文件事务、缓存、临时文件和清理；
- 错误映射、脱敏、日志、进度与诊断；
- 白板绘制手/笔尖素材、笔尖锚点与尺寸参数、品牌文字派生、`handPath` 轨迹和 renderer profile；
- 旧 API、页面静态托管和进程生命周期。

每项只能迁往一个明确 owner。迁移完成的定义不是“复制了函数”，而是：共享端口/领域契约存在、API/CLI 双入口调用同一实现、旧入口不再被新启动路径导入、行为与故障测试通过。

## 4. 前置条件资产领域

### 4.1 最小模型

```json
{
  "precondition_id": "precondition-explainer-001",
  "revision": 3,
  "name": "讲解者A",
  "kind": "visual-explainer|renderer-hand",
  "applies_to": ["storyboard", "illustration"],
  "status": "active",
  "engine_compatibility": ["whiteboard"],
  "preview_asset_id": "asset-precondition-preview",
  "description": "一个人在画面中讲解内容",
  "condition_text": "同一位讲解者在所有相关画面保持一致",
  "selectable": true,
  "default_selected": false
}
```

前置条件必须具备稳定 ID、revision、明确 kind、作用 Stage、启停、预览图片、展示文字、引擎兼容性和版本历史。资产自身的 `status` 表示目录中是否可用；任务界面的选中圆点表示本 Task 是否选择该条件，两者不能混为一个布尔值。Secret、绝对路径、Provider 原始响应和未经确认的身份推断不得进入资产 View。

当前旧代码事实：

- `STYLE_PRESETS` 与部分 `character_rule` 包含风格专属人物画法或角色，例如漫画墨线风的圆头极简线人与暖黄边牧，这些归 Style；
- `character_manifest`、`character_references`、`visual_references.characters` 和 `custom_reference_context` 把人物名称、描述和 1–3 张参考图绑定在一次自定义风格参考包中，这些归自定义 Style revision；
- 非特定风格分支中的“中国青年男性，短黑发，朴素深色上衣”是 `visual-explainer` 前置条件候选，应从 storyboard/image prompt fallback 中剥离；
- `HAND` / `drawing-hand*.png` 和相关笔尖参数是 `renderer-hand` 前置条件候选；
- 原文指定的人物或动物是内容语义，不归资产目录。

### 4.2 引用与快照

- 新建任务以带图片、标题、说明文字和选中圆点的卡片展示可用前置条件；具体选择保存字段在下一轮需求统一时冻结。
- Run 创建时写入已选择前置条件的不可变 snapshot；后续资产修改不追溯改变已开始的 Run。
- 各 Stage 只消费 `applies_to` 包含自己的条件 snapshot，不能回查并静默使用“最新条件”。
- 条件 revision 变化只失效依赖它的 Stage 及必要下游，不重做无关 Voice。
- 视觉讲解者与 Style revision 自带人物约束的优先级、冲突处理和 compatibility 必须由后端 Capability 明确返回。

### 4.3 规划中的 API 与 WebUI

候选 API：

```text
GET    /api/v1/assets/preconditions
POST   /api/v1/assets/preconditions
GET    /api/v1/assets/preconditions/{precondition_id}
PATCH  /api/v1/assets/preconditions/{precondition_id}
POST   /api/v1/assets/preconditions/{precondition_id}/revisions
POST   /api/v1/assets/preconditions/{precondition_id}/enable|disable
GET    /api/v1/assets/preconditions/{precondition_id}/content/{asset_id}
```

资产管理增加“前置条件”入口，不再称为“自定义人物”。每项以图片、标题、说明文字和是否启用/选中的圆点呈现，并清楚标出作用阶段。预置和自定义风格仍在自己的详情与 revision 中展示其人物画法或人物参考组。新建任务如何保存前置条件选择，等待下一轮需求统一；不可由前端先行伪造。

### 4.4 绘制手/画笔边界

旧实现中的 `HAND`、`assets/drawing-hand*.png` 和 `make_branded_hand()` 不属于人物领域。WebUI 可以把基础绘制手作为 `renderer-hand` 前置条件展示，但实现仍需拆成三个 owner：

- 基础手部/笔尖图片及笔尖锚点、目标高度等兼容信息属于 Renderer Asset / Renderer Profile；
- “笔身文字”属于 Task 的渲染设置，由基础资产派生出的 `hand-branded.png` 属于本次 Run 的 Artifact；
- 每个分镜的 `handPath` 属于渲染 Stage 的 annotation/timeline 输出，不是可复用资产。

绘制手与讲解者共用“前置条件”页面表面，但以 `kind` 和 `applies_to` 保持后端语义隔离；迁移实现不得把它误放进人物或 Style prompt。

## 5. 渐进迁移顺序

1. 最高优先关闭 WebUI 与签入原型基线的可见和交互差异，完成资产管理、新建任务六 Tab、状态保持、真实资产选择和错误/禁用态的浏览器联调；真实 API 契约优先于原型 mock，但任何差异必须显式记录。
2. 在不继续扩大旧实现的前提下，建立旧 `webapp/server.py` 能力 inventory、依赖图、characterization tests 和禁止新增检查，开始把业务与工作流能力渐进迁入共享内核。
3. 完成当前工作树的变更归属、测试证据和提交边界整理；在 WebUI 主线、后端契约和联调门禁通过后，评估把已验收提交回归 `main`，不得把未验收脏工作树直接合并到主干。
4. 冻结 Style/Voice/Precondition schema、Repository port、快照和兼容性契约。
5. 将旧业务逐项迁入 `domain/application/stages/ports/adapters`，API/CLI 改用共享用例。
6. 实现真实前置条件 Repository/API，再实现资产管理“前置条件”入口；新建任务选择契约需另行统一。
7. 用旧数据只读迁移、双入口契约、故障/并发/脱敏和真实浏览器验证关闭差异。
8. 证明新启动路径、测试和运行时均不导入旧模块后，再单独审批归档或删除旧 `webapp/server.py`。

## 6. 进入与完成门槛

规划进入实现前必须由 PM 单独建任务并确认范围、数据迁移和兼容策略。完成时至少满足：

- `webapp` 只承担适配和装配，业务与工作流规则均有唯一共享 owner；
- 新产品代码没有对旧 `webapp.server` 的运行时依赖；
- 前置条件有真实持久化、重建、版本、启停、上传安全、权限、脱敏和并发测试；
- WebUI、API、CLI/Skills读取同一前置条件资产与 Run snapshot；
- 不以 fixture、localStorage、硬编码人物、固定手部路径或旧 prompt 常量冒充生产闭环；
- 未达到删除门槛前保留旧代码为只读迁移来源，不擅自删除历史数据。

## 7. 项目内统一任务包输出契约

### 7.1 原始需求

所有 Task 的中间文件和最终文件统一记录在当前项目的 `outputs/<task_id>/` 目录下，使一个 Task 可以作为完整任务包进行查看、备份、迁移、复核和后续重做。

至少需要统一纳入：

- Task 输入及创建时的配置快照；
- Voice Unit、分镜、视觉锚点和时间轴；
- 配音、Whisper 对齐结果及 fallback 证据；
- 插图候选、正式图片和对应 manifest；
- 单段渲染视频、字幕、合成清单和最终视频；
- Gate 决策、hash、质量验证和必要日志；
- 任务包自身的索引、schema/version 和生成时间。

### 7.2 已冻结目录边界

用户已于 2026-09-04 冻结以下规则：新建任务“成片设置”增加“输出目录”；该字段表示任务包根目录。用户未指定时，默认使用当前项目根目录的 `outputs/`。Task ID 生成后，后端必须追加真实 `task_id` 作为子目录：

```text
<project-root>/outputs/<task_id>/
```

用户指定的其他目录同样必须追加 `<task_id>/`，不得把多个 Task 直接写入同一目录。一个 Task 可能有多个 Run，目录至少保持以下边界，不能让不同运行结果互相覆盖：

```text
outputs/<task_id>/
  task.json
  inputs/
    assets/
    parameters/
  runs/<run_id>/
    planning/
    audio/
    images/
    clips/
    subtitles/
    manifests/
    evidence/
    final/
  task-package.json
```

任务的输入、中间文件、任务级资产/快照、中间参数文件、证据和最终成品必须能从该任务目录完整定位；共享资产可以保留全局主记录，但 Task 使用的 revision/内容必须在任务包内形成不可变快照或受控副本，不能只留下会漂移的外部引用。物理细分文件名、去重实现和整包下载方式仍可在不破坏此顶层契约的前提下细化。

### 7.3 必须保持的不变量

- `task_id` 和 `run_id` 必须来自真实领域对象，不能由目录扫描临时推断。
- 正式 Artifact 仍须有逻辑 key、revision、hash、producer stage 和状态；统一目录不能退化为无索引文件堆。
- 任务包不得包含 Secret、Authorization、Provider 私密原始响应或不受控绝对路径。
- 临时文件必须先在受控 staging 中生成，经校验和原子提交后才能进入任务包正式位置。
- 重跑不能静默覆盖已验收 Run；保留版本或明确执行受控替换。
- API、CLI、Skills和WebUI必须通过同一 Repository/Artifact 应用契约定位文件，不能各自拼接目录。
- `/tmp` 可以用于短期计算、锁和 staging，但不能成为正式任务成果的唯一保存位置。

### 7.4 仍需实现时细化的事项

1. 自定义输出根目录的允许范围、规范化、权限检查和不可写错误契约。
2. 共享内容寻址资产采用复制、硬链接或快照 manifest 的具体实现，但任务包必须可复核且不能依赖可变 revision。
3. 多 Run、重做、失败 Run、人工候选和已批准 Artifact 的保留策略。
4. `outputs/` 默认 Git ignore，以及备份、压缩、下载和空间清理策略；正式任务包不得适用三天临时目录清理。
5. 旧数据和昨日 `tester` Task 的可验证恢复/迁移；缺失的中间文件不得伪造，迁移失败时不能影响幸存成品。
6. WebUI 中任务包浏览、单文件下载、整包导出和空间占用提示。

### 7.5 当前状态

截至 2026-09-04，顶层输出根、默认值、`<task_id>` 隔离和任务全文件归包已由用户确认，进入实现范围。当前运行数据目录的 `GET /api/v1/tasks` 返回空列表；名为 `/tmp/csboard-phase-one-manual-20260903` 的目录 birth time 为 2026-09-04 08:49，昨日 `task-02b3a76b491445bfaf594b02c75cd70e` 已不在其中。幸存的 `/home/ubuntu/Developments/final.mp4` 与昨日记录 SHA-256 一致；历史任务只能按可验证证据恢复，不能伪造已缺失的中间文件。

## 8. 近期优先级与团队执行方式

### 8.1 优先级

近期工作严格按以下顺序推进：

1. **P0：WebUI 资产管理一致性与实时联调。** 当前先以资产管理为中心对齐签入原型，重点关闭预置/自定义风格、音色库和前置条件的领域归属、页面入口、真实数据、图片/文字展示及启用选中状态差异。以真实后端 API 为数据与业务真相；源代码看似一致、mock 测试通过或陈旧服务页面都不算完成。新建任务和任务队列只保持现有可用能力，不在需求再次统一前自行定稿或扩大实现。
2. **P1：脱离旧代码。** 冻结 `webapp/server.py` 的业务增量，优先拆出会继续阻碍前后端联调的 HTTP、工作流和业务耦合；采用行为测试保护下的渐进迁移，不以一次性重写扩大风险。
3. **P2：回归主干。** 先把当前未提交变更按前端、后端/CLI、测试、文档和运行机制盘点，形成可审核提交；在专项、全量和真实联调门禁通过后选择合适窗口回归 `main`。合并前必须检查主干新变化和冲突，合并后重新运行门禁；不推送、不删除工作树，除非用户另行授权。
4. **P3：任务包、完整前置条件 CRUD 及更深迁移。** 按独立任务和已冻结契约推进，不能挤占 P0 的用户可见闭环。

### 8.2 规划完成后的团队启动门槛

满足以下条件后，使用项目级 `pos-workmates` 恢复 tmux 团队协作模式：

- P0 差异矩阵、旧代码迁移 inventory 和 Git 回归策略均已落盘；
- 前端、后端和联调工作包分别具备明确入口、出口、依赖、验证命令和回执位置；
- 当前脏工作树的文件归属明确，能够避免多个 Agent 同时修改同一文件；
- 需要用户决定的原型/API 差异已进入决策或仲裁，而不是由执行者自行猜测。

建议的最小真实编制为：

- PM：维护目标、拆分任务、验收回执和补充队列，不承担长时间编码或测试；
- `worker_frontend`：处理原型一致性、真实 API 消费和 WebUI 状态；
- `worker_backend`：处理旧代码解耦、API/Application 契约和持久化；
- `tester_frontend`、`tester_backend`：分别独立验证浏览器/构建与后端/CLI 门禁；
- `integration`：在前后端具备入口条件后立即开展跨域调试，直接推动契约问题闭环。

所有执行角色默认使用适当能力的 Codex `standard/medium`。只有同一问题有三次返工证据或存在明确高风险收益时才能提出升级；`sol high` 及以上仍须用户审批。tmux 布局必须启动真实 Agent 执行项目内 assignment，不能把空 shell 描述为团队成员。

### 8.3 用户可见的同步联调出口

团队运行期间维持一个与当前工作树绑定的 WebUI 预览地址，默认沿用 `http://127.0.0.1:5182`，并将实际 PID、工作目录、Vite root、后端代理目标、健康状态和最新验证时间写入 `docs/workmates/board.md`。用户可以在团队工作期间刷新浏览器观察进展并提交人工反馈。

服务在线不等于验收通过。每次前端交付仍须证明运行页面加载的是当前工作树源码、真实 API 可达、关键交互可复现；停止或重启服务必须记录原因和新旧进程信息。共享看板是状态事实源，tmux pane 和页面视觉只提供运行可见性。

### 8.4 首轮团队任务队列

规划门槛满足后，PM 首轮至少创建并并行投递以下工作包：

1. 前端：建立原型到 `web-v2` 的资产管理逐入口/逐控件差异矩阵，优先关闭风格、音色库和前置条件差异；前置条件以图片、文字和启用选中圆点展示，新建任务与任务队列等待再次需求统一；
2. 后端：建立 `webapp/server.py` 业务 inventory 与依赖图，特别标注应迁入前置条件、风格、音色和 Renderer Profile 的业务定义，再选择一个会阻碍当前资产联调的最小垂直切片迁移；
3. 前端验证：对实时 5182 页面执行浏览器行为、真实 API、状态保持和错误态检查；
4. 后端验证：对迁移切片执行 characterization、API/CLI 同源、旧数据只读和回归测试；
5. 联调：持续核对前端 DTO、后端 View、真实资产、任务保存和服务运行证据，问题直接分流给明确 owner。

前后端工作不是等待对方全部完成后再串行联调；只要共同契约和可运行入口存在，就同步进入 integration。PM 按回执补充下一批任务，避免有可派工作时所有执行资源同时空闲。
