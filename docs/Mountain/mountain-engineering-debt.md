# Mountain Engineering Debt

## 未关闭债务

### 2026-08-30 - CCB-TASK-INPUT-ATOMIC-10

**遗留项**:

1. **Task Router 其他端点直接访问 `repository.task_dir/run_dir`**
   - 影响：`get_task`、`get_artifacts`、`get_events`、`get_logs`、`get_diagnostics`、`get_final` 等端点
   - 路径：`webapp/mountain_task_api.py`
   - 优先级：中
   - 建议：逐段收口，添加正式接口到 Repository

2. **FastAPI 422 未统一 body.error**
   - 影响：FastAPI 框架的 validation error 仍使用 `detail` 字段
   - 路径：`webapp/mountain_task_api.py`
   - 优先级：低
   - 建议：添加 FastAPI exception handler 统一 422 响应格式

### 2026-08-31 - CCB-TASK-INPUT-TRANSACTION-11

**已解决**:

- ✅ 故障注入测试：`FaultInjectRepository` 子类可在 `_install_target` 的每个步骤注入故障
- ✅ 回滚逻辑：先删除新 target，再恢复旧 backup
- ✅ 跨扩展 reference：使用新扩展名，失败时正确清理
- ✅ 所有保存走同一事务：`save_inputs()` 的 `txn_dir` 参数从 `Path | None` 改为 `Path`
- ✅ /mnt/d 实测：`test_real_http_upload_mnt_d()` 使用真实数据盘

**遗留项**:

（继承 CCB-TASK-INPUT-ATOMIC-10 的 Task Router 收口和 FastAPI 422 统一）
