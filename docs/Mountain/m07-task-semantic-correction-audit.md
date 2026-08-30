# M07 Task 语义纠偏 PR — 审计文档

**日期**: 2026-08-30
**分支**: `feat/mountain-m07-project-api-web-v2`
**前序提交**: `b44ad5c` (Project → Task 全栈术语迁移)

---

## 一、变更范围

### 1.1 文案整理 (Script Preparation) — 确定性算法

| 文件 | 变更 |
|------|------|
| `csboard/domain/script_preparation.py` | **新增** — `prepare_script()` 函数，确定性文案整理 |
| `csboard/application/commands.py` | `create_task()` 保存 request.json 后自动运行文案整理 |
| `webapp/mountain_v1_api.py` | `POST /inputs` 保存后自动运行文案整理 |

**输出格式** (存储于 `task.json` 的 `script_preparation` 字段):
```json
{
  "algorithm_version": "deterministic-v1",
  "rules": {"target_chars": 80, "min_chars": 35, "max_chars": 140},
  "voice_units": [
    {"unit_id": "unit-001", "order": 1, "source_range": {"start": 0, "end": 42}, "text": "..."}
  ]
}
```

### 1.2 generate-visual-anchors 阶段 (替代 segment-script)

| 文件 | 变更 |
|------|------|
| `csboard/application/pipeline.py` | STAGE_ORDER[0]: `segment-script` → `generate-visual-anchors` |
| `csboard/application/commands.py` | `segment_script()` → `generate_visual_anchors()`；stage 注册更新 |
| `csboard/application/av_artifacts.py` | producer_stage 更新 |
| `csboard/application/storyboard.py` | 错误消息更新 |
| `cli/csboard.py` | stage dispatch 更新 |

### 1.3 术语收口

| 文件 | 变更 |
|------|------|
| `skills/video-workflow/SKILL.md` | `project create/show` → `task create/show` |
| `skills/script-segmenter/SKILL.md` | 整体重写为 visual-anchor-generator |
| `skills/voice-cloner/SKILL.md` | `segment-script` → `generate-visual-anchors` |
| `skills/storyboard-planner/SKILL.md` | `segment-script` → `generate-visual-anchors` |
| `web-v2/README.md` | 路由表、API 表、文件结构全部更新 |
| `web-v2/src/pages/TasksPage.tsx` | `projects` → `tasks`，CSS `.proj-*` → `.task-*` |
| `web-v2/src/lib/api/client.ts` | 注释 `Projects` → `Tasks` |
| `web-v2/src/lib/api/types.ts` | Stage 类型和名称映射更新 |
| `web-v2/src/pages/TaskWorkbenchPage.tsx` | placeholder 文案更新 |

### 1.4 Legacy 隔离标记

| 文件 | 变更 |
|------|------|
| `webapp/server.py` | 添加 LEGACY ARCHIVE 注释块 |
| `webapp/mountain_v1_api.py` | 更新模块文档字符串 |

### 1.5 Task Queue API 增强

| 文件 | 变更 |
|------|------|
| `webapp/mountain_v1_api.py` | `GET /api/v1/tasks` 支持 `cursor`, `status`, `q` 过滤；响应增加 `active_run` 嵌套对象 |

### 1.6 变量命名修正

| 文件 | 变更 |
|------|------|
| `webapp/mountain_v1_api.py` | `_task_detail_view(project, run)` → `_task_detail_view(task, run)` |

---

## 二、测试覆盖

| 类别 | 测试文件 | 状态 |
|------|----------|------|
| 后端全量 | `tests/` (238 tests) | ✅ 通过 |
| 前端全量 | `web-v2/tests/` (113 tests) | ✅ 通过 |
| TypeScript | `npx tsc --noEmit` | ✅ 无错误 |

---

## 三、残留已知项

| 项 | 说明 |
|----|------|
| `webapp/mountain_api.py` | 旧 API，仍调用 `segment_script` (通过 backward-compatible alias 支持) |
| `webapp/mountain_stages.py` | 旧阶段定义，M07 不修改 |
| `tests/test_mountain_api.py` | 测试旧 API，引用旧端点路径 |
| `csboard/domain/av_timing.py` | `segment_script()` 函数保留为底层确定性算法 |

---

## 四、向后兼容

- `MountainCommands.segment_script` 保留为 `generate_visual_anchors` 的别名
- `csboard.domain.av_timing.segment_script` 函数名不变 (底层算法)
- 旧 `/api/mountain/` 端点继续工作
