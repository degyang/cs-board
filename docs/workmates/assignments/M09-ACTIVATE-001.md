# M09-ACTIVATE-001 — evidence-bound dynamic-infographic create-option activation

状态：assigned

Owner：`backend`（独立工作区 `/mnt/d/Workstation/Projects/cs-board-worktrees/backend`，仅负责本任务列出的后端/共享内核文件与测试）；独立验证：`verification`；PM 负责集成服务、看板与最终开放决定。

你不是代码库中的唯一执行者。保留并适配现有跨批次改动，不回滚他人修改，不修改集成区看板，不提交、合并或推送。

## 已满足前置门禁

- PM 已消费 `docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md` 的独立 `PASS`。
- V3 回执 SHA-256 由执行者开始时现场记录；其新鲜 Workmates evidence 为 `/tmp/m09-v3-corridor-verify-001-evidence-1788742080.json`，exit `0` / `PASS`。
- 只允许绑定任务 `task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f`、接受运行 `run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63`、MP4 SHA-256 `18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a`、artifact index SHA-256 `47872bed9097e32271cd3a8ca6bd253e157f3bdc49b9c948b06513a39e60d188`、render manifest SHA-256 `75e30cccc87b8b802710d238e28d56f4430e28a12ca8bcf0d7edbeca66c37f15`。
- 规范实现与输出仍分别位于集成区和 backend worktree 的既有 output；开始前重算上述绑定。任一不一致立即 fail closed 并停止，不生成新 render。

## 目标

把当前 V3 已接受 corridor evidence 接入现有 fail-closed activation verifier，使 capability API 与 `tasks/create-options` 只有在以下条件每次现场复核均成立时，才公开 `infographic-remotion + preset`：V3 明确 PASS、任务/运行身份一致、Task/Run/Stage 状态真实、MP4/ffprobe/manifest/index 及全部引用哈希有效、当前 renderer/toolchain 与受验版本匹配、当前 bootstrap/service prerequisites ready。不得把常量 `supported`/`available` 直接改成 true，不得添加测试或 CLI bypass。

## 范围

- 可修改：`csboard/application/activation.py`、`csboard/application/capabilities.py`、必要的 composition/API glue，以及直接覆盖本契约的后端测试。
- 可写：backend worktree 内一个新的 operator-owned activation pointer/evidence 文档；内容只允许相对引用、任务/运行/产物哈希、V3 回执哈希与安全版本指纹，不写秘密、真实素材或环境完整转储。
- 可写回执：`docs/workmates/receipts/M09-ACTIVATE-001.md`（backend worktree）。
- 禁止：修改 frozen renderer/corridor 产物来迎合校验；创建新 render/task/run；修改既有断言掩盖失败；启动 8000/5182；修改 frontend、assignment、board；提交/合并/推送。

## 必须 fail closed

- pointer/evidence/receipt 缺失、不可读、过期、未来时间、非 PASS 或身份/哈希不一致；
- task active run 不等于接受 run，或 Task/Run/`render-visuals` 非 succeeded；
- MP4 不是真实 ffprobe-valid H.264 1920×1080，或 hash/size/probe/manifest/index 任一不一致；
- renderer、lockfile、Node/Remotion/browser/FFmpeg/ffprobe 或安全 service fingerprint 改变；
- bootstrap/service prerequisite 不 ready；
- 任一异常。公开诊断必须脱敏且使用稳定 reason code。

## 验收

1. 正向 fixture/现场受控检查证明 capability snapshot 与 `create_options()` 同时公开该组合，且 pipeline id/engine/visual source 正确。
2. 至少覆盖以上 fail-closed 矩阵；失败时 capability 与 create-options 同时关闭，task create 仍以稳定 `CAPABILITY_NOT_AVAILABLE` 拒绝。
3. 证明“新建任务”入口消费的是同一 capability projection；仅创建隔离临时夹具中的 task，不在规范 outputs 写新 task/run，不执行阶段。
4. 运行与改动相称的 focused tests（至少 activation、capability、create-options、task creation、routing/e2e）、完整后端门禁 `.venv/bin/python scripts/run_backend_test_gate.py`、renderer test/typecheck（若改到相关契约）、scoped `git diff --check`。
5. 从集成根运行 `./scripts/workmates verify --role backend --evidence <全新不存在的本地路径>`；若角色入口不接受 backend，记录原始结果并由 PM/verification 补指定角色门禁，不伪造 PASS。
6. 回执列出修改文件、前后 hash、pointer/evidence schema 与绑定值、所有命令/exit code、已知未验证范围和明确 verdict。不要把测试通过等同于 8000/5182 真实 API/WebUI 验收；该部分由 PM 集成后执行并交 verification 独立复验。

## 停止条件

任何绑定失效、需要真实秘密/素材、需要改变 frozen V3 产物、需要扩大到 frontend 或无法在不降低 fail-closed 约束下激活时，保持公开关闭，写 `BLOCKED`/`CHANGES_REQUIRED` 回执并停止。
