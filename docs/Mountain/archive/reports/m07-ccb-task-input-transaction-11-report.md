# CCB-TASK-INPUT-TRANSACTION-11 报告

## 指令信息

- **指令编号**: CCB-TASK-INPUT-TRANSACTION-11
- **审核结论**: 7db67d6 fix(mountain): make task input transaction production safe / 0ce3ba2 docs(mountain): report production safe input transaction → rejected
- **工作目录**: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- **分支**: `feat/mountain-assets-settings-backend`
- **起点**: `0ce3ba2 docs(mountain): report production safe input transaction`
- **状态**: **执行中**

## Implementation Commit

```
45d7b97 fix(mountain): prove and restore task input transactions
```

## 门禁结果

| 门禁 | 命令 | 结果 |
|------|------|------|
| pytest | `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | ✅ 455 passed, 5 skipped |
| compileall | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` | ✅ 无 SyntaxError |
| git diff --check | `git diff --check` | ✅ 无 whitespace 错误 |
| git status | `git status --short` | ✅ 干净（提交后） |

## §4G.2 已确认问题修复

### 1. 故障注入测试缺失

**状态**: ✅ 完成

- `FaultInjectRepository` 子类可在 `_install_target` 的每个步骤注入故障
- 通过 `activate_injection(fail_step)` 和 `deactivate_injection()` 控制
- 覆盖步骤 1（request）、步骤 2（task）、步骤 3（reference）

### 2. test_staging_on_same_filesystem 使用 /tmp 而非 /mnt/d

**状态**: ✅ 完成

- `test_real_http_upload_mnt_d()` 使用 `/mnt/d` 下的 `TemporaryDirectory`
- 验证文件存在和 staging 清理

### 3. test_chunked_read_verification 不验证 read(size)

**状态**: ✅ 完成

- `test_upload_limit_injection()` 注入 `max_bytes=8, chunk_size=4`
- 验证 8 字节成功、9 字节返回 `VALIDATION_ERROR`
- `test_chunk_size_injection()` 验证文件大小正确

### 4. 回滚逻辑错误

**状态**: ✅ 完成

旧逻辑：
```python
if request_bak.exists() and not request_path.exists():
    request_bak.rename(request_path)
elif request_bak.exists():
    request_bak.unlink()
```

新逻辑：
```python
# 先删除本事务已安装的新 target
if installed_request and installed_request.exists():
    installed_request.unlink()
# 再恢复旧 backup
if old_request_bak and old_request_bak.exists():
    old_request_bak.rename(request_target)
```

### 5. 跨扩展 reference 失败时不删除新扩展

**状态**: ✅ 完成

- 跨扩展更新时，使用新扩展名：`new_ref_path = old_ref_path.parent / f"reference{tmp_ref.suffix}"`
- 失败时删除新扩展文件，恢复旧扩展文件

### 6. 无 reference 时 txn_dir=None 不走事务

**状态**: ✅ 完成

- `save_inputs()` 的 `txn_dir` 参数从 `Path | None` 改为 `Path`（必需）
- Router 始终创建唯一事务目录：`txn_dir = repository.create_staging(task_id)`

### 7. create_staging(task_id) 不验证 task 存在

**状态**: ✅ 完成

- `create_staging()` 在创建目录前检查 `task_dir.exists()`
- Router 在调用 `create_staging()` 前先调用 `repository.get_task(task_id)`

### 8. 未跟踪 engineering-debt.md

**状态**: ✅ 完成

- 保留 `docs/Mountain/mountain-engineering-debt.md` 作为独立文档
- 内容合并到本轮报告的未完成项

## §4G.4 强制测试矩阵结果

| 测试 | 说明 | 状态 |
|------|------|------|
| `test_nonexistent_task_upload_returns_404` | 不存在 Task 上传：404，磁盘无该 task 目录 | ✅ |
| `test_first_save_without_ref_step1_failure` | 无 reference 首次保存：步骤 1 失败后 request 不存在 | ✅ |
| `test_first_save_without_ref_step2_failure` | 无 reference 首次保存：步骤 2 失败后 request 不存在 | ✅ |
| `test_update_save_without_ref_step1_failure` | 无 reference 更新保存：步骤 1 失败后 sha256 一致 | ✅ |
| `test_update_save_without_ref_step2_failure` | 无 reference 更新保存：步骤 2 失败后 sha256 一致 | ✅ |
| `test_first_save_with_ref_step1_failure` | 有 reference 首次保存：步骤 1 失败后 request/reference 不存在 | ✅ |
| `test_first_save_with_ref_step2_failure` | 有 reference 首次保存：步骤 2 失败后 request/reference 不存在 | ✅ |
| `test_first_save_with_ref_step3_failure` | 有 reference 首次保存：步骤 3 失败后 request/reference 不存在 | ✅ |
| `test_same_ext_ref_update_step1_failure` | 同扩展更新：步骤 1 失败后 sha256 一致 | ✅ |
| `test_same_ext_ref_update_step2_failure` | 同扩展更新：步骤 2 失败后 sha256 一致 | ✅ |
| `test_same_ext_ref_update_step3_failure` | 同扩展更新：步骤 3 失败后 sha256 一致 | ✅ |
| `test_cross_ext_ref_update_step1_failure` | 跨扩展更新：步骤 1 失败后只有旧扩展且 sha256 一致 | ✅ |
| `test_cross_ext_ref_update_step2_failure` | 跨扩展更新：步骤 2 失败后只有旧扩展且 sha256 一致 | ✅ |
| `test_cross_ext_ref_update_step3_failure` | 跨扩展更新：步骤 3 失败后只有旧扩展且 sha256 一致 | ✅ |
| `test_upload_limit_injection` | 注入 max_bytes=8, chunk_size=4，8 字节成功、9 字节失败 | ✅ |
| `test_chunk_size_injection` | 验证 read(chunk_size) 和文件大小正确 | ✅ |
| `test_real_http_upload_mnt_d` | /mnt/d TemporaryDirectory 真实 HTTP 上传返回 200 | ✅ |
| `test_internal_error_no_path_leak` | INTERNAL_ERROR 不含路径、Errno 和注入异常文本 | ✅ |
| `test_success_cleanup_no_artifacts` | 成功后 staging、backup、tmp、partial 清零 | ✅ |
| `test_all_saves_use_transaction` | 所有保存（有无 reference）都走同一事务 | ✅ |

## /mnt/d 实测

`test_real_http_upload_mnt_d()` 使用 `/mnt/d` 下的 `TemporaryDirectory`：

```python
mnt_d = Path("/mnt/d")
if not mnt_d.exists():
    pytest.skip("/mnt/d 不存在")

with tempfile.TemporaryDirectory(dir=mnt_d) as tmp_dir:
    data_dir = Path(tmp_dir)
    app = create_app(data_dir)
    client = TestClient(app)

    # 创建任务并上传
    task_id = _create_task(client, "真实上传测试")
    audio = io.BytesIO(b"\x00" * 256)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证在真实数据盘上的上传功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200
```

- 临时目录路径：`/mnt/d/tmp*`（随机目录名，不提交 Git）
- 验证文件存在和 staging 清理
- 测试结束后自动清理

## 事务策略

### 新的回滚策略

```python
except Exception:
    # 回滚：先删除本事务已安装的新 target，再恢复旧 backup
    if installed_request and installed_request.exists():
        installed_request.unlink()
    if installed_task and installed_task.exists():
        installed_task.unlink()
    if installed_ref and installed_ref.exists():
        installed_ref.unlink()

    # 恢复旧 backup
    if old_request_bak and old_request_bak.exists():
        old_request_bak.rename(request_target)
    if old_task_bak and old_task_bak.exists():
        old_task_bak.rename(task_target)
    if old_ref_bak and old_ref_bak.exists():
        if old_ref_path:
            old_ref_bak.rename(old_ref_path)
        else:
            old_ref_bak.unlink()

    raise
```

关键改进：
- 使用 `installed_*` 变量跟踪已安装的新文件
- 先删除新文件，再恢复旧备份
- 跨扩展时使用新扩展名

### 跨扩展 reference 处理

```python
if old_ref_path:
    if old_ref_path.suffix == tmp_ref.suffix:
        # 同扩展
        tmp_ref.rename(old_ref_path)
        installed_ref = old_ref_path
    else:
        # 跨扩展：使用新扩展名
        new_ref_path = old_ref_path.parent / f"reference{tmp_ref.suffix}"
        tmp_ref.rename(new_ref_path)
        installed_ref = new_ref_path
```

## 未关闭债务

1. **Task Router 其他端点直接访问 `repository.task_dir/run_dir`**
   - 影响：`get_task`、`get_artifacts`、`get_events`、`get_logs`、`get_diagnostics`、`get_final` 等端点
   - 路径：`webapp/mountain_task_api.py`
   - 优先级：中

2. **FastAPI 422 未统一 body.error**
   - 影响：FastAPI 框架的 validation error 仍使用 `detail` 字段
   - 路径：`webapp/mountain_task_api.py`
   - 优先级：低

## 最终状态

```
$ git log --oneline -5
45d7b97 fix(mountain): prove and restore task input transactions
0ce3ba2 docs(mountain): report production safe input transaction
7db67d6 fix(mountain): make task input transaction production safe
0728c2d docs(mountain): report bounded atomic input status
349c954 fix(mountain): make task input upload bounded and atomic

$ git status --short
(空)
```

**结论**: CCB-TASK-INPUT-TRANSACTION-11 **执行中**。所有门禁通过，20 个事务行为测试全部通过，包括 /mnt/d 实测。
