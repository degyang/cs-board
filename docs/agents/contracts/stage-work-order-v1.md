# Stage Work Order v1 与外部插画 Gate

状态：**冻结给 CORE、WEB 和 Skills 的实现契约；尚未由生产代码实现。** 本文不改变
现有 `schemas/mountain/*.schema.json`。实现切片必须先把本契约落为领域 DTO、持久化和测试，
再改动任何 Stage 行为。

## 1. 范围与术语

唯一的标准流水线顺序来自 `csboard/application/pipeline.py`：

1. `generate-visual-anchors` / `visual-anchor-generator`
2. `clone-voice` / `voice-cloner`
3. `plan-storyboard` / `storyboard-planner`
4. `generate-illustrations` / `illustration-generator`
5. `render-visuals` / `visual-renderer`
6. `compose-video` / `av-compositor`

`video-workflow` 只编排，不能成为 Stage Work Order（以下简称 WO）。一个 WO 只描述一个
`task_id + run_id + stage`；可选的 `scope.unit_id` 或 `scope.visual_id` 把它缩小为一次局部
操作，二者不得同时存在。没有局部 scope 的 WO 覆盖该 Stage 当前有效的全部上游范围。

`task_root` 是 `tasks/<task_id>/`，`run_root` 是
`tasks/<task_id>/runs/<run_id>/`。本文所有 `*_path` 和 command 参数中的路径均相对
**run_root**：禁止 `/`、盘符、`..`、波浪号和符号链接逃逸。现有 Artifact Store 的 index
仍以 `artifacts/` 下的相对路径登记；WO 不能要求调用方直接修改它。

## 2. 共用 envelope

WO 的 JSON 文件位于 `work-orders/<stage>/work-order.json`，旁置参数和指令文件分别为
`work-orders/<stage>/parameters.json`、`work-orders/<stage>/instructions.md`。局部重做使用
`work-orders/<stage>/retries/<retry_id>/`，不会覆盖原 WO。

必填字段：

| 字段 | 规则 |
| --- | --- |
| `schema_version` | 固定字符串 `"1.0"`。 |
| `work_order_id` | 稳定、不可复用 ID；同一输入重取返回同一 ID。 |
| `identity` | `task_id`、`run_id`、规范 `stage`、匹配的 `skill`、`pipeline_id`、`engine`。 |
| `revision` | 正整数；输入变化、retry 或被拒后产生新 revision，不覆盖旧审计记录。 |
| `input_fingerprint` | `sha256:` 值，规范化身份、scope、输入 Artifact 的 key/revision/hash/status、参数和风格快照后计算。 |
| `status` | 仅使用第 4 节的 WO 状态；它和现有 Run/Stage DTO 分离。 |
| `scope` | `{ "kind": "stage" }` 或附 `unit_id` / `visual_id` 的局部 scope。局部 ID 必须存在于已验收上游 Artifact。 |
| `input_artifacts` | 每项均有 `artifact_key`、`revision`、`sha256`、`status: "succeeded"`、`relative_path`。 |
| `parameters_path`、`instructions_path`、`output_directory` | 均为 run-root 相对路径。`instructions` 只提供可执行说明，`parameters` 才保存机器输入。 |
| `expected_outputs` | 可由领域校验的目标，而不只是文件存在。 |
| `commands` | `run/import/validate/accept/reject/retry` 的结构化 command；未适用动作使用空数组。 |

命令对象是 `{ "command_id", "argv", "idempotency_key", "preconditions" }`。`argv` 是 JSON
字符串数组，由 Application Command/CLI 解释，不经 shell；不能含 Secret、Provider URL、绝对
路径、用户参考音频、完整脚本或 Provider 原始响应。`command_id` 只在该 WO revision 内唯一，
`idempotency_key` 是不透明 UUID；同 key、同规范请求必须返回第一次的结果，同 key、不同请求
返回 `IDEMPOTENCY_KEY_CONFLICT`，绝不重复副作用。

## 3. 规范 Artifact 和插画文件层级

Artifact key 与当前 `schemas/mountain/` 和 `csboard/adapters/filesystem/artifacts.py` 一致：
`planning.av-plan`、`audio.voice-manifest`、`timing.timeline`、`planning.storyboard`、
`illustrations.manifest`、`render.manifest`、`output.final-manifest`。外部 Gate 还使用设计中已
声明的 `illustrations.job` 和 `illustrations.candidates`，它们在实现时须有对应 schema。

插画 WO 的唯一可写目录为：

```text
manual/illustrations/candidates/<work_order_id>/<visual_id>/
  source.<ext>       # Codex/imagegen 或外部工具原始结果，未验收
  processed.png      # 本地确定性处理的候选，未验收
```

导入后，候选元数据以 `illustrations.candidates` 登记；所有文件仍是候选，不能写入
`media/images/` 或 `illustrations.manifest`。只有 accept 的原子事务才复制/移动到正式受控路径、
登记 `illustrations.manifest` 并允许 `render-visuals`。source 与 processed 均需 hash；正式
manifest 中沿用当前 schema 的 `source_image_path`、`final_image_path`、`sha256`、宽高、profile、
model、attempt 字段。

## 4. 状态、所有者与迁移

WO 状态不等于 Run 的 `pending/running/...`，也不把暂停伪装为失败。CORE 是唯一可写状态机、
Artifact index 和审计事件的所有者；CLI/Skill 只调用 command，WEB 只读 DTO 并请求已授权的
Application Command；用户只决定候选效果是否接受。

| 状态 | 设置者 | 允许进入 | 可退出到 | 含义/下一动作 |
| --- | --- | --- | --- | --- |
| `ready` | CORE | 创建、retry 成功创建 | `running`、`waiting-manual-trigger`、`stale` | 输入完整，可自动执行或等待策略判断。 |
| `waiting-manual-trigger` | CORE 编排器 | `ready` | `running`、`stale` | execution plan 要求显式触发；`resume` 不得执行它。 |
| `running` | CORE command | `ready`、`waiting-manual-trigger` | `waiting-external-output`、`validating`、`succeeded`、`failed`、`stale` | command 已被领取；重复请求按 idempotency 返回同一操作。 |
| `waiting-external-output` | CORE（插画任务包生成后） | `running` | `validating`、`failed`、`stale` | 等候候选文件和 import；下游 render 被阻断。 |
| `validating` | CORE import/validate | `waiting-external-output` | `waiting-acceptance`、`waiting-external-output`、`failed`、`stale` | 校验候选；可修正的校验失败回外部等待。 |
| `waiting-acceptance` | CORE validate | `validating` | `succeeded`、`waiting-external-output`、`stale` | 已有有效候选，等接受或拒绝。 |
| `succeeded` | CORE accept 或非外部 Stage 成功 | `running`、`waiting-acceptance` | `stale` | 正式 Artifact 已原子提交；仅此状态解锁下游。 |
| `failed` | CORE | `running`、`validating` | `ready`（retry 新 revision）、`stale` | 不可自动恢复错误；报告稳定错误码。 |
| `stale` | CORE invalidation | 任一非 `stale` 状态 | `ready`（新 revision） | 输入 fingerprint 或已验收上游不再匹配；旧命令一律 `WORK_ORDER_STALE`。 |

因此每个中间态均能由明确动作退出：用户/CLI trigger、候选 import、validate、accept/reject、
retry 或上游失效。拒绝不是失败：它保留候选和理由、使 WO 回到 `waiting-external-output`；retry
创建新的 revision 为 `ready`，旧 revision 保持审计不可变。

## 5. 外部插画 Gate commands

`generate-illustrations` 的 `run` 命令只生成任务包并进入 `waiting-external-output`，不产生正式
`illustrations.manifest`。Candidate 由 import 登记，validate 计算结论，accept 才提交正式成果。

| 动作 | 请求（除 command 通用字段外） | 成功响应 | 错误码/幂等 |
| --- | --- | --- | --- |
| import | `candidate_id`、`visual_id`、`source_path`、`processed_path`、`source_kind`、声明 hash | `candidate_id`、observed hashes/尺寸/格式、`status: "imported"` | `CANDIDATE_PATH_INVALID`、`CANDIDATE_SOURCE_INVALID`、`CANDIDATE_DUPLICATE`；相同 key+同 hash 返回原 candidate。 |
| validate | `candidate_id` | `validation_id`、`passed`、checks、`status` | `CANDIDATE_NOT_FOUND`、`CANDIDATE_NOT_IMPORTED`、`VALIDATION_FAILED`；同 key 返回同 validation。 |
| accept | `candidate_id`、`accepted_by`（`user` 或 `codex-rule`） | 新 `illustrations.manifest` revision、accepted visual IDs、局部 stale 列表、`status: "succeeded"` | `CANDIDATE_NOT_VALID`、`CANDIDATE_HASH_CHANGED`、`WORK_ORDER_STALE`、`ACCEPT_CONFLICT`；同 key 的已提交事务返回相同 revision。 |
| reject | `candidate_id`、`reason_code`、可选安全短说明 | 候选保留、`status: "waiting-external-output"` | `CANDIDATE_NOT_FOUND`、`WORK_ORDER_STALE`；同 key 返回同拒绝记录。 |
| retry | `scope`（同 stage/unit/visual 约束）和 `reason_code` | 新 `work_order_id` / revision、父 revision、`status: "ready"` | `RETRY_SCOPE_INVALID`、`RETRY_NOT_ALLOWED`；同 key 返回同新 WO，不再增加 attempt。 |

validate 必须逐项输出而非只给布尔值：`source_kind` 是已允许的 `codex-imagegen` 或
`external-import`；source/processed 文件都在该 WO 的候选目录；格式可解码且在 WO 的允许集合；
processed 宽高精确等于对应 storyboard `expected_size`；观察到的 SHA-256 等于 import 声明；
每个请求的 `visual_id` 恰好一次、无额外 visual、且属于输入 `planning.storyboard`。校验过程或
accept 复核任何 hash 改变都不提交正式 Artifact。

一次 accept 可接受一个或多个已通过校验的 visual；必须在一个事务中验证完整 visual coverage
并原子发布全量 `illustrations.manifest`。局部重做时，新 manifest 复用未变 visual 的已验收
revision，只替换目标 visual；CORE 只将该 visual clip 和 `render.manifest`/`output.final-manifest`
标 stale，不能重做 Voice 或其他图片。

## 6. 输入 fingerprint 与失效

CORE 在创建、run、import、validate、accept 前重新比对 `input_fingerprint`。它涵盖 storyboard
revision/hash、style snapshot revision/hash、目标 visual 集合、scope、参数文件 hash 和相关上游
Artifact refs。任一项目变化都使旧 WO stale、拒绝其旧 command，并按当前 Artifact Store 的
`planning.storyboard → illustrations.manifest → render.manifest → output.final-manifest` 依赖方向
传播。局部 Visual retry 不因无关 visual 的变更失效；但 storyboard/style 改变目标 visual 时，
其候选也必须 stale。

## 7. WEB、Skills 与 CLI 的消费边界

WEB 的只读 `StageWorkOrderView` 必须显示：identity、revision、fingerprint（可截断展示）、
status/next_action、scope、输入 Artifact key/revision/hash/status、参数/指令下载引用、输出目录、
expected outputs、candidate summaries、validation checks、可用 commands 与最近稳定 error code。
它不得显示 Secret、Provider URL、绝对路径、完整 prompt/脚本或自行计算状态。布局不是本契约范围。

Skills 先调用 `work-order show --task <id> --run <id> --stage <stage>`，只消费返回的相对路径和
结构化 commands；不再索取 `--script`、`--reference`、`--tts-url`、provider 参数或聊天路径。
CLI 将每个 command 的 argv 逐项传递给 Application Command，不能拼 shell 字符串、直接写
`artifacts/index.json` 或把 candidate 直接放入正式 media。当前 CLI 尚无这些命令，故本节是实现
要求而非现状描述。

完整示例见 [illustration Work Order](examples/illustration-work-order-v1.example.json) 与
[局部 retry](examples/illustration-visual-retry-v1.example.json)。
