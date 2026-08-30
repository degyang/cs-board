---
name: visual-anchor-generator
slug: visual-anchor-generator
description: Generate visual anchor points for storyboard planning
---

# Visual Anchor Generator Skill

Generate visual anchor points from script text for downstream storyboard planning.

## 目标

为 `plan-storyboard` 生成 av-plan.json 输入文件。

## 前置条件

- 任务已创建（`task create`）
- 文案已保存（`POST /api/v1/tasks/{task_id}/inputs`）
- 文案整理（script_preparation）已自动完成
- Provider 连通（`provider.check`）

## 输出

- `planning/av-plan.json`：voice_units（含 visual_items）

## 执行方式

```bash
# CLI
python -m cli.csboard stage run \
  --task <task-id> \
  --run <run-id> \
  --stage generate-visual-anchors \
  --script "完整文案内容" \
  --json

# API
curl -X POST /api/v1/tasks/{task_id}/runs/{run_id}/start
```

## av-plan.json 格式

```json
{
  "task_id": "...",
  "run_id": "...",
  "engine": "whiteboard",
  "voice_units": [
    {
      "unit_id": "unit-001",
      "order": 1,
      "source_range": {"start": 0, "end": 42},
      "text": "旁白原文",
      "visual_items": [
        {
          "visual_id": "visual-001-01",
          "order": 1,
          "source_range": {"start": 0, "end": 20},
          "text": "画面描述"
        }
      ]
    }
  ]
}
```

## 验证规则

- voice_units 非空
- source_range 覆盖完整文案
- visual_items 顺序连续

## 约束

- 确定性算法（deterministic-v1），相同输入相同输出
- 不依赖 LLM（LLM 增强在 M09 开放）
- 不读取、缓存或打印参考音频

## 错误处理

- Provider 不可用 → `PROVIDER_UNAVAILABLE`
- 文案为空 → `VALIDATION_ERROR`
