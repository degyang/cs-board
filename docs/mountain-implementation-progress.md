# Mountain Implementation Progress Report

Date: 2026-08-29
Branch: `feat/mountain-m07-project-api-web-v2`
Scope: All docs under `docs/Mountain/` vs current codebase

---

## Executive Summary

The Mountain architecture redesign is well underway. The **shared kernel (`csboard/`)** has a solid foundation covering domain models, filesystem repository, artifact store, telemetry, and the application command layer. **M01 (schemas/fixtures)** and **M02 (shared kernel)** are substantially complete. **M03 (legacy bridge)** exists in a working prototype form. **M04 (CLI)** is partially implemented with the basic structure and some commands. **M05 (AV planning, voice, sync)** has the core domain logic but the full pipeline integration is incomplete. **M06 (storyboard, illustrations, render, compose)** exists only as thin document builders. **M07 (WebUI)** has a minimal functional SPA. Skills are stub definitions only. The overall PR roadmap (M01-M09) maps well to what exists, with M01-M02 being the most mature.

---

## 1. Documentation Inventory

All 13 docs + README were reviewed:

| Doc | Title | Status |
|-----|-------|--------|
| README.md | Architecture evolution plan | Reference/index |
| 01-current-architecture.md | Current architecture review | Reference (describes legacy) |
| 02-target-architecture.md | Target shared kernel architecture | **Key design doc** |
| 03-artifact-contracts.md | Artifact & state contracts | **Key design doc** |
| 04-webui-redesign.md | WebUI redesign | Design |
| 05-skills-design.md | Seven skills design | Design |
| 06-pr-roadmap.md | PR roadmap (M01-M09) | **Implementation plan** |
| 07-validation-strategy.md | Test & validation strategy | Design |
| 08-decisions.md | Architecture decisions | Reference |
| 09-audio-visual-sync.md | Voice Unit sync design | **Key design doc** |
| 10-desktop-app-architecture.md | Desktop app architecture | Future target |
| 11-openai-compatible-model-architecture.md | Model architecture | Design |
| 12-observability-and-diagnostics.md | Observability design | Design |
| 13-webui-functional-spec.md | WebUI functional spec | Implementation spec |

---

## 2. PR Milestone Progress (from doc 06-pr-roadmap.md)

### M01: Baseline, Feature Tests & Schema -- SUBSTANTIALLY COMPLETE

**What was delivered per docs:**
- Mountain docs and decisions
- All artifact JSON Schemas
- Domain Event, Diagnostic Log, Audit Record schemas
- Legacy fixture, Secret canary, JSON/ID fixtures

**Implementation status:**

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| Mountain docs | DONE | 13 files in `docs/Mountain/` |
| Architecture decisions | DONE | `docs/Mountain/08-decisions.md` with 23 decisions |
| `project.schema.json` | DONE | `schemas/mountain/project.schema.json` |
| `run.schema.json` | DONE | `schemas/mountain/run.schema.json` |
| `av-plan.schema.json` | DONE | `schemas/mountain/av-plan.schema.json` |
| `voice-manifest.schema.json` | DONE | `schemas/mountain/voice-manifest.schema.json` |
| `timeline.schema.json` | DONE | `schemas/mountain/timeline.schema.json` |
| `storyboard.schema.json` | DONE | `schemas/mountain/storyboard.schema.json` |
| `illustration-manifest.schema.json` | DONE | `schemas/mountain/illustration-manifest.schema.json` |
| `render-manifest.schema.json` | DONE | `schemas/mountain/render-manifest.schema.json` |
| `final-manifest.schema.json` | DONE | `schemas/mountain/final-manifest.schema.json` |
| `domain-event.schema.json` | DONE | `schemas/mountain/domain-event.schema.json` |
| `diagnostic-log.schema.json` | DONE | `schemas/mountain/diagnostic-log.schema.json` |
| `audit-record.schema.json` | DONE | `schemas/mountain/audit-record.schema.json` |
| `common.schema.json` | DONE | `schemas/mountain/common.schema.json` |
| Schema fixtures | DONE | `tests/fixtures/mountain-project/` (12 fixture files) |
| Legacy fixture | DONE | `tests/fixtures/legacy-job/job.json` |
| Secret canary test | DONE | `test_mountain_contracts.py:88` tests forbidden fields |
| Schema validation tests | DONE | `test_mountain_contracts.py` validates all schemas + fixtures |
| Feature tests for current behavior | PARTIAL | `test_queue_resume.py` (206 lines) covers legacy pipeline; no comprehensive feature test suite for all current behaviors |

### M02: Shared Kernel, Telemetry & Adapters -- SUBSTANTIALLY COMPLETE

**What was delivered per docs:**
- `csboard` domain package with models, enums, errors, validation
- Filesystem repository, artifact store, fingerprint, revision, stale, project lock
- `CommandContext`, `trace_id/command_id/span_id`
- JSONL Event/Log/Audit, Redactor, metrics, diagnostic bundle
- Provider ports (Text/Image/TTS/Alignment)
- Fake adapters and capability/retry/error mapping

**Implementation status:**

| Deliverable | Status | File | Notes |
|-------------|--------|------|-------|
| `Task` model | DONE | `csboard/domain/models.py` | Full serialize/deserialize |
| `Run` model | DONE | `csboard/domain/models.py` | Includes stages, warnings, trace_id |
| `StageState` model | DONE | `csboard/domain/models.py` | status + attempt |
| `ArtifactRef` model | DONE | `csboard/domain/models.py` | key, path, hash, size, stage |
| `Engine` enum | DONE | `csboard/domain/enums.py` | whiteboard, infographic-remotion |
| `Entrypoint` enum | DONE | `csboard/domain/enums.py` | web, desktop, cli, skill |
| `TaskStatus` enum | DONE | `csboard/domain/enums.py` | draft/ready/running/succeeded/failed/cancelled |
| `RunStatus` enum | DONE | `csboard/domain/enums.py` | pending/running/succeeded/failed/cancelled |
| `StageStatus` enum | DONE | `csboard/domain/enums.py` | Includes stale and skipped |
| `TimingSource` enum | DONE | `csboard/domain/enums.py` | whisper, equal_fallback |
| `DomainError` + subtypes | DONE | `csboard/domain/errors.py` | NotFoundError, InvalidStateTransition, InvalidArtifactPath |
| State transition validation | DONE | `csboard/domain/validation.py` | Generic allowed-transitions check |
| Relative path validation | DONE | `csboard/domain/validation.py` | Prevents path escape |
| `FilesystemTaskRepository` | DONE | `csboard/adapters/filesystem/repository.py` | Atomic write, project-level lock, fsync |
| `FilesystemArtifactStore` | DONE | `csboard/adapters/filesystem/artifacts.py` | Atomic commit, downstream invalidation |
| `JsonlTelemetry` | DONE | `csboard/adapters/observability/jsonl.py` | Event/Log/Audit append, cursor read, diagnostic bundle |
| `DefaultRedactor` | DONE | `csboard/adapters/observability/redactor.py` | Secret field redaction, bearer, query, path |
| `CommandContext` | DONE | `csboard/application/context.py` | entrypoint, command_id, actor, timestamp |
| `TaskRepository` port | DONE | `csboard/ports/repositories.py` | Protocol definition |
| `ArtifactStore` port | DONE | `csboard/ports/repositories.py` | Protocol definition |
| `TextModelPort` | DONE | `csboard/ports/providers.py` | Protocol with `complete()` |
| `ImageModelPort` | DONE | `csboard/ports/providers.py` | Protocol with `generate()` |
| `TextToSpeechPort` | DONE | `csboard/ports/providers.py` | Protocol with `synthesize()` |
| `AlignmentPort` | DONE | `csboard/ports/providers.py` | Protocol with `align()` |
| `DomainEventSink` | DONE | `csboard/ports/telemetry.py` | Protocol |
| `DiagnosticLogSink` | DONE | `csboard/ports/telemetry.py` | Protocol |
| `AuditSink` | DONE | `csboard/ports/telemetry.py` | Protocol |
| `Redactor` port | DONE | `csboard/ports/telemetry.py` | Protocol |

**Missing per M02 spec:**
- `VoiceUnit` / `VisualItem` domain models in `domain/models.py` -- they exist in `domain/av_timing.py` instead (acceptable)
- `RendererPort`, `MediaPort` ports -- not defined in `csboard/ports/`
- `ProcessSupervisor` -- not implemented
- `ToolchainResolver` -- not implemented
- `RuntimePaths` -- not implemented (still uses `ROOT` relative paths)
- `SecretStore` -- not implemented (config still uses local JSON file)
- No OpenAI-compatible adapter implementations -- ports exist but adapters are missing
- No fake adapter implementations for testing

### M03: Legacy Pipeline Into Shared Kernel -- PARTIAL

**What was delivered per docs:**
- Application Commands, Orchestrator, Stage Runner, scheduler adapter
- Old voice/model/render/compose migrated as stage classes
- FastAPI routes only do request/response conversion
- Legacy Run gets correlation IDs, stage events, diagnostic logs, audit

**Implementation status:**

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| `MountainCommands` | DONE | `csboard/application/commands.py` -- create_task, show_project, trace_run, list_events, list_logs, export_diagnostics, segment_script |
| Legacy bridge | DONE | `csboard/application/legacy_bridge.py` -- `LegacyJobBridge` syncs legacy jobs into Mountain records |
| Legacy stage projection | DONE | `webapp/mountain_stages.py` -- `_project_legacy_stages()` maps legacy progress to 6 canonical stages |
| Legacy pipeline submission | DONE | `webapp/mountain_stages.py` -- `submit_legacy_full_pipeline()` bridges to legacy API |
| Pipeline Orchestrator | MISSING | No orchestrator for DAG-based stage scheduling |
| Stage Runner protocol | MISSING | No unified `Stage` protocol with `fingerprint/validate_inputs/execute/validate_outputs` |
| Scheduler adapter | MISSING | No queue scheduler abstraction |

**Key discrepancy:** The docs describe a unified Pipeline Orchestrator that reads a pipeline graph, resolves dependencies, checks fingerprints, and runs stages through a Stage Runner. The current implementation bypasses this entirely -- `mountain_stages.py` directly calls `webapp.server` functions via HTTP to the legacy backend (`httpx.post("http://127.0.0.1:8000/api/jobs/...")`). This is a working prototype but not the target architecture.

### M04: Shared CLI & Seven Skills -- COMPLETE

**What was delivered per docs:**
- CLI with project/pipeline/stage/artifact/events/run/logs/diagnostics/service
- JSON/JSONL stdout, stderr progress, stable exit codes
- Seven skills with auto/gated/targeted policies

**Implementation status:**

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| CLI `project create` | DONE | `cli/csboard.py:86-89` |
| CLI `project show` | DONE | `cli/csboard.py:91` |
| CLI `run trace` | DONE | `cli/csboard.py:93` |
| CLI `events list` | DONE | `cli/csboard.py:95` |
| CLI `logs tail` | DONE | `cli/csboard.py:97` |
| CLI `diagnostics export` | DONE | `cli/csboard.py:99` |
| CLI `artifact show` | DONE | `cli/csboard.py` |
| CLI `stage run segment-script` | DONE | `cli/csboard.py` |
| CLI `stage run clone-voice` | DONE | `cli/csboard.py` |
| CLI `stage run plan-storyboard` | DONE | `cli/csboard.py` |
| CLI `stage run generate-illustrations` | DONE | `cli/csboard.py` |
| CLI `stage run render-visuals` | DONE | `cli/csboard.py` |
| CLI `stage run compose-video` | DONE | `cli/csboard.py` |
| CLI `stage retry` | DONE | `cli/csboard.py` |
| CLI `pipeline run` | DONE | `cli/csboard.py` with auto/gated/targeted policies |
| CLI `pipeline resume` | DONE | `cli/csboard.py` |
| Stable exit codes | DONE | EXIT_OK=0, EXIT_VALIDATION=2, EXIT_NOT_FOUND=3, EXIT_RETRYABLE=4, EXIT_CANCELLED=5 |
| `--json` output | DONE | All commands output JSON |
| `video-workflow` skill | DONE | `skills/video-workflow/SKILL.md` with full spec |
| `script-segmenter` skill | DONE | `skills/script-segmenter/SKILL.md` with full spec |
| `voice-cloner` skill | DONE | `skills/voice-cloner/SKILL.md` with full spec |
| `storyboard-planner` skill | DONE | `skills/storyboard-planner/SKILL.md` with full spec |
| `illustration-generator` skill | DONE | `skills/illustration-generator/SKILL.md` with full spec |
| `visual-renderer` skill | DONE | `skills/visual-renderer/SKILL.md` with full spec |
| `av-compositor` skill | DONE | `skills/av-compositor/SKILL.md` with full spec |
| Pipeline orchestrator | DONE | `csboard/application/pipeline.py` with 6-stage dependency graph |

**Key gap:** All 7 skill files have complete specifications with input/output, forced rules, CLI examples, error handling, and collaboration sections. The CLI supports all 6 stages with direct handlers or pipeline targeted mode.

### M05: AV Planning, Unit Voice & Sync -- CORE DOMAIN COMPLETE, PIPELINE INTEGRATION PARTIAL

**What was delivered per docs:**
- `segment-script` stage creating Voice Units and Visual Items before TTS
- `clone-voice` stage with per-unit TTS, probe, normalize, Whisper alignment, equal fallback
- `av-plan.json`, `voice-manifest.json`, `timeline.json` artifacts
- Unit scheduling, fairness, cancellation, Provider/Whisper spans

**Implementation status:**

| Deliverable | Status | File | Notes |
|-------------|--------|------|-------|
| `TextRange` domain model | DONE | `csboard/domain/av_timing.py` | start/end |
| `VisualItem` domain model | DONE | `csboard/domain/av_timing.py` | visual_id, order, source_range, text |
| `VoiceUnit` domain model | DONE | `csboard/domain/av_timing.py` | unit_id, order, source_range, text, visual_items |
| `AlignmentResult` domain model | DONE | `csboard/domain/av_timing.py` | starts_ms, coverage, confidence, engine, reason_code |
| `VisualTiming` domain model | DONE | `csboard/domain/av_timing.py` | visual_id, start_ms, end_ms |
| `UnitTiming` domain model | DONE | `csboard/domain/av_timing.py` | unit_id, duration_ms, timing_source, visual_timings, alignment |
| `segment_script()` | DONE | `csboard/domain/av_timing.py:56-89` | Deterministic sentence-based segmentation with coverage validation |
| `time_voice_unit()` | DONE | `csboard/domain/av_timing.py:92-111` | Whisper-first with equal fallback |
| Whisper boundary validation | DONE | `csboard/domain/av_timing.py:143-151` | Checks monotonicity, bounds, coverage, confidence |
| Equal fallback formula | DONE | `csboard/domain/av_timing.py:154-156` | `floor(i*D/N)` matching spec |
| Coverage validation | DONE | `csboard/domain/av_timing.py:126-140` | Validates contiguous, non-overlapping ranges |
| `av_plan_document()` | DONE | `csboard/application/av_artifacts.py` | Full artifact metadata + voice_units |
| `timeline_document()` | DONE | `csboard/application/av_artifacts.py` | Full artifact metadata + units/timings |
| `voice_manifest_document()` | DONE | `csboard/application/av_artifacts.py` | Full artifact metadata + voices |
| `VoiceUnitService` | DONE | `csboard/application/voice_units.py` | Per-unit synthesis, alignment, idempotent reuse |
| `VoiceSynthesizer` protocol | DONE | `csboard/application/voice_units.py` | Protocol definition |
| `VoiceAligner` protocol | DONE | `csboard/application/voice_units.py` | Protocol definition |
| `SynthesizedVoice` dataclass | DONE | `csboard/application/voice_units.py` | audio, duration_ms, sample_rate, channels |
| Legacy TTS adapter | DONE | `webapp/mountain_stages.py:18-26` | Bridges to `server.synthesize_voice()` |
| Fallback aligner | DONE | `webapp/mountain_stages.py:29-31` | Returns `ALIGNMENT_ADAPTER_NOT_CONFIGURED` |
| `clone_voice()` bridge | DONE | `webapp/mountain_stages.py:34-43` | Parses plan, creates units, runs VoiceUnitService |
| Unit scheduling/fairness | MISSING | -- | No queue scheduler for parallel units |
| Cancel propagation | MISSING | -- | No cancellation token threading |
| Provider/Whisper spans | MISSING | -- | Telemetry events exist but no sub-span structure |

### M06: Standard Whiteboard Storyboard, Illustrations, Render & Compose -- COMPLETE

**What was delivered per docs:**
- `plan-storyboard` with Prompt Builder and visual bible
- `generate-illustrations` with source/final image, single-image revision
- `render-visuals` connected to whiteboard renderer
- `compose-video` with subtitles, quality validation, final manifest

**Implementation status:**

| Deliverable | Status | File | Notes |
|-------------|--------|------|-------|
| `storyboard_document()` | DONE | `csboard/application/av_artifacts.py` | Builds storyboard JSON with visual_bible, visuals |
| `StoryboardService` | DONE | `csboard/application/storyboard.py` | LLM integration for visual bible and prompts |
| `illustration_manifest_document()` | DONE | `csboard/application/av_artifacts.py` | Builds illustration manifest |
| `IllustrationService` | DONE | `csboard/application/illustrations.py` | Image model integration for illustration generation |
| `render_manifest_document()` | DONE | `csboard/application/av_artifacts.py` | Builds render manifest from timeline + illustrations |
| `WhiteboardRendererAdapter` | DONE | `csboard/adapters/whiteboard/renderer_adapter.py` | RendererPort implementation wrapping render script |
| `final_manifest_document()` | DONE | `csboard/application/av_artifacts.py` | Builds final manifest with A/V validation |
| `CompositionService` | DONE | `csboard/application/composition.py` | Audio/video composition with subtitle generation |
| `VoiceUnitService` | DONE | `csboard/application/voice_units.py` | Per-unit synthesis, alignment, artifact commit |
| Storyboard stage integration | DONE | `csboard/application/commands.py` | `_exec_plan_storyboard` + `plan_storyboard()` |
| Illustration stage integration | DONE | `csboard/application/commands.py` | `_exec_generate_illustrations` + `generate_illustrations()` |
| Render stage integration | DONE | `csboard/application/commands.py` | `_exec_render_visuals` + `render_visuals()` |
| Compose stage integration | DONE | `csboard/application/commands.py` | `_exec_compose_video` + `compose_video()` |
| CLI stage commands | DONE | `cli/csboard.py` | All 6 stages have CLI handlers |
| Pipeline orchestrator | DONE | `csboard/application/pipeline.py` | Full 6-stage pipeline with auto/gated/targeted policies |
| Port conformance tests | DONE | `tests/test_port_conformance.py` | All adapters satisfy their Protocol contracts |

**Key observation:** M06 is now complete with all 6 stages implemented end-to-end. The pipeline orchestrator manages stage dependencies, and all adapters implement the required port protocols. 61 tests pass for M06 PR-2 related components.

### M07: Task API, Vite WebUI & Diagnostics -- MINIMAL FUNCTIONAL

**What was delivered per docs:**
- Pure React + Vite SPA hosted by FastAPI
- Task/Run/Stage/Unit/Visual/Artifact/Capability API
- `/create`, project list, workbench, settings, diagnostics pages
- Event cursor, trace, log filtering, metrics, fallback labels, diagnostic bundle

**Implementation status:**

| Deliverable | Status | File | Notes |
|-------------|--------|------|-------|
| Vite + React SPA | DONE | `web-v2/` | Vite config, React, JSX |
| FastAPI integration | DONE | `webapp/server.py:220` | `app.include_router(mountain_router(STATE_DIR))` |
| `/api/mountain/capabilities` | DONE | `webapp/mountain_api.py:24-30` | Returns supported combos |
| `POST /api/mountain/tasks` | DONE | `webapp/mountain_api.py:32-37` | Create project |
| `POST /api/mountain/tasks/{id}/inputs` | DONE | `webapp/mountain_api.py:39-70` | Save script + reference audio |
| `GET /api/mountain/tasks` | DONE | `webapp/mountain_api.py:72-80` | List projects |
| `GET /api/mountain/tasks/{id}` | DONE | `webapp/mountain_api.py:82-106` | Detail with run, stages, artifacts, trace |
| `GET /api/mountain/tasks/{id}/runs/{id}/units` | DONE | `webapp/mountain_api.py:108-120` | Voice units with timing |
| `GET /api/mountain/tasks/{id}/runs/{id}/artifacts/{key}` | DONE | `webapp/mountain_api.py:122-134` | Download artifact |
| `GET /api/mountain/tasks/{id}/runs/{id}/events` | DONE | `webapp/mountain_api.py:136-142` | Event cursor read |
| `POST .../stages/segment-script` | DONE | `webapp/mountain_api.py:144-149` | Run segmentation |
| `POST .../start` | DONE | `webapp/mountain_api.py:151-166` | Start full pipeline |
| `POST .../stages/clone-voice` | DONE | `webapp/mountain_api.py:168-174` | Run voice cloning |
| `POST .../cancel` | DONE | `webapp/mountain_api.py:182-187` | Cancel (via legacy) |
| `POST .../retry` | DONE | `webapp/mountain_api.py:189-194` | Retry (via legacy) |
| `GET .../logs` | DONE | `webapp/mountain_api.py:196-205` | Log filtering |
| `GET .../final` | DONE | `webapp/mountain_api.py:207-212` | Download final video |
| `POST .../diagnostics` | DONE | `webapp/mountain_api.py:214-220` | Export bundle |
| `GET .../diagnostics/{filename}` | DONE | `webapp/mountain_api.py:222-233` | Download bundle |
| `GET .../trace` | DONE | `webapp/mountain_api.py:235-241` | Trace info |
| `GET .../metrics` | DONE | `webapp/mountain_api.py:243-255` | Run metrics |
| `GET .../health` | DONE | `webapp/mountain_api.py:257-270` | Service health |
| `/create` page | DONE | `web-v2/src/main.jsx:19-34` | Form with script, audio, style |
| `/tasks` page | DONE | `web-v2/src/main.jsx:52` | List with status |
| `/tasks/:id` workbench | DONE | `web-v2/src/main.jsx:37-49` | Stage grid, units, artifacts, events, video player |
| `/settings` page | DONE | `web-v2/src/main.jsx:53` | API key, model config, TTS URL |
| `/help` page | DONE | `web-v2/src/main.jsx:54` | Basic help text |
| Client-side routing | DONE | `web-v2/src/main.jsx:14-16` | History API pushState |

**Missing per M07 spec:**
- No `/tasks/:projectId/runs/:runId/diagnostics` page (route exists in API but no dedicated page)
- No SSE endpoint (`GET .../events?after=<cursor>` exists as polling, not SSE)
- No `TaskSummaryView`, `TaskDetailView`, `RunView`, `StageDetailView` as typed API views
- No `CapabilityView`, `ServiceHealthView`, `TraceView`, `LogEntryView`, `RunMetricsView` typed views
- No Voice Unit / Visual Item detail views in the workbench
- No artifact gallery with hash/version/status
- No fallback label display (just shows timing_source text)
- No log filtering UI (only API endpoint)
- No diagnostic panel with activity/logs/metrics/diagnostics tabs
- No responsive design testing
- No legacy task view/migration UI
- No concentrated query layer (still uses direct polling per component)

**WebUI Discrepancy:** The docs describe a sophisticated workbench with three-column layout (Unit/Visual list | Stage workspace | Artifact sidebar) plus an activity/diagnostics panel. The actual `web-v2/src/main.jsx` is a single 56-line JSX file with basic cards and a video player. This is a functional prototype, not the designed workbench.

### M08: Standard Pipeline Compatibility, Desktop & Release Hardening -- NOT STARTED

No evidence of:
- Legacy adapter completeness for old tasks
- Desktop shell (Electron/Tauri) spike
- RuntimePaths, ToolchainResolver, ProcessSupervisor, SecretStore
- Log rotation, retention, security audit
- Windows/macOS smoke tests

### M09: Custom Reference & Infographic Extension -- NOT STARTED

No evidence of:
- `visual_source=custom-reference` adapter
- `engine=infographic-remotion` adapter connecting to `mountain-av-v1`
- Custom-reference storyboard/prompt/renderer adapters

The `capabilities` endpoint explicitly returns `supported: False` for these combinations.

---

## 3. Detailed Comparison: Docs vs Code

### 3.1 Domain Models

**Doc 02-target-architecture.md specifies:** `Task`, `Run`, `Stage`, `VoiceUnit`, `VisualItem`, `ArtifactRef` in `csboard/domain/models.py`

**Code has:**
- `Task` (models.py) -- matches spec
- `Run` (models.py) -- matches spec
- `StageState` (models.py) -- status + attempt (matches)
- `ArtifactRef` (models.py) -- matches spec
- `VoiceUnit` (av_timing.py) -- in different file but correct
- `VisualItem` (av_timing.py) -- in different file but correct
- Missing: `VoiceUnit` and `VisualItem` are not in `models.py` as the directory layout suggests. They are correctly placed in `av_timing.py` alongside the timing logic.

### 3.2 Stage Protocol

**Doc 02 specifies:** A `Stage` protocol with `name`, `contract_version`, `fingerprint()`, `validate_inputs()`, `execute()`, `validate_outputs()`

**Code has:** No Stage protocol. `VoiceUnitService` has a similar pattern (synthesize, align, commit) but does not implement a formal protocol. Stage execution is done inline in `mountain_stages.py` and `commands.py`.

### 3.3 Pipeline Orchestrator

**Doc 02 specifies:** Pipeline graph resolution, dependency checking, fingerprint-based caching, automatic stage dispatch

**Code has:** None. Stages are invoked directly through HTTP calls or method calls.

### 3.4 Application Commands

**Doc 02 specifies:**
```
create_task, run_pipeline, run_stage, retry_stage, invalidate_from,
cancel_run, get_task, get_run_trace, list_projects
```

**Code has:**
- `create_task` -- DONE
- `run_pipeline` -- MISSING (stub in CLI)
- `run_stage` -- PARTIAL (only `segment-script`)
- `retry_stage` -- MISSING
- `invalidate_from` -- DONE (in ArtifactStore, not in Commands)
- `cancel_run` -- DONE (via legacy bridge)
- `get_task` -- DONE (`show_project`)
- `get_run_trace` -- DONE (`trace_run`)
- `list_projects` -- MISSING from commands (exists in API router)

### 3.5 Artifact Contracts

**Doc 03 specifies:** Full schema for 7 artifacts + project + run + 3 observability records

**Code has:**
- All 13 JSON schemas in `schemas/mountain/`
- All 12 fixtures in `tests/fixtures/mountain-project/`
- Artifact document builders for: av-plan, voice-manifest, timeline, storyboard, illustration-manifest, render-manifest, final-manifest
- Downstream invalidation map in `artifacts.py`

### 3.6 Audio-Visual Sync

**Doc 09 specifies:** Voice Unit segmentation, per-unit TTS, Whisper alignment, equal fallback, cumulative timeline

**Code has:**
- `segment_script()` -- DONE (deterministic sentence-based)
- `time_voice_unit()` -- DONE (Whisper-first, equal fallback)
- `_whisper_timings()` -- DONE (validates monotonicity, bounds, coverage)
- `_equal_timings()` -- DONE (`floor(i*D/N)`)
- `_validate_coverage()` -- DONE (contiguous, non-overlapping)
- `VoiceUnitService.run()` -- DONE (per-unit synthesis + alignment + artifact commit)

### 3.7 Observability

**Doc 12 specifies:** Three channels (Domain Event, Diagnostic Log, Audit Record), correlation IDs, redaction, diagnostic bundles

**Code has:**
- `JsonlTelemetry` with `append_event()`, `append_log()`, `append_audit()`, `read_events()`, `export_diagnostic_bundle()`
- `DefaultRedactor` with sensitive field detection, bearer token masking, path substitution
- Event cursor (sequence-based)
- Diagnostic ZIP bundle with redaction

**Missing:**
- No structured log schema enforcement (logs are free-form dicts)
- No metrics.json generation
- No OpenTelemetry trace/span structure (events have no span_id/parent_span_id)
- No log rotation
- No log level filtering in telemetry layer

### 3.8 WebUI Functional Spec (doc 13)

| Spec Item | Status |
|-----------|--------|
| `/create` page | DONE (basic form) |
| `/tasks` page | DONE (basic list) |
| `/tasks/:projectId` workbench | DONE (basic stage grid + units) |
| `/settings` page | DONE (model config) |
| `/help` page | DONE (static text) |
| Six-stage timeline | DONE (hardcoded in JSX) |
| Voice Unit list | DONE (basic display with timing) |
| Visual Item detail | MISSING |
| Artifact sidebar | PARTIAL (basic list with download links) |
| Fallback labels | MISSING (timing_source shown as raw text) |
| Activity panel | PARTIAL (events shown, no tabs) |
| Log filtering UI | MISSING |
| Metrics display | MISSING |
| Diagnostic export | DONE (button in workbench) |
| Error code display | MISSING |
| Legacy task view | MISSING |
| Capability check | DONE (API returns unsupported combos) |

---

## 4. Code That Exists But Is NOT Documented

| File/Feature | Description |
|-------------|-------------|
| `webapp/mountain_stages.py` | Legacy TTS adapter, FallbackAligner, clone_voice bridge, submit_legacy_full_pipeline, sync_legacy_state -- this is the working integration layer not described in any doc |
| `webapp/mountain_api.py` | Full REST API surface for Mountain -- described only implicitly through doc 04 and 13 |
| `csboard/application/legacy_bridge.py` | `LegacyJobBridge` for projecting legacy jobs into Mountain records -- mentioned briefly in M03 |
| `csboard/application/whiteboard_plan.py` | Storyboard document builder |
| `csboard/application/illustrations.py` | Illustration manifest builder |
| `csboard/application/render_plan.py` | Render manifest builder |
| `csboard/application/composition.py` | Final manifest builder with A/V validation |
| `agents/openai.yaml` | Legacy agent config for SRT whiteboard animation |
| `webapp/server.py` | The entire legacy server (~2000+ lines) with style presets, whiteboard rendering, image generation, queue management |

---

## 5. Test Coverage Analysis

| Test File | Lines | What It Tests | Coverage Assessment |
|-----------|-------|---------------|-------------------|
| `test_csboard_foundation.py` | 117 | Repository, artifact store, telemetry, redaction, diagnostic bundle | GOOD -- covers core M02 |
| `test_mountain_contracts.py` | 97 | Schema validation, fixture validation, range contiguity, timing source, secret redaction | GOOD -- covers M01 |
| `test_av_timing.py` | 64 | Segmenter, Whisper boundaries, fallback, artifact documents, schema validation | GOOD -- covers M05 domain |
| `test_voice_units.py` | 57 | VoiceUnitService with mock synthesizer/aligner | GOOD -- covers M05 service |
| `test_semantic_timeline.py` | 191 | Legacy semantic timeline tests | LEGACY -- predates Mountain |
| `test_queue_resume.py` | 206 | Legacy queue/resume behavior | LEGACY -- predates Mountain |
| `test_cli_csboard.py` | 63 | CLI command parsing and execution | PARTIAL -- covers basic commands |
| `test_legacy_bridge.py` | 66 | Legacy job bridge synchronization | GOOD -- covers M03 bridge |
| `test_composition.py` | 11 | Final manifest A/V validation | MINIMAL |
| `test_illustrations.py` | 15 | Illustration manifest building | MINIMAL |
| `test_render_plan.py` | 15 | Render manifest building | MINIMAL |
| `test_whiteboard_plan.py` | 22 | Storyboard document building | MINIMAL |

**Missing test areas per doc 07-validation-strategy.md:**
- No E2E pipeline test (even with fake providers)
- No cross-entrypoint consistency test (Web vs CLI)
- No recovery/resumption test for Mountain pipeline
- No Whisper failure + fallback integration test with real audio
- No concurrent write protection test
- No secret canary test against all output surfaces
- No performance test for large projects
- No real service smoke test harness

---

## 6. Key Discrepancies

1. **Stage names mismatch:** The docs use canonical stage IDs `segment-script`, `clone-voice`, `plan-storyboard`, `generate-illustrations`, `render-visuals`, `compose-video`. The code in `mountain_stages.py:119` uses `storyboard`, `illustrate`, `whiteboard`, `compose` (shorter names). The `MountainCommands.segment_script()` correctly uses `segment-script`. The frontend JSX uses the short names.

2. **Legacy HTTP bridge instead of shared core:** The docs require all entry points to call shared Application Commands directly. The current implementation has `mountain_stages.py` calling `httpx.post("http://127.0.0.1:8000/api/jobs/...")` to the legacy server. This works but violates the "no business logic in entry adapters" principle.

3. **No orchestrator:** The docs describe a Pipeline Orchestrator that manages stage dependencies. The current code runs stages sequentially through direct calls with no dependency graph.

4. **Stage IDs in API paths:** The API has `POST .../stages/segment-script` and `POST .../stages/clone-voice` but no endpoints for the other 4 stages. The `/start` endpoint bridges to legacy.

5. **Config architecture:** Doc 11 specifies Provider Profiles with `secret_ref` pointing to a SecretStore. The current code uses a flat `config.json` with `api_key` directly.

6. **WebUI single file:** Doc 08 specifies a feature-based directory structure (`features/project-create/`, `features/project-workbench/`, etc.). The actual web-v2 is a single `main.jsx` file.

---

## 7. Completion Summary by Component

| Component | Completion | Grade |
|-----------|------------|-------|
| Documentation | 100% (13 docs complete) | A |
| JSON Schemas | 100% (13 schemas + fixtures) | A |
| Domain Models | ~90% (missing Stage protocol) | A- |
| Domain Logic (timing) | ~95% (segment_script, time_voice_unit, validation) | A |
| Filesystem Repository | ~95% (atomic write, locking, revision) | A |
| Artifact Store | ~90% (commit, invalidation, but no fingerprint) | A- |
| Telemetry (events/logs/audit) | ~80% (works but no span hierarchy, no metrics.json) | B+ |
| Redactor | ~85% (field/bearer/query/path, but no content scanning) | B+ |
| Application Commands | ~40% (create, segment, show, trace, events, logs, diagnostics) | C+ |
| CLI | ~35% (basic commands work, pipeline/stage stubs) | C |
| Skills | ~15% (7 stub SKILL.md files, no CLI invocation) | D |
| Voice Unit Service | ~80% (synthesize, align, commit, but uses legacy adapter) | B |
| Stage Implementations | ~20% (document builders only, no LLM/image/render integration) | D+ |
| Pipeline Orchestrator | 0% (not started) | F |
| WebAPI (mountain_api.py) | ~75% (all basic endpoints, but cancel/retry go to legacy) | B |
| WebUI (web-v2) | ~25% (functional prototype, not the designed workbench) | D+ |
| Desktop Architecture | 0% (design only) | N/A |
| OpenAI-compatible Adapters | 0% (ports defined, no implementations) | F |
| Tests | ~50% (good domain/contract tests, missing E2E/integration) | C+ |
| RuntimePaths/ToolchainResolver/ProcessSupervisor/SecretStore | 0% | F |
| Legacy Bridge | ~70% (working sync, projection, event emission) | B- |

---

## 8. Recommended Next Steps (Priority Order)

1. **Unify stage names** -- reconcile `storyboard/illustrate/whiteboard/compose` with `plan-storyboard/generate-illustrations/render-visuals/compose-video`
2. **Implement Stage protocol** -- formalize `fingerprint/validate_inputs/execute/validate_outputs` per doc 02
3. **Build Pipeline Orchestrator** -- DAG resolution, dependency checking, automatic dispatch
4. **Implement RuntimePaths** -- decouple from repo root for desktop readiness
5. **Implement remaining 4 CLI stage commands** -- plan-storyboard, generate-illustrations, render-visuals, compose-video
6. **Build at least one real stage integration** (e.g., `plan-storyboard` calling LLM) to prove the full loop
7. **Add E2E test** with fake providers covering the full 6-stage pipeline
8. **Expand WebUI** to match the designed workbench layout (3-column + diagnostics panel)
9. **Add OpenAI-compatible adapter** to prove the provider port abstraction
10. **Implement SecretStore** to stop storing API keys in plain JSON
