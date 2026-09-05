# M09-INFRA-BOOTSTRAP-003A-V — P3a Bootstrap 独立验证回执

结论：**FAIL**（fail-closed）。本验证未修改产品代码、规划、配置或测试；未执行 real render、真实任务创建、P6 evidence activation 或 submission。唯一写入为本回执。此 FAIL 不可作为 P4 前置的 PASS。

## 独立执行证据

在当前工作树复跑只读专项：

```text
.venv/bin/python -m pytest -q tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py tests/test_toolchain_resolver.py
16 passed, 1 warning in 3.52s
pytest_exit=0

git diff --check
diff_check_exit=0
```

专项通过仅证明已有的 service/cache projection、API/CLI 基础形状和独立 `ToolchainResolver` 单元测试未立即失败；不能替代 P3a 规定的完整 bootstrap contract。

## 七项核验

1. **FAIL — toolchain diagnostics 缺失。** `csboard/application/capabilities.py:_bootstrap_snapshot()` 只调用 `_bootstrap_service_checks()`，未读取或报告 Node、`video_renderer/render.mjs`、lockfile、锁定 Remotion 依赖、Remotion 实际 browser、FFmpeg 或 ffprobe。计划 `29-m09-dynamic-infographic-execution-plan.md:88-95` 将这些列为 P3a 必需输入/逐项诊断，当前 `bootstrap_ready=true` 可在它们全部缺失时产生，违反 fail-closed exit gate。
2. **FAIL — reason-code matrix 不符合冻结契约。** 当前只会返回 `SERVICE_SECRET_NOT_CONFIGURED` 或 `SERVICE_PROBE_UNAVAILABLE`；未实现计划 `:154` 要求的稳定优先级（`NODE_NOT_FOUND` 至 `EXTERNAL_STAGE_BLOCKED`）。已有 `test_bootstrap_reports_multiple_missing_items_but_one_stable_reason` 也未覆盖该完整多缺项矩阵。
3. **FAIL — external-stage gate 不是实际 gate。** `_bootstrap_snapshot()` 固定追加 `external-stage-gate` 为 `ready=True`，即使 reason code 为 `EXTERNAL_STAGE_GATE_REQUIRED`。因此该阶段不可能使 bootstrap 失败，和 P3a 所要求的 external-stage gate 缺项 fail-closed 相悖。
4. **PASS — bootstrap 不会提前 activation。** 当前 public infographic item 恒 `supported=False`；全部当前 service probe 可用时给出 `REAL_SMOKE_EVIDENCE_REQUIRED`。`tests/test_infographic_capability.py` 覆盖了 `bootstrap_ready=true && supported=false`。
5. **PARTIAL — service diagnostics 保守但不充分。** 非 renderer services 的 enabled/secret presence/cached-probe 使用只读 registry 调用，probe exception 返回不可用；但它没有合并 P3a 所需完整 toolchain、external gate 与稳定 reason matrix，故不能判整体 readiness 合格。
6. **PASS（有限） — CLI/API 读模型和白板未见直接回归。** API route 与 CLI 均实例化 `CapabilityService`；上述 16 项专项（含 API、CLI、whiteboard 断言）通过。没有发现此实现调用 adapter、渲染、创建任务或读取 P6 evidence。
7. **FAIL — 验收测试覆盖不足。** 当前 capability 专项未对每个 toolchain prerequisite、lockfile/Remotion/browser、FFmpeg/ffprobe、external gate false、完整 reason priority，或所有 probe 异常做 P3a contract 断言。独立 `tests/test_toolchain_resolver.py` 没有被 capability projection 消费，不能填补该缺口。

## 纠正条件

在 `capabilities.py`（及必要的 read-only toolchain helper）实现计划规定的逐项安全诊断和完整稳定优先级；external stage 必须作为真实 fail-closed 条件；补齐对应 mocked tests，再由独立验证人复跑专项。期间继续保持 `supported=false`，且不得运行 render、创建真实任务、读取 P6 evidence、activation 或开放 submission。

## Reverify — P3a non-renderer rework

结论：**FAIL**。本次未修改实现、测试、配置或计划，未执行 real render、任务创建、P6 evidence/activation 或 submission；唯一写入仍是本回执。

### 已通过的独立检查

- `csboard/application/capabilities.py` 已删除 Node、Remotion、browser、FFmpeg/ffprobe、render script、lockfile 与 `node_modules` 的 helper/constant/check；仅保留引擎字符串 `infographic-remotion`。`_bootstrap_service_checks()` 仅枚举 `text_generation`、`speech_synthesis`、`speech_alignment`、`image_generation`、`media`，不含 `rendering`（`:101-116`）。
- `tests/test_infographic_capability.py` 当前为存在的常规文件（3317 bytes）。
- 指定专项复跑：

```text
.venv/bin/python -m pytest -q tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py
12 passed, 1 warning in 3.34s
exit 0
```

- P3a 仍使用 `datetime.now(UTC).isoformat()` 记录 `bootstrap_checked_at`（`:88-99`），公开 `infographic-remotion.supported` 恒为 false；bootstrap true 时公开 reason 为 `REAL_SMOKE_EVIDENCE_REQUIRED`（`:71-84`），对应专项断言通过（`test_infographic_capability.py:43-51`）。
- 白板 projection 仍独立使用原 `WHITEBOARD_STAGE_REQUIREMENTS`；CLI/API 都构造同一 `CapabilityService` projection，且指定 API/CLI/whiteboard 专项通过。

### 失败定位

1. **external gate 非 fail-closed。** `csboard/application/capabilities.py:88-93` 无条件追加 `_check("external-stage-gate", True, _EXTERNAL_GATE_CODE)`。因此即使 external-stage gate 尚未解除，它永远不会成为 `first_failure`，也不会令 `bootstrap_ready=false`。这不满足 P3a 的 external-gate 检查及“任何缺项 fail closed”要求。
2. **全矩阵/多缺项/exception 证据不足。** `tests/test_infographic_capability.py` 仅有四个测试（`:37-69`）：没有模拟 external gate false；多缺项 test 没有断言完整 diagnostics 列表和确定排序；没有让 `get_cached_probe()` 或 `has_required_secrets()` 抛异常并验证 snapshot 保持 false/安全 reason。实现仅在 `_cached_probe_available()` 捕获 `get_cached_probe()` 异常（`capabilities.py:118-123`），`_bootstrap_service_checks()` 中的 secret access 本身未有异常转换（`:101-116`）。
3. **安全 UTC 测试不完整。** 实现使用 UTC 是正确的，但测试仅断言字段存在（`test_infographic_capability.py:50`），未验证可解析 UTC/offset；这使任务所要求的 UTC timestamp 专项验收未被独立证明。

需要将 external-stage gate 接到真实的可判定、fail-closed 条件，并补齐所有服务/secret/probe/external-gate 缺项、多缺项优先级、registry exception、UTC 可解析与安全诊断的 mocked tests；随后重新以指定三模块 exit 0 复验。此前 P3a 不得作为 P4 前置 PASS。

## Final Reverify — PLAN-004 authoritative P3a boundary

结论：**PASS**。本次以 `M09-INFRA-PLAN-004` 为 P3a 职责权威：P3a 只负责 SecretStore presence、五类非-renderer cached service probe、external-stage gate 与 UTC timestamp；旧回执中要求 P3a 检查 Node/Remotion/browser/FFmpeg/render-script/lockfile 的陈述已被 PLAN-004 取代，不作为本次验收条件。未修改实现、测试、配置或计划，未执行 real render、任务创建、evidence activation 或 submission；唯一写入仍是本回执。

### 复跑门禁

```text
.venv/bin/python -m pytest -q tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py
34 passed, 1 warning in 3.31s
exit 0
```

warning 为 Starlette `BlockingPortal` deprecation，不影响测试结果。

### 独立核验

1. **PASS — 无 renderer/toolchain bootstrap。** `capabilities.py` 只 import `UTC`/`datetime`、typing 与 service registry（`:7-12`），不含 `_detect_remotion_readiness`、`_bootstrap_toolchain_checks`、browser/lockfile helper、`shutil.which`、Node、Remotion、ffmpeg、ffprobe、render script 或 P2/P6 evidence 读取。`rendering` 仅存在于独立白板 `WHITEBOARD_STAGE_REQUIREMENTS`（`:18-25`），不在 `INFOGRAPHIC_STAGE_REQUIREMENTS`（`:26-31`）或 P3a `_bootstrap_service_checks()` 枚举（`:111-126`）。
2. **PASS — external gate 三态 fail-closed。** 缺失、false 或 callable exception 均产出 `external-stage-gate: ready=false, reason_code=EXTERNAL_STAGE_BLOCKED`（`capabilities.py:96-109`；矩阵 `test_infographic_capability.py:82-92`）。没有 ready fallback 或异常正文泄露。
3. **PASS — 五类 non-renderer matrix 与唯一首因。** `text_generation`、`speech_synthesis`、`speech_alignment`、`image_generation`、`media` 按固定顺序检查（`capabilities.py:111-126`）；24-test matrix 对每类 missing、secret failure、cached probe failure 都断言对应自身 component/reason（`tests/test_infographic_capability.py:94-131`）。多缺项完整 diagnostics 的固定顺序、第一失败项唯一决定 `bootstrap_reason_code` 由 `:146-160` 验证。
4. **PASS — exception fail-closed 与安全诊断。** secret/probe registry exception 分别归约为 `SERVICE_SECRET_MISSING`/`SERVICE_PROBE_FAILED`（`capabilities.py:128-139`；tests `:134-143`）；诊断仅有 `component`、`ready`、`reason_code`，不含异常文本、路径或 secret（`:43-45,146-160`）。
5. **PASS — UTC 与 public fail-closed。** `bootstrap_checked_at` 由 `datetime.now(UTC).isoformat()` 生成（`:104-108`），矩阵使用 `datetime.fromisoformat()` 并断言 UTC offset（tests `:146-154`）。public infographic `supported` 恒 false；bootstrap true 仍唯一给出 `REAL_SMOKE_EVIDENCE_REQUIRED`（`capabilities.py:79-94`；tests `:53-61`）。
6. **PASS — 白板与 CLI/API 同源未回归。** 白板仍使用自身完整 requirements/projection（`capabilities.py:18-25,74-94`），whiteboard 回归断言保留（tests `:74-79`）；API、CLI 各以 monkeypatch `CapabilityService.snapshot` 证明消费同一 read model（`tests/test_capabilities_api.py:77-84`、`tests/test_cli_capabilities.py:48-54`）。

P3a rework 已满足 PLAN-004 规定的独立出口，可标记 PASS 并作为既定 P4 合流前置。此 PASS 不授权 P4 执行、real render、任务创建、activation 或用户/API/WebUI submission。
