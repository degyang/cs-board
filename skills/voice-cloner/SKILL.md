---
name: voice-cloner
description: Run or inspect unit-level voice cloning and alignment in a cs-board project. Use after an AV Plan exists; do not use for script segmentation or visual planning.
---

Call the shared CLI with the project/run identifiers. Each Voice Unit is independently synthesized from exactly its unit text. The core records Whisper alignment when valid and `equal_fallback` for the entire unit when alignment fails.

Do not call a TTS provider, Whisper, or media probe directly. Surface warnings and timing source from structured artifacts/events, and retry only the requested failed unit through the CLI.
