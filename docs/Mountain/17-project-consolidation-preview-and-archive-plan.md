# Mountain 项目收口、预览与 Legacy 归档计划

状态：进入下一产品阶段前的执行基线。

日期：2026-09-01。

## 1. 当前结论

Mountain 新项目已经形成可独立运行的前后端，但尚未合并为单一干净分支：

- 后端基线：`feat/mountain-assets-settings-backend`，已完成新组合根、Task/Run、动态服务、资产、设置、诊断、加密 SecretStore 和可移植启动入口；
- 前端基线：`feat/mountain-assets-settings-web`，已完成 Vite SPA、模型服务、语音与对齐、资产管理、工具链、存储、诊断、任务队列和核心 Task 输入保存；
- 文档基线：`main`，持续保存 Mountain 权威设计、审核和执行台账；
- 当前历史集成工作树 `feat/mountain-m07-project-api-web-v2` 存在大量未提交中期文件、旧原型复制和实验产物，不得作为合并或发布基线。

当前开发预览使用两个干净 worktree 直接联调：

```text
WebUI  http://127.0.0.1:5175
API    http://127.0.0.1:8000
```

Vite `/api` 代理已真实访问 Mountain Server；health 返回 Task/Asset/Service 正常、SecretStore 加密、存储可写。

## 2. 目标仓库结构

收口后的生产根目录建议如下：

```text
cs-board/
├── csboard/                 # 共享领域、应用服务、Ports、Adapters
│   ├── domain/
│   ├── application/
│   ├── ports/
│   ├── adapters/
│   └── runtime/
├── webapp/                  # Mountain FastAPI；仅保留新组合根和新 Routers
│   ├── mountain_server.py
│   ├── mountain_task_api.py
│   ├── mountain_asset_api.py
│   ├── mountain_service_api.py
│   ├── mountain_settings_api.py
│   └── error_contract.py
├── web-v2/                  # 唯一生产 WebUI：Vite + React
├── cli/                     # 与 WebUI 共享 Application Core 的 CLI
├── skills/                  # 七个可执行 Skills
├── schemas/mountain/        # Task/Run/Stage/Artifact 等契约
├── assets/
│   ├── preset-styles/       # 已登记的新预置风格种子
│   └── shared/              # 新项目仍需的运行资产
├── tools/
│   └── video_renderer/      # Whisper/Remotion/FFmpeg 辅助工具链
├── scripts/                 # 只保留 Mountain 构建、启动、smoke、迁移脚本
├── tests/                   # 新项目测试；不得导入 Archives
├── docs/Mountain/           # 权威架构、原型基准、执行与审计记录
└── archives/
    └── legacy-v1/           # 只读制作参考，不参与安装、启动、测试和运行
```

`archives/` 是历史参考区，不是兼容层。生产代码、CLI、Skills、测试、构建脚本和启动器均不得 import、读取或执行其中内容。

## 3. 当前目录分类

### 3.1 直接保留为新项目

- `csboard/domain`、`application`、`ports`、`adapters`、`runtime`；
- `webapp/mountain_server.py`；
- `webapp/mountain_task_api.py`、`mountain_asset_api.py`、`mountain_service_api.py`、`mountain_settings_api.py`；
- `webapp/error_contract.py`；
- `web-v2/`；
- `cli/`；
- `skills/` 下现行七个 Mountain Skill；
- `schemas/mountain/`；
- `docs/Mountain/`；
- 与新项目测试直接对应的 `tests/`。

### 3.2 先迁移依赖，再保留为新工具链

`video_renderer/` 当前仍被以下新代码引用：

- `cli/csboard.py` 的 Whisper Alignment；
- `csboard/runtime/toolchain.py`；
- `ProviderFactory` 和 Service Registry；
- `WhisperAlignmentAdapter`。

因此它不是纯 Legacy。先移动为 `tools/video_renderer/`，统一通过 ToolchainResolver/配置解析路径，再删除所有根目录硬编码。完成后它属于新项目，不进入 Archives。

### 3.3 先提取资产种子，再归档原素材

`assets/style-references/` 包含旧流程图片和 Prompt 参考。处理顺序：

1. 将已经在新 WebUI“预置风格”登记的图片、Prompt、negative prompt、标签和配置形成版本化 seed manifest；
2. 将运行时需要的预览图复制到 `assets/preset-styles/<style-id>/`；
3. 用新 Asset Repository seed/import 行为测试证明安装后可见；
4. 原始参考目录再移动到 `archives/legacy-v1/reference-assets/`。

新运行时不得从 Archives 回读风格图片或 Prompt。

### 3.4 归档候选

完成 import graph 门禁后，以下内容进入 `archives/legacy-v1/`：

- `web/`：旧 Next/Vinext WebUI；
- `webapp/server.py`：旧单文件服务与混合工作流；
- `webapp/mountain_api.py`、`mountain_stages.py`：旧 Bridge/Stage HTTP 实现；
- `webapp/mountain_v1_api.py`：已被拆分 Routers 取代的中期组合文件；
- `csboard/application/legacy_bridge.py` 及只验证 Legacy 的测试；
- `agents/` 旧 Agent 配置；
- `examples/` 旧输出样例；
- 根 `SKILL.md` 旧人工流程说明；
- `start-webapp.py/.sh/.ps1/.bat` 和仍启动 `webapp.server:app` 的脚本；
- `scripts/restart_backend_when_idle.ps1` 等旧入口；
- 旧 Job/Project fixtures 和只服务 Legacy 的 schema/test。

归档前必须确认没有新代码、测试或文档启动说明引用这些路径。

## 4. Archives 强隔离规则

1. `archives/` 不加入 Python package，不放 `__init__.py`；
2. 不加入 Node workspace、tsconfig、Vite、pytest、coverage 或发布包扫描范围；
3. Archives 内不得保存真实 API Key、用户音频、Task 数据、`.secrets`、日志或诊断包；
4. 每个归档目录保留 `README.md`，说明来源 commit、归档日期、用途和禁止运行声明；
5. 新代码不得用 fallback 动态读取 Archives；
6. CI 增加禁止引用门禁：

```bash
! rg -n "archives/legacy-v1|archives\\\\legacy-v1" csboard webapp web-v2 cli skills scripts tests
```

7. `archives/` 只供人工参考，不承诺依赖可安装或旧应用可启动。

## 5. 分支与 PR 合并策略

当前三条主线共同 merge-base 为 `e46f180`，`main` 与功能分支各自积累了大量提交。不得在脏的历史集成工作树上直接 merge。

### PR-C0：冻结与备份历史集成工作树

- 对 `feat/mountain-m07-project-api-web-v2` 当前未提交内容做分类清单；
- 删除明确的临时复现文件前先确认无需保留；
- 对有价值但未进入 CCF/CCB 的内容建立只读 backup branch/commit；
- 不把该脏树直接合入新 integration branch。

### PR-C1：后端收口

- 等 `CCB-TASK-EXECUTION-PLAN-23` 完成并验收；
- 从最新 `main` 创建 `integration/mountain-v2`；
- 合入 `feat/mountain-assets-settings-backend`；
- 解决 docs 冲突时以 `main` 权威台账为准，保留后端审计报告；
- 运行全量 Python、compileall、真实 contract smoke。

### PR-C2：前端收口

- 以前端 `60762c5` 和后续由主审核者直接完成的修正为基线；
- 合入 `feat/mountain-assets-settings-web`；
- 解决 `web-v2` 时不得回退到历史集成树的 mock/Project 页面；
- 运行 build、全量 Vitest、warning scan、真实后端 checker；
- 后端 `mountain_server` 构建后的 SPA fallback 必须服务该 `web-v2/dist`。

### PR-C3：工具链迁移与 Legacy 归档

- `video_renderer` → `tools/video_renderer` 并更新唯一 Resolver；
- 提取 preset style seed；
- 移动归档候选；
- 删除 Legacy import、Legacy 路由和旧启动入口；
- 增加 Archives 强隔离门禁；
- 全量测试必须不依赖 Archives。

### PR-C4：统一启动与阶段验收

- 新增一个跨平台 Mountain 启动入口，负责检查/构建 `web-v2` 并启动唯一 `mountain_server`；
- 开发模式仍允许 Vite 5175 + API 8000；生产预览由 API 同源服务静态 `dist`；
- README 顶层只保留新启动方式；
- 真实浏览器完成：配置服务 → 浏览资产 → 新建 Task → 保存 inputs → 查看任务队列/工作台；
- 完成后将 `integration/mountain-v2` 通过最终 PR 合入 `main`。

## 6. 合并门禁

每个合并 PR 至少满足：

```text
Python tests: 0 failed
Frontend tests: 0 failed
Frontend build: success
act/router/unhandled warnings: 0
real backend contract checker: success
SecretStore encrypted by default
git diff --check: clean
worktree: clean
production imports Archives: 0
production imports webapp.server/LegacyJobBridge: 0
old /projects API and Project UI terminology: 0
```

归档 PR 额外使用 `python -X importtime`/静态 import scan 和启动 smoke，证明新应用无需 Archives 即可运行。

## 7. 当前可预览范围

现在可以让用户参与验收：

- 模型服务与 API Key 配置；
- 语音与对齐设置；
- 工具链、存储和系统诊断；
- 预置风格、自定义风格和音色资产；
- 任务队列；
- 新建标准白板 Task 的核心输入保存；
- Task 工作台现有状态、事件、日志和产物视图。

暂不作为完成项：

- `selective` 选择性手动阶段的真实编排；
- 完整资产选择接入新建任务；
- 从 Task 一键产出最终理想视频的全链路验收；
- 动态信息图和自定义参考扩展；
- Desktop 打包。

## 8. 立即执行顺序

1. 保持当前双 worktree 预览在线，让用户验收资产、设置、任务队列和新建任务；
2. CCB 完成 Task execution plan 契约；
3. 主审核者直接完成前端核心输入的剩余安全修正，不再向 CCF 分派；
4. 冻结 CCF/CCB 功能分支，执行 PR-C0～PR-C2；
5. 在干净 integration branch 完成工具迁移和 Archives 隔离；
6. 用统一入口完成真实标准视频验收后再进入下一产品阶段。
