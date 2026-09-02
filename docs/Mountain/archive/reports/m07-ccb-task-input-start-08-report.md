# CCB-TASK-INPUT-START-08 报告

## 指令信息

- **指令编号**: CCB-TASK-INPUT-START-08
- **工作目录**: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- **分支**: `feat/mountain-assets-settings-backend`
- **起点**: `89626a7 docs(mountain): report reproducible runtime baseline`
- **状态**: **执行中**

## Implementation Commit

```
98f4061 refactor(mountain): move task input and start semantics into application
```

## 门禁结果

| 门禁 | 命令 | 结果 |
|------|------|------|
| pytest | `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | ✅ 430 passed, 5 skipped |
| compileall | `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` | ✅ 无 SyntaxError |
| git diff --check | `git diff --check` | ✅ 无 whitespace 错误 |
| git status | `git status --short` | ✅ 干净（提交后） |

## §4D.2 七项处理结果

### 1. Router 分块写入受控临时 staging

**状态**: ✅ 完成

- Router 不再直接写入 `repository.task_dir(task_id) / "inputs"`
- 改为读取 `reference_audio_data = await reference.read()`
- 委托 `commands.save_inputs()` 处理文件保存
- Repository 使用 `save_input_file()` 方法，内部使用临时文件和原子替换

### 2. MountainCommands.save_inputs 接收 staging 引用

**状态**: ✅ 完成

```python
def save_inputs(
    self,
    task_id: str,
    script: str,
    reference_audio_data: bytes | None = None,  # 接收 bytes
    reference_audio_filename: str | None = None,
    # ... 其他参数 ...
) -> dict[str, Any]:
```

- 接收 `bytes` 而非文件路径
- 通过 `self.repository.save_input_file()` 保存
- 通过 `self.repository.save_request()` 原子写入 request.json
- 通过 `self.repository.save_task()` 更新 task.json

### 3. MountainCommands.get_inputs 返回稳定 DTO

**状态**: ✅ 完成

```python
def get_inputs(self, task_id: str) -> dict[str, Any]:
    """读取已保存的任务输入。"""
    self.repository.get_task(task_id)  # validate task exists
    request_data = self.repository.get_request(task_id)
    # ... 构建 DTO ...
```

- 通过 `self.repository.get_request()` 读取
- 通过 `self.repository.get_input_audio()` 获取音频元信息
- Router 不读取或合并 JSON

### 4. 启动前置条件进入 Application

**状态**: ✅ 完成

```python
def start_run(
    self,
    task_id: str,
    run_id: str,
    policy: str = "auto",
    context: CommandContext | None = None,
) -> dict[str, Any]:
    """启动运行：检查输入和服务可用性。"""
    # 检查输入是否已保存
    request_data = self.repository.get_request(task_id)
    if not request_data:
        raise DomainError("VALIDATION_ERROR", "请先上传文案与参考音频")

    # 检查 capability 可用性
    if self.service_resolver is not None:
        # ... 检查所有 capability ...
        if unavailable:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", ...)

    # 启动 pipeline
    return self.pipeline_run(task_id, run_id, policy, context=context)
```

- "输入是否已保存"检查进入 Application
- capability 计算进入 Application
- Router 只调用一个启动入口

### 5. 缺输入返回 VALIDATION_ERROR，缺服务返回 CAPABILITY_NOT_AVAILABLE

**状态**: ✅ 完成

- 缺输入: `DomainError("VALIDATION_ERROR", "请先上传文案与参考音频")`
- 缺服务: `DomainError("CAPABILITY_NOT_AVAILABLE", "缺少必要的服务配置", details={"unavailable": [...]})`
- `unavailable` 只出现在 `details` 中，不重复

### 6. 更新输入保留旧 reference

**状态**: ✅ 完成

```python
existing = self.repository.get_request(task_id) or {}
request_data = {
    "reference_audio": reference_audio_path if reference_audio_path else existing.get("reference_audio"),
    # ...
}
```

- 未提供新 reference 时保留旧 reference
- 失败时旧 manifest/reference 完整保留

### 7. CLI 与 Web 复用同一 Application 语义

**状态**: ✅ 完成

- CLI 通过 `MountainCommands.save_inputs()` 保存输入
- Web 通过 `MountainCommands.save_inputs()` 保存输入
- 两者使用相同的方法签名和行为

## 行为测试覆盖

| 测试 | 说明 |
|------|------|
| `test_inputs_and_start_boundary` | 真实 multipart 上传后 GET 回读一致，缺服务返回 CAPABILITY_NOT_AVAILABLE |
| `test_start_without_inputs_returns_validation_error` | 未上传输入时 start 返回 VALIDATION_ERROR |
| `test_update_inputs_preserves_old_reference` | 更新输入不带新 reference 时保留旧文件 |
| `test_save_and_read_inputs` | 保存 inputs 后能读取（已有测试） |
| `test_default_encrypted_startup` | 默认加密模式启动测试（已有测试） |

## 生产调用关系

### POST /api/v1/tasks/{task_id}/inputs

```
Router.upload_inputs()
  → await reference.read()  # Router 读取文件数据
  → commands.save_inputs()  # Application 处理
    → repository.get_task()  # 验证任务存在
    → repository.save_input_file()  # 保存音频文件
    → repository.get_request()  # 读取已有 request
    → repository.save_request()  # 原子写入 request.json
    → prepare_script()  # 文案整理
    → repository.save_task()  # 更新 task.json
    → telemetry.append_event()  # 记录事件
```

### GET /api/v1/tasks/{task_id}/inputs

```
Router.get_inputs()
  → commands.get_inputs()  # Application 处理
    → repository.get_task()  # 验证任务存在
    → repository.get_request()  # 读取 request.json
    → repository.get_input_audio()  # 获取音频元信息
    → 构建 DTO 返回
```

### POST /api/v1/tasks/{task_id}/runs/{run_id}/start

```
Router.start_run()
  → commands.start_run()  # Application 处理
    → repository.get_request()  # 检查输入是否已保存
    → service_resolver.resolve()  # 检查 capability 可用性
    → commands.pipeline_run()  # 启动 pipeline
```

## 未关闭债务

以下债务留给后续独立切片处理：

1. **Task Router 其他端点**: `get_task`、`get_artifacts`、`get_events`、`get_logs`、`get_diagnostics`、`get_final` 等端点仍直接访问 `repository.task_dir/run_dir`，需逐段收口。

2. **CAPABILITY_NOT_AVAILABLE 真实 start 行为**: 当前测试验证了缺服务返回 CAPABILITY_NOT_AVAILABLE，但需要真实 Service 注册后验证有服务时的行为。

3. **FastAPI 422 未统一 body.error**: FastAPI 框架的 validation error（422）仍使用 `detail` 字段，未统一为 `body.error` 格式。

4. **CLI 与 Web 输入状态一致性**: 需要验证 CLI 和 Web 对同一 Task 读取相同输入状态。

## 最终状态

```
$ git log --oneline -3
98f4061 refactor(mountain): move task input and start semantics into application
89626a7 docs(mountain): report reproducible runtime baseline
5c3deff fix(mountain): make encrypted runtime baseline reproducible

$ git status --short
(空)
```

**结论**: CCB-TASK-INPUT-START-08 **执行中**。所有门禁通过，三个端点已收口到 Application 层，但存在未关闭债务（其他端点、FastAPI 422 格式）。
