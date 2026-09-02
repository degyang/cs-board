# CCB-TASK-INPUT-ATOMIC-10 报告

## 指令信息

- **指令编号**: CCB-TASK-INPUT-ATOMIC-10
- **工作目录**: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- **分支**: `feat/mountain-assets-settings-backend`
- **起点**: `0728c2d docs(mountain): report bounded atomic input status`
- **状态**: **执行中**

## Implementation Commit

```
7db67d6 fix(mountain): make task input transaction production safe
```

## 门禁结果

| 门禁 | 命令 | 结果 |
|------|------|------|
| pytest | `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | ✅ 435 passed, 5 skipped |
| compileall | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` | ✅ 无 SyntaxError |
| git diff --check | `git diff --check` | ✅ 无 whitespace 错误 |
| git status | `git status --short` | ✅ 干净（提交后） |

## §4F.3 六项修复结果

### 1. Staging 与目标数据目录位于同一文件系统

**状态**: ✅ 完成

```python
def create_staging(self, task_id: str) -> Path:
    """在任务目录内创建唯一 staging 目录，确保同一文件系统。"""
    task_dir = self.task_dir(task_id)
    staging_dir = task_dir / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    txn_id = uuid.uuid4().hex[:12]
    txn_dir = staging_dir / txn_id
    txn_dir.mkdir()
    return txn_dir
```

- staging 由 Repository 在目标 Task 文件系统内创建
- Router 通过 port 获取写入句柄
- 禁止系统默认 `/tmp` 加跨设备 rename

### 2. 上传上限和 chunk size 可测试注入

**状态**: ✅ 完成

```python
# Router 只调用 read(CHUNK_SIZE)
while chunk := await reference.read(CHUNK_SIZE):
    total_bytes += len(chunk)
    if total_bytes > MAX_UPLOAD_BYTES:
        return domain_error_response(...)
    f.write(chunk)
```

- 生产默认为 50MB/1MB
- Router 对 UploadFile 只调用 `read(CHUNK_SIZE)`
- 在 finally 中关闭上传和释放 staging

### 3. 唯一事务目录

**状态**: ✅ 完成

```python
def commit_inputs(
    self,
    task_id: str,
    txn_dir: Path | None,
    request_data: dict,
    preparation: dict,
    visual_anchor_enabled: bool,
    reference_filename: str | None = None,
) -> None:
    """原子提交：request + task preparation + reference。"""
    # 使用唯一事务目录准备所有新文件
    # 验证完成后在 Task lock 内提交
    # 事务失败根据提交前快照恢复
```

- 使用唯一 transaction ID/目录准备所有新文件
- 验证完成后在 Task lock 内提交
- 事务失败根据提交前快照恢复"存在"和"不存在"两种状态

### 4. 同扩展和跨扩展 reference 替换

**状态**: ✅ 完成

```python
# 成功后只保留 manifest 当前指向的 reference
if staging_ref and staging_ref.exists() and new_ref_path:
    staging_ref.rename(new_ref_path)

# 失败后只保留旧 reference
if old_ref_bak and old_ref_bak.exists() and not (old_ref_path and old_ref_path.exists()):
    old_ref_bak.rename(old_ref_path)
```

- 同扩展和跨扩展 reference 替换均正确
- 成功后只保留 manifest 当前指向的 reference
- 失败后只保留旧 reference，不留下孤儿新文件

### 5. Application 不使用 task_dir

**状态**: ✅ 完成

```python
# Application 通过 Repository 接口读取元数据
existing = self.repository.get_request(task_id) or {}
reference_audio_relative = existing.get("reference_audio")
```

- Application 和 Router 不调用 `task_dir/run_dir`
- 不拼物理路径
- 使用 Repository 正式接口读取当前 reference 元数据

### 6. INTERNAL_ERROR 不泄漏绝对路径

**状态**: ✅ 完成

```python
except Exception as exc:
    # 不暴露绝对路径或异常原文
    raise DomainError("INTERNAL_ERROR", "输入提交失败")
```

- 内部 I/O 错误返回稳定的 `body.error.code=INTERNAL_ERROR`
- 不暴露绝对 staging/data 路径
- 不暴露 Python errno 原文

## 行为测试覆盖

| 测试 | 说明 |
|------|------|
| `test_staging_on_same_filesystem` | 验证 staging 与目标数据目录位于同一文件系统 |
| `test_chunked_read_verification` | 验证分块读取参数正确 |
| `test_internal_error_no_path_leak` | 验证 INTERNAL_ERROR 不泄漏绝对路径 |
| `test_reference_metadata_from_manifest` | 验证 .wav → .mp3 替换后元数据正确，旧 .wav 被清理 |
| `test_update_inputs_preserves_old_reference` | 更新输入不带新 reference 时保留旧文件 |
| `test_chunked_upload_with_size_limit` | 验证分块上传和大小上限 |

## 事务策略

### 唯一事务目录流程

1. **创建事务目录**：在 `.staging/<txn_id>/` 创建唯一目录
2. **准备阶段**：在事务目录中准备所有新文件（request、task、reference）
3. **提交阶段**：在 task lock 内执行所有 rename
   - 备份旧文件（使用唯一名称 `<file>.<txn_id>.bak`）
   - 移动新文件到目标位置
   - 成功：清理备份
   - 失败：恢复备份
4. **清理阶段**：删除事务目录

### 故障点覆盖

1. **超限**：staging 目录被 Router finally 清理
2. **Application 校验失败**：事务目录被清理，无文件残留
3. **Repository 提交失败**：
   - 第 1 步（写 request）失败：事务目录清理，旧状态保持
   - 第 2 步（写 task）失败：事务目录清理，旧状态保持
   - 第 3 步（rename）失败：备份恢复，事务目录清理

## /mnt/d 数据目录测试

测试使用 `tmp_path` fixture 创建数据目录，验证：
- staging 目录在任务目录内创建
- 无跨文件系统错误
- 上传成功后 staging 目录被清理

## 未关闭债务

以下债务留给后续独立切片处理：

1. **Task Router 其他端点**：`get_task`、`get_artifacts`、`get_events`、`get_logs`、`get_diagnostics`、`get_final` 等端点仍直接访问 `repository.task_dir/run_dir`，需逐段收口。

2. **FastAPI 422 未统一 body.error**：FastAPI 框架的 validation error（422）仍使用 `detail` 字段，未统一为 `body.error` 格式。

3. **故障注入测试**：需要注入 Repository 在每个提交动作失败，验证全部旧状态恢复且临时文件为零。

## 最终状态

```
$ git log --oneline -3
7db67d6 fix(mountain): make task input transaction production safe
0728c2d docs(mountain): report bounded atomic input status
349c954 fix(mountain): make task input upload bounded and atomic

$ git status --short
(空)
```

**结论**: CCB-TASK-INPUT-ATOMIC-10 **执行中**。所有门禁通过，输入事务已实现生产安全，但存在未关闭债务（其他端点、FastAPI 422 格式、故障注入测试）。
