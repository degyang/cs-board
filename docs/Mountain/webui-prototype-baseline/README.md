# WebUI 原型设计基准

> 术语说明：`source/` 是外部原型的原样镜像，可能保留旧的 Project/项目命名或历史交互；它不是现行产品术语权威。现行产品统一使用 Task/任务、任务队列和任务工作台，规则见 [`../14-task-and-script-preparation.md`](../14-task-and-script-preparation.md)。

## 已同步的增量原型

- 语音与对齐：`VoiceAlignmentPage`、共享 `SettingsSubnav`、两张服务状态卡和加载/不可用 fixture 已从 workbuddy 同步；基准中的任务文案与链接已按当前 Task 术语校正。
- 此页仅定义展示模型与交互边界：运行时应由真实 capability/provider 数据替代 fixture，不得复制 mock、localStorage 或密钥逻辑进 `web-v2`。

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

## 设置－模型基准更新（2026-08-31）

本次再次从来源目录同步了配置与资产相关设计。当前快照包含：

- `source/src/features/settings/ModelsTab.tsx`
- `source/src/features/settings/modelsRegistry/`
- `source/src/features/settings/SettingsPage.tsx`
- `source/src/features/settings/systemStatus/`
- `source/src/pages/VoiceAlignmentPage.tsx`
- `source/src/features/voice-alignment/`
- `source/src/features/asset-management/`
- `source/src/styles/app.css` 中的 `.mp-*` 样式
- `screenshots/settings/` 中的六张配置页验收截图

当前原型将模型服务展示为只读注册表，将工具链、任务存储状态和系统诊断定义为只读运行状态；语音与对齐页明确不上传任务级文案或参考音频，也不伪造刷新/探测按钮。这些页面定义的是**视觉、信息层级和产品边界基准**，其中 fixture 仅用于展示状态。

正式实现的权威契约仍是动态 Service Registry：使用 `/api/v1/services`、资产 API 和 SecretStore；不得恢复固定 Provider Profile、`/api/v1/providers`、localStorage 业务持久化或明文 Secret。原型中的只读模型卡片不取消正式产品已经确定的 Service 创建、编辑、Secret 提交和显式 Probe 能力；实现时应保留原型的信息层级，并由真实 API 驱动这些操作。

本次快照校验值：

| 文件 | SHA-256 |
| --- | --- |
| `ModelsTab.tsx` | `dcdbc7573c9cb5abcb506d441cc069b796e07603b6be3c8da2aa556374c45ecc` |
| `SettingsPage.tsx` | `6a21443091c46ccf6f6b01d6e5f0f8415e60ea63d86b79c665461d39366fec17` |
| `VoiceAlignmentPage.tsx` | `98bd3cfe04de3920851d53ab00bacb0af015612a677c9e5e4700c8e0b0837cc7` |
| `AssetManagementPage.tsx` | `e88d66fb6a3e7b3e6d1c95592c9f37607f1e68f050a251ff02e0eaa5073ff309` |
| `app.css` | `8479a0072082b5715b9bc1de9caa6fe1a6dd71aabe00bf02dc862ac11d6645df` |

## 重点页面

- `source/src/pages/ProjectsPage.tsx`：项目入口与过滤。
- `source/src/pages/CreateProjectPage.tsx`：创建项目。
- `source/src/pages/ProjectWorkbenchPage.tsx`：标准制作工作台。
- `source/src/pages/RunDiagnosticsPage.tsx`：运行诊断。
- `source/src/features/*`：阶段时间线、Voice Unit、产物、活动面板、工作区。
- `source/src/components/*` 与 `source/src/styles/*`：共享布局、UI 和设计 token。
