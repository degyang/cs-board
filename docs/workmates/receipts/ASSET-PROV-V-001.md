# ASSET-PROV-V-001 — 资产溯源第一批独立验证回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、标准、看板或服务。

## 冻结目标

| 项 | 值 |
| --- | --- |
| Backend HEAD | `e34ba6e`（`chore(repo): remove legacy web and flatten schemas`） |
| Backend 冻结哈希 | `cce1422b684adce30ba9971bed7281453719c820055827b53b7d461be4f734ad` |
| Frontend HEAD | `e34ba6e`（同基线） |
| Frontend 冻结哈希 | `9233c2d12c60377467036fff664c3112a73b4bfc7d30dbd6e47acf38566d2164` |
| Backend 回执 | `cs-board-worktrees/backend/docs/workmates/receipts/ASSET-PROV-001.md` |
| Frontend 回执 | `cs-board-worktrees/frontend/docs/workmates/receipts/ASSET-PROV-FE-001.md` |

## Backend 独立验证

### Schema 审计（`schemas/artifacts/generation-record.schema.json`）

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| B1 | 覆盖 image/audio/video | `asset_kind` enum `["image","audio","video"]`；`generation_parameters` 以 `oneOf` 三分支分别定义 kind-specific 必填字段（image: width/height/format, audio: sample_rate/channels/format, video: width/height/fps/container/codec） | PASS |
| B2 | revision/attempt 结构 | `revision` integer ≥1，`parent_revision` integer ≥1 或 null；`attempt` 含 attempt_id/status/started_at/finished_at/error_summary，status enum 五态 | PASS |
| B3 | 相对路径限制 | `output_path` def pattern `^outputs/[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)+$`；绝对路径 `/tmp/...` 不匹配，`..` 段不匹配 | PASS |
| B4 | Secret 拒绝 | 所有对象 `additionalProperties: false`；`public_parameters` 仅 allowlist quality/style/voice；`error_summary` 仅 code/message；无 credential/header/secret 字段入口 | PASS |
| B5 | record_scope=current 约束 | `allOf` if/then：current → `is_current=true`、attempt status `succeeded`、output 为 object（非 null） | PASS |
| B6 | record_scope=attempt 约束 | else 分支：`is_current=false`；output 可为 null（失败 attempt 无需输出） | PASS |

### 后端测试审计（`tests/test_generation_record_schema.py`）

| # | 测试 | 独立复验 | 结论 |
| --- | --- | --- | --- |
| B7 | image/audio/video 正向 | 参数化三类，各自 kind-specific parameters 通过；且断言 `output.relative_path.split("/")[1] == identity.task_id` | PASS — 15 passed |
| B8 | 绝对路径拒绝 | `relative_path="/tmp/asset.png"` → errors 非空 | PASS |
| B9 | 路径穿越拒绝 | `relative_path="outputs/task-001/../outside.png"` → errors 非空 | PASS |
| B10 | Secret 字段拒绝 | `provider.api_key="redacted-test-value"` → errors 非空（additionalProperties=false） | PASS |
| B11 | 缺失 revision 拒绝 | `pop("revision")` → errors 非空（required 字段缺失） | PASS |
| B12 | 失败 attempt 冒充 current | scope=current + status=failed + output=None → errors 非空（allOf then 约束） | PASS |
| B13 | 历史失败 attempt 正向 | scope=attempt + is_current=False + status=failed + output=None → 无 errors | PASS |

### 后端门禁

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_generation_record_schema.py tests/test_mountain_contracts.py` | **15 passed, 2 warnings**, exit 0 | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |

### 后端 Diff 范围

新增文件（untracked）：`schemas/artifacts/generation-record.schema.json`、`tests/test_generation_record_schema.py`、`docs/workmates/receipts/ASSET-PROV-001.md`。
已有未提交变更（非本票）：`requirements-dev.txt`、`tests/test_infographic_activation.py`（NEXT-BE-001 遗留，receipt 已声明）。
无 API、UI、种子、目录迁移或真实素材改动。**未越权。**

---

## Frontend 独立验证

### 实现审计

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| F1 | 三类预览覆盖 | `AssetMedia` 组件：image → `<img>`，audio → `<audio controls>`，video → `<video controls>`；无 mediaUrl 时显示"预览地址等待后端契约提供" | PASS |
| F2 | 鼠标/键盘/触屏入口 | CSS: `.artifact-config-trigger` 默认 `opacity:0; pointer-events:none`；hover 和 focus-within 设为可见可点击；`@media (hover: none)` 触屏始终可见。测试覆盖 mouseEnter+click、focus+Enter、pointerDown(touch)+click 三种路径 | PASS |
| F3 | 不伪造再生成 API | "再次生成"按钮 `disabled`；附注"等待后端再生成契约"；`grep -rn fetch/axios/apiClient` 仅在注释中出现；无实际请求代码 | PASS |
| F4 | 不用 localStorage 保存业务数据 | `grep -rn localStorage` 无匹配；draft 状态仅 `useState` 内存 | PASS |
| F5 | 敏感字段过滤 | `sanitizeGenerationRecord`：regex `/secret\|authorization\|credential\|password\|token\|api[_-]?key/iu` 过滤 key；`ABSOLUTE_PATH` regex 过滤值；递归应用于嵌套对象和数组。测试断言 `api_key`、`authorization`、`/tmp/` 路径值均不出现在 JSON DOM | PASS |
| F6 | 仅声明的 editable_fields 可编辑 | `editableFieldNames` 仅从 `record.editable_fields` 数组提取字符串字段；测试断言 `positive_prompt` 和 `steps` 有输入控件 | PASS |
| F7 | types.ts 仅添加可选字段 | `Artifact` 接口新增 `asset_id?`, `asset_kind?`, `media_url?`, `generation_record?`；无 API client 或后端改动 | PASS |
| F8 | TaskWorkbenchPage 仅条件渲染 | 仅当 `artifact.asset_kind` 存在时渲染 `ArtifactPreviewCard`；不从 `relative_path` 猜测类型 | PASS |

### 前端门禁

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `npm --prefix web-v2 test -- tests/artifact-preview-card.test.tsx` | **5 passed**, 0 failed, 0 skipped, exit 0 | ✅ 一致 |
| `npm --prefix web-v2 test` | **21 files, 452 passed**, 0 failed, 0 skipped, exit 0 | ✅ 一致（回执称 452） |
| `npm --prefix web-v2 run build` | **71 modules**, exit 0 | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |

### Frontend Diff 范围

新增文件：`web-v2/src/components/tasks/ArtifactPreviewCard.tsx`、`web-v2/tests/artifact-preview-card.test.tsx`。
修改文件：`web-v2/src/lib/api/types.ts`（+5 行可选字段）、`web-v2/src/pages/TaskWorkbenchPage.tsx`（条件渲染卡片）、`web-v2/src/styles/app.css`（+25 行样式）。
无 API client、后端、种子或服务改动。**未越权。**

---

## 综合结论

| 维度 | 结论 |
| --- | --- |
| Schema 覆盖 image/audio/video、revision/attempt、相对路径、Secret 拒绝 | **PASS** |
| 前端三类预览、鼠标/键盘/触屏配置入口 | **PASS** |
| UI 不伪造再生成 API 成功，不用 localStorage 保存业务数据 | **PASS** |
| 双方直接测试、前端完整测试/build 通过 | **PASS** |
| Diff 未越权 | **PASS** |

**最终判定：PASS**
