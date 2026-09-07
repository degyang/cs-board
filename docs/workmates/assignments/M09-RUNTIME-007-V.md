# M09-RUNTIME-007-V — independent restart-readiness verification

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`），验证冻结主集成区 `/mnt/d/workstation/projects/cs-board`。只允许新写本任务回执和新 `.workmates-evidence` JSON；不得修改实现、测试、服务配置、Secrets、pointer、frozen outputs 或主看板，不提交/合并/push，不创建 Task、render 或 provider generation。

## 冻结目标

- `backend/mountain_server.py` `85f65b479e0e3b3372aacac2dcfc1a8d8c4a0ed8e9d70ea9ff394499a5dac078`
- `csboard/adapters/filesystem/service_registry.py` `fea4c1d4f1af2bc01f869547f6f21bb75eddc9fcc2289c925211e69cb68bb863`
- `scripts/run_mountain_backend.py` `6f5473666ae9f8527e934d83fa1135bde6d1896bd109a6a7f3a00b3c540841d3`
- `tests/test_m09_runtime_007.py` `1f6063457f806d92a2e0a1baa480d008997f16e0fa510815a52b37fb86111f3e`
- PM restart receipt `docs/workmates/receipts/M09-RUNTIME-007-PM.md` and standard
  Workmates evidence `.workmates-evidence/M09-RUNTIME-007-PM.json`
- 当前 runtime `%26` / PID `292980`；5182 PID `124360`

## 验证标准

1. pre/post hashes 完全一致；审查生产启动 opt-in、测试默认 offline、每能力确定性单一候选、root cache 真分区及失败 fail closed。
2. 独立运行 runtime-007/service-registry/capability/activation 相关套件；可仅排除既有 `browser_version_uses_renderer_resolver`，必须如实记录。
3. 核对 10-service topology 回归证明 startup cache shape 与 accepted four-service fingerprint 相同；不得仅凭测试数量判断。
4. 核对 PM 真实证据：第一次过宽探测 FAIL 被保留，修正版重启 zero manual POST、5.253s、4/4、service_count=10、supported=true。
5. 当前只读实时查询 8000 health/capabilities 与 8000/5182 create-options，必须仍全部开放、无错误 reason；确认 PID/pane。
6. `git diff --check` 针对冻结文件 PASS；运行 `./scripts/workmates verify --role verification --evidence <本轮新 JSON>`。
7. 写 `docs/workmates/receipts/M09-RUNTIME-007-V.md`，给 PASS/FAIL/BLOCKED、criterion mapping、命令/exit/数量、证据路径和 pre/post hashes；完成后固定客户端保持 idle。

任何 hash 漂移、当前 capability 关闭、测试失败或证据与现场不一致，停止并给 FAIL/BLOCKED，不自行修复。
