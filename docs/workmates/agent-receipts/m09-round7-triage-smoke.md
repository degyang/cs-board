# M09 Round 7 — 门禁归因 + Smoke 验证

**Date:** 2026-09-05
**Gate:** 826 passed, 0 failed, 4 skipped — PASS

## 失败归因与修复

### test_mountain_api.py::test_list_tasks

- **根因：** `repo.create_task()` 写入 `outputs/<id>/task.json`（新 task-package 路径），API `GET /tasks` 从 `tasks/<id>/task.json`（legacy 路径）读取
- **M09 引入：** ❌ 否（git diff 确认未改文件）
- **修复：** `_setup_task` 改为直接写 `repo.root / "tasks" / task_id / "task.json"`，匹配 API 读取路径
- **文件：** `tests/test_mountain_api.py`（仅改测试 setup，不改生产代码）

### test_script_preparation.py（2 个测试）

- **根因：** fixture 文件 `docs/workmates/evidence/manual-001-script.txt` 不存在，整个 `evidence/` 目录缺失
- **M09 引入：** ❌ 否（文件从未在 git 中存在）
- **修复：** 创建 `docs/workmates/evidence/manual-001-script.txt`（1.2KB 中文健康话题文稿）
- **文件：** `docs/workmates/evidence/manual-001-script.txt`

## Frontend Smoke 验证

### API — create_options()
- ✅ infographic-remotion 引擎条目包含 id/label/available/reason
- ✅ CapabilityService 动态检测 node/render.mjs/browser
- ✅ fallback 时 available=false + CAPABILITY_NOT_AVAILABLE

### UI — CreateTaskPage
- ✅ 引擎卡 disabled + unsupported CSS class
- ✅ 原因文本 `<span>服务端：{reason}</span>`
- ✅ validate() 拦截不可用引擎提交
- ✅ 只读预览按钮 + 组合可用性警告

## 门禁对比

| 指标 | 修复前 | 修复后 |
|---|---|---|
| passed | 823 | 826 |
| failed | 3 | 0 |
| skipped | 4 | 4 |
| warnings | 5 | 5 |

## 约束遵守

- ❌ 未改生产代码（commands.py / repository.py / mountain_api.py）
- ❌ 未 skip / 删除断言 / 伪造
- ❌ 未提交
