# M09-RUNTIME-007 backend receipt

Status: `READY_FOR_VERIFY`

## Delivered scope and boundary

- Added an explicit production-only startup readiness probe to the native
  `backend.mountain_server` composition root. The launcher sets the opt-in
  before importing that root; ordinary `create_app(tmp_path)` remains offline
  by default and accepts an explicit injected boolean for tests.
- The registry selects one deterministic enabled service for each required
  `text_generation`, `speech_synthesis`, `speech_alignment`, and `media`
  prerequisite, then uses its existing bounded probe implementation. It does
  not probe fallback alternatives on restart: their new failure states would
  alter the accepted activation fingerprint. It invokes no task, render, text,
  image, or TTS generation endpoint.
- Each candidate failure is cached as its real unavailable result and cannot
  abort startup. Startup readiness counts are exposed by the health check;
  full per-service probe evidence remains available through the existing
  service availability projection.
- Process-local probe cache now uses independent partitions per resolved data
  root. Interleaved live registries retain their own entries, while identical
  service IDs cannot inherit another root's result. A narrow flat-cache
  migration remains only for the existing test injection seam; production
  reads and writes are always root-partitioned.
- Readiness selection uses the same safe declared-capability interpretation as
  `CapabilityService`, including valid `config.capabilities` secondary claims.
  This includes MiMo services whose primary `audio_generation` declaration
  supplies `speech_synthesis` or `text_generation` for the runtime gate.
- PM's first restart verdict found that probing all eight eligible alternatives
  changed the accepted fingerprint through irrelevant failures. The corrected
  deterministic ranking prefers explicit secondary declarations (Codeplan
  text), then the `audio_generation` alias (MiMo TTS speech), and favors a
  distinct service for the next prerequisite. The 10-service regression proves
  it restores only Codeplan, MiMo TTS, local Whisper, and local FFmpeg—the same
  four-cache accepted shape—and produces an identical full service fingerprint.

PM owns the required integration stop/start of 8000 and the live 5182 check;
this worker did not restart shared services or issue any manual POST probe.

## Verification

| Command | Exit | Result |
| --- | ---: | --- |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_m09_runtime_007.py tests/test_service_registry.py tests/test_capabilities_api.py tests/test_infographic_capability.py tests/test_m09_activate_003.py` | 0 | 70 passed |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_infographic_activation_projection.py tests/test_infographic_activation.py -k 'not browser_version_uses_renderer_resolver'` | 0 | 28 passed, 1 deselected |
| `git diff --check` | 0 | clean |

The deselected browser-resolver fixture is environment-specific and unrelated
to readiness probing. No provider generation, Task creation, render, service
definition, Secret, activation pointer, frozen output, frontend, commit,
merge, or push was performed.

## File hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `backend/mountain_server.py` | `85f65b479e0e3b3372aacac2dcfc1a8d8c4a0ed8e9d70ea9ff394499a5dac078` |
| `csboard/adapters/filesystem/service_registry.py` | `fea4c1d4f1af2bc01f869547f6f21bb75eddc9fcc2289c925211e69cb68bb863` |
| `scripts/run_mountain_backend.py` | `2d30ebc36b1db81264cb213a7c5027aa60247e65d5098f89058bd75a38a86fad` |
| `tests/test_m09_runtime_007.py` | `1f6063457f806d92a2e0a1baa480d008997f16e0fa510815a52b37fb86111f3e` |

Backend client remains idle for PM integration and independent verification.
