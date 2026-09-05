# M09 Round 3 — InfographicStoryboardAdapter (WBS-2)

**Date:** 2026-09-04
**Branch:** main (uncommitted)
**Status:** COMPLETE — 47/47 tests pass

---

## Deliverables

### New Files

| File | Purpose |
|------|---------|
| `csboard/adapters/remotion/__init__.py` | Remotion adapter package |
| `csboard/adapters/remotion/storyboard_adapter.py` | `InfographicStoryboardAdapter` — domain → Remotion props |
| `tests/test_infographic_storyboard_adapter.py` | 47 focused tests |

### Not Modified

- `web-v2/` — untouched
- `csboard/domain/voice_profile.py` — untouched
- `webapp/mountain_voice_profile_api.py` — untouched
- `webapp/server.py` — not called

---

## Adapter Architecture

### Class: `InfographicStoryboardAdapter`

```
InfographicStoryboard (domain)
        │
        ▼
  to_remotion_props(storyboard, illustrations, audio_paths, metadata)
        │
        ▼
  InfographicVideoProps (JSON-serializable dict matching Remotion types.ts)
```

### Constructor Parameters

| Parameter | Default | Validation |
|-----------|---------|------------|
| `fps` | 30 | Must be ≥ 1 |
| `width` | 1920 | Must be ≥ 1 |
| `height` | 1080 | Must be ≥ 1 |
| `style` | "极简粗线简笔白板风" | Free-form string |
| `subtitles_enabled` | False | Boolean |

### Conversion Pipeline

1. **Validate** — `StoryboardConversionError` with structured codes
2. **Convert pages** — domain `InfographicPage` → Remotion `InfographicPage`
3. **Extract node texts** — node props `text` → `nodes[]` array
4. **Resolve images** — illustration map → node `image_path` → fallback placeholder
5. **Convert cues** — domain `InfographicCue` → Remotion `TimedCue` with frame math
6. **Apply metadata** — series/chapter titles, layout types, composition modes
7. **Sanitize** — control chars stripped, text truncated, invalid enums default

### Frame Math

```python
_ms_to_frames(ms) = max(0, round(ms * fps / 1000))
```

### Error Codes

| Code | Condition |
|------|-----------|
| `EMPTY_STORYBOARD` | No pages |
| `INVALID_DURATION` | `total_duration_ms` ≤ 0 |
| `TOO_MANY_PAGES` | > 200 pages |
| `TOO_MANY_NODES` | > 20 nodes per page |
| `INVALID_PAGE_TIMING` | `cue_end_ms < cue_start_ms` |
| `DURATION_EXCEEDED` | > 600,000 ms (10 min) |
| `INVALID_FPS` | `fps < 1` |
| `INVALID_DIMENSIONS` | `width < 1` or `height < 1` |

### Sanitization

| Field | Rule | Fallback |
|-------|------|----------|
| `layoutType` | Must be one of 14 valid values | `"overview"` |
| `composition` | Must be one of 5 valid values | `"split-right"` |
| `slideRole` | Must be one of 4 valid values | `"detail"` |
| `relationshipType` | Must be one of 5 valid values | `"none"` |
| Text (nodes, cues) | Strip control chars (except `\n\t`), truncate to 500 chars | N/A |
| Error messages | No internal paths, stack traces, or secrets | Structured code + message |

---

## Test Coverage

### 47 Tests — 100% Pass

| Category | Tests | Coverage |
|----------|-------|----------|
| **Normal Conversion** | 7 | Single page, multi-page, custom dimensions, subtitles flag, audio passthrough |
| **Frame Math** | 4 | 30fps, 24fps, page frame ordering, minimum 1-second duration |
| **Node Text Extraction** | 3 | Ordered extraction, non-string coercion, empty text |
| **Illustration Resolution** | 4 | By visual_id, by image_path, fallback to page_id, precedence |
| **Cue Conversion** | 3 | Enter cues → enterIds, non-enter cues, ordering |
| **Metadata Passthrough** | 2 | All fields populated, missing metadata defaults |
| **Sanitization** | 8 | Control chars stripped, newlines preserved, text truncation, invalid layout/composition/role/relationship, error message safety |
| **Invalid Input** | 9 | Empty pages, zero/negative duration, too many pages/nodes, invalid timing, invalid fps/dimensions, duration exceeded |
| **Serialization** | 2 | JSON round-trip, domain→props→verify |
| **Edge Cases** | 5 | Single node+cue, unicode, mixed node kinds, overlapping pages, all valid layout types |

### Key Assertions

- Frame math: `5000ms @ 30fps = 150 frames`, `3333ms @ 30fps ≈ 100 frames`
- Page ordering: `startFrame` increases monotonically
- Illustration precedence: `illustrations[visual_id]` > `node.image_path` > fallback placeholder
- Sanitization: `\x00`, `\x08` stripped; `\n`, `\t` preserved; text capped at 500 chars
- Error messages: no `/` or `\\` characters (no path leakage)

---

## Security Boundaries

1. **No network calls** — adapter is a pure in-memory transformer
2. **No file I/O** — illustrations are string paths, not opened
3. **No Remotion execution** — produces props dict only, does not invoke renderer
4. **No old webapp coupling** — does not import `webapp/server.py`
5. **Error messages sanitized** — no internal paths, no stack traces, no secrets
6. **Input validation first** — all validation runs before any conversion

---

## Integration Notes

### For WBS-3 (Remotion execution layer)

The adapter output `InfographicVideoProps` dict is ready for:
- Direct JSON serialization to `render-manifest.json`
- Passing to Remotion `<Composition>` component props
- FilesystemTaskRepository artifact storage

### Dependency Chain

```
domain/infographic.py (WBS-1)
        ↓
adapters/remotion/storyboard_adapter.py (WBS-2, this)
        ↓
[Future WBS-3: Remotion executor]
```

### TypeScript Contract Alignment

Output keys match `video_renderer/src/types.ts` exactly:
- `InfographicVideoProps.fps`, `.width`, `.height`, `.totalDurationMs`, `.totalDurationFrames`
- `InfographicPage.id`, `.image`, `.startFrame`, `.endFrame`, `.seriesTitle`, `.chapterTitle`, `.pageTitle`
- `TimedCue.id`, `.anchorText`, `.startFrame`, `.endFrame`, `.spokenStartMs`, `.spokenEndMs`, `.enterIds`

---

## Verification Command

```bash
python -m pytest tests/test_infographic_storyboard_adapter.py -v
```

Result: **47 passed in 0.41s**
