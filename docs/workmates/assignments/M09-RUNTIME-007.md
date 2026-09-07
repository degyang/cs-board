# M09-RUNTIME-007 — truthful probe readiness across backend restart

状态：assigned

Owner：`backend`，工作区 `/mnt/d/workstation/projects/cs-board-worktrees/backend`；PM 集成与真实重启；`verification` 独立复验。

你不是代码库中的唯一执行者。保留所有已有改动，不修改服务定义、Secrets、activation pointer、frozen outputs、frontend 或主看板，不提交/合并/push。

## 现场缺口

PM 将已接受代码集成后安全重启 8000。新进程健康且服务目录仍为 10，但进程内 `_probe_cache` 为空，capability 立即变为 `READINESS_FAILED` / `NOT_PROBED`。PM 必须手工 POST `local-ffmpeg`、`local-whisper`、`MiMo-TTS`、`MiMo-TTS-Codeplan` 四个 probe 后才恢复 `supported=true`。这使已接受入口依赖未记录的人工恢复步骤。

## 目标

1. 生产后端启动后自动执行真实、有限、可审计的 readiness probe，使 capability 无需人工 POST 即可恢复。
2. 只探测启用且与当前能力前置条件相关的候选服务；不得调用文本、图片、TTS 生成接口，不得创建 Task/render。
3. 每个 probe 沿用现有超时与脱敏错误；失败必须保留真实 unavailable/fail-closed，不允许复用无时间边界的历史成功或伪造 cache。
4. 启动不能因单个外部服务失败而崩溃；健康端点可用，capability 如实说明未就绪项。
5. 不污染不同 data root 的测试/进程状态；避免扩大现有全局 cache 的跨 root 风险。若该风险影响设计，必须在本任务内以最小方式隔离并加回归。
6. 为测试提供显式注入或关闭自动探测的边界，避免普通 `create_app(tmp_path)` 测试访问真实网络或变慢。

## 可修改范围

- `backend/mountain_server.py`
- `csboard/adapters/filesystem/service_registry.py`（仅当根隔离/安全 probe API 必需）
- `scripts/run_mountain_backend.py`（仅当需要明确生产启动开关）
- 直接相关新测试
- backend 回执 `docs/workmates/receipts/M09-RUNTIME-007.md`

如需越界，先停止并在回执给出 Contract Gap，不自行扩展。

## 验收

- 离线测试覆盖：启动自动探测相关候选；失败不崩溃且 fail closed；测试默认不碰真实网络；不同 roots 不共享 probe 成功。
- PM 集成后一次真实停止/启动 8000，不做任何手工 POST probe，等待有界启动窗口后 capability 自动回到 `supported=true`，8000/5182 create-options 均可用且无 reason，服务数仍为 10。
- focused tests 与 `git diff --check` PASS；回执列出 hashes、命令、exit、数量、设计边界和 `READY_FOR_VERIFY / CHANGES_REQUIRED`。
- 完成后固定客户端保持 idle。
