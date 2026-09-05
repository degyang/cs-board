# M09 Round 4 — WBS-5 Backend Receipt

**Date:** 2026-09-05
**Scope:** WBS-5 — API create_task 接受 infographic-remotion + 阶段 engine 选路

## Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `csboard/application/commands.py` | +68/-10 | create_task 解锁 infographic engine、render_visuals 按 engine 选路 |

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_infographic_task_creation.py` | ~200 | 7 tests covering engine validation, routing, guardrails |

## Implementation Summary

### Change 1: `create_task()` 解锁引擎 (~line 129)

- 删除 `engine is not Engine.WHITEBOARD` 硬拒绝
- `engine=INFOGRAPHIC_REMOTION` 时：创建 CapabilityService 检查 `supported=true`，否则抛 `CAPABILITY_NOT_AVAILABLE`
- `service_resolver=None` 时拒绝 infographic engine
- `engine=WHITEBOARD` 行为不变

### Change 2: `_exec_render_visuals()` engine 选路 (~line 1622)

- 读取 `task.engine`
- `INFOGRAPHIC_REMOTION` → 构造 `RemotionRendererAdapter()` (local import)
- `WHITEBOARD` → 保持现有 ServiceResolver 路径

### Change 3: `_exec_plan_storyboard()` engine 感知 (~line 1449)

- 读取 task 确认 engine 字段可访问
- 当前 infographic 路径复用白板 storyboard 规划（后续 WBS 可细化）

## Tests — 7 passed

| Test | What's verified |
|------|-----------------|
| test_create_task_accepts_infographic_engine | capability 可用时接受 infographic-remotion |
| test_create_task_rejects_infographic_without_capability | capability 不可用时拒绝 |
| test_create_task_rejects_infographic_without_service_resolver | 无 ServiceResolver 时拒绝 |
| test_create_task_whiteboard_unchanged | 白板路径完全不变 |
| test_render_visuals_routes_to_remotion_adapter | infographic task 走 RemotionRendererAdapter |
| test_render_visuals_routes_to_whiteboard_adapter | whiteboard task 走原有路径 |
| test_no_webapp_imports_in_commands_changes | AST 扫描无 webapp 导入 |

## Regression Results

```
专项 7/7 passed in 0.69s
WBS suite 99/99 passed in 4.05s (WBS-1~4,6,8 + WBS-3 + WBS-5)
全量 291 passed, 1 pre-existing failure (test_list_tasks — old /api/mountain/ endpoint)
```

## Exclusions Respected

- ❌ 仅改 commands.py + 新测试文件
- ❌ 无 webapp.server 导入
- ❌ 无 VoiceProfile 变更
- ❌ 无前端变更
- ❌ 无真实 Remotion 执行
- ❌ 未提交

## Integration Points

- **Consumes:** `RemotionRendererAdapter` (WBS-3)
- **Consumes:** `CapabilityService.snapshot()` (WBS-4)
- **Unblocks:** WBS-6 (CLI `--engine` 参数现在可传入 infographic-remotion)
