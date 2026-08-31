# 制作控制面、外部资产与风格模板

状态：权威设计基线。本文定义执行策略、任务队列、人工外部制作、资产回存和风格模板边界；旧 `webapp/server.py` 的内存 Job、硬编码风格和自动图片调用不属于新产品。

## 1. 领域边界

```text
制作控制面                         资产管理
Task → Run → Stage → Unit/Visual    风格模板 / 参考素材 / 音色资产
状态、队列、门禁、重试、失效           创建、版本、启停、预览、引用
```

- 工作流内核只消费某次 Run 的不可变风格快照，绝不硬编码预置风格、角色、提示词常量或资产文件名。
- 资产管理维护预置风格和自定义风格；模板修改不追溯改变已开始的 Run。
- 任务队列是生产控制中心；任务工作台是单 Task/Run 的细粒度控制与验收界面。
- WebUI、CLI 和 Skills 调用同一 Application Command、读取同一 Run 状态和 Artifact，不得各自维护进度或重做逻辑。

## 2. 新建任务：执行策略

成片设置保存 `execution_policy`。Task 可保存默认值；创建 Run 时写入不可变快照，后续新 Run 可选择新策略。

```json
{"mode":"auto","manual_stages":[],"version":1}
```

| UI 选择 | 保存值 | 行为 |
| --- | --- | --- |
| 自动完成 | `auto`, `[]` | 能力满足时连续执行到成片，或停在外部素材门禁。 |
| 手动完成：每道工序 | `manual`，六个 Stage ID | 每个 Stage 开始前等待用户触发。 |
| 手动完成：指定工序 | `manual`，用户多选 Stage ID | 未选 Stage 连续执行，直至下一人工门禁。 |

稳定 Stage ID 为：`generate-visual-anchors`、`clone-voice`、`plan-storyboard`、`generate-illustrations`、`render-visuals`、`compose-video`。前端只显示中文名。

### 2.1 必须区分的等待状态

| 状态 | 含义 | 下一动作 |
| --- | --- | --- |
| `waiting-manual-trigger` | 用户将此 Stage 配为手动；该 Stage 尚未运行。 | 执行此工序。 |
| `waiting-external-output` | 已生成外部制作任务包，等待素材、导入和验收。 | 导入候选，再验收。 |
| `failed` | 真实执行或校验错误。 | 修复、重试或替换。 |

手动执行一个 Stage 后，编排器继续自动执行后续未选择的 Stage，直到下一个门禁。未满足等待条件时 `resume` 必须保持等待，不能标记成功或执行下游。

“自动完成”表示所有必需能力可由 API 无人值守完成。当前视觉来源为人工 Codex 时，插画阶段必然进入 `waiting-external-output`，页面和 CLI 必须明确提示它不是无人值守自动成片。

## 3. 任务队列与任务工作台

### 3.1 队列

`/tasks` 是生产控制面：按运行中、等待人工、等待外部、失败、更新时间排序；每项显示当前 Run、执行策略、阻塞 Stage、六阶段摘要、Voice/Visual/Asset 数量、fallback/错误摘要、短 `trace_id` 与成片（若可用）。队列操作只包含继续、暂停、取消、打开工作台、诊断；不得通过前端删文件或推测状态。

### 3.2 工作台

`/tasks/<task_id>` 展开 Stage、Voice Unit、Visual Item、Shot 与 Artifact。用户可以试听/预览成果，查看稳定 ID、输入 hash、生成参数和目标路径，发起最小范围重做、外部制作任务包、导入、验收，并在执行前看到下游失效范围。

## 4. 外部制作、导入与精确失效

对 Voice、Image、Clip 或 Final 的“重做”先产生版本化参数包。用户选择：当前服务执行、生成 Codex Skill 任务包、或外部工具制作后导入。

图片的 `illustrations.job` 指定项目 `skills/illustration-generator/SKILL.md` 与 Codex `imagegen` Skill，并逐项提供 `visual_id`、prompt、negative prompt、尺寸、风格快照、参考资产相对路径和唯一候选输出路径。

```text
任务包 → candidate outputs → import（校验） → candidate Artifact
       → preview / 人工验收 → 原子提交 → 正式 Asset / manifest
```

外部文件不能直接写入正式 `media/` 或资产库。导入校验 ID 完整性、无额外文件、格式、可解码性、尺寸/时长、hash、路径边界和来源 Run；验收重新校验 hash，并以 staging + 原子提交或可恢复事务完成。`import` 不等于 `accept`。

| 被替换成果 | 必须失效 | 不失效 |
| --- | --- | --- |
| 一个 Voice Unit | 本 Unit timeline、相关 clip、final | 其他 Unit Voice/图片 |
| 一个 Visual 图片 | 该 Visual clip、final | Voice、其他图片 |
| 一个 Render Clip | final | Voice、图片、其他 clip |
| 成片设置 | final（必要时字幕） | Voice、图片、clip |

失效是结构化命令/Event，不是删除文件；旧 Artifact 保留 revision 与审计关系。

## 5. 风格模板与资产管理

资产管理包含“预置风格”“自定义风格”“音色库”。预置模板可复制为自定义模板；自定义模板可引用参考图、角色组与授权素材。

```json
{
  "template_id":"style-whiteboard-minimal",
  "revision":3,
  "kind":"preset",
  "name":"极简粗线简笔白板风",
  "engine_compatibility":["whiteboard"],
  "status":"active",
  "prompt_rules":{"base_prompt":"...","negative_prompt":"..."},
  "visual_bible":{"palette":["#000000"],"line_style":"..."},
  "references":[{"asset_id":"asset-style-ref-001","role":"style-reference"}]
}
```

新建任务只选择 `style_template_id` 与 revision；创建 Run 时生成 `style.snapshot` Artifact。Storyboard、Codex 任务包和 Renderer 均消费快照，而非查询可变模板。

风格 CRUD、上传、版本、启停、预览属于资产管理领域；Pipeline 只校验模板与 Engine 兼容性和快照引用完整性。Provider 配置属于设置，不属于风格资产；密钥不得进入模板、任务包、Artifact、日志或浏览器存储。

## 6. 新服务入口与验收

新产品入口为 `webapp.mountain_server:app`，只装配 Mountain v1 Task API、共享内核、静态 Vite SPA 与必要生命周期依赖；不得导入 `webapp.server`、`mountain_api`、`mountain_stages`、`LegacyJobBridge` 或旧 `JOBS`。

验收要求：同一策略从 WebUI、CLI、Skills 获得相同等待点、Run View、Event 和 Trace；队列能区分人工触发/外部素材/失败；单 Asset 重做只失效必要下游；人工 Codex 出图 E2E 必须有真实 Skill 输出、导入/验收记录、最终 MP4 与 ffprobe 音视频流。PIL、placeholder、Fake 不能作为 E2E 出图证据。
