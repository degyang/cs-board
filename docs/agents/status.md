# CS Board Agent Coordination

近期唯一目标：完成 `docs/agents/milestone-m1-manual-skills-closure.md` 的人工 Codex Skills 视频闭环；
工程交付后进入 `USER_ACCEPTANCE`，停止新增开发和自动派工，等待用户从正式 WebUI 创建真实 Task 验收。

| Task | Owner | Status | Contract | Delivery | Review |
| --- | --- | --- | --- | --- | --- |
| `BASELINE-WEB-001` | WORKER_WEB | APPROVED | `docs/agents/tasks/BASELINE-WEB-001.md` | `docs/agents/reports/BASELINE-WEB-001.md` | PM accepted |
| `BASELINE-CORE-001` | WORKER_CORE | APPROVED | `docs/agents/tasks/BASELINE-CORE-001.md` | `docs/agents/reports/BASELINE-CORE-001.md` | PM accepted |
| `BASELINE-MEDIA-001` | WORKER_MEDIA | APPROVED | `docs/agents/tasks/BASELINE-MEDIA-001.md` | `docs/agents/reports/BASELINE-MEDIA-001.md` | PM accepted |
| `CORE-EXEC-002` | WORKER_CORE | APPROVED | `docs/agents/tasks/CORE-EXEC-002.md` | `e1bc3d5` | `docs/agents/reviews/CORE-EXEC-002.md` |
| `MEDIA-WO-002` | WORKER_MEDIA | APPROVED | `docs/agents/tasks/MEDIA-WO-002.md` | `7bc8af9` | `docs/agents/reviews/MEDIA-WO-002.md` |
| `PM-AUTO-001` | PM | APPROVED | `docs/agents/tasks/PM-AUTO-001.md` | `fa840d7` | `docs/agents/reviews/PM-AUTO-001.md` |
| `CORE-WO-003` | WORKER_CORE | APPROVED | `docs/agents/tasks/CORE-WO-003.md` | `1c5e9ce` | `docs/agents/reviews/CORE-WO-003.md` |
| `WEB-INTAKE-003` | WORKER_WEB | APPROVED | `docs/agents/tasks/WEB-INTAKE-003.md` | `51656c9` | `docs/agents/reviews/WEB-INTAKE-003.md` |
| `MEDIA-SKILLS-003` | WORKER_MEDIA | APPROVED | `docs/agents/tasks/MEDIA-SKILLS-003.md` | `6fc2924` | `docs/agents/reviews/MEDIA-SKILLS-003.md` |
| `CORE-CAP-004` | WORKER_CORE | APPROVED | `docs/agents/tasks/CORE-CAP-004.md` | `c567c3a` | `docs/agents/reviews/CORE-CAP-004.md` |
| `CEO-RECOVERY-002` | PM | SUPERSEDED | `docs/agents/tasks/CEO-RECOVERY-002.md` | `38a98f8` | archived; replaced by independent CEO timer and separate PM |
| `CORE-CAP-005` | WORKER_CORE | APPROVED | `docs/agents/tasks/CORE-CAP-005.md` | `7ac3cb0` | `docs/agents/reviews/CORE-CAP-005.md` |
| `CORE-RUNTIME-006` | WORKER_CORE | APPROVED | `docs/agents/tasks/CORE-RUNTIME-006.md` | `de57fab` | `docs/agents/reviews/CORE-RUNTIME-006.md` |
| `CORE-RUNTIME-007` | WORKER_CORE | BLOCKED | `docs/agents/tasks/CORE-RUNTIME-007.md` | `09009f103439d5d17e44fc6d30ebc1dfb1b1ec8e` | no bound Tester report; dispatcher dependency unavailable |
| `WEB-PARITY-004` | WORKER_WEB | APPROVED | `docs/agents/tasks/WEB-PARITY-004.md` | `9db741f` | TESTER_WEB PASS; PM approved |
| `PROTOTYPE-GOLDEN-005` | PROTOTYPE | APPROVED | `docs/agents/tasks/PROTOTYPE-GOLDEN-005.md` | `b4287d9` | `docs/agents/reviews/PROTOTYPE-GOLDEN-005.md` |
| `WEB-WO-003` | WORKER_WEB | BLOCKED | `docs/agents/tasks/WEB-WO-003.md` | `7adc8f5` | supervised dispatcher unavailable; attempt 2 cannot start until restored |
| `MEDIA-PREFLIGHT-004` | WORKER_MEDIA | BLOCKED | `docs/agents/tasks/MEDIA-PREFLIGHT-004.md` | `4610cbb` | full suite repeats exit 124 at input/start boundary; needs separate runtime diagnosis |
| `MEDIA-E2E-003` | WORKER_MEDIA | BACKLOG | `docs/agents/tasks/MEDIA-E2E-003.md` | pending | final M1 closure; waits for WEB-WO-003 + MEDIA-PREFLIGHT-004 |
| `DASH-STATS-003` | DASH | APPROVED | `docs/agents/tasks/DASH-STATS-003.md` | `45a3fba` | `docs/agents/reviews/DASH-STATS-003.md` |

## 当前决策

- `CORE-EXEC-002` attempt 2 已批准；`CORE-WO-003` 的两个依赖均满足并已派发。
- `MEDIA-WO-002` 契约已批准但未合并；CORE 通过固定 commit/path 只读消费该契约，不改写其产品语义。
- WEB 与 MEDIA 各增加一个不依赖 Work Order 生产 DTO 的真实并行切片；它们不改变原三个 BACKLOG 的依赖关系。
- WEB intake 自动化已真实发现 native Mountain Server 缺少 `/api/v1/capabilities`；前端保持阻塞，后端修复已进入 READY，不允许 WEB 吞掉 404。
- MEDIA Skills 主体方向正确，但首阶段 Artifact 映射和未实现 illustration retry 说明矛盾，进入有界 attempt 2。
- CEO/PM 协调线程为注册表中的真实 Codex CLI UUID。Worker 完成后必须按注册表直接唤醒 CEO，
  而不是只通知 `/root` 或等待用户追问。
- `CORE-CAP-004` attempt 2 已补齐真实依赖图并获批准；同一 `WEB-INTAKE-003` 已恢复，先完成 intake
  浏览器证据，再领取 `WEB-WO-003`。
- 当前 orchestrator 会话树已失效，`CEO-RECOVERY-002` 负责注册真实 CLI CEO、修复 stale work 检测，
  并恢复 `WEB-INTAKE-003`；恢复完成前不得把 `WEB-WO-003` 并发派给同一 WEB Owner。
- CEO 首次恢复周期核验 WEB 推送提交 `0b99b50` 后，确认并非遗失执行，而是新的 CORE 集成缺口：
  capabilities 调用了消费基线不存在的 public registry method。WEB 转为 `BLOCKED`，`CORE-CAP-005`
  使用固定 WEB base 做最小自包含修复；其独立审核通过前不得恢复 WEB。
- `CORE-CAP-005` 的独立审核已通过，CEO 批准交付 `7ac3cb0`；WEB 已注册为真实 Codex CLI 会话并恢复
  `WEB-INTAKE-003`，只引入自包含实现 `6699d20` 后重跑原 intake 门禁。`WEB-WO-003` 继续等待，不得并发。
- `WEB-INTAKE-003@672f820` 与 `DASH-STATS-003@45a3fba` 已完成 Worker 交付并进入独立审核，不在本轮跑长门禁。
- 用户确认 `127.0.0.1:5181` 仍是旧 `c221947` 表面且偏离原型；新增 P0 `WEB-PARITY-004`，依赖
  `WEB-INTAKE-003=APPROVED`，同 Owner 队列顺序优先于 P1 `WEB-WO-003`。
- `DASH-STATS-003@45a3fba` 的独立审核已通过，CEO 批准；`WEB-INTAKE-003@672f820` 尚无已提交的
  独立审核结论，继续保持 `REVIEW_READY`，不提前释放同 Owner 后续任务。
- 用户将已停止的 5182 只读 prototype dist 定为 `WEB-PARITY-004` 的正式 golden；任务使用同尺寸截图逐页
  对照，但生产实现只保留 Task 术语与真实 `/api/v1`，不得迁移 mock、localStorage、`/projects` 或明文 Secret。
- `WEB-INTAKE-003@672f820` 的独立评审结论为 `CHANGES_REQUESTED`；attempt 2 只修正报告脱敏/启动说明与
  API checker 有界失败行为。纠正再次获独立审核前，不批准且不派发 `WEB-PARITY-004` 或 `WEB-WO-003`。
- `WEB-INTAKE-003@0dbbf4e` 的 attempt 2 独立复审结论仍为 `CHANGES_REQUESTED`：默认 5000ms checker
  deadline 与 fresh 后端 voice-alignment 的 5 秒 probe 形成边界竞态。attempt 3 已由 `51656c9`
  有界纠正并完成 Worker handoff；本轮仅记为 `REVIEW_READY`，不在 record-review-ready 事件中作 CEO
  批准决定，也不释放 `WEB-PARITY-004`、`WEB-WO-003` 或其他后续 WEB 工作。
- `WEB-INTAKE-003@51656c9` 的 attempt 3 独立评审提交 `9885f57` 结论为 `APPROVED`；PM 据此将任务
  置为 `APPROVED`。队列重算后，依赖已满足的 P0 `WEB-PARITY-004` 进入 `READY`，同 Owner 的 P1
  `WEB-WO-003` 保持 `READY` 但排在其后。本决策不构成用户、发布或合并审核批准。
- `WEB-PARITY-004` 已固定在 WEB 分支 `feat/mountain-webui-surface-parity`、交付基线 `51656c9`，并按
  P0 顺序异步派发；PM 不等待其长门禁，`WEB-WO-003` 不得并发领取。
- WEB 已提交并推送 `WEB-PARITY-004@d7819d2`，分支与远端一致且报告存在；本轮只记录
  `REVIEW_READY` handoff。五组 golden/actual 配对、真实视觉对齐和全部门禁仍需独立 Reviewer 核验，
  不提前批准或派发同 Owner 的 `WEB-WO-003`。
- `WEB-PARITY-004@d7819d2` 的独立评审提交 `d069a34` 结论为 `CHANGES_REQUESTED`：actual 页面和工程
  门禁通过，但缺少五张 golden、hash/来源 manifest 与真实 prototype 访问。Git 中现有 prototype source
  不可构建且冻结截图只覆盖 settings，CEO 将任务置为 `BLOCKED`；先提供不可变、可复现的五页 golden
  输入，再派发同一任务的有界纠正。`WEB-WO-003` 继续等待，不得越过该 P0 blocker。
- WEB 的 golden blocker 不再无人认领：新增独立 P0 `PROTOTYPE-GOLDEN-005`，只恢复已跟踪原型的构建
  外壳并冻结五组 golden/hash manifest，禁止修改 `web-v2` 或原型视觉；独立审核通过后 CEO 才解除并
  重派 `WEB-PARITY-004` attempt 2。
- Agent 默认按适中能力派工；同一任务连续三次返工仍未解决，CEO 才可提出升级申请。任何 `gpt-5.6-sol`
  的 high/xhigh/max/ultra 使用必须先获用户针对该任务的明确审批。PROTOTYPE 已停止未审批高配会话，改用
  `gpt-5.6-terra + medium` 执行，停止前均无文件变更。
- DASH 是按任务动态注册的 Worker，不是常驻席位。其唯一任务 `DASH-STATS-003` 已批准且没有后续待办，
  当前已从 Agent 注册表和瞬时运行态回收；历史任务/审核保留，4317 面板服务继续作为团队基础设施运行。
- 先前 CORE Reviewer 启动失败但留下短期 working runtime，造成待审核任务存在而面板随后显示 idle。CEO 已
  注册真实 `/root/core_runtime_reviewer_live` 并启动 CORE 独立审核；Reviewer WIP=1，MEDIA 与刚交付
  `PROTOTYPE-GOLDEN-005@069ace1` 明确排队，不再用运行态冒充并行审核。
- Reviewer 调度全面审核已完成：Reviewer 改由唯一 systemd wrapper 确定性执行，真实进程启动后才写
  working，异常退出写 blocked，正常完成写 review；PM 只消费 verdict，事实未变化不得 ack。旧的
  orchestrator Reviewer 注册已切换为 `codex_exec`，后续审核队列由单一服务按 WIP=1 自动接力。
- PROTOTYPE attempt 2 也复现了旧 Worker 调度缺陷：预写 working 后 orchestrator 会话停在 pending_init，
  租约过期且工作树无进展。悬空会话已回收，真实 `/root/prototype_golden_attempt2_live` 已启动；Worker
  调度将沿用 Reviewer 的“受监督进程启动后才写 working、失败回滚”方案统一修复。
- PROTOTYPE Reviewer 的首次恢复同样只写入 runtime、没有创建真实会话；该伪 working 已被替换为已确认
  存活的 `/root/prototype_golden_reviewer_live`。当前优先审核关键路径 golden，随后才处理 CORE attempt 3
  与 MEDIA；后续只有会话启动成功后才能写 Reviewer working。
- CORE 与 MEDIA 的空闲资源分别领取独立 P0 `CORE-RUNTIME-006`、`MEDIA-PREFLIGHT-004`；两项都不依赖
  WEB Work Order，不执行 Stage 链。契约提交后由各自 Worker 异步执行，PM 不等待长门禁。
- `MEDIA-PREFLIGHT-004` 的 idle runtime 对应已完成而非遗失执行：实现 `d9f3a41` 与报告交付 `8532302`
  已提交推送，分支干净并与远端一致。CEO 未重复唤醒 MEDIA，只恢复为 `REVIEW_READY`；live readiness
  仍非全绿，独立审核与环境就绪前不派发 `MEDIA-E2E-003`。
- `CORE-RUNTIME-006@7a74378` 已修复造成全量挂起的启动边界，pytest 由 180 秒超时恢复为 76.32 秒正常
  exit 0；但仍有 5 个 skip，未满足契约。CEO 已派发 attempt 2：把四个 legacy skip 迁移为当前 `/api/v1`
  等价断言，并修正一个误把类名漂移当成“缺少 httpx”的 conformance 测试；禁止删断言或继续 skip。
- `CORE-RUNTIME-006` attempt 2 实现 `4ab3867` 与报告交付 `eb1a248` 已提交推送，CORE 分支干净且与
  远端一致。本轮仅记录 `REVIEW_READY` handoff；独立审核前不批准，也不作下游发布决定。
- CORE 与 MEDIA 的 review 事件均无已提交 digest；按 Reviewer WIP=1 和返工优先顺序，本轮只启动
  `CORE-RUNTIME-006` 独立审核，使用 `gpt-5.6-terra + medium`。`MEDIA-PREFLIGHT-004` 保持
  `REVIEW_READY` 排队，不并发启动第二个 Reviewer。
- 本轮 CORE、MEDIA、PROTOTYPE 的 review digest 均为空，CORE Reviewer 仍有有效 working lease。
  `PROTOTYPE-GOLDEN-005@069ace1` 已核验提交推送且工作树干净，纠正契约头为 `REVIEW_READY`；由于它
  直接解除 M1 主链的 WEB blocker，Reviewer 释放后先审 PROTOTYPE，再审 MEDIA，期间不伪造并行审核。
- `CORE-RUNTIME-006@eb1a248` 独立评审提交 `33544e1` 结论为 `CHANGES_REQUESTED`：全量 456 passed、
  0 skipped 和 smoke 通过，但正常停止后同一端口不能立即复用。CEO 已记录有界 attempt 3 lifecycle/
  same-port test 范围；本轮按纠正优先级异步派发 attempt 3，沿用 `gpt-5.6-terra + medium`，不等待门禁。
  Reviewer WIP 仍由关键路径 `PROTOTYPE-GOLDEN-005` 占用，MEDIA 继续排队且不重复启动审核。
- `CORE-RUNTIME-006` attempt 3 实现 `706ab2e` 与报告交付 `de57fab` 已提交推送，CORE 分支干净且与
  远端一致；本轮仅记录 `REVIEW_READY` handoff。PROTOTYPE 独立审核仍有有效租约，CORE 与 MEDIA 均
  保持排队，不并发启动其他 Reviewer，也不提前批准后续工作。
- `PROTOTYPE-GOLDEN-005@069ace1` 独立评审提交 `7f4aaab` 结论为 `CHANGES_REQUESTED`：连续 capture
  会因动画相位改变 PNG hash，且默认脚本会静默改写 manifest。CEO 记录仅限 capture/golden/manifest/
  报告的 deterministic attempt 2；本轮按纠正优先级使用 `gpt-5.6-terra + medium` 异步派发，不等待
  Worker 门禁。`WEB-PARITY-004` blocker 保持；Reviewer 槽仍服务 `CORE-RUNTIME-006` attempt 3，
  MEDIA 继续排队。
- `CORE-RUNTIME-006@de57fab` attempt 3 独立评审提交 `95ac14a` 结论为 `APPROVED`：全量 457 passed、
  0 skipped，同端口两轮真实冷启动均正常退出并立即可 bind，且无残留进程。CEO 据此批准本任务；这不
  代表用户验收、发布或合并批准。CORE 当前无其他活动任务，按动态团队约定回收当前注册席位，历史保留。
- Worker 调度已统一整改：WEB、MEDIA、PROTOTYPE 及后续动态角色全部改用 `codex_exec` systemd wrapper；
  dispatcher 不写 runtime，只有真实 wrapper 启动后写 working，正常/异常退出分别写 review/blocked，同
  Owner WIP=1。CEO/PM 禁止再创建 orchestrator Worker 或预写 Agent 状态。
- `PROTOTYPE-GOLDEN-005@b4287d9` attempt 2 独立评审提交 `2dd4e99` 结论为 `APPROVED`：连续复验五张
  golden 与 manifest 字节稳定、默认 fail closed、显式 `--update` 才更新，且无 `web-v2`/视觉源码越界。
  CEO 据此批准并解除 WEB golden blocker，立即派发 `WEB-PARITY-004` attempt 2；不构成用户验收或发布批准。
- PROTOTYPE 唯一任务已批准且 WEB blocker 已解除，CEO 已按动态角色规则回收其当前注册和瞬时 runtime；
  历史任务、golden、报告与审核保留，后续确有新原型任务时再按适中能力重新注册。
- `PROTOTYPE-GOLDEN-005` attempt 2 实现 `7db041b` 与报告交付 `b4287d9` 已提交推送且分支干净；本轮
  仅登记 `REVIEW_READY`，不解除 WEB blocker。`MEDIA-PREFLIGHT-004@8532302` 独立评审提交 `a8a4aca`
  结论为 `CHANGES_REQUESTED`：缺少 controlled 4xx 证据，且全量 pytest 未能在评审中复现正常退出；
  CEO 记录有界 attempt 2，但本轮不派发，`MEDIA-E2E-003` 保持阻塞。
- `MEDIA-PREFLIGHT-004` attempt 2 已按纠正优先级异步派发，沿用 `gpt-5.6-terra + medium`；提交
  tracked `DISPATCHED` 后仅调用 supervised dispatcher，由 wrapper 独占发布 Worker runtime。PM 不等待
  长门禁，`MEDIA-E2E-003` 继续阻塞。
- `MEDIA-PREFLIGHT-004@4610cbb` 已补齐 controlled 4xx 且 focused/Skills 门禁通过，但注册 Worker 的
  全量 pytest 再次在 180 秒以 124 结束；交付报告明确为 `BLOCKED`，不能按 record-review-ready 标签
  伪记通过。超时位于 `test_inputs_and_start_boundary` 且超出 MEDIA 允许面，后续需独立 runtime 诊断；
  `MEDIA-E2E-003` 继续阻塞。
- `WEB-PARITY-004@cdda872` attempt 2 独立评审提交 `de37fe1` 结论为 `CHANGES_REQUESTED`：五组视觉
  证据与工程门禁均通过，唯一缺口是 verifier 源码新增 `/projects` 字面量触发 forbidden scan。CEO 记录
  仅移除 verifier legacy 引用的 bounded attempt 3；本轮提交 `DISPATCHED` 后仅调用 supervised Worker
  dispatcher，沿用 `gpt-5.6-luna + medium`，不等待门禁。`WEB-WO-003` 不得越过。
- `WEB-PARITY-004` attempt 3 实现 `9a6ec6c` 与报告交付 `9db741f` 已提交推送，分支无 tracked 脏改；
  legacy `record-review-ready` 事件按最新五泳道约定登记为 `TEST_READY`，等待 WEB_TESTER 独立验证。
  PM 不运行长门禁、不预标 Tester，`WEB-WO-003` 继续等待。
- 当前队列只服务 M1 人工 Skills 闭环：正式 WebUI Task 输入 → 人工可读 Work Order → Codex 按
  task_id/run_id 和持久化输入逐阶段执行 → Codex imagegen 图片 gate → 可播放 MP4。M1 不实现
  auto/selective 编排；完成后进入 `USER_ACCEPTANCE` 并停止自动新增/派发开发任务。
- `WEB-PARITY-004@9db741f` 的 TESTER_WEB 结果为 `PASS`：精确交付 checkout 上的 build、349 tests、
  真实 API、五组浏览器 parity、diff 与 forbidden-pattern gates 均通过，且报告记录十张截图的目视核验与
  临时进程清理。PM 据此批准任务。M1 仍需要既有后续任务 `WEB-WO-003`；本 review-only 事件不派发它，
  留待独立 PM dispatch 事件处理。
- `WEB-WO-003` 的前置 `CORE-WO-003` 与同 Owner P0 `WEB-PARITY-004` 均已批准；PM 固定 base
  `9db741f` 并置为 `DISPATCHED`，交由受监督 Worker dispatcher 异步执行。该任务直接服务 M1 的
  人工可读 Work Order 面，完成后仍需 Tester 证据与 PM 决策；暂不生成后续任务。
- `WEB-WO-003` 收到 `recover-stale(runtime_missing)` 时仍为 `DISPATCHED`，且没有 Worker handoff
  或报告。PM 已确认当前 checkout 与命令路径均无法取得 `dispatch_cli_agent.sh`，因此不能合规唤醒
  受监督 Worker；任务改为 `BLOCKED`，等待恢复该 dispatcher。未创建 orchestrator Worker、未手写
  runtime，也未派发后续任务。
- `MEDIA-PREFLIGHT-004@4610cbb` 的 `resolve-blocker` 事件已建立并派发独立 P0
  `CORE-RUNTIME-007`：仅诊断/修复全量 pytest 在 `test_inputs_and_start_boundary` 的共享 runtime
  生命周期边界，禁止改动 media preflight 语义或将 watchdog 当成功。该任务使用
  `gpt-5.6-terra + medium`；在 Tester 证据和 PM 决策前，`MEDIA-PREFLIGHT-004` 与
  `MEDIA-E2E-003` 均保持 `BLOCKED`，不生成其他后续工作。
- `CORE-RUNTIME-007` 收到 `recover-stale(runtime_idle)` 时仍为 `DISPATCHED`，没有 Worker
  handoff 或 Tester 报告。提交重派记录后，PM 已确认仓库与命令路径均不存在
  `dispatch_cli_agent.sh`，因而无法合规调用受监督 dispatcher；任务改为 `BLOCKED`，等待该外部
  调度依赖恢复。未写入 Worker runtime、未运行门禁、未作 PM 决策，且不生成后续任务。
- `CORE-RUNTIME-007` 的本次 `resolve-blocker` 事件以任务契约中的外部依赖记录结案：恢复
  `dispatch_cli_agent.sh` 及其 `run_worker_agent.sh` 受监督 wrapper 是唯一恢复条件；在该条件满足前，
  不创建重复诊断任务、不派发 WORKER_CORE，也不改变 `MEDIA-PREFLIGHT-004` 或 `MEDIA-E2E-003` 的
  `BLOCKED` 状态。
- `CORE-RUNTIME-007` 再次收到 `resolve-blocker` 事件；PM 复核其任务契约的外部依赖记录后确认恢复条件
  未变：必须先恢复 `dispatch_cli_agent.sh` 及 `run_worker_agent.sh` 的受监督 wrapper。该依赖恢复前不创建
  重复诊断任务、不派发 `WORKER_CORE`，并保持 `CORE-RUNTIME-007`、`MEDIA-PREFLIGHT-004` 与
  `MEDIA-E2E-003` 为 `BLOCKED`。
- `CORE-RUNTIME-007` 收到 `resolve-blocker` 事件 `2ce3d5b0acb9c19960489ed4a6ca5a65b718604893376778608dc934cee127ba`；
  PM 依据任务契约中的外部依赖记录确认唯一恢复动作仍是恢复 `dispatch_cli_agent.sh` 与
  `run_worker_agent.sh` 的受监督 wrapper。依赖未恢复前不创建重复任务、不派发 `WORKER_CORE`，并保持
  `CORE-RUNTIME-007`、`MEDIA-PREFLIGHT-004` 与 `MEDIA-E2E-003` 为 `BLOCKED`。
- `WEB-WO-003@7adc8f5` 的 `TESTER_WEB` 结果为 `FAIL`：构建、351 项 Web 测试、50 项 contract-checker
  测试、focused Work Order、真实后端 API、forbidden-pattern 与 whitespace gates 均通过；但契约要求的
  浏览器 Task-flow 证据已记录 POST `/tasks` 超时和 `Failed to fetch`，且无浏览器通过证据。PM 判定
  `CHANGES_REQUESTED`。M1 仍需要该既有任务的有界 attempt 2 来修复真实浏览器流程并交付证据；不创建或
  派发任何后续任务，`MEDIA-E2E-003` 继续等待 `WEB-WO-003=APPROVED` 与 `MEDIA-PREFLIGHT-004=APPROVED`。
- `WEB-WO-003` 已按该有界返工决定置为 `DISPATCHED` 并交由 `WORKER_WEB` 的受监督 dispatcher 异步执行；
  attempt 2 仅修复真实浏览器 Task 创建流程并提交通过证据，沿用默认适中配置。当前 Owner 仍有此非终态任务，
  不生成或派发后续 WEB 工作；`MEDIA-E2E-003` 继续等待既有依赖。
- 对 `CORE-RUNTIME-007` 的同一 `resolve-blocker` 签名作幂等 PM 决定：任务契约中的外部依赖记录仍完整且
  可执行，须恢复 `dispatch_cli_agent.sh` 与 `run_worker_agent.sh` 受监督 wrapper 后才可原样重派；结论为
  `BLOCKED`，阶段目标当前不需要新任务，未派发 `WORKER_CORE`。
- `CORE-RUNTIME-007` 的 `resolve-blocker` 事件 `2ce3d5b0acb9c19960489ed4a6ca5a65b718604893376778608dc934cee127ba`
  再次作幂等 PM 决定：外部 dispatcher/wrapper 依赖仍未恢复，维持 `BLOCKED`；M1 当前不需要下一任务，未派发
  `WORKER_CORE`，`MEDIA-PREFLIGHT-004` 与 `MEDIA-E2E-003` 继续保持 `BLOCKED`。
- `CORE-RUNTIME-007` 的 `pm-review` 事件 `96d0dedbc4e7fd105e143c6095ed14bde3ddc38b7627d371c7ab32a9bdf8abc1`：未找到
  bound Tester report，且任务契约记录的 dispatcher/wrapper 外部依赖未恢复，因此 PM 决定为 `BLOCKED`。M1 当前
  不需要下一任务；未派发 `WORKER_CORE`，`MEDIA-PREFLIGHT-004` 与 `MEDIA-E2E-003` 继续保持 `BLOCKED`。

## 队列规则

标准状态机：`READY → WORKING → TEST_READY → TESTING → PM_DECISION → APPROVED`；失败验证由 PM
判为 `CHANGES_REQUESTED` 后返回 `READY`，外部依赖不足进入 `BLOCKED`。旧状态只为历史兼容，不用于新任务。

1. 优先级按任务契约中的 `Priority`，同优先级按依赖拓扑排序；
2. `BACKLOG` 只有在全部 `Depends on` 均为 `APPROVED` 后才能由 PM 改成 `READY`；
3. Worker 同一时间只领取一项 `DISPATCHED` 任务；返工沿用原任务并递增 attempt；
4. Tester 提交验证证据后置为 `PM_DECISION`；PM 只核对证据、写最终状态，并在同一轮决定是否创建或派发下一个任务；
5. Dashboard 心跳只表示有限租约内的真实活动，不表示 Agent 能跨会话自行运行。
6. 每个 Owner 的 WIP 上限为 1；BACKLOG 不设硬长度上限，按真实里程碑风险滚动维护跨角色后续链；
7. 不再设置 Reviewer；WEB/CORE 使用固定领域 Tester，其他领域 Tester 按需生成并超时回收；
8. CEO 每个有事件的调度周期先读取 `docs/agents/agreements.md` 最新 `ACTIVE` 时间线节点；用户范围变更只追加新节点，历史不得删除。
8. M1 期间只派发里程碑契约列出的直接任务；其他想法仅可记为 `POST-M1`，不得占用当前 Worker。
