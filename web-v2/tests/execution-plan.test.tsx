import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
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
    expect(screen.getAllByText('后端人工 Gate 尚未就绪，当前操作不可用', { exact: false })).toHaveLength(6)
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

  it('clears the previous task identity before the next task request settles', async () => {
    const taskA = { ...task, task: { ...task.task, task_id: 'task-a', title: '任务 A' } }
    const taskB = { ...task, task: { ...task.task, task_id: 'task-b', title: '任务 B' }, active_run: null, stages: [], artifacts: [] }
    const taskBRequest = deferred<TaskDetail>()
    vi.mocked(fetchTask).mockImplementation((id) => id === 'task-a' ? Promise.resolve(taskA) : taskBRequest.promise)
    vi.mocked(fetchInputs).mockResolvedValue({ ...inputs, task_id: 'task-a' })
    render(
      <MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText('任务 A')
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    expect(screen.queryByText('任务 A')).toBeNull()
    expect(screen.queryByText('任务 B')).toBeNull()
    taskBRequest.resolve(taskB)
    await screen.findByText('任务 B')
    expect(screen.queryByText('任务 A')).toBeNull()
  })

  it('keeps every A marker out of the B page while B is pending and after it completes', async () => {
    const taskA = {
      ...task,
      task: { ...task.task, task_id: 'task-a', title: '任务 A 完整标记' },
      active_run: { ...task.active_run!, run_id: 'run-a', trace_id: 'trace-a' },
      artifacts: [{ artifact_key: 'artifact-a', relative_path: 'a.json', sha256: 'a', size_bytes: 1, producer_stage: 'plan-storyboard', status: 'succeeded' }],
    }
    const taskB = {
      ...task,
      task: { ...task.task, task_id: 'task-b', title: '任务 B 完整标记' },
      active_run: { ...task.active_run!, run_id: 'run-b', trace_id: 'trace-b' },
      artifacts: [{ artifact_key: 'artifact-b', relative_path: 'b.json', sha256: 'b', size_bytes: 1, producer_stage: 'plan-storyboard', status: 'succeeded' }],
    }
    const taskBRequest = deferred<TaskDetail>()
    vi.mocked(fetchTask).mockImplementation((id) => id === 'task-a' ? Promise.resolve(taskA) : taskBRequest.promise)
    vi.mocked(fetchInputs).mockImplementation((id) => Promise.resolve({ ...inputs, task_id: id, inputs: { ...inputs.inputs!, script: id === 'task-a' ? '输入 A' : '输入 B' } }))
    vi.mocked(fetchUnits).mockImplementation((id) => Promise.resolve({ items: [{ unit_id: id === 'task-a' ? 'unit-a' : 'unit-b', order: 0, text: id === 'task-a' ? '单元 A' : '单元 B' }] }))
    vi.mocked(fetchEvents).mockImplementation((id) => Promise.resolve({ items: [{ event_type: id === 'task-a' ? '事件 A' : '事件 B', timestamp: '2026-09-02T00:00:00Z', sequence: 1 }], next_cursor: 1 }))
    vi.mocked(fetchLogs).mockImplementation((id) => Promise.resolve({ items: [{ level: 'INFO', message: id === 'task-a' ? '日志 A' : '日志 B', timestamp: '2026-09-02T00:00:00Z' }] }))
    render(
      <MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText('任务 A 完整标记')
    await screen.findByText('artifact-a')
    await screen.findByText('单元 A')
    await screen.findByText('事件 A')
    await screen.findByText('日志 A')
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    expect(screen.queryByText(/任务 A 完整标记|artifact-a|单元 A|事件 A|日志 A|输入 A/)).toBeNull()
    taskBRequest.resolve(taskB)
    await screen.findByText('任务 B 完整标记')
    await screen.findByText('artifact-b')
    await screen.findByText('单元 B')
    await screen.findByText('事件 B')
    await screen.findByText('日志 B')
    expect(screen.queryByText(/任务 A 完整标记|artifact-a|单元 A|事件 A|日志 A|输入 A/)).toBeNull()
  })

  it('lets B win when A resources are still pending and A later rejects', async () => {
    const taskA = { ...task, task: { ...task.task, task_id: 'task-a', title: '任务 A 延迟' }, active_run: { ...task.active_run!, run_id: 'run-a' } }
    const taskB = { ...task, task: { ...task.task, task_id: 'task-b', title: '任务 B 先完成' }, active_run: null, stages: [], artifacts: [] }
    const aInputs = deferred<InputsReadback>()
    const aUnits = deferred<{ items: Array<Record<string, unknown>> }>()
    const aEvents = deferred<{ items: Record<string, unknown>[]; next_cursor: number }>()
    const aLogs = deferred<{ items: Record<string, unknown>[] }>()
    const bRequest = deferred<TaskDetail>()
    vi.mocked(fetchTask).mockImplementation((id) => id === 'task-a' ? Promise.resolve(taskA) : bRequest.promise)
    vi.mocked(fetchInputs).mockImplementation((id) => id === 'task-a' ? aInputs.promise : Promise.resolve({ ...inputs, task_id: 'task-b' }))
    vi.mocked(fetchUnits).mockImplementation((id) => id === 'task-a' ? aUnits.promise : Promise.resolve({ items: [] }))
    vi.mocked(fetchEvents).mockImplementation((id) => id === 'task-a' ? aEvents.promise : Promise.resolve({ items: [], next_cursor: 0 }))
    vi.mocked(fetchLogs).mockImplementation((id) => id === 'task-a' ? aLogs.promise : Promise.resolve({ items: [] }))
    render(
      <MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText('任务 A 延迟')
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    bRequest.resolve(taskB)
    await screen.findByText('任务 B 先完成')
    aInputs.reject(new Error('late A inputs'))
    aUnits.reject(new Error('late A units'))
    aEvents.reject(new Error('late A events'))
    aLogs.reject(new Error('late A logs'))
    await Promise.resolve()
    expect(screen.getByText('任务 B 先完成')).toBeInTheDocument()
    expect(screen.queryByText(/late A/)).toBeNull()
  })

  it('uses an unavailable status for missing stages instead of fabricating pending or attempt zero', async () => {
    vi.mocked(fetchTask).mockResolvedValue({ ...task, active_run: { ...task.active_run!, run_id: 'run-empty' }, stages: [] })
    renderPage()
    await screen.findByText('后端尚未报告 Stage 状态。')
    expect(screen.getAllByText('尚未报告')).toHaveLength(6)
    expect(screen.queryByText('attempt 0')).toBeNull()
  })

  it('preserves every backend stage status, including waiting-review and cancellation', async () => {
    vi.mocked(fetchTask).mockResolvedValue({
      ...task,
      stages: [
        { stage: 'generate-visual-anchors', status: 'pending', attempt: 0 },
        { stage: 'clone-voice', status: 'running', attempt: 1 },
        { stage: 'plan-storyboard', status: 'waiting-external', attempt: 1 },
        { stage: 'generate-illustrations', status: 'waiting-review', attempt: 1 },
        { stage: 'render-visuals', status: 'succeeded', attempt: 1 },
        { stage: 'compose-video', status: 'failed', attempt: 2 },
        { stage: 'skipped-stage', status: 'skipped', attempt: 0 },
        { stage: 'stale-stage', status: 'stale', attempt: 0 },
        { stage: 'cancelled-stage', status: 'cancelled', attempt: 0 },
      ],
    })
    renderPage()
    await screen.findByText('waiting-review')
    for (const status of ['待执行', '运行中', 'waiting-external', 'waiting-review', '已成功', '失败', '已跳过', '已过期', '已取消']) {
      expect(screen.getAllByText(status, { exact: true }).length).toBeGreaterThanOrEqual(1)
    }
  })

  it('does not update state when task resources resolve or reject after unmount', async () => {
    const taskRequest = deferred<TaskDetail>()
    const inputRequest = deferred<InputsReadback>()
    vi.mocked(fetchTask).mockReturnValue(taskRequest.promise)
    vi.mocked(fetchInputs).mockReturnValue(inputRequest.promise)
    vi.mocked(fetchCapabilities).mockReturnValue(new Promise(() => {}))
    vi.mocked(fetchUnits).mockReturnValue(new Promise(() => {}))
    vi.mocked(fetchEvents).mockReturnValue(new Promise(() => {}))
    vi.mocked(fetchLogs).mockReturnValue(new Promise(() => {}))
    const view = renderPage()
    view.unmount()
    taskRequest.resolve(task)
    inputRequest.reject(new Error('late input failure'))
    await Promise.resolve()
    expect(screen.queryByText('手动阶段工作台测试')).toBeNull()
  })
})
