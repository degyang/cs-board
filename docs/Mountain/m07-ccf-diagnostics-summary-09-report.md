#### CCF-DIAGNOSTICS-SUMMARY-09 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web`
- branch: `feat/mountain-assets-settings-web`
- implementation commit: `7218eb5`
- git status: clean

##### 六类 DTO 映射

| 类别 | DTO 字段 | 页面渲染 |
|---|---|---|
| API | `api.status` | healthy/ok→正常, degraded→降级, failed/down/unavailable→不可用, 其他→原样 |
| 动态服务 | `services.{total,available,unavailable}` | 总计 N · 可用 N · 不可用 N |
| 工具链 | `toolchain.{total,available,missing}` | 总计 N · 可用 N · 缺失 N |
| 存储 | `storage.{writable,free_bytes,used_bytes}` | 可写/不可写 + 共享 `formatCapacityBytes` |
| 遥测 | `telemetry.{enabled}` | 已启用/未启用/未配置(null) |
| 近期错误 | `logs.recent_errors` | 计数；logs=null 时显示0 |

##### API 状态映射

```
healthy / ok    → 正常   (dg-status--ok)
degraded        → 降级   (dg-status--warn)
failed / down / unavailable → 不可用 (dg-status--fail)
其他未知字符串  → 原样   (dg-status--unknown)
```

##### 共享容量 helper

`hasValidCapacity` 和 `formatCapacityBytes` 从 `StoragePage` 提取至 `src/lib/formatting.ts`，StoragePage 改为 import 共享版本。既27个 Storage 测试继续通过。

##### 敏感字段不渲染

页面不展示：`api.endpoint`、`telemetry.endpoint`、`logs.log_path`、`recent_errors[].message`、`recent_errors[].details`，以及响应中可能携带的 `path`、`command`、`token`、`secret`、`credential`。

##### 竞态时序

```
T0: renderAt → call #1 挂起
T1: unmount (mounted=false, requestId++)
T2: renderAt → call #2 挂起
T3: resolve #2 → DOM 显示 second data (services=5)
T4: resolve #1 → guard 阻止 setState → DOM 仍显示 second (services=5)
```

两个 Promise 均 resolve，两个 fetch 均断言 `toHaveBeenCalledTimes(2)`。

##### 能力矩阵 API gap

后端 `GET /api/v1/settings/diagnostics` 当前不返回系统能力矩阵（engine × visualSource）。原型 `DiagCapabilityRow` 未实现。页面不渲染该区，不伪造固定列表。

##### 门禁原始摘要

```
build: ✓ (tsc --noEmit && vite build)
contract checker tests:48/48
full tests:300/300
act warnings:0
Router warnings:0
unhandled rejection:0
fixture checker: ✓ (fixture mode)
rg forbidden patterns:0 matches
git diff --check: clean
```

##### 未完成事项

- 真实 CCB checker 未运行（blocked: waiting for CCB runtime）
- 能力矩阵等待后端提供字段
