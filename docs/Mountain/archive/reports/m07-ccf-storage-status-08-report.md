#### CCF-STORAGE-STATUS-08 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation commit: `879482d`
- git status: clean (implementation commit only)

##### §3L.2 逐项结果

######1. 三类逻辑存储卡文案语义修正

**修改文件**: `web-v2/src/pages/StoragePage.tsx:50-52`

| 原文案 | 新文案 |
|---|---|
| 存储目录正常，可读写。 | 逻辑存储已就绪。 |
| 存储目录不可用，请检查运行环境。 | 尚不可用。 |

三类 boolean `*_available` 不再暗示单目录可读写，不与整体 `writable` 矛盾。`available=false` 使用中性"尚不可用"，不展示后端未返回的修复建议。

######2. 真实双请求竞态测试

**删除旧测试**: `second request wins when first arrives after second` — 原测试只 unmount 第一实例，未发起第二请求、未 resolve 第二 Promise、未断言新页面。

**新测试时序**:

```
T0: renderAt → fetchStorageSettings() call #1 → Promise #1 挂起
T1: unmount() (mounted=false, requestId 递增)
T2: renderAt → fetchStorageSettings() call #2 → Promise #2 挂起
T3: resolve Promise #2 (writable=true, cleanup_policy='fresh')
    → 第二实例 mounted=true, currentRequest===requestId → setState 生效
    → DOM 显示 fresh
T4: resolve Promise #1 (writable=false, cleanup_policy='stale', error_code='OLD_ERROR')
    → 第一实例 mounted=false → guard 阻止 setState
    → DOM 仍显示 fresh，不含 stale / OLD_ERROR
```

两个 Promise 均实际 resolve，两个 API 调用均断言 `toHaveBeenCalledTimes(2)`。最终 DOM 只显示第二响应。

######3. retry 测试 act warning 修复

**修改文件**: `web-v2/tests/storage-page.test.tsx:419-446`

- 移除 `await act(async () => { renderAt(...) })`，改为直接 `renderAt()`
- 移除 `await act(async () => { await user.click(...) })`，改为直接 `await user.click(...)`
- 使用 `userEvent.setup()` + `waitFor` 等待异步状态更新
- 不嵌套不必要的 `act`，不屏蔽 `console.error` 或 warning

######4. writable=false + available=true 中性状态测试

**新增测试**: `shows neutral "已就绪" on cards when writable is false but all available are true`

- `writable=false`, 三类 `available=true`, `error_code='STORAGE_READONLY'`
- 三类卡显示 `逻辑存储已就绪。`，不出现"可读写"
- 整体卡单独显示 `STORAGE_READONLY` 和后端 suggestion

##### 门禁原始摘要

```
build: ✓ (tsc --noEmit && vite build)
contract checker tests:48/48
full tests:271/271
act warnings:0
Router warnings:0
unhandled rejection:0
fixture checker: ✓ (fixture mode)
rg forbidden patterns:0 matches
git diff --check: clean
```

##### API gap

无新增。Storage DTO 字段与 §3K 一致。

##### 未完成事项

- 真实 CCB checker 未运行（blocked: waiting for CCB runtime）
- fixture checker 为 fixture mode，非真实 API 验证
