# CCB-REAL-RUNTIME-CONTRACT-16 Report

**指令编号**: CCB-REAL-RUNTIME-CONTRACT-16 (§4L)
**日期**: 2026-09-01
**分支**: feat/mountain-assets-settings-backend
**提交**: 97be79b

---

## 1. 实际 uvicorn 命令（隐藏随机路径）

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m uvicorn webapp.mountain_server:app \
  --host 127.0.0.1 --port <随机端口> --log-level warning
```

环境变量:
- `CSBOARD_DATA_DIR=<临时目录>/data`
- `PYTHONPATH=<worktree根目录>`
- 无 `CSBOARD_ALLOW_PLAINTEXT_SECRETS`（默认加密模式）

---

## 2. Health 摘要

```json
{
  "status": "ok",
  "checks": {
    "task_repository": {"status": "ok"},
    "asset_repository": {"status": "ok"},
    "service_registry": {"status": "ok", "service_count": 0},
    "secret_store": {"status": "ok", "encrypted": true},
    "storage": {"status": "ok", "writable": true}
  }
}
```

---

## 3. 契约 Service 非敏感字段

```json
{
  "schema_version": 1,
  "revision": 1,
  "service_id": "contract-test-svc",
  "display_name": "契约测试服务",
  "capability": "speech_synthesis",
  "adapter_type": "openai_compatible",
  "endpoint": "https://example.invalid/v1",
  "model": "test-model",
  "enabled": true,
  "priority": 100,
  "is_default": true,
  "created_at": "2026-09-01T02:41:20.543Z",
  "updated_at": "2026-09-01T02:41:20.543Z",
  "config_status": {
    "configured": false,
    "missing_fields": [],
    "missing_secrets": ["api_key"]
  },
  "availability": {
    "available": false,
    "checked_at": "",
    "latency_ms": 0,
    "component": "contract-test-svc",
    "error_code": "NOT_PROBED",
    "suggestion": "尚未探测，请调用 /probe 端点"
  },
  "secret_status": {
    "configured": false,
    "required": ["api_key"],
    "missing": ["api_key"]
  }
}
```

---

## 4. 生产 Checker 原始成功输出

```
🔗 Connecting to real backend: http://127.0.0.1:47943/api/v1

All contracts aligned against real backend ✓
```

---

## 5. 后端契约修复

**文件**: `webapp/mountain_settings_api.py`

**问题**: `_service_to_alignment_summary()` 访问不存在的 `svc.metadata` 和 `svc.timeout` 属性，导致 `/api/v1/settings/voice-alignment` 返回 500。

**修复**:
```python
# Before
"model": (svc.metadata or {}).get("model"),
"timeout": svc.timeout,

# After
"model": svc.model or None,
"timeout": svc.config.get("timeout"),
```

`ServiceDefinition` 没有 `metadata` 和 `timeout` 字段。`model` 是直接字段，`timeout` 存储在 `config` 字典中。

---

## 6. API Smoke 表

| 端点 | 状态码 | 结果 |
|------|--------|------|
| GET /services | 200 | ✓ |
| GET /assets/styles?kind=preset | 200 | ✓ |
| GET /settings/toolchain | 200 | ✓ |
| GET /settings/storage | 200 | ✓ |
| GET /settings/diagnostics | 200 | ✓ |
| GET /nonexistent-api-404 | 404 | ✓ |

所有端点返回正确状态码和统一 `body.error` 结构（404 情况）。

---

## 7. 进程和临时目录清理证据

```
[smoke] 清理中...
[smoke] ✓ uvicorn 进程已终止
[smoke] ✓ 临时目录将由系统清理: /tmp/csboard-smoke-xxx
[smoke] 临时目录已清理: /tmp/csboard-smoke-xxx
```

`finally` 块确保:
1. `cleanup_process(proc)` — SIGTERM + wait(10) + SIGKILL fallback
2. `shutil.rmtree(tmp_dir)` — 递归删除临时目录
3. 不残留后台进程或用户正式 `~/.csboard` 数据

---

## 8. 两次全量 pytest 原始摘要

**第一次**:
```
427 passed, 5 skipped, 4 warnings, 3 subtests passed in 46.71s
```

**第二次**:
```
427 passed, 5 skipped, 4 warnings, 3 subtests passed in 38.83s
```

两次均 0 failed。

---

## 9. 门禁结果

```bash
# 全量测试 (两次)
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS pytest -q
# 427 passed, 5 skipped, 0 failed (x2)

# 编译检查
python -m compileall csboard webapp cli scripts
# OK

# 禁止模式检查（新脚本）
rg -n "webapp\.server:app|from webapp\.server import|/api/v1/providers" scripts/smoke_real_backend_contract.py
# 无输出 ✓

# Smoke 入口
python scripts/smoke_real_backend_contract.py
# All contracts aligned against real backend ✓
# API Smoke: ALL PASSED ✓

# git diff --check
# 无输出 ✓
```

---

## 10. Clean Status

- [x] 真实 uvicorn 进程启动（默认加密模式）
- [x] 通过 HTTP 创建契约 Service
- [x] CCF 生产 checker 输出 "All contracts aligned against real backend"
- [x] 可重复执行的 smoke 入口（自动清理进程和临时目录）
- [x] API smoke 表全部通过
- [x] 进程和临时目录清理证据
- [x] 两次全量 pytest: 427 passed, 5 skipped, 0 failed (x2)
- [x] 后端最小契约修复（voice-alignment metadata/timeout）
- [x] 未修改 CCF 分支、前端 DTO、fixtures 或 checker
