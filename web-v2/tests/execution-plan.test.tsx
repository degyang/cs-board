import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TaskWorkbenchPage, STAGE_CONTRACTS } from '../src/pages/TaskWorkbenchPage'
import type { CapabilitiesResponse, InputsReadback, TaskDetail } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/api/client')>()
  return {
    ...actual,
    fetchTask: vi.fn(), fetchCapabilities: vi.fn(), fetchInputs: vi.fn(), fetchUnits: vi.fn(),
    fetchEvents: vi.fn(), fetchLogs: vi.fn(), uploadInputs: vi.fn(), cancelRun: vi.fn(), retryRun: vi.fn(),
  }
})

import { fetchTask, fetchCapabilities, fetchInputs, fetchUnits, fetchEvents, fetchLogs } from '../src/lib/api/client'

const task: TaskDetail = {
  task: {
    task_id: 'task-1', title: '手动阶段工作台测试', pipeline_id: 'mountain-av-v1', engine: 'whiteboard',
    status: 'pending', created_at: '2026-09-02T00:00:00Z', updated_at: '2026-09-02T00:00:00Z',
    active_run_id: 'run-1', revision: 1, schema_version: 1,
  },
  active_run: {
    schema_version: 1, run_id: 'run-1', task_id: 'task-1', trace_id: 'trace-1', entrypoint: 'web',
    command_ids: [], status: 'pending', target_stage: null, started_at: '2026-09-02T00:00:00Z',
    finished_at: null, stages: {}, warnings: [],
  },
  stages: [
    { stage: 'generate-visual-anchors', status: 'waiting-external', attempt: 1 },
    { stage: 'clone-voice', status: 'running', attempt: 2 },
    { stage: 'plan-storyboard', status: 'succeeded', attempt: 1 },
    { stage: 'generate-illustrations', status: 'failed', attempt: 1 },
    { stage: 'render-visuals', status: 'skipped', attempt: 0 },
    { stage: 'compose-video', status: 'stale', attempt: 0 },
    { stage: 'future-stage', status: 'unknown', attempt: 0 },
  ],
  warnings: [], artifacts: [], trace: null,
}

const capabilities: CapabilitiesResponse = {
  items: [], providers: { all_available: true, unavailable: [], providers: {} },
}

const inputs: InputsReadback = {
  task_id: 'task-1', saved: true,
  inputs: { script: '测试输入', style: '', include_subtitles: false, pen_text: '', stroke_detail: '' },
  reference_audio: { uploaded: true, filename: 'ref.wav', content_type: 'audio/wav', size_bytes: 4 },
  rules: null, script_preparation: null, visual_anchor_enabled: true,
  execution_plan: { mode: 'auto', manual_stages: [] },
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tasks/task-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TaskWorkbenchPage manual six-stage baseline', () => {
  beforeEach(() => {
    vi.mocked(fetchTask).mockResolvedValue(task)
    vi.mocked(fetchCapabilities).mockResolvedValue(capabilities)
    vi.mocked(fetchInputs).mockResolvedValue(inputs)
    vi.mocked(fetchUnits).mockResolvedValue({ items: [] })
    vi.mocked(fetchEvents).mockResolvedValue({ items: [], next_cursor: 0 })
    vi.mocked(fetchLogs).mockResolvedValue({ items: [] })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the canonical six cards in fixed order with complete contract fields', async () => {
    renderPage()
    await screen.findByText('手动阶段工作台测试')
    expect(screen.getAllByRole('article')).toHaveLength(7)
    expect(STAGE_CONTRACTS.map((contract) => contract.id)).toEqual([
      'generate-visual-anchors', 'clone-voice', 'plan-storyboard',
      'generate-illustrations', 'render-visuals', 'compose-video',
    ])
    for (const label of ['入口条件', '持久化输入', '预期输出', '出口条件', '人工 Gate']) {
      expect(screen.getAllByText(label, { exact: true }).length).toBeGreaterThanOrEqual(6)
    }
    expect(screen.getAllByText('后端 Gate 契约尚未提供', { exact: false })).toHaveLength(6)
    expect(screen.getByText('未知阶段')).toBeInTheDocument()
    expect(screen.getByText('waiting-external')).toBeInTheDocument()
  })

  it('does not expose automatic plan controls or Gate mutation actions', async () => {
    renderPage()
    await screen.findByText('手动阶段工作台测试')
    expect(screen.queryByRole('radio')).toBeNull()
    expect(screen.queryByRole('button', { name: /开始制作|执行|批准|拒绝|重做|重试/ })).toBeNull()
  })

  it('keeps six cards safe when there is no active run', async () => {
    vi.mocked(fetchTask).mockResolvedValue({ ...task, active_run: null, stages: [] })
    renderPage()
    await waitFor(() => expect(screen.getAllByRole('article')).toHaveLength(6))
    expect(screen.getByText(/没有 active Run/)).toBeInTheDocument()
  })
})
