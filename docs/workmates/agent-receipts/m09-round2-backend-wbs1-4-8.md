# M09 第二轮调度 — Backend 回执

状态：完成，待集成验收；未提交。
日期：2026-09-05

## 范围

### WBS-1：InfographicPage 领域模型
- 新增 `csboard/domain/infographic.py`
- InfographicCue, InfographicNode, InfographicPage, InfographicStoryboard
- `voice_units_to_pages()` 纯函数：VoiceUnit/Timeline/Storyboard → InfographicStoryboard
- 新增 `tests/test_infographic_domain.py`（12 tests）

### WBS-4：CapabilityService 动态 infographic-remotion 检测
- 修改 `csboard/application/capabilities.py`
- 新增 `_detect_remotion_readiness(project_root)` 检测 Node/render.mjs/browser
- `INFOGRAPHIC_STAGE_REQUIREMENTS` 共享白板阶段需求
- `snapshot()` 不再硬编码 `infographic-remotion supported=False`，改为动态检测
- 新增稳定 reason_code：`REMOTION_NOT_INSTALLED`、`NODE_NOT_FOUND`、`BROWSER_NOT_FOUND`、`RENDER_SCRIPT_MISSING`
- `_missing_requirements()` 增加可选 `requirements` 参数
- 新增 `tests/test_infographic_capability.py`（9 tests）

### WBS-5 部分：create_options 返回 infographic-remotion 引擎条目
- 修改 `csboard/application/commands.py` `create_options()` 方法
- 引擎列表动态包含 infographic-remotion，available/reason 来自 CapabilityService
- 新增 `tests/test_create_options_infographic.py`（3 tests）

### WBS-8：旧 webapp 导入防护测试
- 新增 `tests/test_no_legacy_imports.py`（2 tests）
- 静态扫描 `csboard/adapters/remotion/` 和 `csboard/application/` 不得 import webapp

## 安全边界

- 未修改任何音色 Provider 文件（voice_profile.py, voice_profiles.py, tts_adapter.py 等）
- 未修改 web-v2 前端文件
- 未修改 webapp/mountain_server.py
- 未调用旧 webapp/server.py
- capabilities.py 新增 import 仅限 `shutil` 和 `pathlib.Path`（标准库）

## 验证

```text
python -m pytest -q tests/test_infographic_domain.py tests/test_infographic_capability.py \
  tests/test_no_legacy_imports.py tests/test_capabilities_api.py \
  tests/test_create_options_infographic.py tests/test_task_create_contract_30.py
56 passed

cd web-v2 && npx vitest run tests/create-task.test.tsx
41 passed
```

## 不在本轮范围

- InfographicStoryboardAdapter（WBS-2）
- RemotionRendererAdapter（WBS-3）
- CLI --engine 参数（WBS-6）
- E2E 测试（WBS-7）
