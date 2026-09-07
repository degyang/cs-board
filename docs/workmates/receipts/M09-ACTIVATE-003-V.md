# M09-ACTIVATE-003-V — verification receipt

状态：completed
Verdict：**M09-003 代码 PASS / Activation pointer BLOCKED**

## Criterion-to-evidence

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | `model-service-268dbca4` revision 3 声明 `audio_generation` + `config.capabilities` 含 `text_generation` | PASS | `GET /api/v1/services` via backend health (10 services); local file `settings/services/model-service-268dbca4.json` revision=3, capability=audio_generation, config.capabilities=[audio_generation, text_generation] |
| 2 | `declared_capabilities` 返回去重元组 `('audio_generation', 'text_generation')` | PASS | 运行时验证：`supports_capability(svc, 'text_generation') == True` |
| 3 | `ServiceResolver.resolve('text_generation')` 投影 `capability=text_generation`，`ProviderFactory.create_adapter()` 构造 `OpenAITextAdapter` | PASS | 运行时验证：`replace(service, capability='text_generation')` → `capability == 'text_generation'`；`create_adapter` 中 `openai_compatible` + `text_generation` 分支命中 |
| 4 | infographic bootstrap 的 `generate-illustrations` 阶段无自动 capability 需求 | PASS | `INFOGRAPHIC_STAGE_REQUIREMENTS['generate-illustrations'] == ()` |
| 5 | whiteboard 的 `generate-illustrations` 仍要求 `image_generation`（回归） | PASS | `WHITEBOARD_STAGE_REQUIREMENTS['generate-illustrations'] == ('image_generation',)` |
| 6 | 非列表/非字符串/空值/重复 secondary capabilities 安全处理 | PASS | 运行时验证：string→ignored, empty→filtered, non-string→filtered, duplicates→removed, TTS-only→不支持 text_generation |
| 7 | 16 provider voice records / 8 unique preset voices 未回退 | PASS | `GET /api/v1/voice-profiles` → total=16, unique=8, names=[Chloe, Dean, Mia, Milo, 冰糖, 白桦, 苏打, 茉莉] |
| 8 | 12-file focused suite 全通过 | PASS | 149 passed, 0 failed, exit 0 |
| 9 | 完整 backend test gate | **FAIL** | 4 shards: 136+235+334+212=917 passed, 1+8+3+0=12 failed, exit 1, failed_shards=[0,1,2] |
| 10 | `./scripts/workmates verify` 工具门禁 | PASS | exit 0, status PASS |
| 11 | activation pointer 文件存在且有效 | **BLOCKED** | `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` 不存在 |
| 12 | 浏览器 renderer/toolchain 与 pointer 受验版本匹配 | **BLOCKED** | 当前 `152.0.7977.75` vs V3 收据记录 `152.0.7977.54`；minor patch 漂移 + 无 pointer 可比较 |

## 变更文件 SHA-256

| File | SHA-256 |
|------|---------|
| `csboard/application/capabilities.py` | `ebdb2ea3…260065` |
| `csboard/application/service_resolver.py` | `f6e0afd…63a9` |
| `csboard/application/service_capabilities.py` | `4395576…aa28` |
| `csboard/application/activation.py` | `34bffe0…6b6995` |
| `csboard/adapters/provider_factory.py` | `b553f7b…68dc21` |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `pytest -q <12 focused test files>` | 0 — 149 passed |
| `.venv/bin/python scripts/run_backend_test_gate.py` | 1 — 917 passed, 12 failed |
| `node --input-type=module …resolveBrowserExecutable…` | 0 — `Google Chrome for Testing 152.0.7977.75` |
| `curl http://127.0.0.1:8000/api/v1/voice-profiles` | 0 — 16 records, 8 unique |
| `./scripts/workmates verify --role verification --evidence <path>` | 0 — PASS |

## Evidence paths

- 详细证据：`/tmp/m09-activate-003-v-evidence-1788753744.json`
- Workmates 工具证据：`/tmp/m09-activate-003-v-workmates-verify-1788753854.json`

## 分离结论

**M09-003 代码实现 PASS**：多能力语义、secondary capability 投影、ProviderFactory 文本 adapter、infographic 手工图片边界、whiteboard 回归、unsafe capability 处理、语音预置数量——全部验证通过。

**Activation pointer BLOCKED**（两个独立原因，任一即阻塞）：
1. `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` 不存在，无法执行 activation verification。
2. 即使 pointer 存在，当前 renderer browser `152.0.7977.75` 与 V3 收据记录的 `152.0.7977.54` 存在 minor patch 漂移，`ActivationVerifier._toolchain_ok` 会因 `expected[key] != value` 返回 False。必须重新冻结验证后才能签发 pointer。

**Backend gate FAIL**：12 failures（shard 0: 1, shard 1: 8, shard 2: 3）。非 capability/activation 范围内，但门禁本身 exit 1，如实记录。

## 未验证范围

- 真实 API 生成调用（任务禁止）
- 视觉/视频质量验收（用户保留）
- PM 阶段接受（PM 保留）
