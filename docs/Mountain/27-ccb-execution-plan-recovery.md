# CCB Execution Plan 接管恢复指令

状态：`REJECTED — RESTART WITH STRONGER MODEL`
拒绝提交：`9badecc`、`56bd317`
PM指令基线：`af502e4`
唯一需求来源：本文件和`25-ccb-execution-plan-final-correction.md`

## 1. 必须更换执行会话

当前CCB连续三轮未执行相同的明确测试要求。本轮必须：

- 使用可用的最高等级编码/推理模型；
- 启动全新会话，不继承历史聊天；
- 只读取本文件、25号指令、当前代码和直接相关测试；
- 不阅读整本16号历史台账；
- 先列出25号指令的逐项检查清单，再修改代码。

## 2. 当前事实

- `tests/test_task_execution_plan_23.py`仍为58行、3个测试；
- `9badecc`没有修改任何测试文件；
- 报告中的“25 passed”是把已有Service测试合并计数，不是25号要求的行为证明；
- `tests/test_backend_runtime_17.py`确实存在于当前checkout，共540行；“源码不在checkout”结论错误；
- 全量pytest仍timeout 124；
- `commands.py`通过`getattr(self.service_resolver, "_registry", None)`访问私有成员，违反应用层与Resolver边界，不能保留；
- 本轮仍不得进入Stage Work Order。

## 3. 开工前恢复

保留历史commit，不reset。新实现必须修正`9badecc`引入的私有访问：

- `MountainCommands`不得读取`ServiceResolver._registry`；
- 为“选择配置”和“确认运行可用”建立明确公开方法，或让Resolver公开返回可运行服务；
- 保持required Secret缺失时start fail closed；
- 使用回归测试冻结required/optional/default/priority语义。

## 4. 机器可核验交付条件

申请复审前，以下命令必须全部成立：

```bash
# 本轮必须实际修改专项测试
test -n "$(git diff --name-only af502e4...HEAD -- tests/test_task_execution_plan_23.py)"

# 必须出现要求的测试类别，不接受仅改名或注释
rg -n "parametrize|subprocess|checkpoint|concurr|sha256|diagnostic|old_request|cross_task" \
  tests/test_task_execution_plan_23.py

# 禁止应用层窥探Resolver私有成员
! rg -n 'service_resolver.*_registry|getattr\(self\.service_resolver, "_registry"' \
  csboard/application/commands.py

# runtime测试必须真实存在并单独正常结束
test -f tests/test_backend_runtime_17.py
timeout 60s env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py::test_smoke_checker_failure_path

# 专项、服务与全量
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_task_execution_plan_23.py
env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_service_registry.py tests/test_service_resolver.py
timeout 180s env -u PYTHONPATH -u CSBOARD_ALLOW_PLAINTEXT_SECRETS \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
git diff --check
git status --short
```

25号文档第3节的领域/API、同源读取、兼容只读、事务并发、启动无副作用、安全和服务选择测试全部仍为强制要求，不能用以上字符串扫描代替行为断言。

## 5. 全量挂起处理

若`test_smoke_checker_failure_path`单独通过而全量挂起：

1. 用`pytest -vv`和180秒timeout保存最后30条测试进度；
2. 检查该测试前一项遗留的PID、端口、环境变量和临时目录；
3. 运行最小顺序组合复现测试污染；
4. 修复生命周期根因并增加顺序回归测试；
5. 报告具体测试名、遗留资源和修复，不得使用“隐藏/注入/环境问题”而无证据。

## 6. 提交

实现和测试：

```text
fix(mountain): recover execution plan acceptance
```

新报告：

```text
docs/Mountain/m07-ccb-task-execution-plan-23-recovery-report.md
```

报告提交：

```text
docs(mountain): report recovered execution plan gates
```

报告必须给出真实hash、专项测试类别与数量、全量正常退出结果和耗时、runtime挂起根因、进程清理和clean status。先本地提交，不推送，不自行宣布通过。
