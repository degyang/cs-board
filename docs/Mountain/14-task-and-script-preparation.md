# Task、文案整理与画面锚定重点

状态：权威设计基线。Task 输入、画面规划、Voice、对齐和渲染实现必须以本文为准。

## 1. 领域边界

当前产品只存在 **Task**：一条视频从输入、制作到成片的完整聚合。一个 Task 可有多次 **Run**，Run 共享该 Task 已验证的输入与可复用产物。

`Project` 不是当前领域对象、页面、API、CLI 参数或存储目录名。未来如需把多条视频组织为专题、课程或系列，再新增 Project 作为多个 Task 的上层聚合；不得反向把单条制作任务叫 Project。

```text
Task
  └── Run（一次执行、重试或恢复）
        └── Stage / Voice Unit / Visual Item / Artifact

Future Project（当前不存在）
  └── Task *
```

用户界面固定使用“新建任务”“任务队列”“任务工作台”“任务制作输入”“任务 ID”。内部标识也以 `task_id` 为准；旧 `project_id`、`/projects`、`--project` 不保留兼容别名。

## 2. 文案整理：任务创建期的权威输入

“文案整理”替代“文案分割”这个名称。它发生在新建任务期，而不是耗费 LLM/TTS 的运行时生产阶段。

1. 用户输入完整文案和整理规则，例如目标字数、最小/最大长度、句界与段落边界。
2. 确定性整理算法生成有序 Voice Unit；界面可预览、确认和允许受控编辑。
3. 保存 Task 时，后端校验完整覆盖、顺序、连续范围和稳定 Unit ID，并持久化结果。
4. 后续 Run、重试、WebUI 刷新和 Skills 全部读取同一份已保存的整理计划。

WebUI 不得仅把整理结果留在浏览器内存或 localStorage。界面可发起预览，但保存到 Task 的计划才是权威事实；Skills 必须调用同一应用服务，不能自行实现另一套分段逻辑。

最小输入契约：

```json
{
  "task_id": "task-123",
  "script": "完整旁白",
  "script_preparation": {
    "algorithm_version": "deterministic-v1",
    "rules": {"target_chars": 80, "min_chars": 35, "max_chars": 140},
    "voice_units": [
      {
        "unit_id": "unit-001",
        "order": 1,
        "source_range": {"start": 0, "end": 42},
        "text": "连续且不可改写的旁白原文"
      }
    ]
  },
  "visual_anchor_enabled": true
}
```

每个 Unit 不以“2–3 句话”或“1–2 张图”作为硬上限；规则必须允许较长段落和一个 Unit 对应多张图片。

### 2.1 段落优先的确定性整理规则

`target_chars` 是软目标，不能被实现为固定字数硬切。整理顺序固定为：

```text
保留 raw_script
→ CRLF/CR 归一为 LF
→ 按一个或多个真实换行识别段落
→ 段内识别强句末
→ 按 target/min/max 聚合并处理短尾
→ 仅对超过 max 的单句使用弱边界降级
→ 输出无换行 Voice Unit 与 raw source mapping
```

边界优先级如下：

1. 用户原文中的回车/换行是最高优先级段落边界；页面视觉自动换行不是输入边界。段落独立、顺序处理，不跨段合并。
2. 中文 `。！？` 与符合上下文的英文 `.?!` 是强句末；随后的闭合引号、括号属于前句。
3. 只有单句超过 `max_chars` 时，才依次考虑 `；;`、`，,、：:`、破折号和普通空格等弱边界。
4. 找不到安全边界时才按 Unicode grapheme cluster 兜底；有邻近安全边界时不得切开汉字词组、普通英文单词或受保护 token。

英文 `.` 必须结合上下文判断。它位于小数、版本、IP、日期、URL、邮箱、域名、文件名、常见缩写或 initials 内时不是句末，例如 `3.0`、`v2.0.1`、`127.0.0.1`、`example.com`、`a@example.com`、`video.mp4`、`Dr.`、`e.g.`、`U.S.` 均不得拆开。`...`、`……`、`？！`、`!?` 按一个连续句末结构处理。

段内长度策略：

- 完整句子可超过 `target_chars`，但不超过 `max_chars` 时优先保持完整；不得在软目标处切成 `身`/`体` 或 `医学2.`/`0`。
- 段尾低于 `min_chars` 时，先在 `max_chars` 内与前单元合并；否则通过移动完整句子或完整子句再平衡。
- 用户明确输入的短段落可以低于 `min_chars`，但必须记录 `paragraph-boundary` 原因；它与算法制造的短尾严格区分。
- 单句超过 `max_chars` 才按弱边界拆分；目标位置不是硬边界。

原始输入与下游文本分层保存：`raw_script` 用于回读与审计；`normalized_text` 描述布局归一化后的处理覆盖；每个 `voice_unit.text` 必须非空、trimmed、无 CR/LF、无空行碎片。Unit 同时保存到 raw input 的可追溯 mapping，并声明被归一化或忽略的 layout whitespace。前端只调用同一只读预览应用服务并渲染 ordered units，不得再实现第二套 TypeScript tokenizer/packer。

验收矩阵至少覆盖：LF/CRLF/CR/连续空行、混合中英文标点、引号括号、省略号、连续问叹号、小数/版本/IP/URL/邮箱/缩写、无标点超长中英文、超长 token、Emoji/组合字符，以及 min/target/max 前后边界、短尾和显式短段落。结果必须确定、幂等、不丢不重非布局内容，所有下游 Unit 无换行。

### 2.2 已保存的图片与镜头规划

一个 **Voice Unit** 固定对应一个独立 Voice 文件，但不固定对应一张图片。创建/编辑任务时，系统必须把图片数量和每张图片的镜头数作为可追踪的制作决定保存下来：

```text
Voice Unit（连续原文、一个 Voice）
  └── Visual Item *（每项是一张主图）
        └── Shot 1..4（围绕同一主图的展示、绘制、放大或标注片段）
```

`Shot` 是渲染时间片段，不是额外生成的图片。若需要另一张独立插画，必须创建另一个 `Visual Item`，不能把它称为 Shot。

图片数量策略是任务输入的一部分，至少支持：

- `fixed`：每个 Voice Unit 固定 `images_per_unit` 张；
- `adaptive`：按已保存的条件决定，条件包括 `chars_per_image`、`min_images_per_unit`、`max_images_per_unit`、重点/段落密度；
- `manual`：用户在文案整理预览中为某个 Unit 覆盖图片数和每张图片的 Shot 数。

每个图片的 `shot_count` 必须在 1–4 之间。规则计算出的 `visual_id`、图片顺序和 `shot_count` 是保存计划的一部分；LLM 画面锚定可以补充文字重点和画面意图，但不得擅自改变这些数量、顺序或 ID。

最小扩展契约：

```json
{
  "visual_plan_policy": {
    "mode": "adaptive",
    "chars_per_image": 55,
    "min_images_per_unit": 1,
    "max_images_per_unit": 3,
    "default_shot_count": 2
  },
  "voice_units": [{
    "unit_id": "unit-001",
    "text": "连续且不可改写的旁白原文",
    "visual_items": [
      {"visual_id": "visual-001-01", "order": 1, "shot_count": 2},
      {"visual_id": "visual-001-02", "order": 2, "shot_count": 1}
    ]
  }]
}
```

## 3. 运行时：可选的画面锚定重点

原 `segment-script` 生产阶段替换为 `generate-visual-anchors`，用户名称为“生成画面锚定重点”。它只在 `visual_anchor_enabled=true` 时调用 LLM：

- 输入：已保存的 Voice Unit 原文、风格/视觉约束与可控 Prompt 版本；
- 输出：每个 `Visual Item` 的一个或多个重点、每个重点对应的连续 `source_range` 与 `visual_intent`；
- 禁止：改写旁白、合并/拆开 Unit、生成毫秒时间、替代 Whisper；
- 关闭开关：阶段明确 `skipped`，分镜直接使用 Unit 原文与确定性默认视觉策略。

```json
{
  "unit_id": "unit-003",
  "anchors": [
    {
      "anchor_id": "anchor-003-02",
      "anchor_text": "市场有风险",
      "source_range": {"start": 18, "end": 23},
      "visual_intent": "风险提示与谨慎决策"
    }
  ]
}
```

重点文字可以是摘要或视觉提示，但必须引用所属 Unit 的真实连续范围。否则 Whisper 无法把图片切换精确绑定到语音。锚定阶段不得创建或删除图片，也不得改变 `shot_count`。

## 4. 生产顺序与同步

```text
新建任务：文案整理 → 保存 Task Input
运行任务：生成画面锚定重点（可选）
        → 按 Voice Unit 生成 Voice
        → Whisper 对齐 Unit 原文/锚点
        → 分镜补充图片 Prompt 与镜头动作计划
        → 插画 → 渲染 → 合成
```

一个 Unit 的多张图片使用其锚点原文范围定位：Whisper 成功时，在对应原文开始时切换；Whisper 失败时，先按该 Unit 内图片数等比例分配 **实际** Voice 时长，再按每张图片的 Shot 权重（没有权重则按 Shot 数等分）切分该图片时长，并记录 `timing_source=equal_fallback`。fallback 不改变 Unit 原文、图片计划或锚点计划。

## 5. 失效与重试

| 变化 | 必须失效 | 不应重做 |
| --- | --- | --- |
| 文案、文案整理规则、图片/Shot 规则或 Unit 边界变化 | 锚点、Voice、时间线、分镜、插画、渲染、成片 | 无 |
| 仅开关/Prompt 版本/锚点内容变化 | 分镜、插画、渲染、成片 | 文案整理、Voice、Whisper 对齐 |
| 仅图片视觉配置变化 | 插画、渲染、成片 | 文案整理、锚点、Voice、时间线 |
| Whisper 失败 | 该 Unit 的精确时间改为等分 fallback | Voice、其他 Unit |

## 6. 实施验收

- 新建任务保存后，刷新 WebUI 和从 Skills 恢复均获得相同 Voice Unit。
- 画面锚定开关关闭时不调用 LLM；开启时 LLM 输出 100% 可追溯到 Unit 原文范围。
- 任何锚点范围越界、重叠、逆序或不属于所属 Unit 都必须被拒绝。
- 一个 Unit 可按固定、自适应或人工覆盖规则规划多张图片；每张图片具有 1–4 个 Shot。
- 图片切换具有 Whisper 边界或显式等分 fallback；每个 Shot 的时间边界也可追踪。
- API、CLI、WebUI、Skills、Schema 和目录中不再将 Task 称为 Project。
