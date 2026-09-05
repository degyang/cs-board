# WEB-LOCAL-001 回执

## 真实访问路径

`/settings/voice-alignment` — 在 SettingsLayout 标签栏中显示为"本地服务"。

## 可见交互

| 交互 | 说明 |
|------|------|
| 左侧列表 | 列出所有 `speech_synthesis`、`speech_alignment`、`indextts` 服务；不含 Whisper |
| 列表项点击 | 切换右侧详情面板 |
| 列表项状态徽章 | 每项显示"可用/不可用"实时状态 |
| + 新建本地服务 | 列表顶部按钮，弹出创建表单对话框 |
| 编辑 | 右详情头部按钮，切换为内联编辑模式（名称、能力、适配器、端点、模型、优先级、启用状态、API Key） |
| 保存 | 编辑模式下调用 `PATCH /services/:id` + `POST /services/:id/secrets` |
| 取消 | 编辑模式下恢复原值 |
| 删除 | 右详情头部按钮，确认后调用 `DELETE /services/:id` |
| 探测连通性 | 右详情"连通性"区域按钮，调用 `POST /services/:id/probe`，显示可用性、延迟、错误码、建议 |
| 连通性状态 | 右详情显示 availability 可用/不可用徽章、上次检查时间、延迟、错误码 |

## API 调用

| 操作 | 前端函数 | 后端端点 |
|------|---------|---------|
| 列表加载 | `fetchServices()` | `GET /api/v1/services` |
| 创建服务 | `createService(body)` | `POST /api/v1/services` |
| 更新服务 | `updateService(id, body)` | `PATCH /api/v1/services/{id}` |
| 删除服务 | `deleteService(id)` | `DELETE /api/v1/services/{id}` |
| 探测连通性 | `probeService(id)` | `POST /api/v1/services/{id}/probe` |
| 读取 Secret | `fetchServiceSecrets(id)` | `GET /api/v1/services/{id}/secrets` |
| 写入 Secret | `setServiceSecret(id, body)` | `POST /api/v1/services/{id}/secrets` |

## 测试输出

```
 Test Files  19 passed (19)
      Tests  435 passed (435)
   Duration  17.78s
```

## 构建输出

```
✓ built in 1.32s
dist/index.html                   0.40 kB │ gzip:   0.30 kB
dist/assets/index-K6TIn0zf.css   76.05 kB │ gzip:  12.01 kB
dist/assets/index-DYxapKhu.js   397.77 kB │ gzip: 117.54 kB
```

无 TypeScript 错误，无构建警告。

## 后端缺口

存在一个 API 缺口，详见 `docs/workmates/WEB-LOCAL-001-API-GAP.md`：

- **TTS 音频试听端点缺失**: 当前 `probeService()` 仅返回连通性布尔值+延迟，不生成音频。需要 `POST /api/v1/services/{service_id}/synthesize` 端点来实现真实的 TTS 试听功能。现有的 `POST /api/v1/voice-profiles/{profile_id}/preview` 端点需要 `profile_id`，不适用于任意本地 TTS 服务。

## Whisper 处理

- Whisper 不出现在本地服务页面的服务列表中（`LOCAL_CAPABILITIES` 白名单不含 `whisper`）。
- Whisper 仅在工具链页面 (`/settings/toolchain`) 显示。

## 动态信息图

未改动动态信息图实现。按约束要求，它是下一规划项。
