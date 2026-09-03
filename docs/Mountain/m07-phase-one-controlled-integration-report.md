# Mountain 第一阶段受控集成报告

## 1. 集成基线

- 集成来源：`integration/mountain-v2@e8ab0cd`
- 后端审核 HEAD：`1f57d2715390685671544db7bcc31f70644e6d93`
- 前端审核 HEAD：`16cec62a65c8a863717f48c62408ecd235b1a7fa`
- 集成分支：`integration/mountain-phase-one`
- 集成工作树：`/mnt/d/workstation/projects/cs-board-phase-one-integration`

原 `integration/mountain-v2` 工作树中的用户改动
`docs/agents/tasks/WEB-WO-003.md` 未被暂存、修改或带入本次集成。

## 2. 集成提交

- `2895f2c merge(mountain): integrate approved backend foundation`
- `df00e93 merge(mountain): integrate approved frontend recovery`
- `4d63dca chore(mountain): normalize integrated docs whitespace`

两个审核分支均以非快进 merge 合入，未合并到 `main`，没有推送。

## 3. 集成门禁

- 前端 build：通过，68 modules。
- 前端全量：16 files、388 tests，通过，13.39 秒。
- 前端 warning/unhandled/unmounted 扫描：0 命中。
- 前端 contract checker 单元测试：48 tests，通过，5.12 秒。
- 后端全量：558 passed、5 个既有 skipped、4 warnings、3 subtests passed，99.93 秒，180 秒内正常退出。
- Python compileall：通过。
- 集成范围 `git diff --check`：通过。
- 真实后端 production checker：`All contracts aligned against real backend`，0 violation。

`npm ci` 报告 7 个依赖审计项（5 moderate、1 high、1 critical）；本轮没有执行破坏锁文件或可能引入 breaking change 的 `npm audit fix --force`。该结果不冒充已完成的依赖安全审核。

## 4. 运行清理

production checker 使用独立临时 data dir 和 `127.0.0.1:44793`。验证后后端进程、端口和临时目录均已清理；集成工作树 clean。

## 5. 联调边界

该集成结果只证明统一提交图、自动化门禁和真实 API contract checker 已就绪。Professor 仍需在本集成工作树完成 CCF 检查点 B 的真实浏览器创建、故障、刷新恢复、幂等重试和进程清理，不得据此直接宣布 `USER_ACCEPTANCE`。
