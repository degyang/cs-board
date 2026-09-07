# M09-ACTIVATE-001-V — integrated activation verification

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`，只读验证当前集成区）；PM 负责消费结论和看板。

你不是代码库中的唯一执行者。不得修改产品实现、既有测试、服务定义、Secrets、frozen V3 输出、activation pointer 或共享看板。只可写本任务指定的新证据和回执。

## 冻结目标

- 集成区：`/mnt/d/workstation/projects/cs-board`，当前 dirty 工作树；不得用 HEAD 代替目标状态。
- 原任务：`docs/workmates/assignments/M09-ACTIVATE-001.md`；修正任务：`docs/workmates/assignments/M09-ACTIVATE-001-R.md`；实现回执：`docs/workmates/receipts/M09-ACTIVATE-001.md`。
- V3 回执 SHA-256：`8f5f5a675275791d3fc34fec4cccf402b7ff5ac5f50f89c9c50135526920991e`。
- 接受 task/run/index/manifest/MP4 SHA-256 依次为：`f02c10de8ca62ae458ec2f754fd5c4969264e515243c0ff85dc03465d32ba044`、`952437ed60d68c6eba23cd9b5c32ed5b6d4b4a7ff89d373de65b1940f04ae91e`、`47872bed9097e32271cd3a8ca6bd253e157f3bdc49b9c948b06513a39e60d188`、`75e30cccc87b8b802710d238e28d56f4430e28a12ca8bcf0d7edbeca66c37f15`、`18e95359ac600ebdf746b20702e42af5e0c5b88eea66a5e5b763591ac35d641a`。
- 目标实现文件的最终 hash 以实现回执所列 14 项为准，开始和结束均复核。
- 集成服务：8000 PID `124308`，5182 npm parent PID `124309` / listener child PID `124360`。只观察，不重启或停止。

## PM 已观察但不得替代独立结论

- `/api/v1/health` 为 ok，9 个服务；MiMo-TTS 与 MiMo-TTS-Codeplan 的 secret status 均 configured；`/api/v1/voice-profiles` 返回 16 个 provider records、8 个去重名称。
- 一次真实轻量 probe 后：local-ffmpeg/local-whisper/whiteboard-renderer available；local-indextts `PROBE_ERROR`；两套 MiMo `OPENAI_PROBE_ERROR`；mock/text/image 服务缺 secret。
- capability 与 create-options 仍关闭 dynamic infographic，首因 `READINESS_FAILED`；当前集成区不存在 `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json`。
- 需特别审查潜在自引用：生产 composition 的 `external_stage_gate` 调用 `accepted_v3_gate(root)`，后者要求 pointer；pointer 的 `service_fingerprint` 又包含含 external-stage-gate 的 bootstrap diagnostics。判定是否存在无法签发稳定 pointer 的循环绑定，并以代码与受控临时夹具证明，不得在规范路径创建 pointer。

## 验证要求

1. 逐条映射原任务和修正任务；复核旧常量语义、CLI `webapp.*` guard、unmocked 三投影测试、完整 ffprobe、browser resolver、服务身份/配置指纹和自包含 fixture。
2. 在不触碰规范 outputs 的前提下运行 focused activation/capability/create-options/task/API/CLI tests；运行 scoped `git diff --check`。不得执行 renderer 或创建规范 task/run。
3. 对 8000 真实读取 health、services、voice-profiles、capabilities、tasks/create-options；只记录安全状态，不记录秘密值。若公开入口未打开，明确区分实现 FAIL、环境 BLOCKED 或 MISSING EVIDENCE。
4. 只读检查 5182 新建任务入口是否与相同 API 投影一致；不得提交任务。截图仅在有助于证明入口状态时保存到 `/tmp`。
5. 从集成根运行 `./scripts/workmates verify --role verification --evidence /tmp/m09-activate-001-v-evidence-<新时间戳>.json`，路径必须全新。
6. 写 `docs/workmates/receipts/M09-ACTIVATE-001-V.md`，给出 `PASS / FAIL / MISSING EVIDENCE / BLOCKED`。PASS 必须同时满足实现契约与真实集成正向开放；fixture PASS 不能替代真实 8000/5182。

停止条件：发现需修改实现、补凭据、改服务配置、写 operator pointer 或重新启动服务时，不执行该动作，记录最窄下一责任人后停止。
