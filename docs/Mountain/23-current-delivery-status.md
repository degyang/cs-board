# Mountain 当前交付状态

状态日期：2026-09-04（整理 2026-09-03 实际进展）
权威集成分支：`integration/mountain-phase-one`
本文只记录已由PM核查的当前事实；目标设计不等于已实现。

## 1. 当前产品目标

近期只打通一条主线：

```text
用户在WebUI新建Task
→ 保存真实文案、参考音频、风格和成片设置
→ 生成六阶段工作条件与工作单
→ Codex按六个能力Skills执行
→ 外部图片等成果回存并验收
→ 渲染与合成final.mp4
→ 用户验收
```

动态信息图、自定义参考、Desktop和Legacy兼容均不在当前主线。

当前近期优先级已经明确：首先关闭 WebUI 与签入原型基线的页面和交互差异，并保持真实 5182 预览供用户同步观察；其次渐进拆离旧 `webapp/server.py` 的业务与工作流耦合；待当前变更形成可审核提交且专项、全量、真实联调门禁通过后，再选择合适窗口回归 `main`。任务包、自定义人物和更深层迁移不得抢占上述 P0 主线。

## 2. 分支和人员状态

| 范围 | 分支/工作树 | 当前事实 |
|---|---|---|
| 集成基线 | `integration/mountain-phase-one@ce8253b` | 2026-09-03 已合并批准的前后端基础与受控联调报告 |
| 昨日联调增量 | `cs-board-phase-one-integration` 工作树 | 文案整理、六阶段真实执行、外部插图候选闭环、Whisper/渲染/合成修复仍为未提交工作树变更 |
| 真实 Task | `task-02b3a76b491445bfaf594b02c75cd70e` | 六阶段均 `succeeded`，已生成 `final.mp4`，等待用户内容验收 |
| 团队运行态 | tmux `wm-csboard-phase-one` | 已恢复；8000 原生后端和 5182 当前 `web-v2` 预览运行中，5183 仅保留为冻结原型对照 |

昨日曾使用 Codex + tmux 的 PM、worker、tester和integration协作模式；任务指令、回执、问题与演化证据保存在 `docs/workmates/`。tmux pane 仅作为运行载体，不作为当前状态事实源。

## 3. 已实现并通过阶段验收

- Task/Run/Stage/Artifact、文件仓储、Telemetry、脱敏和诊断基础；
- OpenAI-compatible动态服务配置、加密Secret、Probe与默认服务；
- 预置/自定义风格和音色资产API；
- 设置页面与资产页面真实API接入；
- Task队列真实API、状态筛选、搜索、cursor和空态；
- IndexTTS、Whisper alignment/fallback、FFmpeg和白板渲染适配器代码；
- 六阶段Application Commands和基础CLI命令；
- 7个Skill文件的初版职责说明；
- 可移植后端启动器和真实前后端contract checker。

以上“实现”不代表六阶段已经用一个真实用户Task完整跑通。

## 4. 2026-09-03 完成的主要工作

### 4.1 第一阶段前后端收口与联调

- 合并批准的前后端基础，形成 `integration/mountain-phase-one@ce8253b`；
- 新建 Task 的真实文案、参考音频、预置风格、音色和成片设置能够保存到后端；
- 对照原型持续修正左侧边栏、资产管理、新建任务六 Tab 和恢复交互；
- 建立 `docs/workmates/` 项目控制面，并验证 Codex/Claude/tmux混合团队的角色、回执和恢复机制；
- 根据用户决定，当前项目的实际执行 Agent 统一使用适当能力的 Codex；高能力升级仍需用户审批。

### 4.2 文案分割

- 以输入段落为最高边界，其次使用中文句末符号，避免把小数中的英文句点当成句末；
- 禁止在普通汉字、数字、小数或未结束的句子中硬切；
- 清理结果中的 CR/LF 和多余空行，使每个 Voice Unit 成为连续原文；
- 修复短句孤立、尾部不足和跨段错误合并等实际样本问题，并补充相应测试与契约说明。

### 4.3 六阶段真实执行链

- 修复项目 Skill 和 Whisper 渲染器错误依赖外部 data dir 的路径问题；
- 发现 Whisper medium 模型缓存不完整，重新取得完整模型并完成真实转写；
- 修复 Whisper schema v2 的 `captions` 解析、毫秒单位和识别文本到原文字符范围映射；
- 修复固定 `voice.alignment-16k.wav` 引起的并发临时文件碰撞；
- 实现插图 Work Order 的候选 `import → validate → accept/reject` 闭环；
- 使用 Codex image generation 为 21 个 Visual 分别生成图片，并逐项校验格式、尺寸、路径、hash和覆盖关系；
- 渲染 21 个独立 H.264 白板片段，再合成带 AAC 语音和烧录字幕的最终 MP4；
- 增加合成前后的真实媒体流、时长和音画一致性验证。

### 4.4 稳定性与门禁

- 定位全量 pytest 的唯一失败为健康检查连接造成的服务端 `TIME_WAIT`，修复显式关闭健康探针的端口释放；
- 同端口立即重启测试连续执行 5 次通过，`tests/test_backend_runtime_17.py` 全文件 `16 passed`；
- 专项回归 `76 passed`；
- 全量 pytest 正常退出：`572 passed, 5 skipped, 3 subtests passed, 0 failed`，耗时 `71.08s`；
- 5 个 skip 为 4 个明确标记废弃的 legacy API 测试和 1 个当前环境缺少 `httpx` 的可选一致性测试，不将它们描述为已执行通过。

## 5. 真实 Task 结果

```text
Task:  task-02b3a76b491445bfaf594b02c75cd70e
Run:   run-7d5e2a1fb3a7481a877fb53fb3aded79
Trace: trace-58b8988a0f844e92a60bfebd31e4ece9
```

- 六个 Stage 均为 `succeeded`，对应 Gate 均有当前 Artifact hash 证据；
- 21 个 Voice Unit、21 张独立插图、21 个独立渲染片段；
- 时间轴总长 `290972ms`，最终媒体实际时长 `290.966s`；
- 最终媒体：MP4，H.264，1440×810，30fps；AAC，22050Hz，单声道；
- 文件大小 `33372334` bytes；
- 最终视频 SHA-256：`a2418187bc9793c58b99ed73bfd4a2c6a8589830748d183dc0fc258c73a4c8a6`；
- 8 个单元记录了 `ALIGNMENT_EQUAL_FALLBACK`。当前每个单元只有一个 Visual，因此不产生单元内图片切换误差；告警仍保留，不能描述为 Whisper 全量成功。

最终文件当前仍在专用临时 data dir：

```text
/tmp/csboard-phase-one-manual-20260903/tasks/<task_id>/runs/<run_id>/output/final.mp4
```

这证明真实六阶段可以生成最终媒体，但不代表用户已完成内容质量验收，也暴露出正式任务成果缺少项目内统一任务包目录的问题。

## 6. 当前仍未关闭的事项

- WebUI 尚未取得逐页、逐 Tab 的原型差异矩阵和当前运行页面验收，原型一致性是现阶段最高优先级；
- 用户尚未对昨日最终视频完成内容质量验收；
- 任务中间文件和最终文件仍散布在专用 data dir，尚未形成项目根目录下的持久任务包；
- 任务工作台对完整 Work Order、外部候选、Gate证据、重做和整包下载的呈现仍需继续完善；
- selective编排仍不是当前已批准范围，不得因昨日人工顺序执行成功而描述为自动编排可用；
- 资产管理的自定义人物、旧 `webapp/server.py` 业务拆分和统一任务包输出都仍是后续规划，不得夹带实现。

## 7. Skills现状

- 目录已统一为`skills/visual-anchor-generator/`；
- 已删除废弃`--script`、`--reference`和`--tts-url`运行参数；
- 六个能力Skill统一先读取Stage Work Order；
- illustration Skill按Codex人工候选闭环执行；
- 昨日已由 Codex 按真实 Work Order 完成一次六阶段实跑；
- 本次执行仍包含人工门禁判断、服务准备和故障修复，不能据此声称已经实现无人值守自动编排。

## 8. 昨日四轮目标的实际位置

| 轮次 | CCF | CCB/核心 | 完成标志 |
|---|---|---|---|
| 1 | 新建任务纠偏 | execution plan纠偏 | 已完成一次真实输入保存与恢复联调 |
| 2 | 展示初始化阶段条件 | 六阶段Work Order与外部成果命令 | 后端闭环已用于真实插图候选；工作台呈现仍需完善 |
| 3 | 工作台呈现输入/指令/输出/成果 | Skills和CLI按工作单实跑 | Codex已人工顺序执行一次六阶段 |
| 4 | 真实状态、预览、重做和最终视频 | 联合E2E与质量验证 | 已得到final.mp4；用户内容验收、重做和任务包持久化未完成 |

轮次完成必须通过PM复验，不以开发者自报或测试数量替代。

## 9. 文档权威顺序

1. 本文当前状态；
2. `22-delivery-roles-and-document-handoff.md`角色与交接；
3. `24-codex-six-stage-execution-contract.md`当前执行契约；
4. PM明确点名的本轮指令及最新审核段落；
5. `02/03/07/09/12/14/15`专题设计；
6. 其他设计作为目标或阶段基线；
7. `m*-report/audit`仅为历史证据。

若文档与当前代码冲突，执行者记录Contract Gap，由PM裁决并同步本文；不得自行选择较方便的旧文档。

## 10. 已确认但尚未进入实现的后续规划

- 渐进脱离旧 `webapp/server.py`：冻结旧模块，不再新增业务；将领域规则、应用用例、工作流 Stage、端口和 adapter 分离到共享内核，新 Mountain 服务仅保留装配与 HTTP/SPA 适配。
- 资产管理规划增加“自定义人物”：人物及人物组成为版本化一等资产，Task 引用 revision，Run 保存不可变 character snapshot。
- 所有 Task 的输入、中间文件、候选、证据和最终文件规划统一归档为 `<project-root>/outputs/<task_id>/` 下的可管理任务包；多 Run、canonical storage、迁移和清理策略待讨论。
- 上述三项不因昨日实跑而自动进入实现；必须由 PM 依据 [28-domain-extraction-and-character-assets-roadmap.md](28-domain-extraction-and-character-assets-roadmap.md) 分别建立实施或迁移任务。

规划收口后，项目将通过项目级 `pos-workmates` 恢复 tmux 团队：使用真实 Codex Agent 同时启动前端、后端、各自测试与 integration 工作，PM 保持可响应并负责验收和续派。默认能力为 `standard/medium`，`sol high` 及以上仍须用户审批。团队运行期间应维持与当前工作树绑定的 5182 WebUI 预览，并把真实进程、健康状态和验证时间同步到 `docs/workmates/board.md`，使用户能够边观察边反馈。

## 11. 2026-09-04 当前增量

- 资产风格已与输出引擎解耦：资产页删除引擎筛选和风格详情的输出引擎控件，新建任务按 `kind=preset` 获取风格；动态信息图是否可选仍由服务端 `create-options` 决定。
- “纸感隐喻拼贴风”已迁移 9 条参考图路由，“漫画墨线解释风”已迁移 5 条；每条规则保存名称、关键字、有序图片资产 ID，种子只补齐缺失配置，不覆盖用户显式清空或后续编辑。
- 资产页可预览、上传、移除、排序和编辑路由；后端验证规则数量、关键字、图片数量、图片真实性与资产存在性。插图应用服务按首条关键字命中读取真实 blob，并把一至三张参考图传给图片 Provider；manifest 记录命中规则。
- 根启动器和 Windows 空闲重启脚本已改为 `scripts/run_mountain_backend.py`、`webapp.mountain_server`、`web-v2` 及 `/api/v1` 健康契约；旧 `webapp/server.py` 不再是这些活动启动入口。旧模块本体仍保留为待归档输入，不能描述为已经删除。
- 真实 5182 浏览器检查已确认页面来自当前工作树：没有风格引擎筛选或输出引擎字段，纸感风格展示 9 条规则和 11 张参考缩略图，编辑态有 9 个图片上传入口。
- 动态信息图、自定义参考风格和音色资产仍未形成完整原生执行链，继续保持不可选；不得因资产或枚举已经存在而提前解锁。
- 当前集成工作树包含大量跨批次未提交修改；`main` 与集成分支也各自有独立提交。必须先冻结、拆分可审核提交并在临时集成分支吸收 `main` 后才能回归，禁止在此脏工作树直接 merge。
- 当前团队成本策略：后端 worker/tester 保持 Codex；PM、前端、前端 tester 和 integrator 使用 Claude Code 缺省模型、medium。只有可复核的能力不足才申请 high，且升级前须用户批准。
- 后端并发输入保存曾在全量门禁中复现跨 Repository 实例混写；task lock 已提升为按 canonical root + task ID 共享，两轮 20/20 并发重复和两轮 122/122 受影响矩阵通过。串行全量为 644/644、0 skip，但受真实子进程、HTTP 探针和文件 I/O 等待影响耗时 242.34 秒；项目新增 `scripts/run_backend_test_gate.py`，将全部 61 个 `test_*.py` 文件唯一分配到四个并行 pytest 分片，并把任何 skip 视为失败。该门禁实跑 644 passed、3 subtests passed、0 failed、0 skipped，墙钟 55.22 秒。
