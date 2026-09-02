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

### 任务队列真实证据（2026-09-02）

截图前通过公开 API 请求 `GET /api/v1/tasks?limit=100` 读取当前后端：**0 个任务**，状态计数为 `running=0`、`failed=0`、`succeeded=0`、`pending=0`、`cancelled=0`。因此 `queue-mixed.png` 如实显示全量空状态；`queue-filtered.png` 对应真实 `GET /api/v1/tasks?limit=20&status=failed` 的筛选空状态；`queue-empty.png` 对应真实 `GET /api/v1/tasks?limit=20&status=pending` 的筛选空状态。脚本在筛选图前断言 API 响应成功、status query 正确且 Tab active，未写入任何 Task 数据。

本轮新增的 `settings/models-secret.png` 固定使用 `openai-compatible-text`，将“Secret 管理”滚动至视口中央；脚本断言 password 输入为空并拒绝 key-like 明文。

加载、空、错误和提交态由页面代码及现有 Vitest 覆盖；截图记录的是真实后端的正常可达状态。没有 fixture、mock 或 fallback 数据参与截图。

### 新建任务纠偏证据（2026-09-02）

专项测试已按真实六 Tab 用户路径重写并通过；隔离临时数据目录中的真实后端 contract checker 返回 `All contracts aligned against real backend ✓`。证据脚本已扩展六个 create 截图路径且不调用创建 Task API。当前环境缺少 Playwright Chromium，安装下载失败，因此六张新截图及 SHA-256 尚未生成；现存截图总数为 15，未冒充 21 张完成。

### 浏览器证据最终尝试（2026-09-02）

本轮已改用文档指定 Chromium `/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome`。真实后端 contract checker 通过；5175 `--strictPort` 因外部端口占用无法启动，备用端口流程未完成服务就绪。未创建 Task，未生成六张新图或 SHA-256；PNG 总数仍为 15，等待 PM 复审。
