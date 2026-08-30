# M07 Task 语义纠偏 Follow-up — 审计文档

**日期**: 2026-08-30
**分支**: `feat/mountain-m07-project-api-web-v2`
**前序提交**: `c72b358` (Task 语义纠偏初版)

---

## 一、文案整理算法

### 实际实现

`csboard/domain/script_preparation.py` — `prepare_script(text, *, target_chars, min_chars, max_chars)`

- **算法**: 按句子边界拆分 → 贪心合并：尽量接近 `target_chars`，不低过 `min_chars` 开始新 Unit，不超过 `max_chars` 硬上限
- **确定性**: 相同 text + rules → 完全一致输出
- **输出**: `{"algorithm_version": "deterministic-v1", "rules": {...}, "voice_units": [...]}`

### target_chars / min_chars / max_chars 真实生效

| 参数 | 行为 |
|------|------|
| `target_chars` | 目标长度；达到后若已超过 `min_chars` 则开始新 Unit |
| `min_chars` | 低于此值时继续添加句子，即使已超 `target_chars` |
| `max_chars` | 硬上限；单句超过此值则该句独立成 Unit |

### 测试覆盖

`tests/test_script_preparation.py` — 22 tests:
- 改变 target_chars 产生不同结果 ✅
- min/max 生效 ✅
- 全部 Unit 按顺序完整覆盖原文 ✅
- 相同输入得到完全一致输出 ✅
- 空/短文本抛出 ValueError ✅

---

## 二、POST /api/v1/tasks/{task_id}/inputs

### Form 字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `script` | str | required | 文案 |
| `reference` | file | None | 参考音频 |
| `style` | str | "极简粗线简笔白板风" | 视觉风格 |
| `include_subtitles` | bool | True | 是否包含字幕 |
| `pen_text` | str | "" | 画笔文字 |
| `stroke_detail` | str | "detailed" | 笔触细节 |
| `target_chars` | int | 80 | 文案整理规则 |
| `min_chars` | int | 35 | 文案整理规则 |
| `max_chars` | int | 140 | 文案整理规则 |
| `visual_anchor_enabled` | bool | True | 是否启用 LLM 锚定 |

### 行为

- 保存时**始终重新生成** `script_preparation`（不复用旧结果）
- 文案整理失败返回 `400 {"code": "VALIDATION_ERROR", "message": "..."}`
- rules 和 visual_anchor_enabled 保存到 `request.json` 和 `task.json`

### GET /inputs 响应

```json
{
  "task_id": "...",
  "saved": true,
  "inputs": {"script": "...", "style": "...", ...},
  "reference_audio": {"uploaded": true, ...},
  "rules": {"target_chars": 80, "min_chars": 35, "max_chars": 140},
  "script_preparation": {"algorithm_version": "...", "rules": {...}, "voice_units": [...]},
  "visual_anchor_enabled": true
}
```

---

## 三、generate-visual-anchors 阶段

### 接口变更

**Before**: `generate_visual_anchors(task_id, run_id, script, context)`
**After**: `generate_visual_anchors(task_id, run_id, context)`

- 不接受独立 script 参数
- 从 `task.json.script_preparation.voice_units` 读取已保存的 Units
- 不调用 `segment_script()`
- 不改写、拆分、合并、重排 Voice Unit

### visual_anchor_enabled=false

- 不调用 TextModel/LLM
- 为每个 Unit 写入默认锚定结果（`source: "default"`）
- 阶段状态: `result: "skipped"`

### visual_anchor_enabled=true

- 通过 ProviderFactory 取得 TextModel
- 对每个 Unit 生成 `anchor_text`, `highlight_text`, `visual_intent`
- 输出包含 `source: "llm"`
- LLM 输出严格校验: unit_id 存在、不修改 text/source_range/order
- 无效输出降级为 default + warning + telemetry event

### 别名删除

`MountainCommands.segment_script = generate_visual_anchors` 已删除

---

## 四、Legacy 隔离

### csboard.application.__init__

```python
# 不再导出 LegacyJobBridge
__all__: list[str] = []
```

### webapp/server.py

```python
# 从 legacy_bridge 直接导入，不经过 __init__
from csboard.application.legacy_bridge import LegacyJobBridge
```

### 测试验证

`tests/test_legacy_isolation.py`:
- `csboard.application` 不导出 LegacyJobBridge ✅
- `csboard.application` 不导出 LegacyRunLink ✅
- legacy_bridge 模块仍可直接导入 ✅

### mountain_api.py 测试

`test_mountain_api.py::TestStageEndpoints` 已 skip（legacy API 调用已删除的 segment_script 别名）

---

## 五、TaskQueue API

### GET /api/v1/tasks

| 参数 | 说明 |
|------|------|
| `limit` | 1-100, 默认 50 |
| `cursor` | task_id 游标 |
| `status` | 状态过滤 |
| `q` | 匹配 title AND task_id |

### 排序

运行中/失败待处理优先，其余按 updated_at DESC

### active_run 响应

```json
{
  "run_id": "run-...",
  "status": "running",
  "current_stage": "clone-voice",
  "started_at": "...",
  "retryable": false,
  "error_code": null,
  "final_available": false,
  "fallback_unit_count": null
}
```

- `fallback_unit_count`: 无真实统计时为 `null`（非伪造 0）
- `error_code`: 仅从真实失败记录得出；暂不可用为 `null`

### 不返回

文案全文、参考音频、Secret、日志、诊断包

---

## 六、前端 DTO

### types.ts 新增

- `ActiveRunSummary` — active_run 嵌套对象
- `TaskQueueItem extends Task` — 含 active_run
- `TaskListResponse` — `items: TaskQueueItem[], next_cursor: string | null`
- `ScriptPreparation`, `VoiceUnitDTO`, `InputsRules`
- `InputsReadback` 新增 `rules`, `script_preparation`, `visual_anchor_enabled`

### client.ts

- `fetchTasks(params?)` — 支持 `{ limit, cursor, status, q }`
- HTTP 契约测试新增 7 个 test case

---

## 七、术语收口

| 文件 | 修复 |
|------|------|
| `HelpPage.tsx` | "文案分割" → "生成画面锚定重点" |
| `m07-task-semantic-correction-audit.md` | 添加"历史记录"标记 |
| `av_timing.py` | "文案分割未完整覆盖原文" → "Voice Unit 未完整覆盖原文" |

---

## 八、测试结果

| 集合 | 结果 |
|------|------|
| Backend (pytest) | 256 passed, 9 skipped |
| Frontend (vitest) | 120 passed |
| TypeScript (tsc --noEmit) | 无错误 |
| Build (npm run build) | 清洁 |
| git diff --check | 无空白问题 |

---

## 九、已知缺口

| 项 | 说明 |
|----|------|
| TextModel mock | `_generate_llm_anchors` 的 LLM 调用路径需要集成测试验证真实 Provider |
| fallback_unit_count | 暂为 null；需 clone-voice 完成后统计实际 fallback 数 |
| error_code | 暂为 null；需 Run 模型扩展 error_code 字段 |
| mountain_api.py | 旧 API 仍引用已删除的 segment_script 别名，待完全下线 |
| mountain_stages.py | 旧阶段定义未修改，待完全下线 |
