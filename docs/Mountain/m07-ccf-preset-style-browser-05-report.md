# CCF-PRESET-STYLE-BROWSER-05 执行报告

**指令来源**: 统一工程台账 §3I
**执行日期**: 2026-08-31
**实现提交**: b91d051
**分支**: feat/mountain-assets-settings-web

## 执行结果

### 实现范围

**新增功能**:
- `getAssetBlobUrl` helper (`http.ts`): 构造 `/api/v1/assets/blobs/{assetId}` URL，`encodeURIComponent` 编码
- `PreviewImage` 组件: 真实主预览图 + onError 错误占位
- `PresetDetail` 组件: 预置风格只读详情（预览图、名称、description、engine、tags、prompt、negative prompt）
- 预置风格列表: 缩略图、名称、description、tags（截断 +N）
- 复制为自定义: 反馈 + 切换到 custom tab + 选中复制条目
- 复制失败: 保持当前 preset，显示结构化错误

**修改文件**:
- `src/lib/api/http.ts`: 新增 `getAssetBlobUrl` 导出
- `src/lib/api/assets.ts`: 新增 `getAssetBlobUrl` re-export
- `src/pages/AssetManagementPage.tsx`: 重写 preset tab（`PreviewImage`、`PresetDetail`），保留 custom/voice tab
- `src/styles/assets.css`: 新增 preset detail 布局、预览图、prompt、tags 样式
- `tests/assets-contract.test.tsx`: 更新 description 断言（list+detail 双处显示）
- `tests/preset-browser.test.tsx`: 17 个行为测试（新增）

### Gate 执行结果

| Gate | 命令 | 结果 |
|------|------|------|
| 1 | `npm run build` | ✓ 编译通过 |
| 2 | `npm run test:contract-checker` | ✓ 48 tests pass |
| 3 | `npm test -- --run` | ✓ 239 tests pass (+17 new) |
| 4 | `node scripts/check-api-contract.mjs` | ✓ fixture 对齐 |
| 5 | `rg SEED_PRESETS/localStorage` | ✓ 无残留 |
| 6 | `git diff --check` | ✓ 无 whitespace 错误 |
| 7 | `git status --short` | ✓ 干净 |

### 行为测试覆盖（17 tests）

| 测试 | 验证点 |
|------|--------|
| 列表渲染 | name、description、tags 来自真实 DTO |
| 缩略图 | preview_asset_id → blob URL，带 thumbnail |
| 无图占位 | preview_asset_id=null → placeholder |
| Blob URL 编码 | encodeURIComponent 处理特殊字符 |
| 详情展示 | description、engine、tags、完整 prompt/negative prompt |
| 只读约束 | 只有"复制为自定义"，无编辑/删除/启停 |
| 预览图错误 | onError → 暂无预览图占位，页面不崩溃 |
| 复制成功 | copyStyle 调用 → 反馈 → 切换 custom tab |
| 复制失败 | 错误消息 → 保持 preset tab → preset 仍可见 |
| 快速切换 | 连续选两个 preset → 详情始终对应最后选择 |
| 无 negative prompt | negative_prompt=null → 不显示反向提示词区域 |
| 无 prompt | prompt_text=null → 不显示提示词区域 |
| Tags 截断 | 列表最多 3 tag + "+N" |
| 详情全标签 | 详情显示所有 tags |
| 提交中禁用 | 复制按钮 → "复制中..." |
| Custom 回归 | custom tab 仍有编辑/启停/删除 |
| 空状态 | 无数据 → "暂无数据" |

### 视觉基准映射

原型基准路径: `/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/`

| 原型元素 | 生产实现 |
|----------|----------|
| `AssetThumb` + `gradFor` 占位 | `PreviewImage` 组件: 真实图片 + 错误占位 |
| `SEED_PRESETS` + localStorage | API: `/api/v1/assets/styles?kind=preset` |
| `image` 字段（路径/URL） | `preview_asset_id` → `getAssetBlobUrl()` |
| `intro` 视觉配方 | `prompt_text` + `negative_prompt` |
| `shortDesc` 4 字口诀 | `description` |
| `tags` 关键字 | `tags[]` |
| `badge` 角标 | 后端 DTO 未提供 `badge` 字段（已记录 API gap） |
| `refImages` 多参考图 | 后端 DTO 未提供参考图列表（见下方 API gap） |
| 编辑/删除/新建 | preset 只读，仅"复制为自定义" |

### API Gap 记录

1. **`badge` 字段**: 后端 `StyleTemplate` DTO 无 `badge` 字段（原型有"热门"/"新增"）。需要后端在 `StyleTemplate` 中增加 `badge?: string | null`。

2. **多参考图列表**: 后端 `StyleTemplate` 无 `reference_images` 或 `ref_images` 字段。纸感隐喻拼贴风和漫画墨线解释风各有 11/6 张参考图，用于语义路由。需要后端提供:
   - `reference_images?: Array<{ asset_id: string; label?: string }>` 或类似结构
   - 语义路由参数（按文案关键字选图的规则）

3. **语义路由规则**: 原型 `assetStore.ts` 中 ps-cs-9 和 ps-cs-10 的 `intro` 包含按关键字选参考图的路由规则。当前后端无此机制；前端仅展示 `prompt_text` 全文，不解析路由。

### 禁止项遵守

- [x] 未复制 `SEED_PRESETS`、localStorage 或静态图片映射
- [x] 数据来自 `/api/v1/assets/styles?kind=preset`
- [x] 预览图使用 `preview_asset_id` + `getAssetBlobUrl`
- [x] 未修改后端、自定义风格 CRUD、音色库、设置页或 checker 核心
- [x] 多参考图 gap 已记录，未前端硬编码
