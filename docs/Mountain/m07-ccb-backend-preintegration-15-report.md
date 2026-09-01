# CCB-BACKEND-PREINTEGRATION-15 Report

**指令编号**: CCB-BACKEND-PREINTEGRATION-15 (§4K)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: d90e405

---

## 1. 有界阻塞观察

两个并发测试 (`test_same_task_lock_serializes`, `test_concurrent_ref_preservation`) 均已修正：

**Before (rejected)**:
```python
assert not b_entered.is_set(), "B 在 A 持有锁期间进入了 checkpoint"
```

**After (correct)**:
```python
# 有界观察：等待 1 秒确认 B 被锁阻塞（不得用 is_set() 代替等待窗口）
assert not b_entered.wait(timeout=1.0), "B 在 A 持有锁期间进入了 checkpoint"
```

`wait(timeout=1.0)` 提供真实等待窗口，证明 B 在 A 持有锁的 1 秒观察期内无法进入 checkpoint。释放后继续断言 `b_entered.is_set()` 确认 B 最终通过了生产 checkpoint。

---

## 2. 删除旧测试契约依据

**删除文件**: `tests/test_mountain_v1_api.py` (826 行)

**依据**:
- 该文件导入旧 `webapp.server`（非新 `webapp.mountain_server`）
- 测试固定 `/api/v1/providers` 和 Provider Profile（旧架构概念）
- 新 Mountain Server 已有负向测试保证 `/api/v1/providers` 返回 404
- §4K 明确要求删除，不得通过 monkeypatch 或 skip 维持旧契约

**验证**: `rg -n "from webapp\.server import app|import webapp\.server" tests` 输出为空。

---

## 3. 新 Mountain Server 覆盖

**保留测试**:
- `tests/test_mountain_server.py` — 新组合根、动态 `/services`、旧 `/providers` 404、加密 SecretStore、Task API
- `tests/test_input_transaction_11.py` — 22 个输入事务测试（含并发串行化证明）

**剩余 `mountain_v1_router` 直接测试**: 1 个文件 (`tests/test_m07_pr1c_acceptance.py`, 34 tests)

---

## 4. 两次全量 pytest 原始摘要

**第一次**:
```
427 passed, 5 skipped, 4 warnings, 3 subtests passed in 39.90s
```

**第二次**:
```
427 passed, 5 skipped, 4 warnings, 3 subtests passed in 41.43s
```

两次均 0 failed。

---

## 5. 门禁结果

```bash
# 专项测试
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q tests/test_input_transaction_11.py tests/test_mountain_server.py
# 42 passed in 7.20s

# 全量测试 (两次)
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q
# 427 passed, 5 skipped, 0 failed (x2)

# 编译检查
python -m compileall csboard webapp cli scripts
# OK

# 禁止模式检查
rg -n "from webapp\.server import app|import webapp\.server" tests
# 无输出 ✓

rg -n "def _install_target|installed_request|old_request_bak|time\.sleep" tests/test_input_transaction_11.py
# 无输出 ✓

# git diff --check
# 无输出 ✓

# git status --short
# M tests/test_input_transaction_11.py
# D tests/test_mountain_v1_api.py
```

---

## 6. 剩余 mountain_v1_router 测试数量

**1 个文件, 34 个测试**: `tests/test_m07_pr1c_acceptance.py`

该文件使用 `from webapp.mountain_v1_api import mountain_v1_router` 直接构造路由器。本轮不扩大清理，列为后续债务。

---

## 7. Clean Status

- [x] 有界阻塞观察: `b_entered.wait(timeout=1.0)` 替代 `is_set()`
- [x] 旧测试删除: `tests/test_mountain_v1_api.py` 已移除
- [x] 新 Server 覆盖: 保留 `test_mountain_server.py` 和 `test_input_transaction_11.py`
- [x] 两次全量 pytest: 427 passed, 5 skipped, 0 failed (x2)
- [x] 所有门禁通过
- [x] git diff --check 干净
