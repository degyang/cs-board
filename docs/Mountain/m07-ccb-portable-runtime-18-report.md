#### CCB-PORTABLE-BACKEND-RUNTIME-18 完成报告 —2026-09-01

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- branch: `feat/mountain-assets-settings-backend`
- correction commit: `0b02fab`
- git status: clean

##### 仓库外 cwd 真实启动结果

```
test_launch_from_outside_repo_cwd: PASSED
  cwd = /tmp/outside-cwd-XXXXXX (非仓库目录)
  启动: python /absolute/scripts/run_mountain_backend.py --port <dynamic>
  health: status=ok, encrypted=True, writable=True
  清理: 进程终止 ✓, 临时目录消失 ✓
```

##### 含空格 cwd 真实启动结果

```
test_launch_from_cwd_with_spaces: PASSED
  cwd = /tmp/cwd with spaces XXXXXX
  启动: python /absolute/scripts/run_mountain_backend.py --port <dynamic>
  health: status=ok, encrypted=True
  清理: 进程终止 ✓, 临时目录消失 ✓
```

##### 成功与失败清理证据

**成功路径** (`test_success_cleanup_proven`):
```
启动 → health ok → _stop_and_cleanup():
  proc.terminate() → proc.wait(10) → proc.poll() != None ✓
  _pid_alive(pid) == False ✓
  data_dir.exists() == False ✓
```

**端口占用失败路径** (`test_launch_script_port_occupied`):
```
socket.bind + listen → 启动器检测端口占用 → exit(1)
stderr 包含 "端口" ✓
```

**进程 kill 清理** (`test_health_timeout_cleanup`):
```
启动 → sleep(2) → proc.kill() → proc.wait(10)
proc.poll() != None ✓
_pid_alive(pid) == False ✓
data_dir 手动清理后 exists() == False ✓
```

##### 启动器修改摘要

`run_mountain_backend.py` 核心变更:
1. 新增 `_resolve_repo_root()` — 从脚本路径向上两级解析仓库根
2. 新增 `_ensure_importable(repo_root)` — 将仓库根插入 `sys.path[0]`
3. `--data-dir` 在导入 app 之前设置 `os.environ["CSBOARD_DATA_DIR"]`
4. 验证 `from webapp.mountain_server import app` 非 None
5. `uvicorn.run(app, ...)` 传入对象而非字符串，避免二次导入

##### Smoke 修改摘要

`smoke_real_backend_contract.py` 核心变更:
- 移除 `env["PYTHONPATH"] = str(PROJECT_ROOT)` 注入
- 增加 `env.pop("PYTHONPATH", None)` 确保不泄漏

##### 移除的伪行为测试

旧测试文件18个测试中以下为源码字符串搜索，已移除:
- `test_launch_script_uses_sys_executable` — 读源码搜索 "sys.executable"
- `test_launch_script_no_plaintext_secrets` — 读源码搜索 "CSBOARD_ALLOW_PLAINTEXT_SECRETS"
- `test_launch_script_no_webapp_server` — 读源码搜索 "webapp.server"
- `test_launch_script_default_values` — 读源码搜索 "default="
- `test_smoke_script_uses_sys_executable` — 读源码搜索
- `test_smoke_script_no_hardcoded_node` — 读源码搜索
- `test_smoke_script_checker_default` — 读源码搜索
- `test_smoke_script_no_webapp_server` — 读源码搜索
- `test_smoke_script_no_ignore_errors` — 读源码搜索
- `test_smoke_script_asserts_cleanup` — 读源码搜索
- `test_smoke_script_uses_launch_script` — 读源码搜索
- `test_smoke_script_log_file_strategy` — 读源码搜索
- `test_cleanup_process_terminates` — 只测试 Python 自带 shutil
- `test_temp_dir_cleanup_proven` — 只测试 Python 自带 rmtree

替换为10个真实行为测试。

##### 门禁原始摘要

```
专项 tests/test_backend_runtime_17.py: 10/10 passed
全量 pytest: 437 passed, 5 skipped, 4 warnings, 3 subtests passed
compileall: ✓
smoke: ✓ (health ok, encrypted=True, checker aligned, all API smoke passed)
rg forbidden patterns: PYTHONPATH=pop(remove), CSBOARD_ALLOW_PLAINTEXT_SECRETS=check(!=1) — 合法用途
git diff --check: clean
```

##### 未完成事项

无。本轮纠偏目标全部完成。
