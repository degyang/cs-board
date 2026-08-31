# 架构决策与待确认项

## 1. 已接受决策

### D-001：WebUI 与 Skills 共享同一个应用内核

状态：接受。

Web 通过 API adapter、Skills 通过 CLI adapter 调用同一组 Application Commands。任何入口不得复制 Prompt、Provider 或恢复逻辑。

### D-002：采用模块化单体，不拆微服务

状态：接受。

当前本地部署、文件产物和本机渲染不需要分布式系统复杂度。通过 Ports and Adapters 保留未来替换队列或存储的能力。

### D-003：先定义产物契约，再重构实现

状态：接受。

JSON Schema、fingerprint、revision 和失效规则是双入口一致性的基础。UI 和 Skill 只能消费这些契约。

### D-004：标准白板采用七个 Skills

状态：接受。

一个 workflow 编排 Skill 加六个能力 Skill。总编排不作为用户进度时间线中的生产阶段。

### D-005：文案分割与视觉分镜分离

状态：已由 D-016 替代。

早期设计把配音分段和图片范围留给不同阶段，导致 TTS 后仍需再次决定文字—图片关系。D-016 将两者统一提前到 AV Plan。

### D-006：早期标准白板使用两层时间模型

状态：已由 D-016 替代。

早期两层时间模型不再进入目标 Schema；历史原因保留，目标实现统一使用 Voice Unit / Visual Item。

### D-007：输出引擎与视觉来源是两个维度

状态：接受。

`engine = whiteboard | infographic-remotion`；`visual_source = preset | custom-reference`。前后端都不再使用混合含义的 `pageMode` 作为领域字段。

### D-008：动态信息图保留独立 Pipeline Graph

状态：已由 D-016 和统一阶段图替代。

现有动态信息图顺序只作为 legacy adapter 保留。所有新任务使用 `mountain-av-v1`，模式差异只存在于视觉规划和 renderer adapter。

### D-009：显式版本隔离新旧流程

状态：接受。

新任务使用 `mountain-av-v1`。旧任务使用 legacy adapter，不静默补造精确同步 manifest。

### D-010：一致结果以同一内核与产物契约定义

状态：接受。

对同一 Project 两种入口必须复用相同 Artifact，并得到相同 final hash。分别重新调用非确定性模型的两个 Project 只要求同 pipeline、契约、规则和质量，不要求像素级一致。

### D-011：WebUI 默认保持自动执行

状态：接受。

阶段化用于透明度、恢复和返工，不要求普通用户逐步确认。Skills 额外提供 gated policy，但不改变业务指纹。

### D-012：先集中轮询，SSE 后置

状态：接受。

第一阶段消除重复 timer 并使用权威 Project View。事件模型稳定且确有需要后再加入 SSE。

### D-013：段内图片切换必须依赖真实短语对齐

状态：已由 D-017 替代。

仍保留“优先使用真实声学时间”的目标，但不再要求对齐失败即阻断；失败时使用整 Voice Unit 等分。

### D-014：分段优先解决可靠性，并发优化独立验证

状态：接受。

语义分段可以降低超长单次请求风险和失败返工，但不承诺自然降低总 TTS 计算量。项目内默认串行；只有多节点音色一致性实测通过后才开放最多 2 路并发，下游跨阶段流水化放在独立性能 PR。

### D-015：不按文案长度自动切换 legacy 与 v2

状态：接受。

所有新任务统一使用 `mountain-av-v1`。短文案可以自然形成一个 Voice Unit，不需要走旧流程。`standard-v1-legacy` 只用于读取历史任务、显式复现旧结果或受控故障排查，不能根据字符数静默选择。

### D-016：三种模式统一使用 Voice Unit 时间模型

状态：接受；替代 D-005 和 D-006 的早期两层时间模型。

智能文案分割直接产生有序 Voice Unit。每个单元包含一段不可改写的连续原文，独立生成一个 Voice，并关联一张或多张 Visual Item。标准制作、自定义参考和动态信息图共享该模型；模式差异只保留在视觉规划和渲染器。

### D-017：Whisper 优先，单元内等分 fallback

状态：接受；替代 D-013 的“对齐失败即阻断”规则。

每个 Voice Unit 生成后优先通过 Whisper 将 Visual Item 的原文范围对齐到真实语音边界。若 Whisper 执行失败或该单元不能形成合法、单调、完整的时间边界，则整个单元切换为 `equal_fallback`：按照图片数量等分该单元 Voice 的实际媒体时长。禁止在同一单元内混用部分精确、部分估算边界。

### D-018：fallback 必须可见且可复现

状态：接受。

若单元时长为 `D`、图片数为 `N`，第 `i` 张图片的本地边界为 `floor(i × D / N)` 到 `floor((i + 1) × D / N)`。产物必须记录 `timing_source=whisper` 或 `timing_source=equal_fallback`；WebUI 和 Skills 必须显示 fallback 告警，但任务可以继续完成。

### D-019：WebUI 收敛为 React + Vite SPA

状态：接受。

当前页面本质是通过 HTTP 调用 FastAPI 的客户端工作台，不需要 SSR、RSC、Server Actions 或 Cloudflare Worker 运行时。目标 WebUI 使用纯 React + Vite 构建：开发时由 Vite dev server 代理 `/api`；生产 Web 和桌面模式均由 FastAPI 同源托管 SPA `dist` 与 `/api`，Electron 在后端健康检查通过后加载该本机 URL。

### D-020：桌面 APP 使用薄壳 + 本地 Backend Sidecar

状态：接受架构边界，桌面壳技术选型待 spike。

macOS/Windows APP 不复制业务逻辑。桌面壳只负责窗口、进程监管、文件对话框、系统密钥、更新和本机认证；FastAPI sidecar 同源提供 Vite SPA 与 API，并继续装配共享 `csboard` 内核。Electron 是优先验证候选，但 Electron/Tauri 的最终选择不能改变应用命令、API 或 Artifact 契约。

### D-021：模型接口采用 OpenAI API-compatible Profile

状态：接受。

文本和图片模型不绑定 OpenLux、OpenAI 或其他品牌。首版文本基线使用 `/v1/chat/completions`，可选支持 `/v1/responses`；图片使用独立 `ImageModelPort` 和兼容的 `/v1/images/generations` 能力。base URL、secret、protocol 和 model 由可命名 profile 配置，Pipeline 只依赖能力契约。

### D-022：WebUI 与 Skills 共享同一可观测性事实

状态：接受。

每个 Run 持久化唯一 `trace_id`；Web、Desktop、CLI 和 Skill 命令记录独立 `command_id`，Stage/Provider/Process 使用父子 `span_id`。Domain Event、Diagnostic Log 和 Audit Record 分开保存但使用相同关联 ID。WebUI 与 Skills 只能消费结构化事件和日志 API/CLI，不维护各自的进度真相。

### D-023：日志默认脱敏并支持诊断包

状态：接受。

Provider 密钥、Authorization、Cookie、完整 Prompt、完整原文和媒体不进入默认日志。所有日志先经过统一 Redactor；WebUI 和 CLI/Skills 均可导出相同的脱敏诊断包。首版本地 JSONL 为权威存储，同时保留 OpenTelemetry trace 字段供未来扩展。

### D-024：当前制作聚合根统一命名为 Task

状态：接受；替代当前设计中把单条视频制作对象称为 Project 的表述。

新产品不考虑旧接口或目录兼容。Domain、Repository、API、CLI、Skills、WebUI、Schema、文档和目录统一使用 Task/`task_id`/`tasks/`。Project 暂不引入；未来若需要，它只能组织多个 Task，不能作为 Task 的别名。

### D-025：文案整理前置，LLM 仅生成画面锚定重点

状态：接受；替代 D-016 中“智能文案分割直接产生 AV Plan”的表述。

新建任务时以确定性规则完成“文案整理”，保存 Voice Unit 及其原文范围为任务输入。运行时可选 `generate-visual-anchors` 使用 LLM 生成重点、原文范围和画面意图；它不得重新整理或改写旁白。Storyboard 基于 Unit、锚点和 Voice/Whisper 结果决定 Visual Item 数量；对齐失败仍按 Unit 内图片数等分实际 Voice 时长。

### D-026：执行策略采用可选 Stage 门禁

状态：接受。成片设置支持自动完成、全部手动和指定 Stage 多选手动。策略是 Run 不可变快照；编排器在被选 Stage 前等待人工触发，并在其他 Stage 间连续运行。`waiting-manual-trigger` 与失败、外部素材等待严格区分。

### D-027：人工 Codex 出图采用外部素材门禁

状态：接受。当前图片通过 `illustrations.job` 指定项目插画 Skill、Codex `imagegen` Skill、参数与受控路径。图片必须导入校验、人工验收；未验收时为 `waiting-external-output`，下游不能运行。PIL、placeholder、Fake 或 API Provider 不能代替人工 Codex E2E。

### D-028：任务队列是生产控制面

状态：接受。任务队列展示 Task/Run 的工作流、阻塞、成果和告警；工作台提供 Stage/Unit/Visual/Asset 级执行、预览、重做、导入和验收。重做展示可复现参数，并通过精确失效命令影响必要下游。

### D-029：风格模板属于资产管理，不属于工作流内核

状态：接受。预置风格、自定义风格、参考图和角色组以版本化资产模板维护。新建任务只引用模板 ID/revision；Run 保存 style snapshot。新服务、Pipeline 和 Stage 不得保留旧 `server.py` 风格常量或提示词字典。

### D-030：新产品使用独立 Mountain 服务入口

状态：接受。`webapp.mountain_server:app` 是新产品唯一启动入口，只装配 Mountain v1 API、共享内核和新版 SPA。旧 `webapp/server.py`、LegacyJobBridge、旧 Job API 与旧 Mountain routes 不参与新产品启动或测试。

## 2. 暂缓决策

### P-001：允许用户编辑 Voice Unit 或 Visual Item 边界

暂缓到精确失效、分段语气和只读计划稳定后。首版只允许重新运行分割，不支持拖拽合并/拆分。

### P-002：自动 annotation 的高级人工编辑器

现有预览台可继续作为人工精修工具。是否嵌入 Web 工作台在核心 pipeline 完成后评估。

### P-003：事件推送协议

先使用集中轮询；SSE 优先于 WebSocket，除非未来确实需要双向实时编辑。

### P-004：跨机器/对象存储

Artifact Store 先实现本地文件系统。接口不暴露绝对路径，为以后对象存储保留空间。

### P-005：删除旧 Artifact revision

首版只失效、不自动删除。清理策略必须考虑磁盘空间、审计和用户恢复后单独设计。

## 3. 实施前需要确认或实测

### Q-001：IndexTTS 的推荐单段范围

需要在目标环境实测：

- 安全最大字符数；
- 推荐语义段时长；
- 多段连续合成的语气一致性；
- 输出采样率、声道和容器；
- 首尾静音与响度波动。

该结果决定 Voice Unit 的系统级边界约束，但不作为普通用户设置暴露。

### Q-002：最大 Project 规模

需要确定：

- 最长文案或成片时长；
- 最大 Voice Unit 和 Visual Item 数；
- 最大图片调用数；
- 磁盘配额；
- 局域网共享队列的总任务限制。

### Q-003：新流程成为默认的时点

建议顺序：CLI/Skills internal → Web Beta → 新项目默认 → legacy 只读/显式兼容。默认切换必须满足验证文档中的发布门槛。

### Q-004：动态信息图是否支持自定义人物参考

当前 UI 的概念重整要求 capability 明确返回组合是否支持。在没有稳定视觉规范前可以返回 unsupported，但不能靠前端隐式隐藏。

### Q-005：Mountain Project 物理目录名

当前设计使用 `.webapp/projects/<id>` 与 legacy `.webapp/jobs/<id>` 隔离。M02 实施时再次确认是否接受该迁移期物理布局；逻辑 API 不受最终目录名影响。

### Q-006：项目内分段 TTS 并发

分单元降低单次请求长度和失败返工，但不会自动减少总计算量。需要实测同一参考音色在两个语音节点并行生成不同 Voice Unit 时是否产生可闻差异；通过前默认项目内串行，通过后最多开放 2 路受控并发。

## 4. 决策变更流程

更改已接受决策时：

1. 在本文件增加新决策，不能直接抹掉历史原因；
2. 标明替代的决策编号；
3. 列出受影响的 Schema、Stage、PR 和迁移；
4. 若改变产物语义，增加 schema 或 contract version；
5. 更新 README 索引和相关设计文档。
