---
name: manual-srt-whiteboard
description: Refine an SRT-driven whiteboard video through human-reviewed illustration, semantic region annotation, preview, rendering, and composition. Use for deliberate manual refinement of an existing Mountain Task/Run; do not use as a replacement for the standard automatic pipeline.
---

# Manual SRT Whiteboard

Use this skill when the user wants to inspect and refine the pictures, drawing regions, reveal order, or timing of a whiteboard video. It is a manual refinement surface over the same Mountain Task, Run, Work Orders, artifacts, renderer, and compositor used by WebUI and the standard Skills.

## Boundaries

- Work on an existing Task/Run. For a new production request, use `video-workflow` to create the Task and persist the source material first.
- Read the current Stage Work Order before every operation. Treat its IDs, paths, inputs, commands, and expected outputs as authoritative.
- Do not reconstruct authoritative script text, timing, service settings, or artifact paths from chat.
- Do not write directly to the Artifact index or publish files by copying them into a final artifact directory.
- Import generated or edited illustrations through the `generate-illustrations` Work Order's `import`, `validate`, and `accept` commands.
- Render and compose through `visual-renderer` and `av-compositor`. Do not invoke the underlying renderer or FFmpeg scripts directly.
- This workflow is not equivalent to the automatic pipeline and must not claim unattended execution.

## Workflow

1. Inspect the Task, Run, timeline, storyboard, and the current Work Order for the stage being refined.
2. Present a concise refinement plan that maps each proposed change to stable `unit_id` and `visual_id` values. Do not change Voice Unit text, source ranges, order, or authoritative Timeline boundaries.
3. Use the `gated` interaction style by default: pause after the plan, illustration review, annotation preview, and rendered result when those decisions affect visual intent. If the user explicitly requests continuous execution, continue only across already-authorized reversible steps.
4. For illustration changes, place candidates only in the Work Order's `output_directory`, write the candidate manifest it specifies, then execute its returned `import`, `validate`, and `accept` commands in order.
5. For region or reveal refinement, edit only an annotation revision path explicitly exposed by the current Work Order. If no command or writable annotation revision is provided, stop and report that manual annotation persistence is not yet exposed; never bypass this by mutating artifact records.
6. Run `render-visuals` for affected Visual Items and `compose-video` only after their Work Orders and dependencies are ready. Confirm the resulting manifests and validation status before reporting completion.

Use global CLI flags before the resource name, for example:

```bash
python -m cli.csboard --json work-order show --task <task-id> --run <run-id> --stage generate-illustrations
python -m cli.csboard --json artifact show --task <task-id> --run <run-id> --key timing.timeline
python -m cli.csboard --json stage retry --task <task-id> --run <run-id> --stage render-visuals --visual <visual-id>
```

## Visual and annotation guidance

Before planning an illustration or editing an annotation, read [references/annotation-and-rendering.md](references/annotation-and-rendering.md). It contains the retained visual language, semantic annotation rules, mask invariants, and observable render checks from the original SRT whiteboard workflow.

These rules guide manual judgment; persisted Work Orders, schemas, Timeline artifacts, and renderer validation remain authoritative when they differ.

## Completion

Report the Task/Run and affected stable IDs, accepted artifact revisions, render/composition validation, any fallback or warnings, and which visual decisions still require user acceptance. Passing structural tests does not substitute for viewing the preview or final video.
