# M09-ACTIVATE-002-V — verification receipt

Verdict: **PASS**

## Scope verified

Worker 收据声明：`_get_probe_timeout()` 从仅绑定 connect/read 改为显式绑定全部四维 httpx.Timeout（connect=2.0, read=5.0, write=5.0, pool=2.0）。新增两项离线回归测试。

独立复核确认：
- diff 仅涉及 `service_registry.py`（timeout 构造）和 `test_service_registry.py`（2 个新测试），无其他文件变更。
- 四维值均为有限正数，无 `None`、无 `math.inf`、无负数。
- 新测试覆盖：① 四维断言 + 有限正数断言；② Mock HTTP 200 响应成功通过 probe，`error_code` 非 `PROBE_ERROR`。
- 未触及服务定义、Secrets、activation pointer、capability policy、渲染器、前端或看板。

## Frozen state match

| 文件 | 任务声明 SHA-256 | 实际 SHA-256 | 匹配 |
| --- | --- | --- | --- |
| `csboard/adapters/filesystem/service_registry.py` | `0ed986c9…` | `0ed986c938e53fef78d4cf43491bd32de9c982c2897043c8989f5c7e221739b2` | ✓ |
| `tests/test_service_registry.py` | `5f662827…` | `5f662827d220fa1cf0280403fb8e5eee10a8e9b84085112d7355fe5265ef54a8` | ✓ |
| scoped diff | `883e7d04…` | `883e7d047a013ecbd817691e70cf670e5cf26c3a42717026207424c61ab1adf5` | ✓ |

## Checks executed

| 命令 | 结果 |
| --- | --- |
| `pytest tests/test_service_registry.py tests/test_mountain_service_api.py tests/test_capabilities_api.py` | exit 0; 50 passed, 1 warning |
| `git diff --check -- csboard/adapters/filesystem/service_registry.py tests/test_service_registry.py` | exit 0; 无 whitespace 错误 |
| `./scripts/workmates verify --role verification --evidence /tmp/m09-activate-002-v-evidence-*.json` | exit 0; PASS |

## Live backend read-only review (port8000, PID 132790)

**Health**: OK — task_repository, asset_repository, service_registry (9 services), secret_store (encrypted), storage (writable) 全部 ok。

**Services availability** (只读，未 POST probe):

| service_id | available | error_code | 备注 |
| --- | --- | --- | --- |
| local-ffmpeg | ✓ | — | |
| local-whisper | ✓ | — | |
| whiteboard-renderer | ✓ | — | |
| MiMo-TTS (model-service-d4d41011) | ✓ | — | latency 143ms，不再是 `OPENAI_PROBE_ERROR` |
| MiMo-TTS-Codeplan (model-service-268dbca4) | ✓ | — | latency 146ms，不再是 `OPENAI_PROBE_ERROR` |
| local-indextts | ✗ | `TTS_UNREACHABLE` | 符合预期：本地 TTS 服务未启动 |
| mock-llm | ✗ | `SECRET_NOT_CONFIGURED` | 预期：无 api_key |
| openai-compatible-text | ✗ | `SECRET_NOT_CONFIGURED` | 预期：无 api_key |
| openai-compatible-image | ✗ | `SECRET_NOT_CONFIGURED` | 预期：无 api_key |

**Capabilities**:
- `whiteboard` / `infographic-remotion` 均为 `supported: false`。
- `infographic-remotion` 根因：`SERVICE_SECRET_MISSING`（text_generation 和 image_generation 两个服务缺 api_key），非 timeout 修正引入。
- activation 仍被文本/图片 secret 阻断（`EVIDENCE_MISSING` + `READINESS_FAILED`）。

## 结论

**PASS** — timeout 修正可接受：四维显式绑定，有限正数，无网络回归，无错误掩盖。

**Activation 阻断事实**：infographic-remotion 能力仍为 `supported: false`，根因是 `openai-compatible-text` 和 `openai-compatible-image` 两个服务缺少 `api_key` secret。此为独立于本次 timeout 修正的已有阻断项。
