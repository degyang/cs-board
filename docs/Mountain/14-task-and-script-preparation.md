# Task、文案整理与画面锚定重点

状态：权威设计基线，待 Task 术语迁移和流水线重构落地。

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

## 3. 运行时：可选的画面锚定重点

原 `segment-script` 生产阶段替换为 `generate-visual-anchors`，用户名称为“生成画面锚定重点”。它只在 `visual_anchor_enabled=true` 时调用 LLM：

- 输入：已保存的 Voice Unit 原文、风格/视觉约束与可控 Prompt 版本；
- 输出：每个 Unit 的一个或多个重点、每个重点对应的连续 `source_range` 与 `visual_intent`；
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

重点文字可以是摘要或视觉提示，但必须引用原 Unit 的真实连续范围。否则 Whisper 无法把画面切换精确绑定到语音。

## 4. 生产顺序与同步

```text
新建任务：文案整理 → 保存 Task Input
运行任务：生成画面锚定重点（可选）
        → 按 Voice Unit 生成 Voice
        → Whisper 对齐 Unit 原文/锚点
        → 分镜决定每个 Unit 的图片数量与视觉计划
        → 插画 → 渲染 → 合成
```

一个 Unit 的多张图片使用其锚点原文范围定位：Whisper 成功时，在对应原文开始时切换；Whisper 失败时，按该 Unit 内图片数等比例分配 **实际** Voice 时长，并记录 `timing_source=equal_fallback`。fallback 不改变 Unit 原文或锚点计划。

## 5. 失效与重试

| 变化 | 必须失效 | 不应重做 |
| --- | --- | --- |
| 文案或文案整理规则/Unit 边界变化 | 锚点、Voice、时间线、分镜、插画、渲染、成片 | 无 |
| 仅开关/Prompt 版本/锚点内容变化 | 分镜、插画、渲染、成片 | 文案整理、Voice、Whisper 对齐 |
| 仅图片视觉配置变化 | 插画、渲染、成片 | 文案整理、锚点、Voice、时间线 |
| Whisper 失败 | 该 Unit 的精确时间改为等分 fallback | Voice、其他 Unit |

## 6. 实施验收

- 新建任务保存后，刷新 WebUI 和从 Skills 恢复均获得相同 Voice Unit。
- 画面锚定开关关闭时不调用 LLM；开启时 LLM 输出 100% 可追溯到 Unit 原文范围。
- 任何锚点范围越界、重叠、逆序或不属于所属 Unit 都必须被拒绝。
- 分镜可为一个 Unit 规划多张图片；其每次切换都具有 Whisper 边界或显式等分 fallback。
- API、CLI、WebUI、Skills、Schema 和目录中不再将 Task 称为 Project。
