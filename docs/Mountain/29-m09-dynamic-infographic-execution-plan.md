# M09 动态信息图：boundary-first vertical-slice 执行计划

状态：实施前重排；本文件**不授权公开提交或 capability activation**。
重排日期：2026-09-06。权威产品入口：[README.md](README.md)。

## 1. 用户确定的边界

当前目标是证明受控的输入→调用→最终输出 corridor，不是治理 Remotion 的所有内部步骤。唯一必须白盒、可独立复核的表面是：

1. 交给 Remotion 的已验证、版本化 props 与已知本地 assets；
2. 受控 invocation，以及 timeout/失败的真实 Task、Run、Stage 状态；
3. 最终 MP4 的 run-relative 受控位置；
4. 非空 MP4 和有效 ffprobe；
5. 最终视频的 manifest、hash 和 artifact index 原子注册；
6. 对上述 input→invocation→output evidence 的独立复核。

Remotion 内部生成（包括每一张中间图片）是允许的黑盒。逐图可观测性、逐图 hash/manifest、图像 provider 治理和内部 image instrumentation 不是本轮 gate，也不能被用来伪造 corridor 成功。

`create-options`、公开 API/CLI/WebUI 提交一律维持 `available=false` / `supported=false`，直到 corridor 有真实证据、独立复核和 activation。用户已授权在 **G0 独立 PASS 后** 串行执行一次 V1、V2、V3、activation 与“新建任务”动态信息图选项验证；这项授权不跳过任一 gate，也不允许仅改 `available`。

## 2. R-R6 的有限结论

R-R4/R-R5 只证明 direct `CapabilityService.snapshot()` 能返回，而 `TestClient` 与一次 `ASGITransport` 请求均在共享 API lifecycle 中超时。`M09-INFRA-BOOTSTRAP-003A-R-R6` 的静态回执只是 **G0 候选线索**：capability handler 为同步 handler、没有自定义 lifespan/startup hook，问题可能处于 ASGI entry/sync dispatch。它没有 HTTP evidence，不证明根因，不是 P3a PASS/FAIL，也不解锁公开能力。R-R6 的静态 breadth 到此停止。

## 3. 唯一可推进的垂直 DAG

```
G0 共享 API request lifecycle：有界复现、最小修复、独立验证
 │
 └── V1 固定输入的内部 Remotion corridor：受控 invocation → 真 MP4
       │
       └── V2 输出边界：ffprobe + 原子 artifact/manifest/hash + 真状态/重试
             │
             └── V3 独立 input→invocation→output evidence verification
                   │
                   └── 后续：provider/service readiness、legacy cleanup、
                       内部图片治理、activation/public submission
```

任何一票失败均停在该票：记录真实失败/可恢复状态并保持公开入口关闭；不得跳到 activation，也不得以 mock、空文件或内部图片记录替代真实 MP4。

### G0 — 共享 API request lifecycle

- Owner：`backend`（独立 backend worktree）；独立验证：`verification`。
- 输入：R-R4/R-R5/R-R6 与当前 capability route；不依赖 provider readiness、P3a 完整 reason matrix 或图片观测。
- 范围：`backend/mountain_server.py`、`backend/mountain_capability_api.py`、`tests/test_capabilities_api.py`，以及必要的项目本地 test harness/config。不得改 renderer、domain、Task creation、公开 capability policy 或服务配置。
- Exit predicate：新的 bounded API test 能重复完成；`/api/v1/capabilities` 返回 200、`items/providers` 形状、infographic 仍 `supported=false`；失败路径在明确 timeout 内结束且无残留进程。仅在证据表明 product/harness defect 时做最小修复；必须独立 PASS。
- 禁止项：任何 Remotion render、任务创建、公开提交、把 API 通过等同 corridor 成功。

**PM 裁决（2026-09-07）**：历史 `test_bootstrap_ready_still_requires_real_smoke_evidence` 对 `REAL_SMOKE_EVIDENCE_REQUIRED` 的断言属于 activation/real-smoke evidence policy。按本文件 V3 后才独立复核和 activation 的顺序，它不再是 G0 acceptance 条件；测试必须保留、不得 delete/skip，G0 verification 只将其作为预期的延后 gate 记录。G0 仍须独立复核 lifecycle 200、API/CLI、注入式 toolchain interface、范围与无残留，PASS 后才可派 V1。

### V1 — 固定输入的受控内部 corridor

- Owner：`backend`；独立验证：`verification`；需一次显式 real-render 运行授权。
- 输入：G0 独立 PASS；固定 `render.props` schema/version/hash；已知本地 fixture assets；锁定 renderer/lockfile。provider/service readiness 只在该固定输入确实直接需要时才成为 blocker。
- Exit predicate：invocation 有稳定 timeout、失败摘要和 run identity；成功时目标位置存在非空 MP4。内部图片步骤不记录、不审计、不作为条件。
- 禁止项：公开提交、外部用户素材、逐图 instrumentation、activation。

### V2 — 输出边界、登记与真实状态

- Owner：`backend`；独立验证：`verification`。
- 输入：V1 成功或其真实失败结果；不依赖 legacy cleanup、provider 全量 readiness 或中间 image artifacts。
- Exit predicate：成功路径 MP4 非空、ffprobe 有有效视频流/时长/尺寸；`artifacts/render/infographic.mp4`、manifest、SHA-256、index 一致并原子提交。timeout、render exit 非零、空 MP4、ffprobe 或 registration 失败均不得标 SUCCESS，且有可复核 retry 状态。
- 禁止项：把内部图片、raw stderr、secret 或绝对路径写入 artifacts/evidence；开放提交。

### V3 — 独立 corridor evidence verification

- Owner：`verification`；PM 消费 verdict；验证者不改产品实现。
- 输入：冻结的 V1/V2 目标和新鲜 evidence。
- Exit predicate：版本化 input、调用控制、最终 MP4、ffprobe、manifest/hash/index、Task/Run/Stage 状态与失败/重试语义均有一致证据。任何缺项为 FAIL/BLOCKED。PASS 只代表内部 corridor 已验证，仍不改变 `available=false`。

## 4. 延后事项

| 项目 | 何时重新排队 | 当前状态 |
| --- | --- | --- |
| 全量 provider/service readiness 与完整 P3a reason matrix | V3 有独立 evidence 后 | 延后 |
| legacy route/module cleanup | corridor 稳定后 | 延后 |
| Remotion 内部/中间图片可观测性或治理 | 独立产品决定 | 延后，非门禁 |
| activation、`create-options`、用户/API/WebUI 提交 | V3 PASS 后且用户另行授权 | 关闭 |

旧横向 `P3a → P4 → P5 → P6 → P3b` 队列及其“P3a/P4 PASS 才可真 render”解释在本计划中均为 **superseded**；历史回执仅供审计，不能推进新 DAG。

## 5. 首个可执行票

`M09-G0-LIFECYCLE-001` 是唯一立即可派发的 implementation ticket。其独立 PASS 后，按 `M09-V1-CORRIDOR-001` → `M09-V2-OUTPUT-001` → `M09-V3-CORRIDOR-VERIFY-001` → `M09-ACTIVATE-001` 串行派发；每票仍须以前票独立 PASS 为唯一入口。公开入口只可在 activation 完整证据后为一次“新建任务”动态信息图验证临时开放，验证失败即继续关闭。
