# CCB-PORTABLE-BACKEND-RUNTIME-19 Report

**指令编号**: CCB-PORTABLE-BACKEND-RUNTIME-19 (§4O)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: 3155369

---

## 1. 三条 Smoke 路径 Exit Code

| 路径 | exit code | 验证 |
|------|-----------|------|
| checker 成功 | 0 | `All contracts aligned against real backend` + `API Smoke: ALL PASSED` |
| checker 非零 | 1 | `Fake checker failure` 输出确认 |
| health/startup 失败 | 1 | 端口占用 → health 超时 → 启动失败日志输出 |

---

## 2. PID 与临时目录清理证据

三条路径均断言：

```python
# PID 消失
marker = list(tmp_parent.glob("csboard-smoke-*/pid.marker"))
assert len(marker) == 0 or all(not _pid_alive(int(m.read_text())) for m in marker)

# 临时目录消失
remaining = list(tmp_parent.iterdir())
assert len(remaining) == 0
```

smoke 脚本自身也在 finally 中断言：
```python
proc.terminate()
assert proc.poll() is not None  # 进程已终止
shutil.rmtree(tmp_dir)          # 不使用 ignore_errors
assert not Path(tmp_dir).exists()  # 目录已消失
```

pgrep 门禁确认无残留进程：
```
pgrep -af "scripts/run_mountain_backend.py" → 无匹配
```

---

## 3. Canary 脱敏结果

**Canary**: `ccb-runtime-secret-canary-9f3a7b2e`

注入方式：环境变量 `CSBOARD_CONTRACT_CANARY` 在 smoke 子进程中设置。

验证：
```python
# checker 成功路径
assert CANARY_SECRET not in output  # ✓

# checker 失败路径
assert CANARY_SECRET not in output  # ✓

# health/startup 失败路径
assert CANARY_SECRET not in output  # ✓

# 端口占用错误
assert CANARY_SECRET not in output  # ✓
```

所有路径的 stdout、stderr 和启动失败尾部日志均不含 canary。

---

## 4. 修复的问题

| 问题 | 修复 |
|------|------|
| test_launch_script_port_occupied 泄漏进程 | socket 保持打开，temp file 捕获输出，finally kill |
| test_health_timeout_cleanup 手动 kill/rmtree | 删除，改用真实 smoke health 失败路径 |
| test_script_error_no_secret_leak 弱断言 | 注入 canary，断言 canary 不在输出中 |
| ignore_errors=True 在清理中 | 全部移除，失败时直接 assert |
| PIPE 无人消费 | 改用临时日志文件 |
| 无 smoke 真实路径测试 | 新增 checker 成功/失败/health 失败三条路径 |
| 无 `--temp-parent` 观测接口 | smoke 新增 `--temp-parent` 和 PID marker |

---

## 5. 仓库外与空格 cwd Health

```
test_launch_from_outside_repo_cwd: ✓ (encrypted=true, writable=true)
test_launch_from_cwd_with_spaces: ✓ (encrypted=true)
```

---

## 6. 门禁结果

```bash
# 专项测试 (PYTHONPATH -u)
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q tests/test_backend_runtime_17.py
# 12 passed in 15.50s

# pgrep 泄漏检查
pgrep -af "scripts/run_mountain_backend.py"
# 无匹配 ✓

# 全量测试
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q
# 439 passed, 5 skipped, 0 failed

# 编译检查
python -m compileall csboard webapp cli scripts
# OK

# Smoke
python scripts/smoke_real_backend_contract.py --checker-path <CCF checker>
# All contracts aligned against real backend ✓

# 禁止模式
rg -n "pass$|ignore_errors=True|stdout=subprocess.PIPE|stderr=subprocess.PIPE|PYTHONPATH" ...
# 无输出 ✓

# git diff --check
# 无输出 ✓
```

---

## 7. Clean Status

- [x] 每个 Popen 纳入 try/finally
- [x] 无 pass、ignore_errors=True、无主 PIPE
- [x] 三条 smoke 真实路径均执行并验证
- [x] PID 消失 + 目录消失断言
- [x] Canary 脱敏验证
- [x] 仓库外/空格 cwd health
- [x] 12 专项 + 439 全量通过
- [x] pgrep 无泄漏
