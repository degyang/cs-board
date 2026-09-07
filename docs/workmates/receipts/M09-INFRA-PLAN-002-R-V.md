# M09-INFRA-PLAN-002-R-V — P3a 计划修订独立复验回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读计划验证，未修改产品代码、计划、测试、服务或看板。

## 输入

| 文件 | 状态 |
| --- | --- |
| `docs/workmates/assignments/M09-INFRA-PLAN-002-R.md` | ✅ 已读 |
| `docs/workmates/receipts/M09-INFRA-PLAN-002-R.md` | ✅ 已读 |
| `docs/workmates/receipts/M09-INFRA-PLAN-002-V.md`（prior FAIL） | ✅ 已读 |
| `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`（修订后） | ✅ 已读 |

---

## FAIL-5 逐项核验（唯一 FAIL 项）

prior FAIL 的第 5 项是唯一阻断项。以下逐条核验其矛盾是否消除。

### 5a. P3a 是否被定义为唯一的 bootstrap/toolchain 诊断真源

**FAIL 原因**：旧版第 64 行要求 P3a 检查 Node/脚本/锁定依赖/browser/FFmpeg/ffprobe，但 P3a 工作包（旧 88–95 行）禁止检查 "renderer-specific readiness" 并声称 P3a exit 不声明这些工具可用——要求和禁止同时指向同一类条件。

**修订后**：第 64 行现在将 P3a 明确定义为：

> P3a bootstrap readiness 是唯一的 bootstrap/toolchain 诊断真源：只读、fail-closed 地检查 Node、render script、锁定依赖、由 Remotion 实际使用的 browser、FFmpeg/ffprobe、服务配置与 secret presence、服务 probe 及 external-stage gate

**结论：PASS** — P3a 的 Capability 定义现在是单一真源，不再与工作包矛盾。

### 5b. P3a 工作包是否与 Capability 定义一致

**FAIL 原因**：旧 88–95 行称 P3a 为"非 renderer"、禁止检查 renderer-specific readiness、exit 不声明 Node/Remotion/browser/FFmpeg/ffprobe 可用。

**修订后**（第 88–95 行）：
- 第 90 行：目的明确为"检查工具链的存在、锁定关系和安全可用性诊断"
- 第 92 行：输入/输出列出"Node、render script、锁定依赖、Remotion/browser 定位、FFmpeg/ffprobe 的只读检查"
- 第 93 行：测试覆盖"每个 Node/script/lockfile/Remotion/browser/FFmpeg/ffprobe"
- 第 94 行：exit gate 为"仅当全部上述工具链、服务/secret/probe 与 external-gate 条件满足时 `bootstrap_ready=true`"
- 第 94 行："P3a 只报告 bootstrap 诊断，不得运行 adapter、渲染、创建任务、读取 P6 evidence 或宣告 `supported=true`"

**结论：PASS** — 工作包现在明确要求 P3a 检查所有工具链项，同时正确禁止 render/activation/`supported=true`。禁止的是 render 和 activation，不是诊断本身。

### 5c. P3a reason-code matrix 是否独立于 P3b

**修订后**（第 154 行）：
- P3a bootstrap codes：`NODE_NOT_FOUND` → `RENDER_SCRIPT_MISSING` → `LOCKFILE_INVALID` → `REMOTION_NOT_INSTALLED` → `BROWSER_UNAVAILABLE` → `FFMPEG_NOT_FOUND` → `FFPROBE_NOT_FOUND` → `SERVICE_SECRET_MISSING` → `SERVICE_PROBE_FAILED` → `EXTERNAL_STAGE_BLOCKED`
- P3b activation codes：`READINESS_FAILED`、`EVIDENCE_MISSING`、`EVIDENCE_EXPIRED`、`MP4_MISSING`、`FFPROBE_INVALID`、`MANIFEST_INVALID`、`HASH_MISMATCH`、`TOOLCHAIN_CHANGED`、`SERVICE_PROBE_CHANGED`
- 明确："实现不得以 P3a 附加诊断替换 P3b activation/create-options code"

**结论：PASS** — 两套 code 完全分离，无交叉替换。

---

## 其他 PASS 项核验（prior FAIL 中已 PASS 的 1–4 项确认未回归）

### 1. DAG 与 next queue 无循环（PASS — 未回归）

- 第 125–135 行依赖图：`P1 → (P2 || P3a) → P4 → P5 → P6 → P3b/P7`
- 无 P3a/P3b 对 P6 的反向边
- P3b 唯一上游是 P6 独立复核成功 evidence

### 2. create-options fail-closed（PASS — 未回归）

- 第 141 行：`available=true/supported=true` 当且仅当全部六项条件满足
- 第 152 行：24h freshness，工具/lockfile/renderer/props hash 变化立即失效
- 第 154 行：失效时 `available=false/supported=false`

### 3. P4 internal/test 通道不等于用户提交（PASS — 未回归）

- 第 103 行："即使合流成功，P4 也只允许受控 internal/test 的真实任务通道：它不得让 `create-options` 返回 available，也不得打开用户/API/WebUI 提交入口"

### 4. P1–P5 边界未削弱（PASS — 未回归）

- P1/P2/P4/P5 的 entry/exit、测试与禁止项保留
- Legacy read-only 与 anti-fallback 规则（第 156–162 行）保留
- 原子 artifact index、manifest/hash 规则（第 164–178 行）保留

### 6. P4 合流输入一致性（PASS）

- 第 103 行：P4 entry gate 为"P1、P2、P3a exit；P4 在此合流 P3a 的唯一 bootstrap/toolchain 诊断与 P2 的 adapter 契约完成"
- 第 85 行（P2）：P2 "消费并遵守 P3a 已定义的 renderer/toolchain prerequisite contract"，P4 合流的是"P2 adapter 契约完成与 P3a bootstrap 诊断"

**结论：PASS** — P4 合流输入与 P3a/P2 定义一致。

### 7. P6 entry 一致性（PASS）

- 第 121–122 行：P6 entry 为"P1、P2、P3a、P4、P5 全部 exit；P3a 必须报告 `bootstrap_ready=true`"
- P6 不依赖 P3b

**结论：PASS** — P6 entry 与 DAG 一致。

### 8. Next queue 前置一致性（PASS）

- 第 188 行：`M09-INFRA-CONTRACT-001：P1 schema/fixture` → "PLAN-002 独立 PASS"
- 第 196 行：可自动派发顺序为"PLAN-002-R 独立 PASS 后首票 CONTRACT-001（P1）"

**结论：PASS** — next queue 正确要求 PLAN-002-R PASS 后才能派 P1。

---

## git diff --check

由实现回执确认 exit 0。本验证为纯文本审查，未运行 `git diff --check`（未修改任何文件）。

---

**最终判定：PASS**

prior FAIL 的唯一阻断项（P3a 架构职责自相矛盾）已消除。P3a 现在是唯一的 bootstrap/toolchain 诊断真源，明确检查 Node/script/lockfile/browser/FFmpeg/ffprobe/service/secret/probe/external-gate，同时正确禁止 render/activation/`supported=true`。DAG、reason-code、P4 合流、P6 entry 和 next queue 均一致且未回归。P1 可在本 PASS 后派发。
