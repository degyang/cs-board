# Codex 六阶段执行交付契约

状态：当前主线契约草案。  
已实现程度必须结合 [23-current-delivery-status.md](23-current-delivery-status.md)；本文定义下一阶段要补齐的工作条件，不表示Work Order已经存在。

## 1. 使用边界

- 用户只通过WebUI提供真实制作输入和验收决定；
- CCF呈现后端事实，不产生业务工作单；
- CCB/共享内核生成和维护工作单、状态与Artifact；
- Codex只读取工作单和对应Skill执行，不从聊天猜参数/路径；
- WebUI、CLI和Skills读取同一Task/Run/Artifact状态。

## 2. Task创建后的必要输入

当前代码已保存或正在接入：

| 输入 | 当前事实 |
|---|---|
| `title`、`pipeline_id=mountain-av-v1`、`engine=whiteboard` | 已实现 |
| 完整`script` | 已实现 |
| `min_chars/target_chars/max_chars`及script preparation | 已实现 |
| reference音频文件 | 已实现；首次保存必需 |
| `style`名称 | 已实现；`style_id`快照尚未接入Task输入 |
| `visual_anchor_enabled` | 已实现 |
| `include_subtitles/pen_text/stroke_detail` | 已实现 |
| `execution_plan.mode/manual_stages` | CCB纠偏中，尚未验收 |
| 每Voice Unit图片数、每图片1–4分镜 | 领域设计存在，WebUI/Task保存契约尚未收口 |

## 3. 规范六阶段

| 顺序 | Stage ID | Skill | 规范主输出 |
|---|---|---|---|
| 1 | `generate-visual-anchors` | `visual-anchor-generator` | `planning/av-plan.json` |
| 2 | `clone-voice` | `voice-cloner` | unit WAV、`audio/voice-manifest.json`、`timing/timeline.json` |
| 3 | `plan-storyboard` | `storyboard-planner` | `planning/storyboard.json`和图片prompt |
| 4 | `generate-illustrations` | `illustration-generator` | source/final图片、`illustrations/manifest.json` |
| 5 | `render-visuals` | `visual-renderer` | clips、silent master、`render/manifest.json` |
| 6 | `compose-video` | `av-compositor` | SRT、`output/final.mp4`、`output/final-manifest.json`、质量报告 |

`video-workflow`是编排Skill，不计入六个能力Stage。

## 4. Stage Work Order 最小结构

下一后端切片必须先通过Schema/领域测试冻结以下语义，字段名可以在实现前由PM根据现有模型微调：

```json
{
  "schema_version": "1.0",
  "task_id": "task-...",
  "run_id": "run-...",
  "stage": "generate-illustrations",
  "skill": "illustration-generator",
  "status": "ready",
  "input_artifacts": [],
  "parameters_path": "work-orders/generate-illustrations/parameters.json",
  "instructions_path": "work-orders/generate-illustrations/instructions.md",
  "output_directory": "artifacts/illustrations/candidates",
  "expected_outputs": [],
  "run_command": [],
  "import_command": [],
  "validate_command": [],
  "accept_command": [],
  "retry_command": []
}
```

要求：

- 所有文件路径是Task/Run内规范相对路径；
- 命令以参数数组或结构化对象保存，不保存shell拼接字符串；
- instructions不包含Secret、完整Provider响应或绝对路径；
- input Artifact必须带key、revision、hash和状态；
- expected output必须能由领域校验，而非仅检查文件存在；
- 工作单revision与输入fingerprint绑定，上游变化后旧工作单必须stale。

## 5. Codex执行状态

当前产品需要的状态目标：

```text
blocked-input
ready
running
waiting-manual-trigger
waiting-external-output
validating
waiting-acceptance
succeeded
failed
stale
```

这些状态尚未全部实现。下一切片不得把未实现状态只作为前端字符串添加；必须由后端状态机、事件和测试支持。

## 6. 外部/Codex成果闭环

插画阶段是首个必须支持的外部成果阶段：

1. Storyboard完成后生成每个Visual的提示词、参考资产和目标规格；
2. Work Order进入`waiting-external-output`；
3. Codex读取指令，调用可用图片能力，将候选写入指定候选目录；
4. 使用import命令登记候选，不允许直接改Artifact index；
5. validate检查格式、尺寸、Visual覆盖、hash和安全约束；
6. 用户或Codex按规则accept；
7. accept后才提交`illustrations.manifest`并允许渲染；
8. reject保留审计和原因，可生成retry工作单；
9. 单Visual重做只失效该Visual必要下游。

目前上述完整命令和状态尚未实现。

## 7. 六阶段逐项工作条件

### 7.1 generate-visual-anchors

- 输入：已保存script preparation、锚定开关、文本服务配置；
- 关闭锚定时使用确定性默认Visual计划并明确`skipped/default`；
- 开启时LLM失败允许受控fallback并产生warning；
- 输出必须保持Voice Unit原文、范围和顺序。

### 7.2 clone-voice

- 输入：AV Plan、已保存reference、动态TTS/alignment/media服务；
- 每Voice Unit独立WAV；
- Whisper失败只在该Unit内按Visual数量等分真实音频时长；
- 不允许Skill再要求用户从聊天传`tts-url`或reference绝对路径。

### 7.3 plan-storyboard

- 输入：AV Plan、Timeline、风格快照和锚定设置；
- 输出每个Visual的构图、prompt、overlay和1–4 shot规划；
- 不改变原文、Voice Unit、Visual数量或时间边界。

### 7.4 generate-illustrations

- 自动图片API和Codex人工生成共享同一Storyboard与验收规则；
- 当前近期验收优先打通Codex人工生成；
- source与处理后图片分离；候选未accept不得成为正式Artifact。

### 7.5 render-visuals

- 输入只来自已验收插画、Timeline和白板参数；
- 每个Visual/Shot生成可追踪clip；
- 不重复计算Whisper或重新估算Voice时长。

### 7.6 compose-video

- 输入Voice Manifest、Timeline、Render Manifest和字幕设置；
- 输出必须包含视频/音频流和质量验证；
- `validation.passed != true`不能标记Stage成功。

## 8. WebUI初步可用的完成定义

新建任务只有满足以下条件才称为“初步可用”：

- 用户能完成六Tab并保存全部当前必需输入；
- 保存后Task/Run可读取相同inputs与execution plan；
- 系统可以为六阶段计算`blocked/ready`条件；
- 每阶段可查询输入、参数、指令、输出目录和预期成果；
- Codex可从CLI读取工作单并执行，不需要用户提供路径；
- 外部图片可回存和验收；
- 阶段完成后下一阶段条件自动更新；
- 最终能够用一个真实用户Task生成并播放`final.mp4`。

在最终一条完成前，可以称“新建任务表单可用”或“阶段工作条件可用”，不能称“完整工作流可用”。
