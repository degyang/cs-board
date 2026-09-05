# M09-INFRA-ACTIVATE-007 — P3b/P7 Activation Receipt

状态：READY_FOR_VERIFY

## Rework after independent FAIL

- pointer 现要求并校验 `task_id`、`run_id`、`verifier_receipt` 与 run-relative target；Task/Run 身份、成功状态和 `render-visuals=SUCCEEDED` 均为 activation 前提。
- evidence 现通过 `RemotionEvidenceV1` 构造/校验；index hash、manifest output/path/MP4/probe hash/size/duration/frames 与 evidence refs 交叉验证，probe ref 也加入 hash loop。
- 当前 node、ffmpeg、ffprobe 版本实际以 subprocess 读取并与 evidence 比对，renderer/lockfile hash 保留。生产继续因缺独立 service fingerprint 返回 `SERVICE_PROBE_CHANGED`。
- `tests/test_infographic_activation.py` 重跑：9 passed，exit 0。

## Rework 2 — strict verifier binding

- 实际读取 Node、Remotion（lockfile package entry）、受控 pointer browser executable、FFmpeg、ffprobe 版本；不可执行、非零退出、超时或版本不一致一律 `TOOLCHAIN_CHANGED`，公开 diagnostics 不含 executable 路径。
- ffprobe 要求 H.264、1920×1080、非零 duration、container，并逐字段绑定 evidence 摘要和 probe artifact hash；Task package、Task/Run identity、成功状态、render stage success 均校验。
- 全部专项：activation + capability/API/CLI + P4 + P5 → **53 passed**，exit 0；生产仍因缺 signed service fingerprint fail-closed，未开放 submission/WebUI。

状态：READY_FOR_REVERIFY

## Rework 5 — receipt read exception safety

- `receipt_text` 在读取前初始化；缺文件、目录、读取/解析异常均不会抛出，统一 fail-closed 为 `MANIFEST_INVALID`。
- 新增 missing receipt 及六类 receipt 读取/绑定失败回归。
- 完整原组合共 **81 passed**（activation 30 passed；capability/API/CLI/P4/P5/task creation 51 passed），两段专项均正常 exit 0；`git diff --check` exit 0。

状态：READY_FOR_REVERIFY

## Rework 4 — receipt evidence binding

- 指定 P6 verifier receipt 现必须存在、结论行精确为 `结论：**PASS**`，并包含当前 evidence 的 MP4 SHA；已声明的 render-manifest/index SHA 也与当前 evidence 绑定。`NOT PASS` 或任一 hash 篡改均为 `MANIFEST_INVALID`。
- 新增 receipt hash/NOT PASS 反证，以及 node/remotion/browser/ffmpeg/ffprobe 五类版本 mutation 回归。
- 完整原组合：**74 passed**，exit 0（1 个既有 warning）；`git diff --check` exit 0。

状态：READY_FOR_REVERIFY

## Rework 3

- 原始 evidence `schema_version=1` 与必需字段集合、`task-package.json` 的 kind/schema/task_id/runs_dir、指定且存在并含 PASS/task/run 的 `M09-INFRA-REAL-006-V.md` 均已绑定。
- 已撤销 `public_allowed`；即使 capability supported=true，非 `internal-test` 创建仍拒绝。
- 本轮回归：activation + P4 routing + task creation → 20 passed；`git diff --check` exit 0。完整 67 项专项尚未在本轮执行，故不标记 reverify ready。

## Rework 3 completion

- index 现全量双向绑定 evidence refs：extra/missing/ref mismatch/path/size/status 属于 `MANIFEST_INVALID`；全部 index entry 的实际内容 SHA 在独立 hash 层验证，内容篡改为 `HASH_MISMATCH`，即使攻击者重算 index hash 也不能绕过。
- malformed index entry/ref 均安全归约为 `MANIFEST_INVALID`，不会抛出未处理异常。
- 完整原组合：**67 passed**，exit 0（1 个既有 warning）；`git diff --check` exit 0。

状态：READY_FOR_REVERIFY

- 新增 fail-closed `ActivationVerifier`：每次 projection 只读取 `outputs/remotion-activation-pointer.json` 指向的受控 run；不扫描目录，不缓存 ready，并拒绝缺失/越界 pointer。
- 逐项验证 evidence freshness（含未来时间）、MP4、ffprobe、index hash、manifest/index/evidence/MP4/probe hash 与路径/size/duration/frames 绑定、renderer/lockfile hash，以及 current safe bootstrap fingerprint。
- production evidence 缺少独立签发的 `expected_service_fingerprint`，因此按决策稳定返回 `SERVICE_PROBE_CHANGED`，`supported=false`；未补写或伪造 P6 指纹，未开放 public submission/WebUI/create-options。
- 稳定 reason 覆盖由 activation tests 逐项触发：missing pointer/evidence、expired/future、MP4、ffprobe、manifest/index、hash、tool hash、bootstrap、service fingerprint change；fixture 的合法 fingerprint 相等时可 activation。
- 专项：`pytest -q tests/test_infographic_activation.py tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py` → 43 passed，exit 0。
