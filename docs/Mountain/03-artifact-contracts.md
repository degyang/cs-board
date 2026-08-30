# Artifact 与状态契约

> **目标契约迁移。** 当前代码中的 `Project/project_id/projects/` 和 `segment-script/av-plan` 为待删除的中期实现术语。本文件从 Task 迁移完成起以 `Task/task_id/tasks/`、保存的文案整理计划和 `generate-visual-anchors` 为权威；不保留旧兼容读取。

## 1. 契约目标

Artifact 是 WebUI、Skills、CLI、桌面端和各 Stage 之间唯一可持久交换的业务结果。实现不得依赖临时文件名、页面状态或自然语言日志推断任务是否完成。

所有 JSON Artifact 必须包含：

- `schema_version`、`artifact_type`、`artifact_id`、`artifact_key`；
- `task_id`、`run_id`、`pipeline_id`、`engine`；
- `created_at`、`producer_stage`、`producer_version`；
- `input_fingerprint` 和文件引用的相对路径/hash；
- 稳定 ID 引用，不复制或重写上游事实。

首版逻辑 key 固定为：

| 文件 | `artifact_key` |
| --- | --- |
| `av-plan.json` | `planning.av-plan` |
| `voice-manifest.json` | `audio.voice-manifest` |
| `timeline.json` | `timing.timeline` |
| `storyboard.json` | `planning.storyboard` |
| `illustration-manifest.json` | `illustrations.manifest` |
| `render-manifest.json` | `render.manifest` |
| `final-manifest.json` | `output.final-manifest` |

## 2. 任务目录

```text
tasks/<task_id>/
├── task.json
├── inputs/
│   ├── source-script.txt
│   ├── script-preparation.json
│   ├── reference-audio.*
│   └── reference-images/
├── runs/<run_id>/
│   ├── run.json
│   ├── artifacts/
│   │   ├── av-plan.json
│   │   ├── voice-manifest.json
│   │   ├── timeline.json
│   │   ├── storyboard.json
│   │   ├── illustration-manifest.json
│   │   ├── render-manifest.json
│   │   └── final-manifest.json
│   ├── media/
│   │   ├── voices/
│   │   ├── images/
│   │   ├── clips/
│   │   └── final/
│   ├── observability/
│   │   ├── events.jsonl
│   │   ├── logs.jsonl
│   │   ├── audit.jsonl
│   │   └── metrics.json
│   └── diagnostics/
└── latest-run.json
```

所有 manifest 中的文件路径都相对 Task 根目录。`script-preparation.json` 是文案整理的权威输入，保存 Voice Unit 与整理规则；它不是 LLM 阶段产物。Stage 先写同文件系统临时目录，校验后原子移动到最终路径，再通过 Domain Event 和 Artifact 索引完成逻辑提交；未注册文件视为孤立候选并由恢复流程处理。`observability/` 不是业务 Artifact 的输入，不能改变 fingerprint。

## 3. Task 与 Run 状态

### 3.1 `task.json`

```json
{
  "schema_version": 1,
  "task_id": "task-123",
  "title": "示例任务",
  "status": "running",
  "pipeline_id": "mountain-av-v1",
  "engine": "whiteboard",
  "created_at": "2026-08-29T09:00:00+08:00",
  "updated_at": "2026-08-29T10:30:00+08:00",
  "active_run_id": "run-456",
  "revision": 7
}
```

### 3.2 `run.json`

```json
{
  "schema_version": 1,
  "run_id": "run-456",
  "task_id": "task-123",
  "trace_id": "trace-456",
  "entrypoint": "web",
  "command_ids": ["command-789"],
  "status": "running",
  "target_stage": "compose-video",
  "started_at": "2026-08-29T10:00:00+08:00",
  "finished_at": null,
  "stages": {
    "generate-visual-anchors": {"status": "skipped", "attempt": 0},
    "clone-voice": {"status": "running", "attempt": 1},
    "plan-storyboard": {"status": "pending", "attempt": 0}
  },
  "warnings": [
    {
      "code": "ALIGNMENT_EQUAL_FALLBACK",
      "unit_id": "unit-002",
      "message": "该单元已按图片数量等分实际语音时长"
    }
  ]
}
```

Run 被其他入口重试或恢复时追加 `command_ids`，但不更换 `trace_id`。

## 4. 文案整理与画面锚点

新建 Task 时完成文案整理并写入 `inputs/script-preparation.json`，在任何 TTS 前确定 Voice Unit 原文边界。`generate-visual-anchors` 可选地产生重点文字和其原文范围；`plan-storyboard` 再决定 Visual Item。

```json
{
  "schema_version": 1,
  "artifact_type": "script-preparation",
  "artifact_id": "input-script-preparation-001",
  "artifact_key": "input.script-preparation",
  "task_id": "task-123",
  "run_id": "run-456",
  "pipeline_id": "mountain-av-v1",
  "engine": "whiteboard",
  "producer_stage": "task-input",
  "producer_version": "deterministic-v1",
  "created_at": "2026-08-29T10:01:00+08:00",
  "input_fingerprint": "sha256:...",
  "source_text_sha256": "sha256:...",
  "voice_units": [
    {
      "unit_id": "unit-001",
      "order": 1,
      "source_range": {"start": 0, "end": 41},
      "text": "以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。",
      "anchors": []
    }
  ]
}
```

不变量：

- Voice Unit 按顺序、无重叠地覆盖全部有效原文；
- 每个 Voice Unit 独立生成一条 Voice；
- 画面锚点若存在，必须引用所属 Unit 内连续原文；
- Visual Item 由分镜阶段产生，不能跨 Voice Unit；一个 Visual Item 对应一张主图；
- “2–3 句话”和“1–2 张图”都是规划提示，不是 schema 限制；
- 后续阶段只能引用 `unit_id` 和不可变 `source_range`，不得重新整理原文；分镜产生稳定 `visual_id` 后，下游只引用该 ID。

## 5. `voice-manifest.json`

```json
{
  "schema_version": 1,
  "artifact_type": "voice-manifest",
  "artifact_id": "artifact-voice-001",
  "artifact_key": "audio.voice-manifest",
  "project_id": "project-123",
  "run_id": "run-456",
  "pipeline_id": "mountain-av-v1",
  "engine": "whiteboard",
  "producer_stage": "clone-voice",
  "producer_version": "1.0.0",
  "created_at": "2026-08-29T10:10:00+08:00",
  "input_fingerprint": "sha256:...",
  "voices": [
    {
      "unit_id": "unit-001",
      "audio_path": "runs/run-456/media/voices/unit-001.wav",
      "sha256": "sha256:...",
      "duration_ms": 8280,
      "sample_rate": 24000,
      "channels": 1,
      "tts_profile": "narration-default",
      "attempt": 1
    }
  ]
}
```

音频必须在登记前经过 probe 和规范化。失败单元可以单独重试，成功单元不应重新生成。

## 6. `timeline.json`

`clone-voice` 在每条 Voice 完成后运行 Whisper 对齐。对齐结果合法则映射到预先确定的 Visual Item；执行失败、文字覆盖不合格、时间不单调或边界越界时，整个单元使用等分 fallback。

```json
{
  "schema_version": 1,
  "artifact_type": "timeline",
  "artifact_id": "artifact-timeline-001",
  "artifact_key": "timing.timeline",
  "project_id": "project-123",
  "run_id": "run-456",
  "pipeline_id": "mountain-av-v1",
  "engine": "whiteboard",
  "producer_stage": "clone-voice",
  "producer_version": "1.0.0",
  "created_at": "2026-08-29T10:12:00+08:00",
  "input_fingerprint": "sha256:...",
  "units": [
    {
      "unit_id": "unit-001",
      "duration_ms": 8280,
      "timing_source": "whisper",
      "alignment": {
        "status": "succeeded",
        "engine": "whisper",
        "model": "local-default",
        "coverage": 0.98,
        "confidence": 0.91
      },
      "visual_timings": [
        {"visual_id": "visual-001-01", "start_ms": 0, "end_ms": 5740},
        {"visual_id": "visual-001-02", "start_ms": 5740, "end_ms": 8280}
      ]
    },
    {
      "unit_id": "unit-002",
      "duration_ms": 9000,
      "timing_source": "equal_fallback",
      "alignment": {
        "status": "failed",
        "reason_code": "ALIGNMENT_LOW_COVERAGE"
      },
      "visual_timings": [
        {"visual_id": "visual-002-01", "start_ms": 0, "end_ms": 4500},
        {"visual_id": "visual-002-02", "start_ms": 4500, "end_ms": 9000}
      ]
    }
  ]
}
```

等分公式：对时长 `D`、图片数 `N` 和索引 `i`，`start_i=floor(i*D/N)`，`end_i=floor((i+1)*D/N)`。最后一个 `end_ms` 必须等于实际 Voice 时长。Whisper 失败是可见 warning，不阻断该单元后续制作。

## 7. `storyboard.json`

```json
{
  "schema_version": 1,
  "artifact_type": "storyboard",
  "artifact_id": "artifact-storyboard-001",
  "artifact_key": "planning.storyboard",
  "project_id": "project-123",
  "run_id": "run-456",
  "pipeline_id": "mountain-av-v1",
  "engine": "whiteboard",
  "producer_stage": "plan-storyboard",
  "producer_version": "1.0.0",
  "created_at": "2026-08-29T10:15:00+08:00",
  "input_fingerprint": "sha256:...",
  "visuals": [
    {
      "visual_id": "visual-001-01",
      "unit_id": "unit-001",
      "prompt": "...",
      "negative_prompt": "text, watermark, logo",
      "composition": "centered",
      "overlay_text": [],
      "style_profile": "book-whiteboard-v1"
    }
  ]
}
```

Storyboard 只能填充视觉规划，不能改变 Visual Item 数量、顺序、原文范围或时间。

## 8. 图片、渲染与成片 manifest

### 8.1 `illustration-manifest.json`

每个 `visual_id` 恰有一张主图记录，包含 `image_path`、hash、尺寸、生成 profile、model、attempt 和安全的参数摘要。完整 prompt 不默认写入诊断日志；如产品需要保留，应作为受权限保护的业务 Artifact。

### 8.2 `render-manifest.json`

每个 `visual_id` 恰有一个 clip，时长取自 `timeline.json`。记录 renderer、版本、画布、fps、clip 路径、hash 和 probe 结果。白板与动态信息图通过 adapter 生成同一结构。

### 8.3 `final-manifest.json`

记录 Voice 拼接顺序、clip 拼接顺序、字幕、最终文件、容器/编码、分辨率、fps、实际音画时长、时差和质量检查结果。

## 9. 依赖与失效传播

| 变化 | 最早失效 Artifact | 必须向后失效 |
| --- | --- | --- |
| 原文 | `av-plan` | 全部 |
| Voice Unit / Visual Item 边界 | `av-plan` | voice、timeline、storyboard、image、render、final |
| 参考音色或 TTS profile | `voice-manifest` | timeline、render、final |
| Whisper 模型/阈值 | `timeline` | render、final |
| 风格或视觉 prompt | `storyboard` | image、render、final |
| 单张图片重生成 | 对应 image record | 对应 clip、final |
| renderer 设置 | `render-manifest` | final |
| 编码/字幕设置 | `final-manifest` | final |

Stage fingerprint 只由真实业务输入、依赖 Artifact hash、版本和相关设置构成；日志级别、入口、`trace_id` 和界面语言不能使业务 Artifact 失效。

## 10. 观测与诊断文件

- `events.jsonl`：领域状态事实，单调 cursor，可重建 Run 投影；
- `logs.jsonl`：结构化诊断日志，允许轮转，不参与状态恢复；
- `audit.jsonl`：入口、actor、命令、目标和结果，不保存完整正文或 Secret；
- `metrics.json`：阶段/Provider/媒体耗时、重试、fallback 和质量汇总；
- `diagnostics/*.zip`：用户显式导出的脱敏快照，包含 manifest、事件、日志摘要和环境能力，不包含 API key、完整参考音频或默认完整正文。

三类记录统一使用 [12-observability-and-diagnostics.md](12-observability-and-diagnostics.md) 的关联字段和脱敏规则。

## 11. Legacy 读取

旧目录通过显式 adapter 映射为只读 View，并标记原始 `pipeline_id` 和未知精度字段。不得伪造 Whisper 对齐、`timing_source` 或新 schema 的稳定 ID。用户主动迁移时必须创建新 Run，保留原目录，并在 Audit Record 中记录迁移来源。
