# M07 Provider 模型服务映射

## 原型组件 → web-v2 组件 → /api/v1 DTO

| 原型组件 | web-v2 组件 | /api/v1 DTO |
|---------|------------|-------------|
| `ModelsTab` 列表卡片 | `ProvidersPage` `.mp-card` | `GET /providers` → `ProviderEntry` |
| 类别 badge | `.mp-category-badge` | `profile.provider_type` 派生 |
| 模型 chip | `.mp-model-chip` | `profile.config.model` |
| Base URL 显示 | `.mp-url` | `profile.config.base_url` / `profile.config.url` |
| 密钥状态 | `.badge.st-succeeded/st-failed` | `config_status.configured` |
| 掩码密钥 | `.mp-secret-mask` | `secrets.{key}.masked_value` |
| 可用性 badge | `.badge.st-succeeded/st-failed` | `availability.available` |
| error_code | `code` 标签 | `availability.error_code` |
| suggestion | 💡 提示 | `availability.suggestion` |
| 编辑配置 | `ProviderDetailPage` inline form | `PUT /providers/{name}/config` |
| 设置密钥 | password input + 设置按钮 | `POST /providers/{name}/secrets` |
| 删除密钥 | 删除按钮 + confirm | `DELETE /providers/{name}/secrets/{key}` |

## 类别映射（真实 provider_type）

| provider_type | 类别标签 | 图标 | CSS class |
|--------------|---------|------|-----------|
| `text_model` | 文本 | 📝 | `cat-text` |
| `image_model` | 图片 | 🖼️ | `cat-image` |
| `tts` | 语音 | 🔊 | `cat-voice` |
| `alignment` | 工具链 | 🎯 | `cat-tool` |
| `renderer` | 工具链 | 🎨 | `cat-tool` |
| `media` | 工具链 | 🎬 | `cat-tool` |

## 原型 CRUD → 当前固定 Profile → 后续 Provider Registry API

| 原型功能 | 当前后端 | API Gap | 后续契约 |
|---------|---------|---------|---------|
| 添加模型服务 | ❌ 不支持 | 无 API | `POST /providers` (Provider Registry) |
| 删除模型服务 | ❌ 不支持 | 无 API | `DELETE /providers/{name}` (Provider Registry) |
| 编辑配置 | ✅ `PUT /providers/{name}/config` | — | — |
| 设置密钥 | ✅ `POST /providers/{name}/secrets` | — | — |
| 删除密钥 | ✅ `DELETE /providers/{name}/secrets/{key}` | — | — |

页面底部显示说明：
> 当前版本由后端管理 Provider Profile；新增/删除服务商将在 Provider Registry API 发布后开放。

## Secret 安全边界

| 规则 | 实现 |
|------|------|
| Secret 输入使用 `type="password"` | ✅ `ProviderDetailPage.tsx` |
| 提交后立即清空输入 | ✅ `setSecretInputs((s) => ({ ...s, [key]: '' }))` |
| 不回显明文 | ✅ 仅显示后端返回的 `masked_value` |
| 不使用 localStorage/sessionStorage 存储 Secret | ✅ rg 扫描确认 |
| 不提供"眼睛显示完整 Key"功能 | ✅ 无此 UI |
| 不在 React state 之外持久化 Secret | ✅ 仅内存中的 `secretInputs` state |

## 真实后端 Provider 列表

当前后端固定 6 个 Provider Profile：

| 名称 | provider_type | 必需密钥 | 默认配置 |
|------|--------------|---------|---------|
| Text Model | `text_model` | `api_key` | base_url: api.openai.com, model: gpt-4o |
| Image Model | `image_model` | `api_key` | base_url: api.openai.com, model: gpt-image-1 |
| TTS (IndexTTS) | `tts` | 无 | url: 127.0.0.1:7860, mode: gradio |
| Alignment (Whisper) | `alignment` | 无 | mode: node |
| Renderer (Whiteboard) | `renderer` | 无 | {} |
| Media (FFmpeg) | `media` | 无 | {} |

## 视觉对比

### 原型截图
- 列表卡片：类别 badge + 模型 chip + Base URL + 密钥状态
- 详情页：inline form + 密钥管理

### 实际页面
- 使用相同视觉结构，但数据来自真实 `/api/v1/providers`
- 无 mock/localStorage/种子 Key
- 无"眼睛显示完整 Key"按钮
- 无 add/delete 伪 CRUD 按钮
