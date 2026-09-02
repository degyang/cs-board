# MEDIA-WO-002 Delivery

- Base: `integration/mountain-v2@8a59f86`
- Scope: contract and JSON examples only; no production code, existing schema, paid generation,
  TTS, Whisper, render or compose was run.

## Delivered

- [Stage Work Order v1 contract](../contracts/stage-work-order-v1.md): common six-stage envelope,
  run-root path boundary, structured commands, ownership/state transitions, fingerprint/stale rules,
  external illustration candidate import/validate/accept/reject/retry contract, WEB DTO and
  Skill/CLI consumption constraints.
- [Full illustration example](../contracts/examples/illustration-work-order-v1.example.json) and
  [local retry example](../contracts/examples/illustration-visual-retry-v1.example.json).

## Cross-check

Stage IDs follow `csboard/application/pipeline.py`; established Artifact keys and existing schema
names follow `schemas/mountain/` and `csboard/adapters/filesystem/artifacts.py`. Candidate key names
and the external-only boundary follow `docs/Mountain/03-artifact-contracts.md` and
`docs/Mountain/15-production-control-and-style-assets.md`. The new DTO is intentionally additive:
production does not yet implement it.

## Verification

- `jq empty docs/agents/contracts/examples/illustration-work-order-v1.example.json`
- `jq empty docs/agents/contracts/examples/illustration-visual-retry-v1.example.json`
- read-only scope check: only the three delivery documentation files are changed.

No approval claim is made; PM must review this contract before CORE/WEB implementation begins.
