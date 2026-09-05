# M09 Round 5 — Task Engine Wiring (WBS-5)

**Date:** 2026-09-05
**Branch:** main (uncommitted)
**Status:** COMPLETE — 12/12 new tests pass, 823 full suite pass (3 pre-existing failures)

---

## Deliverables

### Modified Files

| File | Change |
|------|--------|
| `csboard/application/commands.py` | `plan_storyboard()`: engine branching for infographic-remotion; new `_plan_storyboard_infographic()` and `_read_artifact()` helper |
| `csboard/adapters/remotion/renderer_adapter.py` | Bug fix: read `voice_units` from storyboard (where plan-storyboard embeds them) instead of timeline |

### New Files

| File | Purpose |
|------|---------|
| `tests/test_task_engine_wiring.py` | 12 focused tests for engine wiring |

### Not Modified

- `cli/csboard.py` — no changes needed
- `web-v2/` — untouched
- `csboard/domain/voice_profile.py` — untouched
- `webapp/server.py` — untouched
- `csboard/adapters/remotion/storyboard_adapter.py` — used as-is from WBS-2

---

## Implementation

### 1. `plan_storyboard()` Engine Branching

```
plan_storyboard(task_id, run_id, text_model, context)
    │
    ├─ task.engine == WHITEBOARD
    │     └─ StoryboardService.run() → storyboard_document() → artifact
    │        (unchanged, no regression)
    │
    └─ task.engine == INFOGRAPHIC_REMOTION
          └─ _plan_storyboard_infographic()
                ├─ Read av-plan artifact (voice_units)
                ├─ Read timeline artifact (timing)
                ├─ voice_units_to_pages() → InfographicStoryboard
                ├─ InfographicStoryboardAdapter.to_remotion_props()
                ├─ storyboard_document() + embed remotion_props + voice_units
                └─ Commit planning.storyboard artifact
```

### 2. `_plan_storyboard_infographic()` (new method)

```python
def _plan_storyboard_infographic(self, task_id, run_id, task, context):
    # Read av-plan → voice_units
    # Read timeline → timeline_units
    # Build visuals list (for storyboard document)
    # voice_units_to_pages(voice_units, timeline_units, visuals)
    # InfographicStoryboardAdapter().to_remotion_props(infographic_sb)
    # storyboard_document() + doc["remotion_props"] + doc["voice_units"]
    # Commit artifact
```

**Storyboard artifact structure for infographic-remotion:**
```json
{
    "schema_version": 1,
    "artifact_type": "storyboard",
    "engine": "infographic-remotion",
    "visual_bible": {...},
    "visuals": [...],
    "voice_units": [...],        ← embedded for renderer
    "remotion_props": {          ← pre-computed Remotion props
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "totalDurationMs": 7000,
        "totalDurationFrames": 210,
        "pages": [...]
    }
}
```

### 3. Bug Fix: `RemotionRendererAdapter` voice_units Source

**Before (broken):**
```python
voice_units = timeline.get("voice_units", [])  # timeline has no voice_units!
```

**After (fixed):**
```python
voice_units = storyboard_data.get("voice_units", timeline.get("voice_units", []))
```

The plan-storyboard stage embeds `voice_units` in the storyboard artifact. The renderer reads them from there. Fallback to timeline for backward compatibility.

### 4. `_exec_render_visuals()` Engine Routing (already existed)

```python
def _exec_render_visuals(self, task_id, run_id, context):
    task = self.repository.get_task(task_id)
    if task.engine is Engine.INFOGRAPHIC_REMOTION:
        renderer = RemotionRendererAdapter()   # direct instantiation
    else:
        # WHITEBOARD: resolve from service registry
        render_def = self.service_resolver.resolve("rendering")
        renderer = self.provider_factory.create_adapter(render_def)
    return self.render_visuals(task_id, run_id, renderer, context)
```

---

## Data Flow

### Whiteboard (unchanged)

```
generate-visual-anchors → av-plan
clone-voice → timeline
plan-storyboard → StoryboardService → storyboard (visual_bible + visuals)
generate-illustrations → illustration-manifest
render-visuals → WhiteboardRendererAdapter → clips
compose-video → final video
```

### Infographic-Remotion (new)

```
generate-visual-anchors → av-plan
clone-voice → timeline
plan-storyboard → voice_units_to_pages() → InfographicStoryboardAdapter
                 → storyboard (visuals + voice_units + remotion_props)
generate-illustrations → illustration-manifest
render-visuals → RemotionRendererAdapter → infographic.mp4
                 (reads voice_units from storyboard, calls Node)
compose-video → final video
```

---

## Test Coverage

### 12 Tests — 100% Pass

| Category | Tests | What's Verified |
|----------|-------|-----------------|
| **infographic plan-storyboard** | 6 | Produces remotion_props, pages match voice units, total duration correct, engine in metadata, visual_bible set, run state updated |
| **whiteboard plan-storyboard** | 1 | No remotion_props (no regression) |
| **Missing dependencies** | 2 | Missing av-plan → stable error; missing timeline → stable error |
| **render-visuals routing** | 3 | infographic → RemotionRendererAdapter (no service_resolver needed); whiteboard → service resolver; whiteboard without resolver → CAPABILITY_NOT_AVAILABLE |

### Regression: Full Suite

```
823 passed, 3 failed (pre-existing), 4 skipped
```

Pre-existing failures (not introduced):
- `test_mountain_api.py::test_list_tasks` — known
- `test_script_preparation.py` × 2 — missing fixture `docs/workmates/evidence/manual-001-script.txt`

---

## Security Boundaries

1. **No Remotion execution** — plan-storyboard only computes props; actual Node.js invocation is in the render stage
2. **No webapp/server.py coupling** — all changes are in `commands.py` and `renderer_adapter.py`
3. **Error messages sanitized** — missing artifact errors contain no paths, no stack traces
4. **voice_units embedded safely** — only domain data (text, IDs, timing), no secrets
5. **Whiteboard path unchanged** — StoryboardService.run() flow is identical

---

## Verification Commands

```bash
# New tests
python -m pytest tests/test_task_engine_wiring.py -v

# Full suite
python -m pytest tests/ -v
```

Result: **12 passed** (new) + **823 passed** (full suite) = **835 total, 0 new failures**
