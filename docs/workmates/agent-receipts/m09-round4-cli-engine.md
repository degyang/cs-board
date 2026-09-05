# M09 Round 4 — CLI Engine Validation (WBS-6)

**Date:** 2026-09-04
**Branch:** main (uncommitted)
**Status:** COMPLETE — 23/23 new tests pass, 13/13 existing CLI tests pass

---

## Deliverables

### Modified Files

| File | Change |
|------|--------|
| `csboard/application/commands.py` | `create_task()` engine validation: replaced hard whiteboard-only gate with capability-based check for `infographic-remotion` |

### New Files

| File | Purpose |
|------|---------|
| `tests/test_cli_engine_validation.py` | 23 focused tests for engine validation, capability gating, snapshot safety |

### Not Modified

- `cli/csboard.py` — argparse already had `choices=[item.value for item in Engine]`; pipeline commands already use task's stored engine
- `web-v2/` — untouched
- `csboard/domain/voice_profile.py` — untouched
- `webapp/server.py` — untouched

---

## Implementation

### Change: `commands.py` `create_task()` (lines 129–145)

**Before:**
```python
if pipeline_id != "mountain-av-v1" or engine is not Engine.WHITEBOARD:
    raise ValueError("M04 仅支持标准 whiteboard 的 mountain-av-v1；自定义参考和动态信息图将在 M09 开放")
```

**After:**
```python
if pipeline_id != "mountain-av-v1":
    raise ValueError("仅支持 mountain-av-v1 流水线")
if engine is Engine.INFOGRAPHIC_REMOTION:
    from csboard.application.capabilities import CapabilityService
    cap_svc = CapabilityService(
        self.service_resolver._registry, project_root=self.root,
    ) if self.service_resolver is not None else None
    if cap_svc is None:
        raise DomainError("CAPABILITY_NOT_AVAILABLE", "引擎 infographic-remotion 当前不可用")
    cap_snapshot = cap_svc.snapshot()
    infographic_item = next(
        (item for item in cap_snapshot["items"]
         if item["engine"] == "infographic-remotion"
         and item["visual_source"] == "preset"),
        None,
    )
    if infographic_item is None or not infographic_item.get("supported"):
        reason = (infographic_item or {}).get("reason_code") or "CAPABILITY_NOT_AVAILABLE"
        raise DomainError("CAPABILITY_NOT_AVAILABLE", f"引擎 infographic-remotion 当前不可用: {reason}")
```

### Validation Flow

```
CLI --engine infographic-remotion
        │
        ▼
  argparse choices (Engine enum values) ── reject invalid
        │
        ▼
  create_task()
        │
        ├─ pipeline_id != "mountain-av-v1" ── reject
        │
        ├─ engine == WHITEBOARD ── always accepted (no capability check)
        │
        └─ engine == INFOGRAPHIC_REMOTION
                │
                ▼
          CapabilityService.snapshot()
                │
                ├─ service_resolver is None ── CAPABILITY_NOT_AVAILABLE
                │
                ├─ infographic item not found ── CAPABILITY_NOT_AVAILABLE
                │
                ├─ supported=False ── CAPABILITY_NOT_AVAILABLE: {reason_code}
                │
                └─ supported=True ── accepted
```

### Error Codes and Messages

| Scenario | Code | Message (stable, no paths/secrets) |
|----------|------|------------------------------------|
| service_resolver is None | `CAPABILITY_NOT_AVAILABLE` | "引擎 infographic-remotion 当前不可用" |
| No infographic item in snapshot | `CAPABILITY_NOT_AVAILABLE` | "引擎 infographic-remotion 当前不可用: CAPABILITY_NOT_AVAILABLE" |
| Node.js not found | `CAPABILITY_NOT_AVAILABLE` | "...NODE_NOT_FOUND" |
| Browser not found | `CAPABILITY_NOT_AVAILABLE` | "...BROWSER_NOT_FOUND" |
| render.mjs missing | `CAPABILITY_NOT_AVAILABLE` | "...RENDER_SCRIPT_MISSING" |
| Service secrets not configured | `CAPABILITY_NOT_AVAILABLE` | "...CAPABILITY_NOT_AVAILABLE" |

All error messages are sanitized: no internal paths, no stack traces, no API keys.

### Non-Sensitive Snapshot

The task snapshot (task.json, request.json) already:
- Strips `output_root` from persisted request (line 137 in commands.py)
- Stores engine as enum value string ("whiteboard" or "infographic-remotion")
- Does not carry API keys, secrets, or absolute machine paths
- Submission signature includes engine value (line 169) for idempotency

### Pipeline Compatibility

Pipeline commands (`pipeline run`, `pipeline resume`) already:
- Read engine from the stored Task object (`task.engine`)
- No explicit `--engine` parameter needed — engine is validated at task creation time
- `_exec_render_visuals` uses `service_resolver.resolve("rendering")` which works for both engines

---

## Test Coverage

### 23 Tests — 100% Pass

| Category | Tests | What's Verified |
|----------|-------|-----------------|
| **Default whiteboard** | 3 | Always accepted, explicit flag, no service_resolver needed |
| **infographic-remotion accepted** | 2 | Capability available → task created, engine persisted in task.to_dict() |
| **infographic-remotion rejected** | 4 | Capability unavailable, no item in snapshot, service_resolver=None, error message sanitized |
| **Invalid engine** | 2 | Argparse rejects unknown values, omitting --engine defaults to whiteboard |
| **Snapshot safety** | 3 | output_root stripped, API keys not in task.to_dict(), JSON serializable |
| **Task package paths** | 3 | output_root isolation, engine persists in task.json, infographic engine persists |
| **Pipeline compatibility** | 2 | Pipeline uses task engine, create_options reflects availability |
| **Reason codes** | 4 | NODE_NOT_FOUND, BROWSER_NOT_FOUND, RENDER_SCRIPT_MISSING, CAPABILITY_NOT_AVAILABLE |

### Regression: Existing Tests

All 13 existing `test_cli_csboard.py` tests pass — no regressions.

---

## Security Boundaries

1. **No secrets in snapshots** — task.to_dict() contains only public fields (task_id, title, engine, status, etc.)
2. **No paths in errors** — all DomainError messages are sanitized strings
3. **No Remotion execution** — only checks capability availability, does not invoke render
4. **No pipeline orchestration change** — engine is a stored attribute, not a runtime override
5. **Capability check is read-only** — CapabilityService.snapshot() only reads service registry and checks toolchain binaries

---

## Verification Commands

```bash
# New tests
python -m pytest tests/test_cli_engine_validation.py -v

# Existing CLI regression
python -m pytest tests/test_cli_csboard.py -v
```

Result: **23 passed** (new) + **13 passed** (existing) = **36 total, 0 failures**
