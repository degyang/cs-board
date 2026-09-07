# NEXT-V-001 — 独立验收矩阵（前端就绪 / 后端等待）

状态：**FE ready for independent verification; BE blocked-input**。
Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。

## 前端 Worker 回执已读

- 回执路径：`/mnt/d/Workstation/Projects/cs-board-worktrees/frontend/docs/workmates/receipts/NEXT-FE-001.md`
- Frozen HEAD：`e34ba6e`（无实现变更，与基线一致）
- 声称门禁：17/17 focused、447/447 full、build 70 modules、`git diff --check` 0
- 浏览器证据：**缺失** — 8000 和 5182 均 HTTP 000，未生成截图
- 状态：`READY_FOR_INDEPENDENT_VERIFICATION`，worker 等待服务健康后补浏览器证据

**PM 指示：等待 worker 浏览器证据更新后再独立验证 FE。当前仅核对 worker 回执声称，不发 verdict。**

## Blocked Read-Only Inspection

以下 worktree git 检查被权限拒绝，记录为 blocker：

| 命令 | 目标 | 结果 |
| --- | --- | --- |
| `cd .../cs-board-worktrees/frontend && git log --oneline -5` | frontend worktree HEAD | **DENIED** — 无法读取当前提交 |
| `cd .../cs-board-worktrees/backend && git log --oneline -5` | backend worktree HEAD | **DENIED** — 无法读取当前提交 |

Worker 回执已确认 frozen HEAD = `e34ba6e`，与 PM 声明一致。Backend frozen target 待 PM 确认。

## 权威输入已读取

| 文件 | 状态 |
| --- | --- |
| `AGENTS.md` | ✅ 已读 |
| `CLAUDE.md` | ✅ 已读 |
| `docs/workmates/team-setup.md` | ✅ 已读 |
| `docs/workmates/assignments/NEXT-V-001.md` | ✅ 已读 |
| `docs/workmates/assignments/NEXT-FE-001.md` | ✅ 已读 |
| `docs/workmates/assignments/NEXT-BE-001.md` | ✅ 已读 |
| `docs/workmates/receipts/PRESET-VOICE-UX-003-V.md` | ✅ 已读（FAIL 权威：edit PATCH 400） |
| `docs/workmates/receipts/PRESET-VOICE-UX-004-FE.md` | ✅ 已读（修复实现回执） |
| `docs/workmates/receipts/M09-INFRA-ACTIVATE-007-V.md` | ✅ 已读（最终 PASS） |
| `docs/workmates/receipts/M09-INFRA-REAL-006-V.md` | ✅ 已读（PASS） |
| `docs/workmates/receipts/M09-FULL-GATE-008.md` | ✅ 已读（914 passed） |
| `docs/workmates/workmates-runtime.md` | ✅ 已读 |

---

## FRONTEND 验证矩阵（NEXT-FE-001）

源：`/mnt/d/Workstation/Projects/cs-board-worktrees/frontend`，分支 `workmates/frontend`。
权威：`PRESET-VOICE-UX-003-V`（FAIL）、`PRESET-VOICE-UX-004-FE`（修复回执）、`NEXT-FE-001.md`（done predicate）。

| # | 验证项 | 方法 | 判定标准 | 状态 |
| --- | --- | --- | --- | --- |
| F1 | 1024 双栏布局 | Playwright/Chromium 真实 5182，viewport 1024×900 | 列表在左、创建/编辑表单在右，不堆叠 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F2 | 1440 双栏布局 | Playwright/Chromium 真实 5182，viewport 1440×900 | 同上，detail 最小宽 ≥640px | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F3 | 列表可滚动、试听区可见 | 同上，选中长列表后滚动 | 试听区不被列表挤出可视区域 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F4 | vendor+remote 去重 | 真实 5182 页面 DOM 检查 | MiMo 双 Provider 16→8 条去重，其他 vendor 不变 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F5 | PATCH DTO | 独立 UI 编辑保存，监控 PATCH body | 不发送 `provider_id`/`example_text`；返回 200 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F6 | 无 Provider model 可见终态 | 选择无 model 的 Provider | 可见错误提示，不发送 400 请求 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F7 | 试听超时与旧音频失效 | 真实 preview 后切换音色 | 旧 audio 清除；timeout 后终态可见 | ⏳ 等 worker 浏览器证据 + 服务健康 |
| F8 | 专项音色测试 exit 0 | `npm --prefix web-v2 test -- tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | 0 failed, 0 skipped | 📋 worker 声称 17/17 — 待独立复验 |
| F9 | 全量前端测试 exit 0 | `npm --prefix web-v2 test` | 0 failed, 0 skipped | 📋 worker 声称 447/447 — 待独立复验 |
| F10 | Build exit 0 | `npm --prefix web-v2 run build` | 0 errors | 📋 worker 声称 70 modules — 待独立复验 |
| F11 | git diff --check | worktree 内执行 | exit 0 | 📋 worker 声称 0 — 待独立复验 |
| F12 | Commit 或 HEAD 记录 | `git log --oneline -1` 或回执记录 | 有实现改动→本地 commit；无改动→记录目标 HEAD | 📋 worker 声称 HEAD=e34ba6e 无变更 — 待独立复验 |

### Frontend verdict 规则

- 全部 F1–F12 PASS → **PASS**
- 任一项 FAIL 且为 PRESET-VOICE-UX-003-V 同类缺陷（edit PATCH 400、布局堆叠、试听区不可见）→ **FAIL**
- 服务未就绪或 worktree 不可达 → **BLOCKED**

---

## BACKEND 验证矩阵（NEXT-BE-001）

源：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`，分支 `workmates/backend`。
权威：`M09-INFRA-ACTIVATE-007-V`（最终 PASS）、`M09-INFRA-REAL-006-V`（PASS）、`M09-FULL-GATE-008`（914 passed）。

| # | 验证项 | 方法 | 判定标准 | 状态 |
| --- | --- | --- | --- | --- |
| B1 | P6 pointer/evidence 存在 | 读 `outputs/remotion-activation-pointer.json` 和 P6 evidence | 文件存在且可解析 | ⏳ 等 backend frozen target |
| B2 | 24h freshness | 核对 evidence `verified_at` vs 当前 UTC | ≤24h 为 PASS，否则 `EVIDENCE_EXPIRED` | ⏳ 等 backend frozen target |
| B3 | Tool/service fingerprint | 比较 evidence 五工具版本 vs 当前系统 | 一致为 PASS，任一不一致→`TOOLCHAIN_CHANGED` | ⏳ 等 backend frozen target |
| B4 | Nine reason codes | 临时副本独立反证：逐码触发 | 每个 code 稳定返回，无未处理异常 | ⏳ 等 backend frozen target |
| B5 | Activation projection | CLI/API `CapabilityService.snapshot()` | `supported=false`（缺 fingerprint）；create-options `available=false` | ⏳ 等 backend frozen target |
| B6 | Public submission fail-closed | 非 internal caller 的 `create_task` | 抛 `CAPABILITY_NOT_AVAILABLE` | ⏳ 等 backend frozen target |
| B7 | Receipt 缺失 fail-closed | 临时副本删 P6 receipt | `MANIFEST_INVALID`，无 `UnboundLocalError` | ⏳ 等 backend frozen target |
| B8 | Activation 专项测试 exit 0 | `pytest -q tests/test_infographic_activation.py ...` | 0 failed, 0 skipped | ⏳ 等 backend frozen target |
| B9 | 全量后端门禁 exit 0 | `.venv/bin/python scripts/run_backend_test_gate.py` | exit 0 | ⏳ 等 backend frozen target |
| B10 | git diff --check | worktree 内执行 | exit 0 | ⏳ 等 backend frozen target |
| B11 | Commit 或 HEAD 记录 | `git log --oneline -1` 或回执记录 | 有实现改动→本地 commit；无改动→记录目标 HEAD | ⏳ 等 backend frozen target |

### Backend verdict 规则

- 全部 B1–B11 PASS → **PASS**
- B4/B6/B7 任一 fail-closed 失败（含 M09-INFRA-ACTIVATE-007-V 已关闭的缺陷回归）→ **FAIL**
- 环境未就绪或 worktree 不可达 → **BLOCKED**

---

## 复验执行计划

PM 提供 frozen target 后，按以下顺序执行：

1. **读取 worktree HEAD** — 确认 commit 与 PM 声明一致
2. **读取 worker 回执** — `NEXT-FE-001.md` / `NEXT-BE-001.md`，核对命令、计数、commit
3. **Backend B1–B7** — 只读核对 activation/freshness/binding/submission 边界
4. **Backend B8–B11** — 运行门禁和 diff 检查
5. **Frontend F1–F7** — 需 5182 服务健康；若不健康则 F1–F7 标 BLOCKED，继续 F8–F12
6. **Frontend F8–F12** — 运行测试、build 和 diff 检查
7. **写最终 verdict** — 分别写 `NEXT-FE-001-V.md` 和 `NEXT-BE-001-V.md` 到本集成区

## 约束遵守

- ❌ 不修改产品实现
- ❌ 不修改共享看板
- ❌ 不执行真实 Remotion render
- ❌ 不调用图片/TTS API
- ❌ 不提交写请求（创建/编辑真实音色数据）
- ❌ 不使用 8001（未归属 PID 244089）
- ✅ 可读 worktree 代码和 receipts
- ✅ 可运行测试和 build
- ✅ 可在 `/tmp` 保存截图/证据
- ✅ 可写新回执到 `docs/workmates/receipts/NEXT-FE-001-V.md` 和 `NEXT-BE-001-V.md`
