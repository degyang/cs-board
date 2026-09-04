---
name: illustration-generator
description: Generate illustrations for each Visual Item based on the storyboard. Use for the image generation stage of the standard pipeline.
---

## 输入与输出

- 输入：Storyboard、风格/人物参考 Artifact、图片模型 profile；
- 输出：每个 Visual Item 的 source image、本地后处理 image 和 `illustrations.manifest`。

## 强制规则

- 图片模型不得生成中文、Logo 或水印；
- source 与本地后处理结果分开保存；
- 单图重生成只使该 `visual_id` 的 clip 和 final 失效；
- 素材必须通过 Artifact Store 读取；
- 不根据 `web|skill` 入口改变 prompt 或 Provider profile。

## Codex 外部候选闭环

```bash
python -m cli.csboard work-order show --task <id> --run <run-id> --stage generate-illustrations --json
```

Read Storyboard prompts and generate one image for every expected `visual_id` with Codex imagegen.
Copy each generated source into the work order's `output_directory`, then write `candidate.json`
there using `{schema_version, work_order_id, candidate_id, items}`. Each item contains
`visual_id`, `unit_id`, and its run-relative `path`. Execute the returned `import`, `validate`,
and `accept` command arrays in that order. Only `accept` may publish `illustrations.manifest`.

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "work-order.accept",
  "stage": "generate-illustrations",
  "result": "succeeded",
  "artifacts": ["illustrations.manifest"],
  "next_stage": "render-visuals"
}
```

## 与其他 Skill 的协作

- **上游**：storyboard-planner 生成 storyboard
- **下游**：visual-renderer 使用 illustrations 生成视频片段

## 错误处理

- storyboard 缺失 → 先运行 plan-storyboard
- 候选缺图或规格错误 → 修正候选后重新 import/validate
- 单图生成失败 → 可独立重试，不影响其他 Visual
