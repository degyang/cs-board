# Mountain 架构演进计划

状态：实施基线（Task 与文案整理语义待代码迁移落地）

创建日期：2026-08-29
适用仓库：`cs-board`

## 目标

Mountain 将白板声画工坊整理为一套可被两种入口共同驱动的生产系统：

1. WebUI：保留“一次提交、自动完成”的使用方式，同时重整页面信息架构、任务工作台和阶段可见性。
2. Skills：由一个总编排 skill 驾驭六个能力 skill，支持完整生成、单步执行、恢复和人工确认。

两种入口不得各自实现业务逻辑。它们必须通过 API 或 CLI 适配器调用同一个共享工作流内核，并消费相同的任务模型、阶段服务、产物契约、Provider 适配器和渲染器。

## 成功标准

- 同一 `pipeline_version`、输入和设置，从 WebUI 或 Skills 发起时生成相同结构的中间产物。
- 对同一个任务目录继续执行时，两种入口复用相同产物，不重复调用 TTS 或图片模型。
- 所有新流程先划分 Voice Unit 并逐单元生成配音；图片优先使用 Whisper 对齐到真实语音边界，对齐失败时只在该单元内按图片数等分实际音频时长。
- 单个阶段可幂等重跑；输入变化只使依赖它的下游产物失效。
- WebUI、Skills、CLI 和桌面端对同一 Run 使用同一 `trace_id`，可查询相同事件、日志、指标和脱敏诊断包。
- WebUI 不再把输出引擎与视觉参考方式混为同一个模式选择。
- 新产品不保留旧 `Project` 概念或旧接口兼容层；历史材料仅用于审计，不进入新流程。

## 范围

Mountain 的目标覆盖：

- 标准制作；
- 自定义视觉参考；
- 白板动画渲染；
- WebUI 与 Skills 的共享内核；
- Task、Run、阶段与产物的版本化演进。

动态信息图、标准制作和自定义参考共享 Voice Unit、Whisper 对齐、等分 fallback 和累计时间轴。三者的视觉规划与渲染器可以不同，但不能继续维护互不兼容的时间模型。

交付顺序是：先完成并稳定“标准制作 + 预设风格白板”，再在最后一个扩展 PR 接入自定义参考与动态信息图。未完成的组合由 Capability API 显式拒绝。

## 文档索引

| 文档 | 作用 |
| --- | --- |
| [01-current-architecture.md](01-current-architecture.md) | 当前组件、数据流、优点、问题和迁移约束 |
| [02-target-architecture.md](02-target-architecture.md) | 目标分层、共享内核、入口适配器和运行时模型 |
| [03-artifact-contracts.md](03-artifact-contracts.md) | Task、阶段和各类中间产物的权威契约 |
| [04-webui-redesign.md](04-webui-redesign.md) | 页面信息架构、交互流程、组件和 API 需求 |
| [05-skills-design.md](05-skills-design.md) | 七个 Skills 的职责、输入输出、调用规则和目录结构 |
| [06-pr-roadmap.md](06-pr-roadmap.md) | 可逐步合并的 PR 实施路线与依赖关系 |
| [07-validation-strategy.md](07-validation-strategy.md) | 测试层次、双入口一致性、恢复和质量验收 |
| [08-decisions.md](08-decisions.md) | 已接受架构决策、暂缓项和待确认问题 |
| [09-audio-visual-sync.md](09-audio-visual-sync.md) | 统一 Voice Unit、Whisper 优先、多图等分 fallback 与恢复设计 |
| [10-desktop-app-architecture.md](10-desktop-app-architecture.md) | React/Vite WebUI 与 macOS/Windows 桌面 APP 的运行时、打包和安全边界 |
| [11-openai-compatible-model-architecture.md](11-openai-compatible-model-architecture.md) | OpenAI API-compatible 文本/图片端口、Profile、能力检测和旧配置迁移 |
| [12-observability-and-diagnostics.md](12-observability-and-diagnostics.md) | WebUI/Skills共享的结构化事件、trace、日志、审计、脱敏和诊断包 |
| [14-task-and-script-preparation.md](14-task-and-script-preparation.md) | Task/Run 边界、文案整理、画面锚定重点与迁移准则 |
| [15-production-control-and-style-assets.md](15-production-control-and-style-assets.md) | 执行门禁、任务队列、外部素材回存、精确失效与风格模板资产 |

## 统一术语

| 术语 | 定义 |
| --- | --- |
| Task | 当前唯一的制作聚合根，对应稳定 `task_id` 和任务目录。 |
| Run | 对一个 Task 的一次执行尝试。一个 Task 可有多次 Run，但复用有效产物。 |
| Project | 暂未引入的未来上层聚合；若需要，用于组织多个 Task，绝不表示一条视频制作任务。 |
| 文案整理 | 新建任务时按用户规则、句界和长度约束确定 Voice Unit 的确定性准备过程。 |
| 画面锚定重点 | 可选 LLM 产物；基于已确定的 Voice Unit 输出重点文字、原文范围和画面意图，不改写或重分段旁白。 |
| Stage | 有稳定输入、输出、状态和校验规则的一项工作流能力。 |
| Voice Unit | 旁白生成和恢复单元：一段连续原文、一份独立 Voice，以及一张或多张相关图片。 |
| Visual Item | Voice Unit 内的一张图片或一个页面状态；优先绑定真实短语时间，失败时在单元内等分。 |
| Artifact | 阶段写出的文件或结构化数据，由逻辑 key 和内容哈希标识。 |
| Pipeline | 一组有向依赖的 Stage，不限定必须是单一线性流程。 |
| Engine | 最终视觉生产引擎，例如 `whiteboard` 或 `infographic-remotion`。 |
| Visual Source | 视觉约束来源，例如 `preset` 或 `custom-reference`。 |
| Entry Adapter | Web API、CLI 或 Skill；只负责交互和协议转换。 |
| Shared Core | 入口共同调用的领域模型、应用服务、阶段实现和端口。 |
| Trace | 一次 Run 的跨入口、Stage、Provider 和进程调用链，以 `trace_id` 关联。 |
| Domain Event | 可恢复的结构化状态事实；与诊断日志和用户审计分开保存。 |

## 规范 Stage ID

| 顺序 | Stage ID | 用户名称 |
| --- | --- | --- |
| 1 | `generate-visual-anchors` | 生成画面锚定重点 |
| 2 | `clone-voice` | 克隆参考音色与时间同步 |
| 3 | `plan-storyboard` | 拆分文案分镜 |
| 4 | `generate-illustrations` | 生成统一插画 |
| 5 | `render-visuals` | 绘制白板动画或渲染信息图 |
| 6 | `compose-video` | 合成音画成片 |

所有文档、事件、CLI 和 API 使用以上稳定 ID；中文名称只用于显示。

## 设计原则

1. 共享能力只有一个实现；WebUI 和 Skills 是适配器，不是两条业务代码线。
2. JSON 产物先于页面和 Skill 文案；产物契约是跨入口边界。
3. 阶段服务不直接依赖 FastAPI、React 或 Codex Skill。
4. 所有昂贵操作必须幂等、可恢复、可验证并支持内容哈希。
5. Voice Unit 的原文边界由保存的“文案整理”结果唯一确定；画面锚定重点和分镜不得重新分段或改写旁白。时间优先来自 Whisper，fallback 只能使用单元实际 Voice 时长等分且必须显式标记。
6. 运行时状态与业务产物分离；状态文件不能替代产物有效性校验。
7. 新流程使用新的 pipeline version，旧任务不静默升级或误用检查点。
8. 日志默认结构化和脱敏；业务恢复只依赖 Domain Event/Artifact，不依赖日志文本。
