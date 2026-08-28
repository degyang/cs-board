---
name: video-workflow
description: Create, resume, inspect, or diagnose a standard whiteboard video project through the cs-board CLI. Use for end-to-end video workflow coordination, not for implementing individual production stages.
---

Use `python -m cli.csboard` as the only stateful interface. Keep the returned `project_id`, `run_id`, `trace_id`, and `command_id`; use event cursors to report progress.

M04 supports only `mountain-av-v1` with `whiteboard`. Reject custom-reference and infographic requests with the capability result; do not silently switch to legacy work.

Use `project create` to start, `project show` and `run trace` to inspect, `events list` for progress, and `diagnostics export` for a redacted support bundle. Do not implement segmentation, TTS, rendering, fallback, or provider calls in this Skill.
