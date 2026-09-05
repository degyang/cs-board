# M09-INFRA-ACTIVATE-007 — PLAN-004 P3b/P7 独立严格审核

结论：**FAIL**

未修改实现、测试、P6 outputs 或配置；没有执行真实 render。唯一写入为本回执。虽专项测试通过，以下独立反证表明 P3b 未满足 PLAN-004 `:141-156` 的必要条件，不能激活。

## 已复跑与独立验证

- `.venv/bin/python -m pytest -q tests/test_infographic_activation.py tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py`：exit 0，`43 passed, 1 warning`。此结果不构成验收替代。
- 在系统临时目录独立复制 P6 包、pointer、renderer 与 lockfile，并单独构造了每个条件：`READINESS_FAILED`、`EVIDENCE_MISSING`、`EVIDENCE_EXPIRED`（包括未来时间）、`MP4_MISSING`、`FFPROBE_INVALID`、`MANIFEST_INVALID`、`HASH_MISMATCH`、`TOOLCHAIN_CHANGED`（renderer 内容改变）、`SERVICE_PROBE_CHANGED`。九码均能返回各自稳定码。
- pointer 不扫描：即使 P6 包仍在，删除 pointer 返回 `EVIDENCE_MISSING`；`../escape` 和绝对 `/tmp/not-a-run` pointer 均被拒绝为 `EVIDENCE_MISSING`。同一 verifier instance 初次成功后将 evidence 改为未来 UTC，下一次调用立即返回 `EVIDENCE_EXPIRED`，证明无 ready 缓存、会重读。
- 当前实机版本与 P6 evidence 现值一致：Node `v24.20.0`、Remotion `4.0.515`、Chrome for Testing `152.0.7977.54`、FFmpeg/ffprobe `6.1.1-3ubuntu5`；renderer 与 lockfile 当前哈希也与 P6 evidence 一致。
- production P6 evidence 没有 `expected_service_fingerprint`；代码仅在该字段和 current safe fingerprint 都为字符串且相等时通过（`csboard/application/activation.py:84-89`），故生产保持 `supported=false`，不会凭 P6 自测开启。Capability、CLI、API 与 create-options 都经 `CapabilityService.snapshot()` 投影；创建仍要求 public supported 或 internal-test 条件（`capabilities.py:82-97`、`commands.py:155-159, 247-267`），公共 task API 不传 internal-test 参数（`mountain_task_api.py:81-103`）。

## 阻断项与精确整改

1. **工具版本变化未失效（阻断）。** `ActivationVerifier` 只比较 `render.mjs` 和 `package-lock.json` 哈希（`activation.py:80-83`），从未读取或比较 evidence 的 `tool_versions`。独立反证：仅将 fixture evidence 的 `tool_versions.node` 改为 `changed-version`，保持其他绑定不变，结果是 `supported=True, reason_code=None`，而非 `TOOLCHAIN_CHANGED`。必须实际读取并比较当前 Node、Remotion、实际 browser identity/path、FFmpeg、ffprobe 与 evidence 的所有对应字段；任一不一致或不可读均返回 `TOOLCHAIN_CHANGED`。renderer、lockfile、props 的现有 hash 比较必须保留。
2. **ffprobe 契约不充分（阻断）。** 当前只接受任意 video stream、正数 duration/width/height（`activation.py:54-60`）；没有要求 `codec_name=h264`、`1920x1080`，没有将保存的 probe 结构与 evidence 的 `ffprobe` 摘要逐字段绑定，也没有重新执行/可信验证真实 ffprobe 结构。必须校验 codec、格式、时长、尺寸与 manifest/props/evidence 的一致性，并保持 probe artifact SHA-256 的绑定；无效统一为 `FFPROBE_INVALID`。
3. **manifest/index/evidence 非全字段绑定（阻断）。** verifier 只检查 index 是 dict、四个 ref key 存在，以及 manifest 的少量字段（`activation.py:61-79`）。它不解析/验证 `RemotionEvidenceV1`，不检查 evidence schema/version、完整 tool/evidence 字段、index 每个条目与 evidence ref 的对应关系，亦不验证 task/run identity、run/task/stage `SUCCEEDED`。这不满足计划 `:150,156` 的 artifact/index/manifest/evidence 完整 binding。必须以 V1 schema 严格解析 evidence，限定 pointer 指向的 Task/Run 与 evidence/run.json/task.json 相互一致，检查 `render-visuals` 与 task/run 状态成功，并逐项校验 index、refs、路径边界、size、hash、manifest duration/frames/output/probe、props 与所有 evidence 声明。
4. **pointer 只限制在 `outputs/` 内，未绑定受控 P6 身份（整改）。** 不扫描和不逃逸已通过（`:28-40`），但任何 `outputs/` 下目录均可成为 run；结合第 3 项的缺失，不能证明其就是已独立复核的 P6 Task/Run。整改时将 pointer 的受控 target 与 evidence 中的 Task/Run identity、独立签发记录严格绑定，并拒绝不一致 target。

在上述阻断项修复并由独立审核再次逐码（尤其是每一种工具版本变化）验证前，必须保持 `supported=false`、create-options `available=false` 且 public submission/WebUI 关闭。

## Reverify 2 — 结论：**FAIL**

本次仅复核更新实现/实现回执并在系统临时目录创建自动清理的测试副本；未改实现、P6 包、配置或产品文件。原 FAIL 的工具版本、ffprobe 语义和部分 Task/Run 绑定已经修复，但“全字段绑定”和 public submission 边界仍不合格。

### 复跑与通过项

- 按实现回执所称的精确 53 项组合复跑：`.venv/bin/python -m pytest -q tests/test_infographic_activation.py tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py tests/test_infographic_routing_p4.py tests/test_infographic_legacy_p5.py`，exit 0，`53 passed, 1 warning`。
- 独立五工具 mutation：分别篡改 evidence 的 Node、Remotion、browser、FFmpeg、ffprobe 版本，五次都得到 `TOOLCHAIN_CHANGED`。当前 verifier 以受控 pointer 的 browser executable 执行 `--version`，并实际比较五种版本以及 renderer/lockfile hash（`activation.py:108-124`）。
- 独立 ffprobe mutation：codec、宽度、container、duration、evidence summary 分别变更均为 `FFPROBE_INVALID`；保持 JSON 语义但改变 probe bytes 为 `HASH_MISMATCH`。H.264、1920×1080、container、非零 duration 与 summary/probe hash 的检查见 `activation.py:76-107`。
- future/expired freshness、九个稳定 reason code、无 pointer 扫描、`..`/绝对 pointer 拒绝、同一 instance 重读均已验证。pointer 现含 Task/Run/receipt/browser 字段，Task、Run 和 `render-visuals` 成功态在 `:51-57` 核对。
- browser 绝对路径仅出现于受控 `outputs/remotion-activation-pointer.json`；`ActivationVerifier._result()` 公开 diagnostics 只返回 component/ready/reason，CLI capability 实测输出中没有 `/home/ubuntu`、Chrome 路径或 `browser_executable`。这一项通过。
- 在真实 production root 直接以 `bootstrap_ready=True` 调 verifier（P6 evidence 仍缺 `expected_service_fingerprint`）得到 `supported=False, reason_code=SERVICE_PROBE_CHANGED`。当前 CLI projection 同样保持 false；其当前首因是现存 P3a readiness 不成立的 `READINESS_FAILED`，而诊断中仍列出 `SERVICE_PROBE_CHANGED`，符合 fixed reason priority。API/CLI/create-options 均消费 `CapabilityService.snapshot()`，但见下述 submission 阻断。

### 仍然阻断的独立反证与整改

1. **原始 evidence schema_version 未绑定。** 临时副本仅将 JSON 的 `schema_version` 改为 `999`，结果仍为 `supported=True, reason_code=None`。`activation.py:64-65` 重新构造 dataclass 时未传入/比较原始 schema_version，故 dataclass 默认 V1 掩盖了输入篡改。整改：拒绝 schema_version 缺失或非 1，并严格比较原 JSON 的 V1 字段集合后再调用领域验证。
2. **task-package 身份未验证。** 临时副本只将 `task-package.json.task_id` 改为其他 ID，仍返回成功。代码只读 `task.json` 与 `run.json`（`activation.py:51-55`），完全不读 task-package。整改：读取 task-package 并要求 package kind/schema/task_id/runs_dir 与 pointer、task、run 一致；不一致 fail-closed（建议 `MANIFEST_INVALID`）。
3. **pointer verifier receipt 仅检查字符串前缀。** 将 `verifier_receipt` 改为不存在的 `docs/workmates/receipts/does-not-exist.md`，仍返回成功；当前仅 `startswith`（`:36`）。整改：限制为指定独立 P6 验证回执，确认受控 receipt 存在并包含该 Task/Run 的独立 PASS 绑定；否则拒绝 pointer。
4. **artifact index 与 evidence refs 未逐条交叉绑定。** 在临时副本中将 `index.artifacts.render.mp4.size_bytes` 改为 `1`，同时重算并写回 evidence 的 `artifact_index_sha256`；verifier 仍成功。`activation.py:90-107` 未把 index entry 的 key/path/hash/size/status 与 evidence refs/实际 artifact 全量对照。整改：逐一验证 index 的每个 artifact 与 evidence ref 及文件实际 path/size/hash/status 相同，并拒绝缺项、额外/不对应条目或任一结构不一致。
5. **public submission 会在 supported=true 时自动开放。** `commands.py:155-159` 以 `public_allowed = infographic_item.supported` 允许非 internal-test 调用；这违背 PLAN-004 P3b/P7 的“supported 不自动开放 WebUI/submission”边界。production 当前因缺 fingerprint 为 false，但正确 evidence/fingerprint 后该分支会打开公共创建。整改：移除 public_allowed 作为 create authorization；保持提交入口独立 PM/security 产品授权和显式门禁，P3b activation 只能影响 capability/create-options projection。

因此，未完成上述五项整改及独立复验前，必须继续保持 `supported=false`、create-options `available=false` 和所有 public/API/WebUI submission 关闭。

## Reverify 3 — 结论：**FAIL**

仅追加本回执；未修改实现。Rework3 已关闭 Reverify2 的大部分绑定缺口，但独立 P6 验证回执的 PASS 语义与 MP4 hash 仍未被真正绑定，故不能接受 activation。

### 复跑

- 以此前 67 项文件组合复跑时，Rework3 新增 7 个 activation cases，当前实际收集/运行为 **74 passed, 1 warning**，exit 0（而非实现回执仍声称的 67）。未为凑计数排除新增安全用例。

### 通过的独立临时副本反证

- `schema_version=999` → `MANIFEST_INVALID`；task-package mismatch → `MANIFEST_INVALID`。
- receipt 缺失、内容为 `FAIL`、Task 不符、Run 不符均 → `MANIFEST_INVALID`。
- index extra/missing/ref mismatch/path escape/size/status/malformed 均在重算 `artifact_index_sha256` 后返回 `MANIFEST_INVALID`；未篡改包的 8 个 index entry 逐个实算 SHA-256 均与声明一致。
- 抽查 Node、browser、ffprobe version mutation 都返回 `TOOLCHAIN_CHANGED`；probe codec mutation 返回 `FFPROBE_INVALID`，无 Rework2 回归。
- 以 capability fixture 强制 `supported=true` 后，非 internal caller 的 `create_task` 仍抛 `CAPABILITY_NOT_AVAILABLE`；public submission 未随 activation 打开。

### 阻断：receipt 内容与 hash 仍可伪造

`activation.py:58-62` 的 receipt 校验只要求文件名为 `M09-INFRA-REAL-006-V.md`，且文本包含子串 `PASS`、Task ID 与 Run ID。它没有校验回执中的 MP4 SHA-256，也没有判定 PASS 是规范结论而非任意子串。

- 临时副本仅将 P6 验证回执的 MP4 hash `18e953…35d641a` 替换为 64 个 `0`，verifier 仍返回 `supported=True, reason_code=None`。
- 临时副本将回执内容设为 `NOT PASS: task p6-real-smoke-51657b64d6d3 run run-p6-51657b64d6d3`，verifier 仍返回 `supported=True, reason_code=None`，因为 `"PASS" in text` 误判非 PASS 状态。

整改：将 receipt 解析为固定、机器可校验的独立验证记录；要求唯一的结论字段精确为 PASS，并将 Task ID、Run ID、MP4 SHA-256（以及计划要求的 evidence/index/manifest identity）以结构化字段与 pointer/P6 包逐项比较。任一缺失、不一致、FAIL/BLOCKED 或无法解析必须 fail-closed（建议 `MANIFEST_INVALID`）。完成后须再次复用上述两项反证复验。

## Final Reverify 4 — 结论：**FAIL**

仅追加本回执，未修改实现。Rework4 已修复上次 receipt 的 hash/PASS 文本阻断，但缺失 receipt 仍抛出未处理异常，未按要求安全归约为 `MANIFEST_INVALID`。

### 完整复跑与独立反证

- 指定的原 74 项组合在 Rework4 新增 7 个 receipt/tool tests 后实际收集为 **81 passed, 1 warning**，exit 0；未排除新增安全用例以人为维持旧计数。
- 在独立临时副本中，将 P6 verifier receipt 内当前 evidence 的 MP4、render-manifest、artifact-index SHA-256 分别篡改，均得到 `supported=False, reason_code=MANIFEST_INVALID`。将结论精确改为 `结论：**NOT PASS**` 亦得到 `MANIFEST_INVALID`。
- `schema_version=999`、task-package identity mismatch、重算 index hash 后的 index status mismatch 均为 `MANIFEST_INVALID`；8 个 index artifact 的实际 SHA-256 全部复算匹配。
- Node、Remotion、browser、FFmpeg、ffprobe 五种版本 mutation 均为 `TOOLCHAIN_CHANGED`；ffprobe codec mutation 为 `FFPROBE_INVALID`；强制 capability `supported=true` 的 non-internal create 仍抛 `CAPABILITY_NOT_AVAILABLE`。

### 唯一阻断：receipt 缺失未 fail-closed

临时副本删除 `docs/workmates/receipts/M09-INFRA-REAL-006-V.md` 后，`ActivationVerifier.verify(True)` 在 `csboard/application/activation.py:77` 访问未初始化的 `receipt_text`，抛出 `UnboundLocalError`，而不是返回 `MANIFEST_INVALID`。原因是 receipt 读取异常时只设置 `receipt_ok=False`，随后 evidence binding 仍无条件使用 `receipt_text`（`:58-77`）。

整改：在 receipt 读取失败时初始化安全空值或直接返回/记录 `verifier-receipt=MANIFEST_INVALID`，确保缺文件、不可读文件和解析失败均无异常、稳定 fail-closed。完成后仅需重跑“缺 receipt”临时反证与完整 suite；在此之前不可标记 PASS 或开放 activation。

## Final Reverify 5 — 结论：**PASS**

只复核更新实现并追加本回执；未修改产品实现、P6 evidence、配置或 submission。

- 完整原组合已复跑。Reverify5 又新增 7 个 receipt cases，因此当前实际输出为 **88 passed, 1 warning**，exit 0（实现回执所述的 81 是新增用例前的计数）。
- 在独立、自动清理的临时副本中，receipt **缺失、目录、空文件、`NOT PASS`、Task 不符、Run 不符、MP4 hash 不符**七类均返回 `supported=False, reason_code=MANIFEST_INVALID`，无未处理异常。
- 回归抽查通过：`schema_version=999`、task-package mismatch、重算 index hash 后的 index status mismatch 均为 `MANIFEST_INVALID`；8 个 artifact 实际 SHA-256 全部与 index 一致；Node、Remotion、browser、FFmpeg、ffprobe 五类版本 mutation 均为 `TOOLCHAIN_CHANGED`；probe codec mutation 为 `FFPROBE_INVALID`。
- 强制 capability `supported=true` 的非 internal caller 仍被 `CAPABILITY_NOT_AVAILABLE` 拒绝，public create 没有随 activation 开放。

此前唯一的 `receipt_text` 未初始化阻断已修复：读取 receipt 之前初始化安全空字符串，缺失、目录和空文件均进入 `verifier-receipt` 的稳定 fail-closed 路径。M09-INFRA-ACTIVATE-007 的独立复验现可判定 PASS；production 仍因缺独立 service fingerprint 保持 `supported=false`，本 PASS 不授权 public/API/WebUI submission。
