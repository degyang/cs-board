import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TaskWorkbenchPage } from '../src/pages/TaskWorkbenchPage'
import { MountainApiError } from '../src/lib/api/client'
import type { CapabilitiesResponse, InputsReadback, TaskDetail } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/api/client')>()
  return {
    ...actual,
    fetchTask: vi.fn(), fetchCapabilities: vi.fn(), fetchInputs: vi.fn(), fetchUnits: vi.fn(),
    fetchEvents: vi.fn(), fetchLogs: vi.fn(), uploadInputs: vi.fn(), startRun: vi.fn(),
    cancelRun: vi.fn(), retryRun: vi.fn(), runStage: vi.fn(), retryStage: vi.fn(),
  }
})

import {
  fetchTask, fetchCapabilities, fetchInputs, fetchUnits, fetchEvents, fetchLogs,
  uploadInputs, startRun, cancelRun, retryRun, runStage, retryStage,
} from '../src/lib/api/client'

const task: TaskDetail = {
  task: {
    task_id: 'task-1', title: '执行计划测试', pipeline_id: 'mountain-av-v1', engine: 'whiteboard',
    status: 'pending', created_at: '2026-09-02T00:00:00Z', updated_at: '2026-09-02T00:00:00Z',
    active_run_id: 'run-1', revision: 1, schema_version: 1,
  },
  active_run: {
    schema_version: 1, run_id: 'run-1', task_id: 'task-1', trace_id: 'trace-1', entrypoint: 'web',
    command_ids: [], status: 'pending', target_stage: null, started_at: '2026-09-02T00:00:00Z',
    finished_at: null, stages: {}, warnings: [],
  },
  stages: [], warnings: [], artifacts: [], trace: null,
}

const capabilities: CapabilitiesResponse = {
  items: [], providers: { all_available: true, unavailable: [], providers: {} },
}

const inputs: InputsReadback = {
  task_id: 'task-1', saved: true,
  inputs: { script: '一段已经保存的测试文案。', style: '', include_subtitles: false, pen_text: '', stroke_detail: '' },
  reference_audio: { uploaded: true, filename: 'ref.wav', content_type: 'audio/wav', size_bytes: 4 },
  rules: null, script_preparation: null, visual_anchor_enabled: true,
  execution_plan: { mode: 'auto', manual_stages: [] },
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tasks/task-1']}>
      <Routes><Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} /></Routes>
    </MemoryRouter>,
  )
}

describe('TaskWorkbenchPage execution plan', () => {
  beforeEach(() => {
    vi.mocked(fetchTask).mockResolvedValue(task)
    vi.mocked(fetchCapabilities).mockResolvedValue(capabilities)
    vi.mocked(fetchInputs).mockResolvedValue(inputs)
    vi.mocked(fetchUnits).mockResolvedValue({ items: [] })
    vi.mocked(fetchEvents).mockResolvedValue({ items: [], next_cursor: 0 })
    vi.mocked(fetchLogs).mockResolvedValue({ items: [] })
    vi.mocked(uploadInputs).mockResolvedValue({
      ok: true, task_id: 'task-1', input_saved: true,
      execution_plan: { mode: 'selective', manual_stages: ['generate-illustrations', 'compose-video'] },
    })
    vi.mocked(startRun).mockResolvedValue({ ok: true, command: 'start', task_id: 'task-1', run_id: 'run-1', trace_id: 'trace-1', command_id: 'command-1' })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('serializes selected stages in canonical order and displays saved plan readback', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByDisplayValue('一段已经保存的测试文案。')

    await user.click(screen.getByRole('radio', { name: '选择手动阶段' }))
    await user.click(screen.getByRole('checkbox', { name: '合成成片' }))
    await user.click(screen.getByRole('checkbox', { name: '生成插画' }))
    await user.click(screen.getByRole('button', { name: '保存制作输入' }))

    await waitFor(() => expect(uploadInputs).toHaveBeenCalledTimes(1))
    const form = vi.mocked(uploadInputs).mock.calls[0][1]
    expect(form.get('execution_mode')).toBe('selective')
    expect(form.get('manual_stages')).toBe('["generate-illustrations","compose-video"]')
    expect(await screen.findByText('已保存执行计划：手动阶段：生成插画、合成成片')).toBeInTheDocument()
  })

  it('shows only the documented non-retryable plan suggestion for a 409 start response', async () => {
    vi.mocked(startRun).mockRejectedValue(new MountainApiError(409, {
      code: 'EXECUTION_PLAN_NOT_READY', message: 'ignored', retryable: false,
      details: { suggestion: '手动阶段编排尚未启用', internal_path: '/private/path' },
    }, 'ignored'))
    renderPage()
    await screen.findByDisplayValue('一段已经保存的测试文案。')
    fireEvent.click(screen.getByRole('button', { name: '开始制作' }))

    expect(await screen.findByText('当前执行计划暂不能启动。手动阶段编排尚未启用')).toBeInTheDocument()
    expect(screen.queryByText('/private/path')).not.toBeInTheDocument()
  })
})
