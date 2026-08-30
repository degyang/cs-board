# WebUI 原型设计基准

本目录是 Mountain 新 WebUI 的**唯一视觉、页面结构与交互层级基准**。

## 来源与快照

- 原始原型（只读）：`/mnt/d/Workstation/SynologyDrive/workbuddy/Workshop/mountain`
- 建立日期：2026-08-30
- 已镜像来源：`source/` 下的 `src/`、`README.md` 与 `package.json`
- 未镜像：`node_modules/`、`dist/`、缓存文件与 lockfile；它们不是设计基准。

关键来源校验值：

| 来源文件 | SHA-256 |
| --- | --- |
| README.md | 408cade674457a67ef58de5b87a3a33a544de16bb12be2ee84a66786ade233b0 |
| package.json | 379df63dd857de7b1b2a497a5821d9c158f5bb5c6ebefbd420dbe35f25533786 |
| src/styles/tokens.css | e3b48227e1e2559b0dee74e31822cbe5b129b4ddd914ab35ec2dc4cf24d755dc |
| src/styles/app.css | 6055f561512204feede235a9e90a296ade7d67b008c18041bccbba08a63569df |
| src/pages/ProjectWorkbenchPage.tsx | 7a17c7b6b24bad2ac138b747f5d669849c28319c671e8352d06dca5fa2f5a92c |
| src/pages/RunDiagnosticsPage.tsx | 33848c7616a670a21f6fcc0fe194ff1721d84c6d5c9676baa3cd0e1477bc4e99 |

## 使用规则

1. `web-v2/` 必须以这里的页面、组件、视觉 token、布局和状态样式为实现基线。
2. `source/lib/api/mock.ts`、`source/lib/api/client.ts` 和 `source/lib/api/queries.ts` 仅保留为原型资料；**不得**被新工程导入或复制其 mock/回退逻辑。
3. 新工程业务数据只能使用 cs-board 的 `/api/v1`；不得使用 `/api/mountain`、旧 `/api/config`、Fake 数据或原型的 mock 数据。
4. 原型不等于后端契约。遇到字段、命令或交互不匹配时，先记录 API gap，不得在前端伪造业务状态。
5. 每个 WebUI PR 都必须在 `docs/Mountain/` 增加“原型文件 → web-v2 文件/API”的映射，并在审查中逐项核对。

## 重点页面

- `source/src/pages/ProjectsPage.tsx`：项目入口与过滤。
- `source/src/pages/CreateProjectPage.tsx`：创建项目。
- `source/src/pages/ProjectWorkbenchPage.tsx`：标准制作工作台。
- `source/src/pages/RunDiagnosticsPage.tsx`：运行诊断。
- `source/src/features/*`：阶段时间线、Voice Unit、产物、活动面板、工作区。
- `source/src/components/*` 与 `source/src/styles/*`：共享布局、UI 和设计 token。
