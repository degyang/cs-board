import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { TaskWorkbenchPage } from '../src/pages/TaskWorkbenchPage'
import type { CapabilitiesResponse, InputsReadback, TaskDetail } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', () => ({
  fetchTask: vi.fn(), fetchCapabilities: vi.fn(), fetchInputs: vi.fn(), fetchUnits: vi.fn(),
  fetchEvents: vi.fn(), fetchLogs: vi.fn(), fetchCurrentAssets: vi.fn(),
  cancelRun: vi.fn(), uploadInputs: vi.fn(), getFinalUrl: vi.fn(), getAssetMediaUrl: vi.fn((url: string) => url),
}))

import { fetchCapabilities, fetchCurrentAssets, fetchEvents, fetchInputs, fetchLogs, fetchTask, fetchUnits } from '../src/lib/api/client'

const capabilities: CapabilitiesResponse = { items: [], providers: { all_available: true, unavailable: [], providers: {} } }
const inputs: InputsReadback = {
  task_id: 'task-a', saved: false, inputs: null,
  reference_audio: { uploaded: false, filename: null, content_type: null, size_bytes: null },
  rules: null, script_preparation: null, visual_anchor_enabled: true, execution_plan: { mode: 'manual' },
}

function taskDetail(taskId = 'task-a', runId = 'run-a', artifacts: TaskDetail['artifacts'] = []): TaskDetail {
  return {
    task: { task_id: taskId, title: `任务 ${taskId}`, pipeline_id: 'mountain-av-v1', engine: 'whiteboard', status: 'pending', created_at: '2026-09-06T00:00:00Z', updated_at: '2026-09-06T00:00:00Z', active_run_id: runId, revision: 1, schema_version: 1 },
    active_run: { schema_version: 1, run_id: runId, task_id: taskId, trace_id: `trace-${taskId}`, entrypoint: 'web', command_ids: [], status: 'pending', target_stage: null, started_at: '2026-09-06T00:00:00Z', finished_at: null, stages: {}, warnings: [] },
    stages: [], warnings: [], artifacts, trace: null,
  }
}

function renderWorkbench(path = '/tasks/task-a') {
  return render(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} /></Routes></MemoryRouter>)
}

function NavigateTo({ taskId }: { taskId: string }) {
  const navigate = useNavigate()
  return <button onClick={() => navigate(`/tasks/${taskId}`)}>切换任务</button>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('TaskWorkbenchPage current asset discovery', () => {
  beforeEach(() => {
    vi.mocked(fetchTask).mockResolvedValue(taskDetail())
    vi.mocked(fetchCapabilities).mockResolvedValue(capabilities)
    vi.mocked(fetchInputs).mockResolvedValue(inputs)
    vi.mocked(fetchUnits).mockResolvedValue({ items: [] })
    vi.mocked(fetchEvents).mockResolvedValue({ items: [], next_cursor: 0 })
    vi.mocked(fetchLogs).mockResolvedValue({ items: [] })
    vi.mocked(fetchCurrentAssets).mockResolvedValue({ items: [] })
  })

  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('uses the task/run identity in order and renders image, audio, and video cards', async () => {
    vi.mocked(fetchCurrentAssets).mockResolvedValue({ items: [
      { asset_id: 'image-1', asset_kind: 'image', media_url: '/media/image-1', generation_record: {} },
      { asset_id: 'audio-1', asset_kind: 'audio', media_url: '/media/audio-1', generation_record: {} },
      { asset_id: 'video-1', asset_kind: 'video', media_url: '/media/video-1', generation_record: {} },
    ] })
    renderWorkbench()
    await screen.findByText('任务 task-a')
    await waitFor(() => expect(fetchCurrentAssets).toHaveBeenCalledWith('task-a', 'run-a'))
    expect(screen.getByRole('button', { name: '查看图片预览：image-1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '试听音频：audio-1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '播放视频：video-1' })).toBeInTheDocument()
  })

  it('keeps current assets visible when legacy artifacts are empty', async () => {
    vi.mocked(fetchCurrentAssets).mockResolvedValue({ items: [{ asset_id: 'current-only', asset_kind: 'image', media_url: '/media/current', generation_record: {} }] })
    renderWorkbench()
    await screen.findByText('暂无产物')
    expect(await screen.findByRole('button', { name: '查看图片预览：current-only' })).toBeInTheDocument()
  })

  it('has distinct loading, empty, 4xx, and network-failure states', async () => {
    const pending = deferred<{ items: [] }>()
    vi.mocked(fetchCurrentAssets).mockReturnValueOnce(pending.promise)
    const view = renderWorkbench()
    await screen.findByRole('status', { name: '' })
    expect(screen.getByText('正在读取当前资产…')).toBeInTheDocument()
    pending.resolve({ items: [] })
    expect(await screen.findByText('当前 Run 暂无可预览资产。')).toBeInTheDocument()
    view.unmount()

    vi.mocked(fetchCurrentAssets).mockRejectedValueOnce(new Error('API error: 404'))
    renderWorkbench()
    expect(await screen.findByRole('alert')).toHaveTextContent('当前资产暂不可读取')
    cleanup()

    vi.mocked(fetchCurrentAssets).mockRejectedValueOnce(new TypeError('network failed'))
    renderWorkbench()
    expect(await screen.findByRole('alert')).toHaveTextContent('当前资产暂不可读取')
  })

  it('does not let a late asset response from task A overwrite task B', async () => {
    const assetsA = deferred<{ items: Array<{ asset_id: string; asset_kind: 'image'; media_url: string; generation_record: Record<string, unknown> }> }>()
    vi.mocked(fetchTask).mockImplementation((taskId) => Promise.resolve(taskDetail(taskId, taskId === 'task-a' ? 'run-a' : 'run-b')))
    vi.mocked(fetchCurrentAssets).mockImplementation((taskId) => taskId === 'task-a' ? assetsA.promise : Promise.resolve({ items: [{ asset_id: 'asset-b', asset_kind: 'image', media_url: '/media/b', generation_record: {} }] }))
    render(<MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} /></Routes></MemoryRouter>)
    await screen.findByText('任务 task-a')
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    expect(await screen.findByText('任务 task-b')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: '查看图片预览：asset-b' })).toBeInTheDocument()
    await act(async () => { assetsA.resolve({ items: [{ asset_id: 'asset-a', asset_kind: 'image', media_url: '/media/a', generation_record: {} }] }) })
    expect(screen.queryByRole('button', { name: '查看图片预览：asset-a' })).toBeNull()
  })
})
