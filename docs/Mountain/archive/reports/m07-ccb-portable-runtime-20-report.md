#### CCB-PORTABLE-BACKEND-RUNTIME-20 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- branch: `feat/mountain-assets-settings-backend`
- implementation commit: `a16e622`
- git status: clean

##### 三条 smoke 路径的真实 PID 及死亡断言

| 路径 | PID 来源 | PID 值 | 死亡断言 |
|---|---|---|---|
| 成功 (`test_smoke_success_pid_marker`) | 外部 marker 文件 | smoke 子进程 PID（非空） | `pid_alive(pid) == False` ✓ |
| checker 失败 (`test_smoke_checker_failure_pid_and_redaction`) | 外部 marker 文件 | smoke 子进程 PID（非空） | `pid_alive(pid) == False` ✓ |
| 仓库外 cwd (`test_launch_from_outside_cwd_with_pid_marker`) | 外部 marker 文件 | 启动器子进程 PID | `pid_alive(pid) == False` ✓ |

PID marker 位于 `tempfile.mkdtemp()` 根目录（smoke 临时目录之外）。smoke 不删除调用者提供的 marker。测试读取 marker 后断言 PID 已死，再自行删除 marker。禁止 `marker 不存在 OR PID 已死` 形式。

##### canary 原始输入和脱敏输出摘要

**原始 canary 形态**（写入测试 checker 的 stdout/stderr）：
```
stdout: Authorization: Bearer ccb-runtime-secret-canary-FAKE123
stdout: https://api.example.com/v1?api_key=ccb-runtime-secret-canary-QUERY456
stderr: Bearer ccb-runtime-secret-canary-STDERR789
```

**脱敏输出**（smoke 回显时应用 `redact_text()`）：
```
stdout: Authorization: Bearer [REDACTED]
stdout: https://api.example.com/v1?api_key=[REDACTED]
stderr: Bearer [REDACTED]
```

**测试断言**：
- `ccb-runtime-secret-canary-FAKE123` not in output ✓
- `ccb-runtime-secret-canary-QUERY456` not in output ✓
- `ccb-runtime-secret-canary-STDERR789` not in output ✓
- `[REDACTED]` in output ✓

##### 独立真实 CCF checker 结果

```
smoke --checker-path <CCF worktree>/check-api-contract.mjs
→ All contracts aligned against real backend ✓
→ API Smoke: ALL PASSED ✓
→ PID terminated ✓, temp dir cleaned ✓
```

##### 专项及全量测试结果

```
专项 tests/test_backend_runtime_17.py: 11 passed, 1 skipped
全量 pytest: 438 passed, 6 skipped, 4 warnings, 3 subtests passed
compileall: ✓
```

##### 修改摘要

| 文件 | 修改 |
|---|---|
| `run_mountain_backend.py` | app import 异常不打印 `str(exc)`；端口错误不打印 `{exc}` |
| `smoke_real_backend_contract.py` | 新增 `--pid-marker`；新增 `redact_text()` 脱敏函数；checker 输出脱敏后回显；异常消息脱敏 |
| `test_backend_runtime_17.py` | 删除硬编码 CCF 路径；三条 smoke 路径用外部 marker 读取真实 PID；checker 失败测试注入真实 canary 并断言脱敏；删除 `len(marker)==0 or PID dead` 模式 |

##### 门禁原始摘要

```
专项 tests: 11 passed, 1 skipped
全量 pytest: 438 passed, 6 skipped
compileall: ✓
real CCF checker: All contracts aligned ✓
rg forbidden patterns (tests): 0 matches
rg forbidden patterns (print exc): 0 matches
git diff --check: clean
```

##### 未完成事项

无。
