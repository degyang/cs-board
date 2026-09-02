# CCB-PORTABLE-BACKEND-RUNTIME-22 Report

**指令编号**: CCB-PORTABLE-BACKEND-RUNTIME-22 (§4R)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: e963454

---

## 1. 任务边界

本轮只删除后端 pytest 对 CCF sibling worktree 的硬编码依赖。
**不修改**已经验收的启动器 (`scripts/run_mountain_backend.py`) 与 smoke 生命周期
(`scripts/smoke_real_backend_contract.py`)。

---

## 2. 删除的内容

| 删除 | 位置 | 原因 |
|------|------|------|
| `CCF_CHECKER` 常量 | `tests/test_backend_runtime_17.py` 顶部 | 硬编码 `/mnt/d/.../mountain-assets-settings-web/...`，指向 sibling worktree |
| `--checker-path str(CCF_CHECKER)` | `test_smoke_checker_success_path` | 改用 pytest 临时最小成功 checker |
| `--checker-path str(CCF_CHECKER)` | `test_smoke_startup_failure_path` | 改用临时存在 checker |

删除的常量原文：
```python
CCF_CHECKER = Path(
    "/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/"
    "mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs"
)
```

---

## 3. 替换为 pytest fixture checker（只证明生命周期）

### 3.1 成功路径 — 临时最小成功 checker

`test_smoke_checker_success_path` 在 `tmp_parent` 下创建
`min-success-checker.mjs`：

```js
console.log("All contracts aligned against real backend ✓");
process.exit(0);
```

- 只证明 smoke 生命周期（启动 → health → checker → 清理）
- **不冒充**真实 CCF 契约检查（不做任何 HTTP 断言）
- 成功标记串与 smoke 期望一致 → exit=0

### 3.2 启动失败路径 — 临时存在 checker

`test_smoke_startup_failure_path` 在 `tmp_parent` 下创建
`existing-checker.mjs`：

```js
console.log("placeholder checker");
process.exit(0);
```

- launcher (`bad_launcher.py`) 输出 canary 后 `sys.exit(42)`，在 checker
  运行前即失败
- smoke 的 `wait_for_health` 检测 `proc.poll() is not None` → startup failure
- checker 只需**存在**（smoke 启动前校验 `checker_path.exists()`），永不执行

### 3.3 checker 失败路径 — 临时失败 checker（未变）

`test_smoke_checker_failure_path` 已使用临时 `fake-checker.mjs`，本轮无需改动。

---

## 4. 真实 CCF checker 仅保留在独立集成 smoke 门禁

`scripts/smoke_real_backend_contract.py` 的 checker 解析：

```python
def resolve_checker_path(checker_arg: str | None) -> Path:
    if checker_arg:
        return Path(checker_arg)
    env_path = os.environ.get("MOUNTAIN_CONTRACT_CHECKER")
    if env_path:
        return Path(env_path)
    return PROJECT_ROOT / "web-v2" / "scripts" / "check-api-contract.mjs"
```

- 默认路径 repo-relative（`PROJECT_ROOT / "web-v2" / ...`），无 sibling 依赖
- 真实 CCF checker 通过 `--checker-path` 或 `MOUNTAIN_CONTRACT_CHECKER` 环境变量
  注入，仅在独立集成 smoke 门禁运行，不进入 pytest

**本轮未修改启动器与 smoke 脚本。**

---

## 5. 门禁结果

### 5.1 专项

```
.venv/bin/python -m pytest -q -rs tests/test_backend_runtime_17.py
..............                                                           [100%]
14 passed in 20.70s
```

**14 passed, 0 skipped。**

### 5.2 全量后端

```
.venv/bin/python -m pytest -q
441 passed, 5 skipped, 4 warnings, 3 subtests passed in 58.49s
```

**0 failed。全量不依赖另一个 worktree。**

### 5.3 compileall

```
.venv/bin/python -m compileall -q tests/test_backend_runtime_17.py
compileall OK
```

### 5.4 禁止路径扫描

```
rg -n "/mnt/d/|CCF_CHECKER|mountain-assets-settings-web" tests/test_backend_runtime_17.py
exit=1   # 无输出（clean）

rg -n "mountain-assets-settings-web|CCF_CHECKER" tests/
exit=1   # 无输出（clean）

rg -n "mountain-assets-settings-web|/mnt/d/.*worktrees" scripts/
exit=1   # 无输出（clean）
```

### 5.5 git diff --check

```
（无输出 — 无 whitespace 错误）
```

---

## 6. 独立真实 CCF checker 结果

```
.venv/bin/python scripts/smoke_real_backend_contract.py \
  --checker-path /mnt/d/.../mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs

[smoke] Health: status=ok
[smoke]   secret_store: encrypted=True
[smoke]   storage: writable=True
[smoke] 契约 Service: service_id=contract-test-svc
[smoke] 运行 checker: .../check-api-contract.mjs
[smoke] Checker output (redacted):
🔗 Connecting to real backend: http://127.0.0.1:<port>/api/v1
All contracts aligned against real backend ✓
[smoke] ✓ All contracts aligned against real backend
[smoke] API Smoke: ALL PASSED ✓
[smoke] ✓ 进程 (PID <pid>) 已终止
[smoke] ✓ 临时目录已清理
[smoke] 所有检查通过 ✓
exit=0
```

真实 CCF 契约检查在独立 smoke 门禁中通过。

---

## 7. 进程清理

```
pgrep -af "run_mountain_backend|smoke_real_backend"
none (clean)
```

本轮 smoke 与 pytest 启动的进程（经 `scripts/run_mountain_backend.py` →
`uvicorn.run(app)`）全部已清理。

> 注：系统中存在 3 个 `python -m uvicorn webapp.mountain_server:app`
> 进程（端口 47400/47401/47402），其命令行模式（`-m uvicorn` 直接调用，
> 路径 `/mnt/d/workstation/...`）与本轮启动器（`run_mountain_backend.py`）
> 不同，属于其他会话/仓库的遗留进程，按约束**不予杀灭**。

---

## 8. Clean Status

- [x] 删除 `CCF_CHECKER` 常量与 `/mnt/d/...` 硬编码路径
- [x] lifecycle 成功测试使用 pytest 临时最小成功 checker
- [x] checker 失败使用临时失败 checker（已有，未变）
- [x] startup 失败使用临时存在 checker
- [x] pytest fixture checker 只证明生命周期，不冒充真实 CCF 契约
- [x] 真实 CCF checker 仅保留在独立集成 smoke 门禁
- [x] 专项 14 passed, 0 skipped
- [x] 全量后端测试不依赖另一个 worktree（441 passed, 5 skipped, 0 failed）
- [x] 未修改启动器与 smoke 生命周期脚本
- [x] 无 sibling worktree 路径残留（tests/、scripts/ 扫描 clean）
