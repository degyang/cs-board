#### CCF-STORAGE-STATUS-07 完成报告 — 2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation_commit: `1539e95`
- git status: clean (implementation commit 后)

---

**真实 DTO 映射**

`GET /api/v1/settings/storage` → `StorageSettings`：

| 字段 | 类型 | 页面用途 |
|------|------|----------|
| `writable` | boolean | 整体可写状态卡片，`false` 时显示 `error_code` + `suggestion` |
| `assets_available` | boolean | 素材存储卡片状态 |
| `tasks_available` | boolean | 任务存储卡片状态 |
| `temp_available` | boolean | 临时存储卡片状态 |
| `free_bytes` | number \| null | 可用空间，异常值显示"未统计" |
| `used_bytes` | number \| null | 已用空间，异常值显示"未统计" |
| `cleanup_policy` | string \| null | 只读策略摘要，无编辑控件 |
| `error_code` | string \| null | writable=false 时展示 |
| `suggestion` | string \| null | writable=false 时展示 |

后端当前只提供资产、任务、临时三类逻辑存储。原型提到"五类逻辑存储"，但后端不提供另外两类，页面不伪造。

---

**三类存储状态**

- 素材存储（`assets_available`）
- 任务存储（`tasks_available`）
- 临时存储（`temp_available`）

每类以独立卡片呈现：名称 + 状态徽标（可用/不可用）+ 简要说明。全部三种状态均有行为测试覆盖（全可用、全不可用、混合）。

---

**容量异常测试**

| 场景 | free_bytes | used_bytes | 预期 |
|------|-----------|------------|------|
| 两者 null | null | null | "未统计"，不显示"可用空间"/"已用空间" |
| 0 字节 | 0 | 0 | "0 B" |
| 负数 free | -1 | 1000 | free 显示"未统计"，used 显示"1000 B" |
| 负数 used | 1000 | -1 | free 显示"1000 B"，used 显示"未统计" |
| NaN free | NaN | 1000 | free 显示"未统计"，used 显示"1000 B" |
| Infinity free | Infinity | 1000 | free 显示"未统计"，used 显示"1000 B" |
| 有效双值 | 100GB | 100GB | 格式化显示 + 比例 50.0% |
| 仅 free 有效 | 50GB | null | free 显示，used"未统计"，无比例 |
| 仅 used 有效 | null | 50GB | free"未统计"，used 显示，无比例 |

---

**敏感字段不渲染测试**

响应注入 `path`、`directory`、`filename`、`task_id`、`command`、`token`、`storage_path` 后，`container.textContent` 均不包含这些值。

---

**请求生命周期**

- `mounted` ref + `requestId` ref 模式（与已验收 ToolchainPage 一致）
- 卸载后旧响应不写回（测试验证无 act warning）
- 先发请求 A、再发请求 B 的竞态场景：旧请求不覆盖新状态

---

**行为测试清单（storage-page.test.tsx）**

1. 三类逻辑存储正常状态显示名称和可用徽标
2. 三类全不可用显示不可用徽标
3. 混合可用状态正确渲染
4. writable=false 显示真实 error_code 和 suggestion
5. writable=false 且 error_code/suggestion 为 null 时显示中性说明
6. writable=true 不显示错误详情
7. 两者 null → "未统计"
8. 0 字节 → "0 B"
9. 负数 free → free"未统计"，used 正常
10. 负数 used → free 正常，used"未统计"
11. NaN free → free"未统计"
12. Infinity free → free"未统计"
13. 有效双值格式化
14. 双值有效显示比例
15. 仅 free 有效无比例
16. 仅 used 有效无比例
17. cleanup_policy 只读展示
18. cleanup_policy null 不渲染
19. 页面无保存/编辑/清理控件
20. 敏感字段不渲染
21. loading 骨架
22. 请求错误
23. retry 重新调用 API
24. unmount 后不更新状态
25. 竞态：第二请求胜出
26. 页面标题和只读描述

---

**门禁原始摘要**

```
$ npm --prefix web-v2 run build
✓ built in 983ms

$ npm --prefix web-v2 run test:contract-checker
Tests 48 passed (48)

$ npm --prefix web-v2 test -- --run
Test Files 12 passed (12)
Tests 270 passed (270)

$ node web-v2/scripts/check-api-contract.mjs
⚠ MOUNTAIN_API_BASE not set — falling back to fixture comparison only
NOTE: This is fixture mode, NOT real API verification.
All fixture contracts aligned (fixture mode — not real API) ✓

$ ! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/StoragePage.tsx
(no matches)

$ git diff --check
(clean)

$ git status --short
(clean)
```

---

**API gap**

- 后端当前只有资产、任务、临时三类存储；原型的五类逻辑存储缺少后端支持，不伪造。
- `free_bytes` / `used_bytes` 来自后端运行时存储卷统计，非 Mountain 独占空间，页面已标注。
- 真实 CCB contract checker 需要 CCB 服务运行，当前标记 `blocked: waiting for CCB runtime`。

---

**未完成事项**

- 真实 CCB 服务端 contract checker 验证（blocked: waiting for CCB runtime）
- 后端补齐更多逻辑存储类别后可扩展页面卡片
