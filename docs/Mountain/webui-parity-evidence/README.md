# WebUI surface parity evidence

截图由 `web-v2/scripts/capture-parity-evidence.mjs` 在 2026-09-02 以真实 Mountain 后端重新生成；视口固定为 1440×900，WebUI 通过 Vite 的同源 `/api` 代理访问 `http://127.0.0.1:8000/api/v1`。前端基线：`3757cb6`；后端共同基线：`origin/integration/mountain-v2` (`036b7ff`)。脚本会清空侧栏 localStorage、断言默认完整侧栏与页面结构，并将所有 pathname 以 `/api/` 开头的 4xx/5xx 响应视为失败；本次 console error/warning、未处理异常和失败 API 请求均为 0。

| 截图 | 原型文件 | 生产文件 | 真实 API | 覆盖状态 | 有意差异 |
|---|---|---|---|---|---|
| `settings/models-list.png` | `prototypes/webui/src/features/settings/ModelsTab.tsx` | `web-v2/src/pages/ModelServicesPage.tsx` | `GET /services` | success、empty、error、submitting | 卡片保留探测、启停、默认与删除，均为真实服务管理动作。 |
| `settings/models-create.png` | `ModelsTab.tsx` 的表单语言 | `web-v2/src/pages/ServiceFormPage.tsx` | `POST /services`、`PUT /services/:id/secrets` | success、validation error、submitting | 原型没有独立创建路由；生产页以同一 card/form hierarchy 承载必需的动态字段与 Secret。 |
| `settings/models-detail.png` | `ModelsTab.tsx` 的卡片/状态语言 | `web-v2/src/pages/ServiceDetailPage.tsx` | `GET /services/:id`、`GET /secrets`、probe/enable/default/delete 端点 | loading、success、not-found、error、submitting | 详情、Secret 脱敏与维护操作为生产必需扩展。 |
| `settings/models-secret.png` | `ModelsTab.tsx` 的 Secret 区域 | `web-v2/src/pages/ServiceDetailPage.tsx` | `GET /secrets` | masked Secret、空 password 输入 | 滚动到 Secret 管理区域截图；只截取 masked 状态，不写入或截取真实 API Key。 |
| `settings/models-edit.png` | `ModelsTab.tsx` 的表单语言 | `web-v2/src/pages/ServiceFormPage.tsx` | `GET/PATCH /services/:id` | loading、success、error、submitting | 真实编辑路由回填现有服务配置。 |
| `settings/voice-alignment.png` | `prototypes/webui/src/pages/VoiceAlignmentPage.tsx`、`features/voice-alignment/VoiceServiceCard.tsx` | `web-v2/src/pages/VoiceAlignmentPage.tsx` | `GET /settings/voice-alignment`、`POST /services/:id/probe` | loading、configured/unavailable、error | 探测按钮是真实 API 动作；原型仅展示跳转。 |
| `settings/toolchain.png` | `prototypes/webui/src/features/settings/systemStatus/SystemStatusTabs.tsx` | `web-v2/src/pages/ToolchainPage.tsx` | `GET /settings/toolchain` | loading、success、unavailable、error | 无。 |
| `settings/storage.png` | `prototypes/webui/src/features/settings/systemStatus/SystemStatusTabs.tsx` | `web-v2/src/pages/StoragePage.tsx` | `GET /settings/storage` | loading、success、unavailable、error | 无。 |
| `settings/diagnostics.png` | `prototypes/webui/src/features/settings/systemStatus/SystemStatusTabs.tsx` | `web-v2/src/pages/DiagnosticsPage.tsx` | `GET /settings/diagnostics` | loading、success、error | 无。 |
| `assets/preset.png` | `prototypes/webui/src/pages/AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET /assets/styles?kind=preset`、preview blob | loading、success、empty、error | “复制为自定义”保留真实写操作。 |
| `assets/custom.png` | `AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET/POST/PATCH/DELETE /assets/styles` | loading、empty、success、error、submitting | CRUD 与预览上传是生产必需扩展。 |
| `assets/voices.png` | `AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET/POST/PATCH/DELETE /assets/voices`、播放端点 | loading、empty、success、error、submitting | 上传、播放和启停是生产必需扩展。 |
| `tasks/queue-mixed.png` | `prototypes/webui/src/pages/ProjectsPage.tsx` | `web-v2/src/pages/TasksPage.tsx` | `GET /api/v1/tasks` | loading、success、empty、error、status filter、cursor pagination | 使用 Tabs 共享组件和真实 /api/v1/tasks 端点。 |
| `tasks/queue-filtered.png` | `ProjectsPage.tsx` 的状态过滤 | `web-v2/src/pages/TasksPage.tsx` | `GET /api/v1/tasks?status=failed` | filtered success、filtered empty | 点击"失败"Tab 截图；如无失败任务则显示 filtered-empty。 |
| `tasks/queue-empty.png` | `ProjectsPage.tsx` 的空状态 | `web-v2/src/pages/TasksPage.tsx` | `GET /api/v1/tasks?status=pending` | filtered-empty、清除筛选 | 点击"待执行"Tab 截图；真实后端通常无 pending 任务。 |

加载、空、错误和提交态由页面代码及现有 Vitest 覆盖；截图记录的是真实后端的正常可达状态。没有 fixture、mock 或 fallback 数据参与截图。
