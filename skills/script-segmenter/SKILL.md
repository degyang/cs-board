---
name: script-segmenter
description: Run or inspect the semantic script-segmentation stage of a cs-board project. Use when deciding Voice Units and Visual Items, not when synthesizing voice or generating images.
---

Invoke the shared CLI stage command and retain its correlation IDs. A valid plan covers the source exactly and assigns continuous text ranges to Voice Units and Visual Items. Two to three sentences and one to two images are targets, never hard limits.

Do not infer timings, call TTS, or repair invalid coverage in this Skill. Report structured validation errors and use diagnostics when requested.
