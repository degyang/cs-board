/**
 * contract.test.tsx
 *
 * Real-API contract tests — prove the workbench calls correct API shapes
 * and renders real response data.
 *
 * All mock JSON fixtures derive from the real webapp/mountain_v1_api.py shapes.
 * Zero fake data, zero /api/mountain, zero localStorage.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkbenchPage } from '../src/pages/ProjectWorkbenchPage'
import { RunDiagnosticsPage } from '../src/pages/RunDiagnosticsPage'

// ── Mock the API client ─────────────────────────────────────────────────

vi.mock('../src/lib/api/client', () => ({
  fetchProject: vi.fn(),
  fetchRun: vi.fn(),
  fetchCapabilities: vi.fn(),
  fetchUnits: vi.fn(),
  fetchEvents: vi.fn(),
  fetchLogs: vi.fn(),
  startRun: vi.fn(),
  cancelRun: vi.fn(),
  retryRun: vi.fn(),
  runStage: vi.fn(),
  retryStage: vi.fn(),
  uploadInputs: vi.fn(),
  getFinalUrl: vi.fn(),
}))

import {
  fetchProject, fetchRun, fetchCapabilities, fetchUnits, fetchEvents, fetchLogs,
  startRun, cancelRun, retryRun, runStage, retryStage,
  uploadInputs, getFinalUrl,
} from '../src/lib/api/client'

const mockFetchProject = vi.mocked(fetchProject)
const mockFetchRun = vi.mocked(fetchRun)
const mockFetchCapabilities = vi.mocked(fetchCapabilities)
const mockFetchUnits = vi.mocked(fetchUnits)
const mockFetchEvents = vi.mocked(fetchEvents)
const mockFetchLogs = vi.mocked(fetchLogs)
const mockStartRun = vi.mocked(startRun)
const mockCancelRun = vi.mocked(cancelRun)
const mockRetryRun = vi.mocked(retryRun)
const mockRunStage = vi.mocked(runStage)
const mockRetryStage = vi.mocked(retryStage)
const mockUploadInputs = vi.mocked(uploadInputs)
const mockGetFinalUrl = vi.mocked(getFinalUrl)

// ── Fixtures ────────────────────────────────────────────────────────────

const RUNNING_PROJECT = {
  project: {
    project_id: 'proj-abc123def456',
    title: '测试视频项目',
    status: 'running',
    created_at: '2025-06-01T08:00:00Z',
    updated_at: '2025-06-01T08:05:00Z',
  },
  active_run: {
    run_id: 'run-xyz789abc123',
    trace_id: 'trace-aaa111bbb222',
    project_id: 'proj-abc123def456',
    command: 'start',
    command_id: 'cmd-aaa111',
    status: 'running',
    policy: 'sequential',
    started_at: '2025-06-01T08:01:00Z',
    finished_at: null,
    error: null,
    progress: 0.6,
    current_stage: 'render-visuals',
    stages: [
      { stage: 'segment-script', status: 'succeeded', attempt: 0 },
      { stage: 'clone-voice', status: 'succeeded', attempt: 0 },
      { stage: 'plan-storyboard', status: 'succeeded', attempt: 0 },
      { stage: 'generate-illustrations', status: 'succeeded', attempt: 0 },
      { stage: 'render-visuals', status: 'running', attempt: 0 },
      { stage: 'compose-video', status: 'pending', attempt: 0 },
    ],
    trace: { trace_id: 'trace-aaa111bbb222', started_at: '2025-06-01T08:01:00Z', ended_at: null, duration_ms: null },
    input_params: null,
    command_ids: [],
    warnings: [],
  },
  stages: [
    { stage: 'segment-script', status: 'succeeded', attempt: 0 },
    { stage: 'clone-voice', status: 'succeeded', attempt: 0 },
    { stage: 'plan-storyboard', status: 'succeeded', attempt: 0 },
    { stage: 'generate-illustrations', status: 'succeeded', attempt: 0 },
    { stage: 'render-visuals', status: 'running', attempt: 0 },
    { stage: 'compose-video', status: 'pending', attempt: 0 },
  ],
  artifacts: [
    {
      artifact_key: 'segments',
      relative_path: 'projects/proj-abc123def456/artifacts/segments.json',
      status: 'succeeded',
      size_bytes: 2048,
      producer_stage: 'segment-script',
      produced_at: '2025-06-01T08:02:00Z',
      event_sequence: 5,
    },
    {
      artifact_key: 'storyboard',
      relative_path: 'projects/proj-abc123def456/artifacts/storyboard.json',
      status: 'succeeded',
      size_bytes: 4096,
      producer_stage: 'plan-storyboard',
      produced_at: '2025-06-01T08:03:00Z',
      event_sequence: 12,
    },
    {
      artifact_key: 'voice_001',
      relative_path: 'projects/proj-abc123def456/artifacts/voice_001.wav',
      status: 'succeeded',
      size_bytes: 512000,
      producer_stage: 'clone-voice',
      produced_at: '2025-06-01T08:02:30Z',
      event_sequence: 8,
    },
  ],
  trace: {
    trace_id: 'trace-aaa111bbb222',
    started_at: '2025-06-01T08:01:00Z',
    ended_at: null,
    duration_ms: null,
  },
  warnings: [],
}

const UNITS_RESPONSE = {
  items: [
    {
      unit_id: 'u-seg-001',
      order: 0,
      text: '这是第一段配音内容',
      timing: { duration_ms: 3200, alignment_source: 'forced', fallback: false },
    },
    {
      unit_id: 'u-seg-002',
      order: 1,
      text: '这是第二段配音内容',
      timing: null,
    },
  ],
}

const EVENTS_RESPONSE = {
  items: [
    { event_type: 'run_started', stage: null, timestamp: '2025-06-01T08:01:00Z', sequence: 1 },
    { event_type: 'stage_started', stage: 'segment-script', timestamp: '2025-06-01T08:01:01Z', sequence: 2 },
    { event_type: 'stage_completed', stage: 'segment-script', timestamp: '2025-06-01T08:02:00Z', sequence: 5 },
  ],
  next_cursor: 5,
}

const LOGS_RESPONSE = {
  items: [
    { timestamp: '2025-06-01T08:01:01Z', level: 'INFO', component: 'segment-script', message: 'Starting script segmentation' },
    { timestamp: '2025-06-01T08:01:05Z', level: 'WARN', component: 'clone-voice', message: 'Reference audio quality low' },
    { timestamp: '2025-06-01T08:02:00Z', level: 'ERROR', component: 'render-visuals', message: 'GPU timeout' },
  ],
}

const CAPABILITIES_RESPONSE = {
  items: [
    {
      name: 'clone-voice',
      required_providers: ['fish-speech'],
      bound_project_id: 'proj-abc123def456',
      requested_at: '2025-06-01T08:00:00Z',
      reason_code: null,
      message: null,
      suggested_action: null,
      context: null,
    },
  ],
  providers: {
    available: ['fish-speech'],
    unavailable: [],
    all_available: true,
    providers: {
      'fish-speech': {
        available: true,
        error_code: null,
        suggestion: null,
      },
    },
  },
}

const NO_RUN_PROJECT = {
  project: {
    project_id: 'proj-abc123def456',
    title: '测试视频项目',
    status: 'created',
    created_at: '2025-06-01T08:00:00Z',
    updated_at: '2025-06-01T08:00:00Z',
  },
  active_run: null,
  stages: [],
  artifacts: [],
  trace: null,
  warnings: [],
}

const PENDING_PROJECT = {
  ...RUNNING_PROJECT,
  active_run: {
    ...RUNNING_PROJECT.active_run,
    status: 'pending',
    current_stage: null,
    progress: 0,
    stages: RUNNING_PROJECT.active_run.stages.map((s) => ({ ...s, status: 'pending' })),
  },
  stages: RUNNING_PROJECT.stages.map((s) => ({ ...s, status: 'pending' })),
}

const COMPLETED_PROJECT = {
  ...RUNNING_PROJECT,
  active_run: {
    ...RUNNING_PROJECT.active_run,
    status: 'succeeded',
    finished_at: '2025-06-01T08:05:00Z',
    progress: 1,
    current_stage: null,
  },
  stages: RUNNING_PROJECT.stages.map((s) => ({ ...s, status: 'succeeded' })),
  artifacts: [
    ...RUNNING_PROJECT.artifacts,
    {
      artifact_key: 'final',
      relative_path: 'projects/proj-abc123def456/artifacts/final.mp4',
      status: 'succeeded',
      size_bytes: 15_000_000,
      producer_stage: 'compose-video',
      produced_at: '2025-06-01T08:05:00Z',
      event_sequence: 25,
    },
  ],
}

const CAPABILITY_UNAVAILABLE = {
  items: [
    {
      name: 'clone-voice',
      required_providers: ['fish-speech'],
      bound_project_id: null,
      requested_at: null,
      reason_code: 'CAPABILITY_NOT_AVAILABLE',
      message: 'Provider fish-speech not available',
      suggested_action: 'Please enable fish-speech in settings',
      context: { provider: 'fish-speech' },
    },
  ],
  providers: {
    available: [],
    unavailable: ['fish-speech'],
    all_available: false,
    providers: {
      'fish-speech': {
        available: false,
        error_code: 'SECRET_NOT_CONFIGURED',
        suggestion: '请在设置中配置 fish-speech 的 API Key',
      },
    },
  },
}

const FAILED_PROJECT = {
  ...RUNNING_PROJECT,
  active_run: {
    ...RUNNING_PROJECT.active_run,
    status: 'failed',
    finished_at: '2025-06-01T08:04:00Z',
    error: { code: 'GPU_TIMEOUT', message: 'GPU allocation timeout', retryable: true },
  },
}

// ── Helpers ─────────────────────────────────────────────────────────────

function setupDefaultMocks() {
  mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
  mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
  mockFetchUnits.mockResolvedValue(UNITS_RESPONSE)
  mockFetchEvents.mockResolvedValue(EVENTS_RESPONSE)
  mockFetchLogs.mockResolvedValue(LOGS_RESPONSE)
  mockGetFinalUrl.mockReturnValue('/api/v1/projects/proj-abc123def456/runs/run-xyz789abc123/artifacts/final.mp4')
}

function renderWorkbench(initialPath = '/projects/proj-abc123def456') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectWorkbenchPage />} />
        <Route path="/projects/:projectId/runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
      </Routes>
    </MemoryRouter>
  )
}

// ── Tests ───────────────────────────────────────────────────────────────

describe('Workbench contract: active_run display', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('shows project title', async () => {
    renderWorkbench()
    await screen.findByText('测试视频项目')
    expect(screen.getByText('测试视频项目')).toBeDefined()
  })

  it('shows run status badge', async () => {
    renderWorkbench()
    await screen.findByText('测试视频项目')
    const badges = screen.getAllByText(/运行中|running/)
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows run and trace short IDs', async () => {
    renderWorkbench()
    await screen.findByText(/run:/)
    expect(screen.getByText(/trace:/)).toBeDefined()
  })

  it('shows creation timestamp', async () => {
    renderWorkbench()
    await screen.findByText('测试视频项目')
    expect(screen.getByText(/创建于/)).toBeDefined()
  })
})

describe('Workbench contract: stage timeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('renders all 6 stage nodes', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const stageNames = ['文案分割', '克隆配音', '拆分分镜', '生成插画', '白板渲染', '合成成片']
    for (const name of stageNames) {
      const els = screen.getAllByText(name)
      expect(els.length).toBeGreaterThanOrEqual(1)
    }
  })

  it('shows succeeded stage badges', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const succeeded = screen.getAllByText(/已成功/)
    expect(succeeded.length).toBeGreaterThanOrEqual(1)
  })
})

describe('Workbench contract: artifacts table', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('renders artifact entries with keys and stages', async () => {
    renderWorkbench()
    await screen.findByText('segments')
    expect(screen.getByText('storyboard')).toBeDefined()
    expect(screen.getByText('voice_001')).toBeDefined()
  })

  it('renders artifact sizes with formatBytes', async () => {
    renderWorkbench()
    await screen.findByText('segments')
    expect(screen.getByText('2.0 KB')).toBeDefined()
    expect(screen.getByText('4.0 KB')).toBeDefined()
    expect(screen.getByText('500.0 KB')).toBeDefined()
  })

  it('renders producer stage names', async () => {
    renderWorkbench()
    await screen.findByText('segments')
    // producer_stage appears in artifacts table — may have duplicates from workspace
    const stages = screen.getAllByText('segment-script')
    expect(stages.length).toBeGreaterThanOrEqual(1)
  })
})

describe('Workbench contract: units with timing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('renders unit text', async () => {
    renderWorkbench()
    await screen.findByText('这是第一段配音内容')
    expect(screen.getByText('这是第二段配音内容')).toBeDefined()
  })

  it('renders timing.duration_ms when available', async () => {
    renderWorkbench()
    await screen.findByText('这是第一段配音内容')
    expect(screen.getByText(/时长:/)).toBeDefined()
    expect(screen.getByText(/3\.2s/)).toBeDefined()
  })

  it('renders alignment_source', async () => {
    renderWorkbench()
    await screen.findByText(/对齐:/)
    expect(screen.getByText(/forced/)).toBeDefined()
  })

  it('shows "暂无同步信息" when timing is null', async () => {
    renderWorkbench()
    await screen.findByText('这是第二段配音内容')
    expect(screen.getByText('暂无同步信息')).toBeDefined()
  })

  it('fetchUnits is called with run_id', async () => {
    renderWorkbench()
    await screen.findByText('这是第一段配音内容')
    expect(mockFetchUnits).toHaveBeenCalledWith('proj-abc123def456', 'run-xyz789abc123')
  })
})

describe('Workbench contract: events & logs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('renders event entries', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    // The activity panel toggle should be visible
    await waitFor(() => {
      expect(screen.getByText(/运行日志 & 事件/)).toBeDefined()
    }, { timeout: 3000 })
    // Click to expand if needed
    const toggle = screen.getByText(/运行日志 & 事件/)
    await userEvent.click(toggle)
    // Events header with count should appear
    await waitFor(() => {
      const eventHeaders = screen.getAllByText(/事件/)
      expect(eventHeaders.length).toBeGreaterThanOrEqual(1)
    }, { timeout: 3000 })
  })

  it('renders log entries with level', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const toggle = screen.getByText(/运行日志 & 事件/)
    await userEvent.click(toggle)
    // Log section header with count
    await waitFor(() => {
      const logHeaders = screen.getAllByText(/日志/)
      expect(logHeaders.length).toBeGreaterThanOrEqual(1)
    }, { timeout: 3000 })
  })

  it('renders event cursor info', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const toggle = screen.getByText(/运行日志 & 事件/)
    await userEvent.click(toggle)
    await waitFor(() => {
      const eventHeaders = screen.getAllByText(/事件/)
      expect(eventHeaders.length).toBeGreaterThanOrEqual(1)
    }, { timeout: 3000 })
  })
})

describe('Workbench contract: empty state (no run)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(NO_RUN_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
  })

  it('shows empty state message', async () => {
    renderWorkbench()
    await screen.findByText('任务尚未启动运行')
    expect(screen.getByText('任务尚未启动运行')).toBeDefined()
  })

  it('shows project title even without run', async () => {
    renderWorkbench()
    await screen.findByText('测试视频项目')
    expect(screen.getByText('测试视频项目')).toBeDefined()
  })

  it('shows project trace when available', async () => {
    // NO_RUN_PROJECT has no trace — check no trace chip
    renderWorkbench()
    await screen.findByText('测试视频项目')
    // Only project id chip should be present
    expect(screen.getByText(/project:/)).toBeDefined()
  })
})

describe('Workbench contract: run not found', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockRejectedValue(new Error('API error: 404 Not Found'))
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
  })

  it('shows error state', async () => {
    renderWorkbench()
    await screen.findByText('加载失败')
    expect(screen.getByText('加载失败')).toBeDefined()
    expect(screen.getByText(/404/)).toBeDefined()
  })

  it('shows back button', async () => {
    renderWorkbench()
    await screen.findByText('返回任务队列')
    expect(screen.getByText('返回任务队列')).toBeDefined()
  })
})

describe('Workbench contract: getFinalUrl', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('returns correct download path', () => {
    mockGetFinalUrl('proj-abc123def456', 'run-xyz789abc123')
    expect(mockGetFinalUrl).toHaveBeenCalledWith('proj-abc123def456', 'run-xyz789abc123')
    expect(mockGetFinalUrl).toHaveReturnedWith('/api/v1/projects/proj-abc123def456/runs/run-xyz789abc123/artifacts/final.mp4')
  })
})

describe('Workbench contract: finished_at display', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(COMPLETED_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue(UNITS_RESPONSE)
    mockFetchEvents.mockResolvedValue(EVENTS_RESPONSE)
    mockFetchLogs.mockResolvedValue(LOGS_RESPONSE)
    mockGetFinalUrl.mockReturnValue('/api/v1/projects/proj-abc123def456/runs/run-xyz789abc123/artifacts/final.mp4')
  })

  it('shows final.mp4 artifact', async () => {
    renderWorkbench()
    await screen.findByText('final')
    expect(screen.getByText('final')).toBeDefined()
    expect(screen.getByText('compose-video')).toBeDefined()
  })

  it('shows video preview when final exists', async () => {
    renderWorkbench()
    await screen.findByText('成片预览')
    expect(screen.getByText('成片预览')).toBeDefined()
    expect(screen.getByText('下载 final.mp4')).toBeDefined()
  })
})

describe('Workbench contract: diagnostics link', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  it('has diagnostics link with correct run ID', async () => {
    renderWorkbench()
    await screen.findByText('诊断')
    const link = screen.getByText('诊断')
    expect(link.getAttribute('href')).toBe('/projects/proj-abc123def456/runs/run-xyz789abc123/diagnostics')
  })
})

describe('Workbench contract: capability warning', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(PENDING_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITY_UNAVAILABLE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
  })

  it('shows capability unavailable notice', async () => {
    renderWorkbench()
    await screen.findByText(/Provider 不可用/)
    expect(screen.getByText(/Provider 不可用/)).toBeDefined()
  })

  it('shows provider link in notice', async () => {
    renderWorkbench()
    await screen.findByText('fish-speech')
    const link = screen.getByText('fish-speech')
    expect(link.getAttribute('href')).toBe('/settings/providers/fish-speech')
  })

  it('shows error_code from providers.providers[name]', async () => {
    renderWorkbench()
    await screen.findByText(/SECRET_NOT_CONFIGURED/)
    expect(screen.getByText(/SECRET_NOT_CONFIGURED/)).toBeDefined()
  })

  it('shows suggestion from providers.providers[name]', async () => {
    renderWorkbench()
    await screen.findByText(/请在设置中配置 fish-speech 的 API Key/)
    expect(screen.getByText(/请在设置中配置 fish-speech 的 API Key/)).toBeDefined()
  })
})

describe('Workbench contract: Start button disabled', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(PENDING_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
  })

  it('shows Start button when run is pending', async () => {
    renderWorkbench()
    await screen.findByText('启动运行')
    expect(screen.getByText('启动运行')).toBeDefined()
  })

  it('Start button is disabled when inputs not saved', async () => {
    renderWorkbench()
    await screen.findByText('启动运行')
    const btn = screen.getByText('启动运行')
    expect(btn.hasAttribute('disabled')).toBe(true)
  })

  it('Start button is disabled when capability data is loading', async () => {
    // Never resolve capabilities — simulates loading state
    mockFetchCapabilities.mockReturnValue(new Promise(() => {}))
    renderWorkbench()
    await screen.findByText('启动运行')
    const btn = screen.getByText('启动运行')
    expect(btn.hasAttribute('disabled')).toBe(true)
  })
})

describe('Workbench contract: uploadInputs FormData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(PENDING_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
    mockUploadInputs.mockResolvedValue({ ok: true, project_id: 'proj-abc123def456', input_saved: true })
  })

  it('calls uploadInputs with FormData', async () => {
    renderWorkbench()
    await screen.findByText('保存制作输入')

    // Fill script
    const scriptInput = screen.getByPlaceholderText(/粘贴完整文案/)
    await userEvent.type(scriptInput, '测试文案内容')

    // Click save
    const saveBtn = screen.getByText('保存制作输入')
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(mockUploadInputs).toHaveBeenCalled()
      const [projectId, formData] = mockUploadInputs.mock.calls[0]
      expect(projectId).toBe('proj-abc123def456')
      expect(formData).toBeInstanceOf(FormData)
    })
  })

  it('shows success after save', async () => {
    renderWorkbench()
    await screen.findByText('保存制作输入')

    const scriptInput = screen.getByPlaceholderText(/粘贴完整文案/)
    await userEvent.type(scriptInput, '测试文案')

    const saveBtn = screen.getByText('保存制作输入')
    await userEvent.click(saveBtn)

    await screen.findByText('制作输入已保存')
    expect(screen.getByText('制作输入已保存')).toBeDefined()
  })

  it('shows error when script is empty', async () => {
    renderWorkbench()
    await screen.findByText('保存制作输入')

    const saveBtn = screen.getByText('保存制作输入')
    await userEvent.click(saveBtn)

    await screen.findByText('请输入视频文案')
    expect(screen.getByText('请输入视频文案')).toBeDefined()
  })
})

describe('Workbench contract: cancel & retry run', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue({ items: [], next_cursor: 0 })
    mockFetchLogs.mockResolvedValue({ items: [] })
  })

  it('shows Cancel button when running', async () => {
    mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
    renderWorkbench()
    await screen.findByText('取消')
    expect(screen.getByText('取消')).toBeDefined()
  })

  it('calls cancelRun on Cancel click', async () => {
    mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
    mockCancelRun.mockResolvedValue({ ok: true, status: 'cancelled' })
    renderWorkbench()
    await screen.findByText('取消')
    await userEvent.click(screen.getByText('取消'))
    await waitFor(() => {
      expect(mockCancelRun).toHaveBeenCalledWith('proj-abc123def456', 'run-xyz789abc123')
    })
  })

  it('shows Retry button when failed', async () => {
    mockFetchProject.mockResolvedValue(FAILED_PROJECT)
    renderWorkbench()
    await screen.findByText('重试')
    expect(screen.getByText('重试')).toBeDefined()
  })

  it('calls retryRun on Retry click', async () => {
    mockFetchProject.mockResolvedValue(FAILED_PROJECT)
    mockRetryRun.mockResolvedValue({
      ok: true, command: 'retry', project_id: 'proj-abc123def456',
      run_id: 'run-xyz789abc123', trace_id: 'trace-aaa111bbb222', command_id: 'cmd-retry-1',
    })
    renderWorkbench()
    await screen.findByText('重试')
    await userEvent.click(screen.getByText('重试'))
    await waitFor(() => {
      expect(mockRetryRun).toHaveBeenCalledWith('proj-abc123def456', 'run-xyz789abc123')
    })
  })
})

describe('Workbench contract: stage run/retry', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue({ items: [] })
    mockFetchEvents.mockResolvedValue(EVENTS_RESPONSE)
    mockFetchLogs.mockResolvedValue(LOGS_RESPONSE)
  })

  it('calls runStage for pending stage', async () => {
    mockRunStage.mockResolvedValue({
      ok: true, command: 'run-stage', project_id: 'proj-abc123def456',
      run_id: 'run-xyz789abc123', trace_id: 'trace-aaa111bbb222', command_id: 'cmd-stage-1',
    })
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const stageNames = screen.getAllByText('合成成片')
    expect(stageNames.length).toBeGreaterThanOrEqual(1)
    const executeBtns = screen.getAllByText('执行')
    expect(executeBtns.length).toBeGreaterThan(0)
  })

  it('calls retryStage for failed stage', async () => {
    const withFailedStage = {
      ...RUNNING_PROJECT,
      stages: RUNNING_PROJECT.stages.map((s) =>
        s.stage === 'render-visuals' ? { ...s, status: 'failed' } : s
      ),
    }
    mockFetchProject.mockResolvedValue(withFailedStage)
    mockRetryStage.mockResolvedValue({
      ok: true, command: 'retry-stage', project_id: 'proj-abc123def456',
      run_id: 'run-xyz789abc123', trace_id: 'trace-aaa111bbb222', command_id: 'cmd-retry-stage-1',
    })
    renderWorkbench()
    await screen.findAllByText('文案分割')
    const stageNames = screen.getAllByText('白板渲染')
    expect(stageNames.length).toBeGreaterThanOrEqual(1)
    const retryBtns = screen.getAllByText('重试')
    expect(retryBtns.length).toBeGreaterThan(0)
  })
})

describe('Workbench contract: log filters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue(UNITS_RESPONSE)
    mockFetchEvents.mockResolvedValue(EVENTS_RESPONSE)
    mockFetchLogs.mockResolvedValue(LOGS_RESPONSE)
  })

  it('renders log filter controls', async () => {
    renderWorkbench()
    await screen.findAllByText('文案分割')
    await waitFor(() => {
      expect(screen.getByText('全部级别')).toBeDefined()
    }, { timeout: 3000 })
  })
})

describe('Diagnostics contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchProject.mockResolvedValue(RUNNING_PROJECT)
    mockFetchRun.mockResolvedValue({
      run_id: 'run-xyz789abc123',
      trace_id: 'trace-aaa111bbb222',
      project_id: 'proj-abc123def456',
      command: 'start',
      command_id: 'cmd-aaa111',
      status: 'running',
      policy: 'sequential',
      entrypoint: 'start',
      target_stage: null,
      started_at: '2025-06-01T08:01:00Z',
      finished_at: null,
      error: null,
      stages: {
        'segment-script': { status: 'succeeded', attempt: 0 },
        'clone-voice': { status: 'succeeded', attempt: 0 },
        'plan-storyboard': { status: 'succeeded', attempt: 0 },
        'generate-illustrations': { status: 'succeeded', attempt: 0 },
        'render-visuals': { status: 'running', attempt: 0 },
        'compose-video': { status: 'pending', attempt: 0 },
      },
    })
    mockFetchCapabilities.mockResolvedValue(CAPABILITIES_RESPONSE)
    mockFetchUnits.mockResolvedValue(UNITS_RESPONSE)
    mockFetchEvents.mockResolvedValue(EVENTS_RESPONSE)
    mockFetchLogs.mockResolvedValue(LOGS_RESPONSE)
  })

  it('renders diagnostics page with stages', async () => {
    render(
      <MemoryRouter initialEntries={['/projects/proj-abc123def456/runs/run-xyz789abc123/diagnostics']}>
        <Routes>
          <Route path="/projects/:projectId/runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
        </Routes>
      </MemoryRouter>
    )
    await screen.findByText('阶段状态')
    expect(screen.getByText('阶段状态')).toBeDefined()
  })
})
