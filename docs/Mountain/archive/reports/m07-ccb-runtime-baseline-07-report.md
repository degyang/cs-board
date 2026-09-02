# CCB-RUNTIME-BASELINE-07 报告

## 指令信息

- **指令编号**: CCB-RUNTIME-BASELINE-07
- **工作目录**: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- **分支**: `feat/mountain-assets-settings-backend`
- **起点**: `b79291a fix(mountain): harden production runtime and task API boundaries` + `391fe40 docs(mountain): report CCB runtime closeout status`
- **状态**: **执行中**

## §4C.3 六项处理结果

### 1. 项目后端唯一安装入口

**状态**: ✅ 完成

- 安装入口: `pip install -r requirements-dev.txt`
- `requirements-dev.txt` 包含 `cryptography>=42.0.0`
- 安装后指定解释器可成功 `import cryptography`

```bash
$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pip install -r requirements-dev.txt
Successfully installed cffi-2.1.1 cryptography-50.0.1 pycparser-3.0

$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -c "import cryptography; print(cryptography.__version__)"
50.0.1
```

### 2. 保持默认 fail-closed

**状态**: ✅ 完成

- 未设置 `CSBOARD_ALLOW_PLAINTEXT_SECRETS` 时，`create_app(temp_dir)` 成功
- `/api/v1/health` 返回 `secret_store.encrypted=true`
- 只有明确 scoped 测试才可启用明文

```bash
$ env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -c "
from pathlib import Path
from webapp.mountain_server import create_app
from starlette.testclient import TestClient
app = create_app(Path('/tmp/test'))
client = TestClient(app)
resp = client.get('/api/v1/health')
print(resp.json()['checks']['secret_store'])
"
{'status': 'ok', 'encrypted': True}
```

### 3. 修复测试隔离问题

**状态**: ✅ 完成

- 添加 `test_default_encrypted_startup` 测试
- 使用 `monkeypatch.delenv("CSBOARD_ALLOW_PLAINTEXT_SECRETS", raising=False)`
- 验证默认加密行为
- 未重新引入全局环境变量或 autouse 明文 fixture

```python
def test_default_encrypted_startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """默认加密模式启动：未设置 CSBOARD_ALLOW_PLAINTEXT_SECRETS 时 health 返回 encrypted=true。"""
    monkeypatch.delenv("CSBOARD_ALLOW_PLAINTEXT_SECRETS", raising=False)
    app = create_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["secret_store"]["encrypted"] is True
```

### 4. webapp.mountain_server:app 必须是 FastAPI 实例

**状态**: ✅ 完成

- 依赖正确安装后 `app` 是 FastAPI 实例
- 依赖缺失时给出明确启动错误

```bash
$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -c "from webapp.mountain_server import app; assert app is not None; print(type(app))"
<class 'fastapi.applications.FastAPI'>
```

### 5. 完整执行全量测试

**状态**: ✅ 完成

```bash
$ env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
427 passed, 5 skipped, 4 warnings, 3 subtests passed in 16.34s

$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
(无 SyntaxError)

$ git status --short
(空)
```

### 6. 报告明确保留的下一阶段债务

**状态**: ✅ 完成

见下方"未关闭债务"章节。

## 门禁结果

| 门禁 | 命令 | 结果 |
|------|------|------|
| pip install | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pip install -r requirements-dev.txt` | ✅ cryptography 50.0.1 安装成功 |
| import + app | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -c "import cryptography; from webapp.mountain_server import app; assert app is not None"` | ✅ app 是 FastAPI 实例 |
| pytest | `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | ✅ 427 passed, 5 skipped |
| compileall | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` | ✅ 无 SyntaxError |
| git diff --check | `git diff --check` | ✅ 无 whitespace 错误 |
| git status | `git status --short` | ✅ 干净 |
| 行为测试 | `test_default_encrypted_startup` | ✅ 通过 |

## Implementation Commit

```
5c3deff fix(mountain): make encrypted runtime baseline reproducible
```

## 未关闭债务

以下债务留给后续独立切片处理：

1. **Task Router 直接文件访问**: `webapp/mountain_task_api.py` 仍直接使用 `repository.task_dir/run_dir`，读取 `request.json/task.json/index.json/JSONL` 并拼接 `final.mp4`。§4B.3.3 要求"Router 不得直接读取这些文件"尚未实现。

2. **CAPABILITY_NOT_AVAILABLE 真实 start 行为**: §4B.3.1 要求"缺能力返回 CAPABILITY_NOT_AVAILABLE"，但当前 start 端点返回 `VALIDATION_ERROR`（因未上传输入），而非 `CAPABILITY_NOT_AVAILABLE`（因无服务）。需要独立审核验证真实 start 路径在有输入但无服务时的行为。

3. **FastAPI 422 未统一 body.error**: FastAPI 框架的 validation error（422）仍使用 `detail` 字段，未统一为 `body.error` 格式。这是 FastAPI 框架行为，非应用层错误。

4. **Service availability 探测**: 注册的 service 显示 `available: false`，需要实际 probe 验证。

## 最终状态

```
$ git log --oneline -3
5c3deff fix(mountain): make encrypted runtime baseline reproducible
391fe40 docs(mountain): report CCB runtime closeout status
b79291a fix(mountain): harden production runtime and task API boundaries

$ git status --short
(空)
```

**结论**: CCB-RUNTIME-BASELINE-07 **执行中**。所有门禁通过，但存在未关闭债务（Task Router 直接文件访问、CAPABILITY_NOT_AVAILABLE 真实行为、FastAPI 422 格式）。
