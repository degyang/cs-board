# CCB-PORTABLE-BACKEND-RUNTIME-21 Report

**指令编号**: CCB-PORTABLE-BACKEND-RUNTIME-21 (§4Q)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: 1930c0b

---

## 1. 三条 Smoke 路径结果

| 路径 | 机制 | exit code |
|------|------|-----------|
| checker 成功 | 真实 CCF checker + 真实 uvicorn | 0 |
| checker 非零 | 假 checker 输出 canary 后 `process.exit(1)` | 1 |
| launcher/startup 失败 | 临时 launcher 输出 canary 后 `sys.exit(42)` | 1 |

---

## 2. 三个真实 PID 和死亡断言

| 路径 | PID | pid_alive(smoke 返回后) |
|------|-----|------------------------|
| checker 成功 | marker 写入，> 0 | False ✓ |
| checker 非零 | marker 写入，> 0 | False ✓ |
| startup 失败 | marker 写入，> 0 | False ✓ |

PID marker 通过 `os.replace` 原子写入。`wait_for_health` 检测 `proc.poll()` 非 None 立即失败，不等待 30 秒。

---

## 3. Startup Canary 脱敏结果

**Canary**: `ccb-runtime-secret-canary-9f3a7b2e`

临时 launcher 写入：
```
Authorization: Bearer ccb-runtime-secret-canary-9f3a7b2e
https://api.example.com/v1?api_key=ccb-runtime-secret-canary-9f3a7b2e
```

断言：
```python
assert CANARY not in output           # ✓ canary 不在 smoke stdout/stderr
assert "[REDACTED]" in output         # ✓ 脱敏标记出现
```

checker 失败路径额外验证：
```python
assert "ccb-runtime-secret-canary-FAKE123" not in output  # ✓
assert "ccb-runtime-secret-canary-QUERY456" not in output  # ✓
assert "ccb-runtime-secret-canary-STDERR789" not in output  # ✓
assert "[REDACTED]" in output                               # ✓
```

---

## 4. 新增 `--launcher-path` 覆盖

```python
parser.add_argument("--launcher-path", type=str, default=None)
# 默认: scripts/run_mountain_backend.py
# 不存在时: 非零退出 + 明确错误
```

测试 `test_smoke_launcher_missing_exits_nonzero` 验证。

---

## 5. Health 轮询 Launcher 退出检测

```python
def wait_for_health(base, proc, timeout=30):
    while ...:
        if proc.poll() is not None:
            raise RuntimeError(f"Launcher exited prematurely with code {proc.returncode}")
        # 正常 health 轮询
```

不再等待完整 30 秒。

---

## 6. 删除的内容

| 删除 | 原因 |
|------|------|
| `pytest.skip("health timeout...")` | 必须真实执行 startup failure |
| `test_startup_failure_log_redaction` | 复制正则，不执行生产脱敏 |
| `test_launcher_no_raw_exception_output` | 读取源码字符串 |

---

## 7. 日志句柄与清理

所有路径：
1. `log_fd.flush()` + `log_fd.close()` 在 `rmtree` 之前
2. `shutil.rmtree(tmp_dir)` 不使用 `ignore_errors`
3. 断言 `Path(tmp_dir).exists() == False`
4. `finally` 块兜底关闭 `log_fd` 并清理

---

## 8. 门禁结果

```
专项: 14 passed, 0 skipped in 20.28s
pgrep: 无匹配
全量: 441 passed, 5 skipped, 0 failed
compileall: OK
smoke: All contracts aligned against real backend ✓
rg: 无输出
git diff --check: 无输出
```

---

## 9. Clean Status

- [x] smoke `--launcher-path` 测试覆盖
- [x] health 轮询检测 launcher 提前退出
- [x] 真实临时 launcher 输出 canary 后退出
- [x] 生产 smoke 验证 startup failure
- [x] 非空 PID、PID 死亡、canary 脱敏、目录消失
- [x] 删除 pytest.skip、复制正则测试、源码字符串测试
- [x] log_fd 先关闭再删除目录
- [x] 无 ignore_errors、无无人消费 PIPE
- [x] 专项 14 passed, 0 skipped
