# WebUI 表面对齐执行指令

状态：设置、资产与任务队列表面对齐已阶段验收；新建任务在CCF分支的后续执行文档中纠偏。本文件保留作表面回归基线，不得重新执行旧建树命令。

共同基线：`origin/integration/mountain-v2`。

设计源：仓库根目录 `prototypes/webui/`。

冻结基准：`docs/Mountain/webui-prototype-baseline/`。

本批次目标：生产 `web-v2` 的样式、布局、交互、状态和文字严格贴近原型，同时所有业务数据继续来自真实 `/api/v1`。

## 1. 共同边界

1. 原型只决定表面和交互意图，生产 API 契约仍以 Mountain 后端为准。
2. 禁止将原型中的 mock、fixture、localStorage 业务数据和 API fallback 复制到 `web-v2`。
3. 原型中的 Project/项目统一翻译为 Task/任务或任务队列。
4. 本批次不新增工作流能力，不重构 Pipeline，不修改 Stage ID。
5. CCF 发现契约缺口时写入本文件“契约缺口”段；CCB 只处理已经记录、确实阻塞表面对齐的缺口。
6. 两方分别提交开发分支，但最终以一个 `PR-P0 WebUI surface parity` 合入 `integration/mountain-v2`。

## 2. CCF 指令

### 工作区准备

```bash
cd /mnt/d/workstation/projects/cs-board-main-docs
git fetch origin
git worktree add -b feat/mountain-webui-surface-parity \
  /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity \
  origin/integration/mountain-v2
cd /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity
```

如果目标 worktree 或分支已存在，不得覆盖；先报告实际状态。

### 页面顺序

严格逐页完成，不得跳到任务主流程：

1. `/settings/models`，以及新建、详情、编辑服务；
2. `/settings/voice-alignment`；
3. `/settings/toolchain`；
4. `/settings/storage`；
5. `/settings/diagnostics`；
6. `/assets` 的预置风格；
7. `/assets` 的自定义风格；
8. `/assets` 的音色库。

### 实现要求

- 对照 `prototypes/webui/src/` 和冻结截图，复用其设计 token、侧边栏、页头、卡片、Tab、表单、状态徽章、空状态和响应式行为。
- 内容区域宽度、栅格、间距、字段顺序、按钮层级和中文文案必须逐项对齐。
- 模型服务仍保留生产所需 CRUD、Secret、Probe、启停和默认服务行为；将这些真实能力放进原型的信息层级，不得退化为只读 fixture。
- 页面必须覆盖 loading、empty、success、unavailable、error、submitting 状态。
- 不得增加新的硬编码供应商、模型或资产数据。
- 不得修改 `webapp/`、`csboard/` 和后端测试。

### 视觉证据

以 `1440x900` 视口对上述八个页面/页签分别生成生产截图，保存到：

```text
docs/Mountain/webui-parity-evidence/settings/
docs/Mountain/webui-parity-evidence/assets/
```

每页在 `docs/Mountain/webui-parity-evidence/README.md` 记录：原型文件、生产文件、真实 API、状态、仍存在的有意差异及原因。不得用“基本一致”“大致完成”替代逐项记录。

### CCF 门禁

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test
MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
git diff --check
```

另外确认：浏览器控制台 error/warning 为 0；`rg -n "VITE_USE_MOCK|mock View|fallback mock|mountain.assets" web-v2/src` 为 0。

### CCF 交付

完成后提交并推送 `feat/mountain-webui-surface-parity`，将报告写入本文“CCF 完成报告”段，包含 commit、变更页、截图路径、门禁结果、契约缺口和未完成项。

## 3. CCB 指令

### 工作区准备

```bash
cd /mnt/d/workstation/projects/cs-board-main-docs
git fetch origin
git worktree add -b feat/mountain-webui-surface-contract \
  /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-contract \
  origin/integration/mountain-v2
cd /mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-contract
```

如果目标 worktree 或分支已存在，不得覆盖；先报告实际状态。

### 范围

- 冻结现有 `/api/v1/services`、`/api/v1/assets`、`/api/v1/settings` 主契约。
- 用全新临时数据目录验证默认 6 个服务和 13 个 preset 能被真实读取。
- 验证 Service 的 `config_status`、`secret_status`、`availability` 不互相矛盾。
- 验证 API Key 保存后重启进程仍可读取 masked 状态，且明文不进入 JSON、日志、诊断和响应。
- 验证 preset 图片 URL、custom CRUD、音色上传/播放端点可供浏览器使用。
- 只修复 CCF 在本文登记的真实契约缺口；禁止为页面外观新增 DTO 字段。
- 不得修改 `web-v2/src` 和原型。

### CCB 门禁

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall -q csboard webapp
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --help
git diff --check
```

为本批次增加一个真实进程 smoke：使用独立临时数据目录启动后端，验证 health、services、preset styles、一个 preview blob、Secret 重启回读，然后关闭进程。不得只使用 monkeypatch 验证。

### CCB 交付

如没有契约缺口，不制造代码变更，只提交真实 smoke/审计报告；如有修复，提交并推送 `feat/mountain-webui-surface-contract`。将结论写入本文“CCB 完成报告”段，包含 commit、真实请求摘要、持久化证据、门禁结果和未完成项。

## 4. 契约缺口

由 CCF 追加；每项必须包含页面、用户操作、请求、实际响应、期望响应和阻塞原因。

- 暂无。

## 5. CCF 完成报告

待填写。

## 6. CCB 完成报告

待填写。

## 7. 主审核者联合验收

CCF/CCB 均完成后，由主审核者把两个开发分支合入临时验收分支，启动真实后端和生产 WebUI，逐页检查截图、交互、刷新持久化和控制台，再决定是否形成最终 PR-P0。单方测试通过不代表本批次完成。
