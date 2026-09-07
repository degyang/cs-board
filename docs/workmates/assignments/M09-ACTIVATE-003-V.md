# M09-ACTIVATE-003-V — independent verification of Codeplan capability activation

状态：assigned

Owner：`verification`（Claude Code / `mimo-v2.5-pro` / medium）；只读验证集成区 `/mnt/d/workstation/projects/cs-board`。PM 负责指针签发、看板和最终接受。

你不是代码库中的唯一执行者。不得修改实现、既有断言、服务配置、Secrets、frozen outputs、activation pointer 或共享看板；只允许写本任务的新回执与新的验证证据。不得执行真实生成、render 或 task create。

## 目标

1. 对照 `docs/workmates/assignments/M09-ACTIVATE-003.md` 独立审查并运行 focused tests，验证显式 `config.capabilities` 多能力语义、secondary capability 投影、ProviderFactory 文本 adapter、infographic 手工图片边界以及 whiteboard 回归。
2. 只读核对 8000：`MiMo-TTS-Codeplan` revision 3 声明 audio+text 且必要 probe available；infographic bootstrap 不再要求 image service；16 provider voice records / 8 个去重预置音色未回退。不得输出 secret 或完整用户配置。
3. 审查 activation pointer 的 toolchain 绑定。已接受 V3 回执与 backend pointer 模板记录 browser `Google Chrome for Testing 152.0.7977.54`，当前 `video_renderer/browser-resolver.mjs` 现场解析为 `152.0.7977.75`。明确判断：是否可直接用当前版本签发指针，还是必须因“当前 renderer/toolchain 与受验版本匹配”要求先重新冻结验证；不得通过改写 pointer 绕过漂移。
4. 从集成根运行 `./scripts/workmates verify --role verification --evidence <本轮新的本地证据路径>`。

## 验收与回执

- 回执：`docs/workmates/receipts/M09-ACTIVATE-003-V.md`。
- 列出逐条标准、命令、exit code、测试数量、目标文件 SHA-256、真实 API 安全观察和未验证范围。
- Verdict 使用 `PASS / FAIL / BLOCKED`。M09-003 代码可以 PASS，同时 activation pointer 因独立工具链漂移保持 BLOCKED；必须分别表述，禁止把局部 PASS 写成公开激活完成。
- 完成写回执后退出；不等待新任务，不停留空闲 shell。
