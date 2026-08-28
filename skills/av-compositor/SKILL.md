---
name: av-compositor
description: Run or inspect final A/V composition for a cs-board project. Use after voice, timeline, and render manifests exist.
---

Use the CLI and retain correlation IDs. Voice Units and Visual ranges must be used once, in stable order, and a subtitle cue must not cross a Voice Unit boundary. Do not report success when the final manifest validation is false.

Do not invoke ffmpeg, modify timing, or overwrite a previous valid final artifact outside the shared core.
