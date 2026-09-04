---
name: visual-anchor-generator
description: Execute the visual-anchor Stage from its persisted Work Order without accepting script text from chat or CLI flags.
---

# Visual Anchor Generator

Read the authoritative work order first:

```bash
python -m cli.csboard work-order show --task <id> --run <run-id> --stage generate-visual-anchors --json
```

Execute the exact `commands.run[].argv` returned by that work order. The Stage reads the saved
`script_preparation`; never pass or reconstruct script text. A missing text service may use the
backend's audited default-anchor fallback. Verify `planning.av-plan`, then submit its current
Artifact hash as Gate evidence before moving to `clone-voice`.

The output must preserve every Voice Unit's text, order, and source range exactly. Never read,
copy, or print the reference audio in this stage.
