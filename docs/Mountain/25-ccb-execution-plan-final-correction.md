# CCB Execution Plan 最终纠偏指令

指令：`CCB-TASK-EXECUTION-PLAN-23-FINAL`  
状态：`CORRECTION REQUIRED`  
工作树：`/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`  
分支：`feat/mountain-assets-settings-backend`  
审核实现：`bbc6fa2`  
审核报告：`7c34586`

## 1. 审核事实

本轮不得进入Stage Work Order。

- `tests/test_task_execution_plan_23.py`相对上次审核零变更，仍只有3个测试；
- 4T.4要求的非法输入、事务故障、并发、CLI、旧数据、脱敏和完整无副作用矩阵未交付；
- 全量pytest仍未完成；
- 报告中的两个commit仍写“待提交”，与实际commit不符；
- `has_required_secrets`和Resolver过滤改变生产服务选择行为，但没有新增回归测试；
- 不能以修复一个挂起测试替代本切片完整验收。

## 2. 唯一目标

不再修改产品范围。严格完成原4T.4的行为证明，并使全量后端门禁结束且0 failed。

## 3. 必须提交的测试

### 3.1 ExecutionPlan领域/API矩阵

逐项参数化证明：

- 默认auto、显式auto；
- selective单项、多项和乱序规范化；
- 非法mode；
- auto+非空；selective+空；
- unknown、duplicate、空字符串、非字符串、`segment-script`；
- `manual_stages`非法JSON、null、字符串、对象和数字。

每个HTTP非法输入必须断言400和`VALIDATION_ERROR`，不能只调用领域对象。

### 3.2 同源读取

使用真实临时data dir证明以下四处结果完全一致：

1. POST保存响应后的规范值；
2. GET `/api/v1/tasks/{task_id}/inputs`；
3. 重新构造Repository/Application后的读取；
4. 真实CLI subprocess `task show --task ... --json`。

CLI测试不得直接调用`execute()`冒充进程边界。

### 3.3 兼容与只读

- 未保存inputs返回默认auto；
- 旧request缺`execution_plan`返回默认auto；
- 两种读取前后所有已有文件hash不变。

### 3.4 事务与并发

- 使用既有Repository checkpoint注入request、task、reference安装故障；
- 每处故障后旧script、reference、preparation和execution plan必须是同一旧revision；
- 两个并发保存使用不同script、reference和plan；最终四类事实必须全部来自同一个事务组合；
- 不复制生产安装算法到测试。

### 3.5 启动与无副作用

- auto start在隔离fake/不可用能力边界内30秒结束；不得触发公网、IndexTTS或图片服务；
- selective start断言409、`retryable=false`和suggestion；
- 对目标Task目录制作“相对路径→SHA-256”快照，调用前后完全一致；
- 不存在run、另一个Task的run必须按当前NotFound契约返回，不能返回409。

### 3.6 安全与服务选择回归

- API/CLI/Event/Log/Diagnostics均不出现完整测试script、reference bytes、绝对路径、Secret或traceback；
- `domain_error_response`的显式details优先和DomainError details fallback均有测试；
- ServiceResolver覆盖：无required secrets可选；required secrets齐全可选；缺一个不可选；optional secret缺失不阻断；多个服务时跳过缺Secret的默认服务并选择真实可用服务；
- SecretStore异常不得泄露Secret或底层异常文本。

## 4. 全量挂起定位

先单独执行并记录以下测试的实际结束时间：

```bash
timeout 60s env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -vv -s \
  tests/test_backend_runtime_17.py::test_smoke_checker_failure_path
```

若单测通过而全量挂起，使用`pytest -vv`记录最后一个开始但未结束的测试，检查遗留进程、端口、全局环境和测试顺序污染。必须修复根因及回归测试；禁止skip、删除断言或只增加timeout。

## 5. 最终门禁

```bash
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_task_execution_plan_23.py

env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_service_registry.py tests/test_service_resolver.py

timeout 180s env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts

! rg -n "segment-script|execution_mode.*gated|selective.*gated" \
  csboard/domain csboard/application/pipeline.py csboard/application/commands.py \
  webapp/mountain_task_api.py cli tests/test_task_execution_plan_23.py

git diff --check
git status --short
```

全量必须在180秒内正常退出并0 failed；timeout、skip增加或“未观察到失败”均不通过。

## 6. 提交和报告

实现/测试提交：

```text
test(mountain): complete execution plan behavior proof
```

新报告：

```text
docs/Mountain/m07-ccb-task-execution-plan-23-final-report.md
```

报告提交：

```text
docs(mountain): report final execution plan evidence
```

报告必须写真实commit hash、测试数量、全量耗时、挂起根因、进程清理、事务/并发矩阵、CLI/API DTO、ServiceResolver矩阵和clean status。旧报告不改写。先本地提交，不推送，不自行宣布通过。
