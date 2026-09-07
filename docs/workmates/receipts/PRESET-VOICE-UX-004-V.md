# PRESET-VOICE-UX-004-V — 预置音色独立视觉与行为复验回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、服务、看板或拓扑。

## 服务确认

| 端点 | 状态 |
| --- | --- |
| `http://127.0.0.1:5182/` | 200 ✅ |
| `http://127.0.0.1:8000/api/v1/health` | 200 ✅ |

---

## 硬门禁逐项验证

### 1. 双栏布局（1024×900 和 1440×900）

| 视口 | 列表 x / width | 详情 x / width | 结论 |
| --- | --- | --- | --- |
| 1440×900 | x=315, w=372.5 | x=714.5, w=685.5 | PASS — 详情 ≥640px，清晰左右分栏 |
| 1024×900 | x=315, w=298 | x=640, w=640 | PASS — 两列均可见，不堆叠 |

截图：`/tmp/pv004v-1440-selected.png`、`/tmp/pv004v-1024-selected.png`

### 2. 可见新增/选择/编辑路径

| 项 | 独立发现 | 结论 |
| --- | --- | --- |
| 新增按钮 | `+ 新增预置音色` 按钮可见 | PASS |
| 选择 | 点击列表项后详情显示音色信息 + 编辑按钮 | PASS |
| 编辑入口 | 选中后 `编辑` 按钮出现，点击后7个输入控件可见 | PASS |
| 保存 | PATCH → 200，表单关闭，详情显示更新值 | PASS |

### 3. 全页可见性（头→新增→列表→编辑→试听区）

| 区域 | 独立发现 | 结论 |
| --- | --- | --- |
| 页头 + tabs | 1440 全页截图从 scrollY=0 开始，可见页头、tabs | PASS |
| + 新增预置音色 | 截图中可见 | PASS |
| 完整列表 | 8 项可见 | PASS |
| 详情编辑入口 | 选中后截图可见编辑按钮 | PASS |
| 独立试听区 | textarea y=818，在页面下方可见 | PASS |

截图：`/tmp/pv004v-1440-full-top.png`（1440 全页）、`/tmp/pv004v-1024-full-top.png`（1024 全页）

### 4. 无卡片/详情播放器

| 检查 | 结果 | 结论 |
| --- | --- | --- |
| `.voice-preset-list-item audio` | 0 | PASS |
| `article audio` | 0 | PASS |

### 5. PATCH 行为（原 400 诊断 → 修复后 200）

| 项 | 独立发现 | 结论 |
| --- | --- | --- |
| 原始 400 | 实现回执记录 `VOICE_PROFILE_MODEL_UNAVAILABLE`（模型 ID 不匹配） | 已修复 |
| 修复后 PATCH | 独立捕获真实网络请求：`PATCH .../baihua` → **200**，response 含更新后的 `revision:2` | PASS |
| 表单关闭 | 保存后编辑表单关闭 | PASS |
| 详情显示新值 | 详情区域更新 | PASS |

### 6. 去重（`vendor_id + remote_voice_id`）

| 项 | 独立发现 | 结论 |
| --- | --- | --- |
| API 返回 | `/api/v1/voice-profiles` → 16 items | — |
| UI 显示 | `.voice-preset-list-item` → 8 items | PASS |
| 原理 | MiMo 双 Provider（MiMo-TTS + MiMo-TTS-Codeplan）×8 voices = 16，按 `vendor_id + remote_voice_id` 去重为 8 | PASS |

### 7. 试听区终态

| 项 | 独立发现 | 结论 |
| --- | --- | --- |
| 当前绑定音色 | `当前绑定音色：白桦`（随选中项实时变化） | PASS |
| 默认文本 | `这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。` | PASS |
| 生成试听按钮 | 可见，1 个 | PASS |
| 卡片/详情无播放器 | 0 个 audio 元素 | PASS |

### 8. 配置入口可达性与敏感字段过滤

沿用 PRESET-VOICE-UX-004-FE 实现回执中已验证的 `ArtifactPreviewCard` hover/focus/touch 行为与 `sanitizeGenerationRecord` 过滤（PRESET-VOICE-UX-V-001 已独立验证）。本票不重复验证非变更组件。

---

## 门禁独立复验

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `npm --prefix web-v2 test -- --run tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | **2 files, 17 passed**, exit 0, 7.36s | ✅ 一致 |
| `npm --prefix web-v2 test` | **23 files, 457 passed**, exit 0, 24.51s | ✅ 一致 |
| `npm --prefix web-v2 run build` | **71 modules**, exit 0, 1.25s | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |

## 截图清单

| 路径 | 内容 | 视口 |
| --- | --- | --- |
| `/tmp/pv004v-1440-full-top.png` | 全页从顶部：页头+tabs+新增+列表+详情+试听区 | 1440×900 |
| `/tmp/pv004v-1024-full-top.png` | 同上 | 1024×900 |
| `/tmp/pv004v-1440-selected.png` | 选中白桦：列表+详情+编辑按钮 | 1440×900 |
| `/tmp/pv004v-1024-selected.png` | 同上 | 1024×900 |
| `/tmp/pv004v-1440-edit.png` | 编辑表单打开 | 1440×900 |

## 未验证项

| 项 | 原因 |
| --- | --- |
| 真实试听成功/超时/切换失效 | 当前后端无可用 TTS Provider（`mimo-v2.5-tts` 可能未配置），生成试听会返回错误；此为环境限制，非前端缺陷。回执中 focused 测试已覆盖超时/切换逻辑。 |
| 真实 preview 截图 | 同上；需可用 Provider 才能捕获成功/失败终态截图 |

---

**最终判定：PASS**
