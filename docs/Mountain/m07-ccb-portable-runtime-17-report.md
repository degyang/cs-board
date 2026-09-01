# CCB-PORTABLE-BACKEND-RUNTIME-17 Report

**指令编号**: CCB-PORTABLE-BACKEND-RUNTIME-17 (§4M)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: efe746c

---

## 1. 正式启动命令

```bash
python scripts/run_mountain_backend.py [--host HOST] [--port PORT] [--data-dir DIR] [--log-level LEVEL]
```

默认: host=127.0.0.1, port=8000, data-dir=$CSBOARD_DATA_DIR 或 ~/.csboard, log-level=info

使用 `uvicorn.run("webapp.mountain_server:app", ...)` 启动，依赖 `sys.executable` 的 Python 环境。

---

## 2. 跨平台路径策略

| 组件 | 策略 |
|------|------|
| Python 解释器 | `sys.executable`（运行时解析） |
| Node.js | `shutil.which("node")`（PATH 查找） |
| Checker | 仓库默认 `web-v2/scripts/check-api-contract.mjs`，允许 `--checker-path` 或 `MOUNTAIN_CONTRACT_CHECKER` 覆盖 |
| 项目根 | `Path(__file__).resolve().parents[1]`（脚本相对位置） |

不得硬编码 `/mnt/d/`、`mise/installs` 或 `.venv` 路径。

---

## 3. Smoke 复用关系

```
smoke_real_backend_contract.py
    └── 通过 sys.executable scripts/run_mountain_backend.py 启动后端
            └── uvicorn.run("webapp.mountain_server:app")
```

smoke 测试的就是用户启动入口，不是另一套 uvicorn 命令。

---

## 4. 失败行为测试

| 测试 | 验证 |
|------|------|
| test_launch_script_port_occupied | 端口占用 → 非零退出 + "端口" 错误 |
| test_smoke_script_checker_missing_exits_nonzero | checker 不存在 → 非零退出 |

---

## 5. PID/临时目录清理断言

```python
# 进程终止
proc_pid = proc.pid
terminated = cleanup_process(proc)
assert terminated, f"进程 {proc_pid} 未能终止"

# 目录清理（不使用 ignore_errors）
shutil.rmtree(tmp_dir)
assert not Path(tmp_dir).exists(), "临时目录未清理"
```

`cleanup_process` 返回 `bool`，先 SIGTERM(10s)，再 SIGKILL(5s)。

---

## 6. 真实 Checker 输出

```
🔗 Connecting to real backend: http://127.0.0.1:45427/api/v1

All contracts aligned against real backend ✓
```

---

## 7. 门禁结果

```bash
# 全量测试
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q
# 445 passed, 5 skipped, 0 failed

# 编译检查
python -m compileall csboard webapp cli scripts
# OK

# Smoke
python scripts/smoke_real_backend_contract.py --checker-path <CCF checker>
# All contracts aligned against real backend ✓

# 禁止模式
rg -n "/mnt/d/|mise/installs|webapp\.server|CSBOARD_ALLOW_PLAINTEXT_SECRETS.*1" scripts/run_mountain_backend.py scripts/smoke_real_backend_contract.py
# 无输出 ✓

# git diff --check
# 无输出 ✓
```

---

## 8. Clean Status

- [x] 新增正式启动脚本 `scripts/run_mountain_backend.py`
- [x] smoke 改用新启动脚本
- [x] sys.executable / shutil.which("node")（无硬编码路径）
- [x] checker 默认仓库内路径，支持参数/环境变量覆盖
- [x] 清理证明: assert poll()/Path.exists()
- [x] 临时日志文件避免 PIPE 阻塞
- [x] 18 个行为测试覆盖参数/失败/清理
- [x] 445 passed, 5 skipped, 0 failed
- [x] rg 禁止模式无匹配
