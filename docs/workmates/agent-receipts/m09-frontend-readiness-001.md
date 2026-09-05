# M09 前端就绪盘点 001

状态：只读盘点；未提交。基于 `main` 工作树 `0568352` + 工作区未提交修改。

---

## 1. 设置页标签统一为「本地服务」

### 已完成修改

| 文件 | 变更 |
|---|---|
| `web-v2/src/pages/SettingsLayout.tsx:10` | Tab 标签 `语音与对齐` → `本地服务` |
| `web-v2/src/pages/VoiceAlignmentPage.tsx:56` | 页面标题 `声音对齐` → `本地服务` |
| `web-v2/tests/services-contract.test.tsx` | 3 处断言从 `语音与对齐` 更新为 `本地服务` |

### 验证结果

- `services-contract.test.tsx`：46/46 通过
- `voice-management.test.tsx`：7/7 通过
- 运行时确认：Tab 标签与页面标题均为「本地服务」

---

## 2. 模型服务列表排除 whisper

### 已完成修改

| 文件 | 变更 |
|---|---|
| `web-v2/src/pages/ModelServicesPage.tsx:18` | `LOCAL_ADAPTERS` 移除 `'whisper'` |
| `web-v2/src/pages/ModelServicesPage.tsx:19` | `LOCAL_IDS` 移除 `'local-whisper'` |

### 效果

- 模型服务页 `/settings/models` 不再显示 whisper 相关条目
- whisper 仅在工具链页 `/settings/toolchain` 呈现（已由 `ToolchainPage` 的 `component` 字段驱动）
- 测试 `removes local runtimes from the model-provider list` 覆盖此过滤逻辑

---

## 3. 音色管理页面完整性

### 未改动确认

`VoiceManagementPage.tsx` 的 diff 仅涉及新增 tabs（预置音色、音色设计、发音风格）和 provider profile 集成，不影响已确认的音色库 CRUD 功能：

- 本地音色库（上传、搜索、筛选、试听、编辑、删除）：原逻辑不变
- `VoiceDetail` 组件：编辑/保存/取消流程不变
- `VoiceFormDialog`：上传/编辑表单不变
- `ConfirmDialog`：删除确认流程不变

### 测试覆盖

```
voice-management.test.tsx — 7/7 通过
  ✓ renders four tabs and directly retains the local voice library behavior
  ✓ uses explicit provider/profile hooks and shows controlled unavailable states
  ✓ groups read-only preset profiles by vendor and renders the required detail fields
  ✓ recognizes a legacy audio_generation service in preset detail and both Provider selectors
  ✓ requests a real backend preview and only renders audio from its returned URL
  ✓ shows a controlled error and no audio when the preview API is unavailable
  ✓ creates designs and speaking styles with an explicit Provider and no secret fields
```

---

## 4. 动态信息图 UI 能力盘点

### 4.1 能力开关状态

来源：`GET /api/v1/capabilities`（运行时真实响应）

| 引擎 | 视觉来源 | supported | reason_code |
|---|---|---|---|
| `whiteboard` | `preset` | **false** | `CAPABILITY_NOT_AVAILABLE` |
| `whiteboard` | `custom-reference` | **false** | `CAPABILITY_NOT_AVAILABLE` |
| `infographic-remotion` | `preset` | **false** | `CAPABILITY_NOT_AVAILABLE` |

**当前无任何引擎/视觉来源组合处于可用状态。**

### 4.2 Provider 可用性

| Provider | available | error_code |
|---|---|---|
| `local-whisper` | ✅ true | — |
| `local-ffmpeg` | ❌ false | `NOT_PROBED` |
| `local-indextts` | ❌ false | `TTS_UNREACHABLE` |
| `whiteboard-renderer` | ❌ false | `NOT_PROBED` |
| `openai-compatible-text` | ❌ false | `SECRET_NOT_CONFIGURED` |
| `openai-compatible-image` | ❌ false | `SECRET_NOT_CONFIGURED` |
| `model-service-d4d41011` | ❌ false | `NOT_PROBED` |
| `model-service-268dbca4` | ❌ false | `NOT_PROBED` |

`providers.all_available = false`，7/8 个 Provider 不可用。

### 4.3 任务创建入口与禁用原因

**入口位置**：`web-v2/src/pages/CreateTaskPage.tsx` → `/tasks/new`

**`create-options` API 状态**：`GET /api/v1/create-options` 返回 `404 NOT_FOUND`。

该 API 尚未注册到 `mountain_server.py` 的路由中。CreateTaskPage 依赖此端点获取：
- `engines[]` — 可用引擎列表及 `available`/`reason` 字段
- `visual_sources[]` — 可用视觉来源
- `voice_sources[]` — 可用声音来源
- `limits` — 文案长度限制
- `defaults` — 默认配置

**禁用链路**：

```
create-options 404
  → options.data 为 null
    → validate() 中 errors.options = "create-options 尚未联调，当前仅可预览，暂不可提交"
    → 提交按钮 disabled={submitting || !options.data}
    → 所有引擎卡片 disabled（engineDisplayOptions fallback 全部 available: false）
    → 视觉来源卡片 disabled
    → 组合校验 combinationAvailable = false
```

**即使 create-options 上线**，仍需以下条件才能提交动态信息图任务：

1. `infographic-remotion` 引擎的 `available = true`（需 capability 服务端判定）
2. 至少一个 `visual_source` 的 `available = true`
3. 引擎+视觉组合通过服务端校验

### 4.4 动态信息图专属 UI 组件（已就位但受控禁用）

| 组件 | 位置 | 当前状态 |
|---|---|---|
| 引擎选择卡片 `infographic-remotion` | `CreateTaskPage.tsx:115` | `disabled`（因 `available: false`） |
| 「预览成片设置」按钮 | `CreateTaskPage.tsx:115` | 可点击（只读预览，不写入任务） |
| 信息图成片设置面板 | `CreateTaskPage.tsx:135` | 只读展示（语义时间轴、智能结构、文字安全） |
| 差异说明 | `CreateTaskPage.tsx:117` | 始终展示 |

### 4.5 当前禁用原因汇总

| 层级 | 原因 | 解除条件 |
|---|---|---|
| API 层 | `/api/v1/create-options` 未注册 | 在 `mountain_server.py` 中注册路由 |
| Capability 层 | 所有引擎组合 `CAPABILITY_NOT_AVAILABLE` | 依赖链中至少一个引擎的 Provider 全部可用 |
| Provider 层 | `openai-compatible-text/image` 未配置 Secret | 用户在模型服务页配置 API Key |
| Provider 层 | `whiteboard-renderer` 未探测 | 执行探测并返回可用 |
| 提交层 | `validate()` 阻断 `!options.data` | create-options 上线且返回有效数据 |

---

## 5. 后端修改同步确认

| 文件 | 变更 | 影响 |
|---|---|---|
| `csboard/adapters/provider_factory.py` | `openai_compatible` 新增 `speech_synthesis`/`audio_generation` → `OpenAITTSAdapter` | 语音合成 Provider 可通过 openai_compatible 适配器工作 |
| `csboard/application/capabilities.py` | `audio_generation` 规范化为 `speech_synthesis` | 兼容历史 capability 命名 |
| `csboard/application/service_resolver.py` | speech_synthesis 解析时合并 audio_generation 服务 | 服务发现兼容历史数据 |
| `tests/test_dynamic_provider_factory.py` | 旧拒绝断言更新为正向 TTS adapter 覆盖 | 9/9 通过 |

---

## 6. 测试汇总

| 测试文件 | 结果 |
|---|---|
| `web-v2/tests/services-contract.test.tsx` | 46/46 ✅ |
| `web-v2/tests/voice-management.test.tsx` | 7/7 ✅ |
| `tests/test_dynamic_provider_factory.py` | 9/9 ✅ |

---

## 7. 结论

- **设置页标签统一**：已完成，测试通过。
- **whisper 过滤**：已完成，模型服务页不再显示 whisper，仅工具链可见。
- **音色管理页**：未破坏已确认功能，新增 tabs 测试覆盖完整。
- **动态信息图**：UI 组件已就位（引擎选择、预览、成片设置），但整条链路受 `create-options` 未注册和 Provider 不可用双重阻断，提交入口不可用。解除阻断需：(1) 注册 create-options 路由；(2) 至少一个引擎的 Provider 链路可用。
