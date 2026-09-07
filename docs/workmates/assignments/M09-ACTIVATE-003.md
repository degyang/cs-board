# M09-ACTIVATE-003 — Codeplan text capability and manual Codex illustration boundary

状态：assigned

Owner：`backend`（独立工作区 `/mnt/d/Workstation/Projects/cs-board-worktrees/backend`）；PM 集成，verification 独立复验。

你不是代码库中的唯一执行者。保留已有 M09、probe timeout、资产和语音改动，不回滚他人修改，不改集成区看板，不提交、合并或推送。

## 用户确认的产品事实

2026-09-07 用户明确：

- 文本 LLM 已由 `MiMo-TTS-Codeplan` 替代；当前集成服务 `model-service-268dbca4` revision 3，安全配置中 `config.capabilities = ["audio_generation", "text_generation"]`，secret 已配置且真实 probe available。
- 图片生成是由 Codex 人工/外部执行，不存在应被自动 probe 的图片 API 服务。已有工单契约将 `generate-illustrations` 定义为 external/manual output，不由 API 触发真实图片生成。

当前 activation bootstrap 错误地只读服务的单值 `capability`，因此忽略 Codeplan 的显式多能力声明；同时又将 `image_generation` 当作自动 service 硬门禁。

## 目标

1. 将服务的主 `capability` 与安全 `config.capabilities` 合并为明确能力声明；仅接受受控字符串列表，去重，不将任意 config 解释为能力。
2. `CapabilityService` 和 `ServiceResolver` 对多能力服务使用同一语义。解析 secondary `text_generation` 时，返回的 `ServiceDefinition.capability` 必须投影为被请求能力，使 `ProviderFactory.create_adapter()` 构造文本 adapter，不误构造 TTS adapter。
3. infographic bootstrap 不再要求自动 `image_generation` service；图片责任只由已有 `external-stage-gate` / accepted V3 operator evidence 表达。不得把 external gate 常量改 true，不得绕过 pointer。
4. 保持 whiteboard 既有自动 image service 语义不变；改动只收窄 infographic activation bootstrap。

## 范围

- 可修改：`csboard/application/capabilities.py`、`csboard/application/service_resolver.py`、必要的共享小型 capability helper、直接测试，以及 backend 回执 `docs/workmates/receipts/M09-ACTIVATE-003.md`。
- 可补充直接相关 Mountain 文档，明确图片是 Codex external/manual gate；不重写已验收 V3 结论。
- 禁止修改 `settings/services/*.json`、Secrets、pointer、frozen outputs、frontend 或 board；不执行真实 provider 请求、renderer 或任务创建。

## 验收

1. 新回归证明：主能力为 `audio_generation`、`config.capabilities` 显式包含 `text_generation` 的 configured+cached-probe-ready 服务，同时满足 capability bootstrap 文本项与 resolver 文本选择，并构造文本 adapter。
2. 无 image service 但 external gate true 时，infographic bootstrap 的图片边界不失败；external gate false 仍 fail closed。whiteboard 仍因缺 image service 不可用。
3. 非列表、非字符串、空值或重复 secondary capabilities 安全处理；未声明文本能力的 TTS 服务不能偷偷充当 LLM。
4. 运行 service resolver/capability/activation/create-options/task creation/provider factory 的 focused tests、scoped diff check，必要时完整 serial backend gate。
5. 回执列出变更文件、hash、命令、exit code、数量和 `READY_FOR_VERIFY / CHANGES_REQUIRED`。

停止条件：若 Codeplan 的现有显式配置无法在不读取 secret 值、不调用真实生成、不修改用户服务的前提下形成一致能力投影，写 `CHANGES_REQUIRED` 后停止。
