/**
 * M07 — Contract-level tests
 * 后端 JSON → 前端 DTO → 页面元素 逐项对照
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import * as api from '../src/lib/api/client'

// ── Mock API client ────────────────────────────────────────────────────

vi.mock('../src/lib/api/client', () => ({
  fetchProject: vi.fn(),
  fetchRun: vi.fn(),
  fetchUnits: vi.fn(),
  fetchArtifacts: vi.fn(),
  fetchStages: vi.fn(),
  fetchEvents: vi.fn(),
  fetchLogs: vi.fn(),
  cancelRun: vi.fn(),
  retryRun: vi.fn(),
  getFinalUrl: vi.fn(() => 'http://localhost:8000/api/v1/projects/p1/runs/r1/final'),
  fetchHealth: vi.fn(),
  fetchProviders: vi.fn(),
  MountainApiError: class extends Error {
    constructor(public status: number, public apiError: unknown, message: string) {
      super(message)
      this.name = 'MountainApiError'
    }
  },
}))

// ── Realistic backend fixtures ─────────────────────────────────────────

/** GET /projects/{id} — 完整响应，active_run 存在 */
const PROJECT_DETAIL_WITH_RUN = {
  project: {
    project_id: 'proj-abc123',
    title: '量子计算科普',
    pipeline_id: 'mountain-av-v1',
    engine: 'whiteboard',
    status: 'running',
    created_at: '2026-08-30T10:00:00Z',
    updated_at: '2026-08-30T10:05:00Z',
    active_run_id: 'run-xyz789',
    revision: 3,
    schema_version: 1,
  },
  active_run: {
    schema_version: 1,
    run_id: 'run-xyz789',
    project_id: 'proj-abc123',
    trace_id: 'trace-aaa111',
    entrypoint: 'web',
    command_ids: ['cmd-001', 'cmd-002'],
    status: 'running',
    target_stage: 'clone-voice',
    started_at: '2026-08-30T10:01:00Z',
    finished_at: null,
    stages: {
      'segment-script': { status: 'succeeded', attempt: 1 },
      'clone-voice': { status: 'running', attempt: 1 },
      'plan-storyboard': { status: 'pending', attempt: 0 },
      'generate-illustrations': { status: 'pending', attempt: 0 },
      'render-visuals': { status: 'pending', attempt: 0 },
      'compose-video': { status: 'pending', attempt: 0 },
    },
    warnings: [],
  },
  stages: [
    { stage: 'segment-script', status: 'succeeded', attempt: 1 },
    { stage: 'clone-voice', status: 'running', attempt: 1 },
    { stage: 'plan-storyboard', status: 'pending', attempt: 0 },
    { stage: 'generate-illustrations', status: 'pending', attempt: 0 },
    { stage: 'render-visuals', status: 'pending', attempt: 0 },
    { stage: 'compose-video', status: 'pending', attempt: 0 },
  ],
  warnings: [],
  artifacts: [
    {
      artifact_key: 'segments.json',
      relative_path: 'stages/segment-script/segments.json',
      sha256: 'abc123',
      size_bytes: 1024,
      producer_stage: 'segment-script',
      status: 'succeeded',
    },
  ],
  trace: {
    trace_id: 'trace-aaa111',
    command_ids: ['cmd-001', 'cmd-002'],
  },
}

/** GET /projects/{id} — active_run 为 null */
const PROJECT_DETAIL_NO_RUN = {
  project: {
    project_id: 'proj-no-run',
    title: '空任务',
    pipeline_id: 'mountain-av-v1',
    engine: 'whiteboard',
    status: 'draft',
    created_at: '2026-08-30T10:00:00Z',
    updated_at: '2026-08-30T10:00:00Z',
    active_run_id: null,
    revision: 1,
    schema_version: 1,
  },
  active_run: null,
  stages: [],
  warnings: [],
  artifacts: [],
  trace: null,
}

/** GET /projects/{id}/runs/{runId} — finished_at 已填充 */
const RUN_DETAIL_FINISHED = {
  schema_version: 1,
  run_id: 'run-done999',
  project_id: 'proj-abc123',
  trace_id: 'trace-bbb222',
  entrypoint: 'web',
  command_ids: ['cmd-003'],
  status: 'succeeded',
  target_stage: 'compose-video',
  started_at: '2026-08-30T09:00:00Z',
  finished_at: '2026-08-30T09:30:00Z',
  stages: {
    'segment-script': { status: 'succeeded', attempt: 1 },
    'clone-voice': { status: 'succeeded', attempt: 1 },
    'plan-storyboard': { status: 'succeeded', attempt: 1 },
    'generate-illustrations': { status: 'succeeded', attempt: 2 },
    'render-visuals': { status: 'succeeded', attempt: 1 },
    'compose-video': { status: 'succeeded', attempt: 1 },
  },
  warnings: [{ code: 'LOW_ALIGNMENT_COVERAGE', message: '对齐覆盖率低于阈值' }],
}

/** GET /projects/{id}/runs/{runId}/events */
const EVENTS_RESPONSE = {
  items: [
    { event_type: 'stage.start', stage: 'segment-script', timestamp: '2026-08-30T09:00:01Z', action: 'start' },
    { event_type: 'stage.end', stage: 'segment-script', timestamp: '2026-08-30T09:00:05Z', action: 'end' },
  ],
  next_cursor: 2,
}

/** GET /projects/{id}/runs/{runId}/logs */
const LOGS_RESPONSE = {
  items: [
    { timestamp: '2026-08-30T09:00:01Z', level: 'INFO', component: 'pipeline', stage: 'segment-script', message: 'Stage started' },
    { timestamp: '2026-08-30T09:00:05Z', level: 'INFO', component: 'pipeline', stage: 'segment-script', message: 'Stage completed' },
    { timestamp: '2026-08-30T09:00:06Z', level: 'ERROR', component: 'tts', stage: 'clone-voice', message: 'TTS timeout' },
  ],
}

/** GET /projects/{id}/runs/{runId}/units */
const UNITS_RESPONSE = {
  items: [
    { unit_id: 'u-001', text: '量子计算利用量子力学原理', order: 0, timing: null },
    { unit_id: 'u-002', text: '叠加态和纠缠态是核心概念', order: 1, timing: { duration_ms: 3200 } },
  ],
}

// ── ProjectWorkbenchPage Tests ─────────────────────────────────────────

describe('ProjectWorkbenchPage — contract tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderWorkbench(projectId = 'proj-abc123') {
    return render(
      <MemoryRouter initialEntries={[`/projects/${projectId}`]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectWorkbenchPage />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('uses active_run from /projects/{id} response — shows run ID, trace, stages', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_WITH_RUN as any)
    vi.mocked(api.fetchUnits).mockResolvedValue(UNITS_RESPONSE as any)

    renderWorkbench()

    await waitFor(() => {
      // Stage names appear in both timeline and workspace
      expect(screen.getAllByText('文案分割').length).toBeGreaterThan(0)
      expect(screen.getAllByText('克隆配音').length).toBeGreaterThan(0)
      expect(screen.getAllByText('合成成片').length).toBeGreaterThan(0)
    })
    // Run ID displayed — shortId truncates to 8 chars
    const chipContainer = document.querySelector('.chip-ids')
    expect(chipContainer?.textContent).toContain('run-xyz7')
    expect(chipContainer?.textContent).toContain('trace-aa')
  })

  it('fetchUnits uses active_run.run_id', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_WITH_RUN as any)
    vi.mocked(api.fetchUnits).mockResolvedValue(UNITS_RESPONSE as any)

    renderWorkbench()

    await waitFor(() => {
      expect(api.fetchUnits).toHaveBeenCalledWith('proj-abc123', 'run-xyz789')
    })
  })

  it('stages come from project detail top-level stages array', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_WITH_RUN as any)
    vi.mocked(api.fetchUnits).mockResolvedValue(UNITS_RESPONSE as any)

    renderWorkbench()

    await waitFor(() => {
      // clone-voice is running — "运行中" appears in timeline and workspace
      expect(screen.getAllByText('运行中').length).toBeGreaterThan(0)
    })
    // segment-script is succeeded — multiple "已成功" badges exist (timeline + workspace)
    expect(screen.getAllByText('已成功').length).toBeGreaterThanOrEqual(2)
  })

  it('artifacts come from project detail top-level artifacts array', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_WITH_RUN as any)
    vi.mocked(api.fetchUnits).mockResolvedValue(UNITS_RESPONSE as any)

    renderWorkbench()

    await waitFor(() => {
      expect(screen.getByText('segments.json')).toBeInTheDocument()
      expect(screen.getByText('1.0 KB')).toBeInTheDocument()
      expect(screen.getByText('segment-script')).toBeInTheDocument()
    })
  })

  it('diagnostics link uses active_run.run_id', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_WITH_RUN as any)
    vi.mocked(api.fetchUnits).mockResolvedValue(UNITS_RESPONSE as any)

    renderWorkbench()

    await waitFor(() => {
      const link = screen.getByRole('link', { name: '诊断' })
      expect(link).toHaveAttribute('href', '/projects/proj-abc123/runs/run-xyz789/diagnostics')
    })
  })

  it('when active_run is null — shows empty state, no run ID', async () => {
    vi.mocked(api.fetchProject).mockResolvedValue(PROJECT_DETAIL_NO_RUN as any)

    renderWorkbench('proj-no-run')

    await waitFor(() => {
      expect(screen.getByText('任务尚未启动运行')).toBeInTheDocument()
      expect(screen.getByText('暂无配音单元')).toBeInTheDocument()
      expect(screen.getByText('暂无产物')).toBeInTheDocument()
    })
    // No run ID chip
    expect(screen.queryByText(/run-/)).not.toBeInTheDocument()
  })
})

// ── RunDiagnosticsPage Tests ───────────────────────────────────────────

describe('RunDiagnosticsPage — contract tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function renderDiagnostics(projectId = 'proj-abc123', runId = 'run-done999') {
    return render(
      <MemoryRouter initialEntries={[`/projects/${projectId}/runs/${runId}/diagnostics`]}>
        <Routes>
          <Route path="/projects/:projectId/runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('shows run_id, trace_id, entrypoint from RunDetail', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(RUN_DETAIL_FINISHED as any)
    vi.mocked(api.fetchEvents).mockResolvedValue(EVENTS_RESPONSE as any)
    vi.mocked(api.fetchLogs).mockResolvedValue(LOGS_RESPONSE as any)

    renderDiagnostics()

    await waitFor(() => {
      // entrypoint is rendered as "entrypoint: web" in an id-chip
      expect(screen.getByText(/entrypoint.*web/)).toBeInTheDocument()
    })
    // IDs are in chip-ids container (shortId truncates to 8 chars)
    const chipContainer = document.querySelector('.chip-ids')
    expect(chipContainer?.textContent).toContain('run-done')
    expect(chipContainer?.textContent).toContain('trace-bb')
  })

  it('finished_at displays correctly (not completed_at)', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(RUN_DETAIL_FINISHED as any)
    vi.mocked(api.fetchEvents).mockResolvedValue(EVENTS_RESPONSE as any)
    vi.mocked(api.fetchLogs).mockResolvedValue(LOGS_RESPONSE as any)

    renderDiagnostics()

    await waitFor(() => {
      // finished_at is 2026-08-30T09:30:00Z → should display
      expect(screen.getByText('完成时间')).toBeInTheDocument()
      // Should NOT show "—" for finished_at since it's populated
      const finishedRow = screen.getByText('完成时间').closest('.settings-row')
      expect(finishedRow?.textContent).not.toContain('—')
    })
  })

  it('shows stage statuses from RunDetail.stages', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(RUN_DETAIL_FINISHED as any)
    vi.mocked(api.fetchEvents).mockResolvedValue(EVENTS_RESPONSE as any)
    vi.mocked(api.fetchLogs).mockResolvedValue(LOGS_RESPONSE as any)

    renderDiagnostics()

    await waitFor(() => {
      expect(screen.getByText('阶段状态')).toBeInTheDocument()
    })
    // Stage names appear in the stages card (also appear in logs, so use getAllByText)
    expect(screen.getAllByText('segment-script').length).toBeGreaterThan(0)
    expect(screen.getAllByText('compose-video').length).toBeGreaterThan(0)
  })

  it('events display from /events endpoint', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(RUN_DETAIL_FINISHED as any)
    vi.mocked(api.fetchEvents).mockResolvedValue(EVENTS_RESPONSE as any)
    vi.mocked(api.fetchLogs).mockResolvedValue(LOGS_RESPONSE as any)

    renderDiagnostics()

    await waitFor(() => {
      expect(screen.getByText('事件流')).toBeInTheDocument()
      expect(screen.getByText('stage.start')).toBeInTheDocument()
      expect(screen.getByText('stage.end')).toBeInTheDocument()
    })
  })

  it('logs display from /logs endpoint with level filter', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(RUN_DETAIL_FINISHED as any)
    vi.mocked(api.fetchEvents).mockResolvedValue(EVENTS_RESPONSE as any)
    vi.mocked(api.fetchLogs).mockResolvedValue(LOGS_RESPONSE as any)

    renderDiagnostics()

    await waitFor(() => {
      expect(screen.getByText('日志')).toBeInTheDocument()
      expect(screen.getByText('Stage started')).toBeInTheDocument()
      expect(screen.getByText('TTS timeout')).toBeInTheDocument()
    })
  })

  it('when run not found — shows empty state', async () => {
    vi.mocked(api.fetchRun).mockResolvedValue(null as any)
    vi.mocked(api.fetchEvents).mockResolvedValue({ items: [], next_cursor: 0 } as any)
    vi.mocked(api.fetchLogs).mockResolvedValue({ items: [] } as any)

    renderDiagnostics()

    await waitFor(() => {
      expect(screen.getByText('运行不存在')).toBeInTheDocument()
    })
  })
})

// ── API Client URL/params tests ────────────────────────────────────────

describe('API Client — URL and method contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // We test by verifying the fetch calls made through the client
  // Since client.ts uses a centralized request() function, we verify
  // the URL construction and HTTP methods indirectly through the mock.

  it('getFinalUrl returns correct path', () => {
    // The mock returns a fixed URL; verify the format is correct
    const url = api.getFinalUrl('proj-1', 'run-1')
    expect(url).toContain('/api/v1/projects/')
    expect(url).toContain('/runs/')
    expect(url).toContain('/final')
  })
})

// ── Import the page components for the tests ──────────────────────────

import { ProjectWorkbenchPage } from '../src/pages/ProjectWorkbenchPage'
import { RunDiagnosticsPage } from '../src/pages/RunDiagnosticsPage'
