# M05 Audit — PR-3b: Whisper Alignment Adapter + FFmpeg Media Adapter

**Date:** 2026-08-29
**Scope:** Infrastructure adapters implementing `AlignmentPort` and `MediaPort`
**Status:** ✅ Complete

---

## Deliverables

### 1. WhisperAlignmentAdapter (`csboard/adapters/whisper/alignment_adapter.py`)

| Aspect | Details |
|--------|---------|
| Port | `AlignmentPort` |
| Modes | `node` (calls `align.mjs` via subprocess) and `http` (calls faster-whisper-server API) |
| Constructor | `mode`, `renderer_root`, `whisper_model`, `base_url`, `timeout` |
| Output | `AlignmentResult` with character-level `starts_ms` |

**Key behaviors:**
- Node mode: resolves `align.mjs` under `renderer_root`, writes alignment output to temp JSON file, parses `speechSegments` into `starts_ms` dict
- HTTP mode: POSTs audio bytes to `/asr` endpoint with language param, parses segments from JSON response
- Both modes compute `coverage` (matched chars / total chars) and `confidence`
- Error paths: missing `renderer_root` raises `ValueError`, process failure raises `RuntimeError`, HTTP errors raise `RuntimeError`

### 2. FFmpegMediaAdapter (`csboard/adapters/ffmpeg/media_adapter.py`)

| Aspect | Details |
|--------|---------|
| Port | `MediaPort` |
| Constructor | `ffmpeg` (path), `ffprobe` (path), `timeout` |
| Methods | `probe()`, `normalize()`, `concat()`, `subtitle()` |

**Key behaviors:**
- `probe()`: runs `ffprobe -print_format json -show_format -show_streams`, parses into `MediaProbeResult` with duration_ms, resolution, codec, sample_rate, channels, bitrate, format
- `normalize()`: runs `ffmpeg -af loudnorm=I={target_lufs}:TP=-1.5:LRA=11 -ar 24000 -ac 1`
- `concat()`: writes file list to temp file, uses `ffmpeg -f concat -safe 0 -c copy`
- `subtitle()`: uses `ffmpeg -vf subtitles={srt} -c:a copy`
- All methods: `FileNotFoundError` → RuntimeError ("ensure ffmpeg installed"), `TimeoutExpired` → RuntimeError, non-zero exit → RuntimeError

---

## Tests

### `tests/test_whisper_adapter.py` (15 tests)

| Test class | Count | Coverage |
|-----------|-------|----------|
| `TestWhisperNodeMode` | 7 | Result type, starts_ms populated, engine name, process failure, missing renderer_root, no segments |
| `TestWhisperHTTPMode` | 7 | Result type, engine name, starts_ms, POST URL, no segments, HTTP error, timeout |
| `TestWhisperPortConformance` | 1 | `isinstance(adapter, AlignmentPort)` |

**Mocking strategy:** Node mode patches `subprocess.run`, `Path.is_file`, `Path.read_text`, `tempfile.NamedTemporaryFile`, `Path.unlink`. HTTP mode installs a mock `httpx` module in `sys.modules` since httpx is not a declared dependency.

### `tests/test_ffmpeg_media_adapter.py` (13 tests)

| Test class | Count | Coverage |
|-----------|-------|----------|
| `TestProbe` | 5 | Result type, duration_ms conversion, resolution, audio fields, bitrate |
| `TestNormalize` | 2 | loudnorm filter presence, custom target_lufs |
| `TestConcat` | 1 | concat demuxer usage |
| `TestSubtitle` | 1 | subtitles filter usage |
| `TestErrorHandling` | 3 | ffprobe failure, ffmpeg not found, timeout |
| `TestFFmpegPortConformance` | 1 | `isinstance(adapter, MediaPort)` |

**Mocking strategy:** All tests patch `subprocess.run` with pre-built `CompletedProcess` mocks containing JSON ffprobe output or empty success results.

---

## Port conformance

Both adapters satisfy their respective `@runtime_checkable` Protocol:

```python
isinstance(WhisperAlignmentAdapter(mode="http", ...), AlignmentPort)  # True
isinstance(FFmpegMediaAdapter(), MediaPort)                            # True
```

---

## Integration with VoiceUnitService

`WhisperAlignmentAdapter` plugs directly into `VoiceUnitService` as the `alignment` parameter:

```python
service = VoiceUnitService(
    tts=IndexTTSAdapter(url="http://localhost:8080"),
    alignment=WhisperAlignmentAdapter(mode="http", base_url="http://localhost:9000"),
    media=FFmpegMediaAdapter(),
    repository=project_repo,
    reference_audio=ref_path,
)
```

`FFmpegMediaAdapter` plugs into `VoiceUnitService` as the `media` parameter for audio normalization and concatenation.

---

## Files added/modified

| File | Action |
|------|--------|
| `csboard/adapters/whisper/__init__.py` | Created (package init) |
| `csboard/adapters/whisper/alignment_adapter.py` | Created (179 lines) |
| `csboard/adapters/ffmpeg/__init__.py` | Created (package init) |
| `csboard/adapters/ffmpeg/media_adapter.py` | Created (153 lines) |
| `tests/test_whisper_adapter.py` | Created (15 tests) |
| `tests/test_ffmpeg_media_adapter.py` | Created (13 tests) |

---

## Test results

```
Ran 28 tests in 0.033s — OK
```

All new tests pass. Pre-existing test failures are unrelated (missing optional deps: httpx, starlette, jsonschema).
