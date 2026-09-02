# CCB-TASK-INPUT-CONCURRENCY-13 Report

## Same-Task Real Concurrency Proof

**指令编号**: CCB-TASK-INPUT-CONCURRENCY-13 (§4I)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: 66bf570

---

## 1. 执行摘要

补齐同一 Task 的真实并发串行化证明。两个新测试使用 Event + contextvars 同步，证明：

1. A 持有 task_lock 时 B 无法进入 checkpoint
2. 释放后两者都成功，最终状态正确

**未修改生产代码** — 测试只覆盖 `_input_txn_checkpoint` hook。

---

## 2. 同步机制

### 问题

`upload_inputs` 是 `async def`，Starlette TestClient 在 asyncio portal 线程中执行，而非调用线程。因此 `threading.current_thread().name` 无法区分逻辑线程。

### 解决方案

使用 `contextvars.ContextVar` 传递逻辑线程标识：

```python
logical_thread = contextvars.ContextVar("logical_thread", default="unknown")

def thread_a():
    logical_thread.set("thread-a")
    client = TestClient(app)
    # ... checkpoint 读取 logical_thread.get() == "thread-a"
```

contextvars 在 asyncio task 创建时自动复制，因此 checkpoint（在 portal 线程中执行）能正确读取。

---

## 3. 测试时序证据

### test_same_task_lock_serializes

```
线程 A: logical_thread="thread-a" → POST /inputs → commit_inputs → task_lock → request.after_install checkpoint
   ↓ a_entered.set() ← 主线程确认 A 已进入
   ↓ a_release.wait() ← A 持有锁，等待释放信号

主线程: a_entered.wait() 成功 → 启动线程 B

线程 B: logical_thread="thread-b" → POST /inputs → commit_inputs → task_lock(阻塞)
   ↓ B 被 task_lock 阻塞，无法进入 checkpoint

主线程: b_entered.wait(1s) 超时 → 确认 B 未进入 checkpoint ✓

主线程: a_release.set() → A 释放锁

线程 A: checkpoint 返回 → commit_inputs 完成 → 200 OK
线程 B: 获得锁 → request.after_install checkpoint → b_entered.set() → 200 OK
```

### test_concurrent_ref_preservation

```
线程 A: upload reference.wav (512 bytes, 0xAA) → checkpoint 阻塞
主线程: 确认 A 进入 → 启动 B
线程 B: 无 reference → 被锁阻塞
主线程: 释放 A → A 完成
线程 B: 获得锁 → preserve_reference=True → 保留 A 的 reference → 完成

验证:
- request.script = "B 的文案..." (B 后获取锁)
- request.reference_audio = "inputs/reference.wav" (preserve_reference 保留)
- reference.wav sha256 = sha256(0xAA * 512) (A 上传的内容)
- staging artifacts = 0
```

---

## 4. 门禁结果

```bash
# 1. 输入事务测试
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q tests/test_input_transaction_11.py
# 22 passed in 5.90s

# 2. 全量测试
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q
# 457 passed, 5 skipped, 4 warnings, 3 subtests passed in 22.24s

# 3. 编译检查
python -m compileall csboard webapp cli scripts
# OK

# 4. 禁止模式检查
rg -n "def _install_target|installed_request|old_request_bak|time\.sleep" tests/test_input_transaction_11.py
# 无输出 ✓

# 5. git diff --check
# 无输出 ✓
```

---

## 5. 关键断言

| 断言 | 证据 |
|------|------|
| A 持有锁时 B 无法进入 checkpoint | `b_entered.wait(1s)` 超时返回 False |
| B 被 task_lock 阻塞（非 sleep） | B 线程存活且未进入 checkpoint |
| 释放后两者都成功 | `results["a"] == 200` and `results["b"] == 200` |
| 最终 script 是 B 的 | `"B 的文案" in request_data["script"]` |
| reference 是 A 上传的 | `sha256(ref) == sha256(audio_a_content)` |
| staging 清零 | `_count_staging_artifacts(task_dir) == 0` |

---

## 6. 未完成项

无。§4I 所有要求已满足：
- [x] 同一 Task 真实并发串行化证明
- [x] A 持有锁时 B 无法进入
- [x] 释放后两者成功，状态正确
- [x] 不同 Task 并行测试保留
- [x] 未修改生产代码
