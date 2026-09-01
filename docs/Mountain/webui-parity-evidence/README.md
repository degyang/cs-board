# WebUI surface parity evidence

截图由 `web-v2/scripts/capture-parity-evidence.mjs` 在 2026-09-01 以真实 Mountain 后端生成；视口固定为 1440×900，WebUI 通过 Vite 的同源 `/api` 代理访问 `http://127.0.0.1:8000/api/v1`。脚本收集 `console.error`、`console.warning`、未处理异常和失败 API 请求；本次均为 0。

| 截图 | 原型文件 | 生产文件 | 真实 API | 覆盖状态 | 有意差异 |
|---|---|---|---|---|---|
| `settings/models-list.png` | `prototypes/webui/src/features/settings/ModelsTab.tsx` | `web-v2/src/pages/ModelServicesPage.tsx` | `GET /services` | success、empty、error、submitting | 卡片保留探测、启停、默认与删除，均为真实服务管理动作。 |
| `settings/models-create.png` | `ModelsTab.tsx` 的表单语言 | `web-v2/src/pages/ServiceFormPage.tsx` | `POST /services`、`PUT /services/:id/secrets` | success、validation error、submitting | 原型没有独立创建路由；生产页以同一 card/form hierarchy 承载必需的动态字段与 Secret。 |
| `settings/models-detail.png` | `ModelsTab.tsx` 的卡片/状态语言 | `web-v2/src/pages/ServiceDetailPage.tsx` | `GET /services/:id`、`GET /secrets`、probe/enable/default/delete 端点 | loading、success、not-found、error、submitting | 详情、Secret 脱敏与维护操作为生产必需扩展。 |
| `settings/voice-alignment.png` | `prototypes/webui/src/pages/VoiceAlignmentPage.tsx`、`features/voice-alignment/VoiceServiceCard.tsx` | `web-v2/src/pages/VoiceAlignmentPage.tsx` | `GET /settings/voice-alignment`、`POST /services/:id/probe` | loading、configured/unavailable、error | 探测按钮是真实 API 动作；原型仅展示跳转。 |
| `settings/toolchain.png` | `prototypes/webui/src/features/settings/ToolchainStatusTab.tsx` | `web-v2/src/pages/ToolchainPage.tsx` | `GET /settings/toolchain` | loading、success、unavailable、error | 无。 |
| `settings/storage.png` | `prototypes/webui/src/features/settings/TaskStorageStatusTab.tsx` | `web-v2/src/pages/StoragePage.tsx` | `GET /settings/storage` | loading、success、unavailable、error | 无。 |
| `settings/diagnostics.png` | `prototypes/webui/src/features/settings/SystemDiagnosticsTab.tsx` | `web-v2/src/pages/DiagnosticsPage.tsx` | `GET /settings/diagnostics` | loading、success、error | 无。 |
| `assets/preset.png` | `prototypes/webui/src/pages/AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET /assets/styles?kind=preset`、preview blob | loading、success、empty、error | “复制为自定义”保留真实写操作。 |
| `assets/custom.png` | `AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET/POST/PATCH/DELETE /assets/styles` | loading、empty、success、error、submitting | CRUD 与预览上传是生产必需扩展。 |
| `assets/voices.png` | `AssetManagementPage.tsx` | `web-v2/src/pages/AssetManagementPage.tsx` | `GET/POST/PATCH/DELETE /assets/voices`、播放端点 | loading、empty、success、error、submitting | 上传、播放和启停是生产必需扩展。 |

加载、空、错误和提交态由页面代码及现有 Vitest 覆盖；截图记录的是真实后端的正常可达状态。没有 fixture、mock 或 fallback 数据参与截图。
