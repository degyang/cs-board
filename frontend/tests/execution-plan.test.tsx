import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor, within, act } from '@testing-library/react'
import { StrictMode } from 'react'
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

async function flushAsync() {
  await act(async () => {
    for (let i = 0; i < 8; i += 1) await Promise.resolve()
  })
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

  it.each(['resolve', 'reject'] as const)('keeps B visible when pending A later %s', async (outcome) => {
    const taskA = { ...task, task: { ...task.task, task_id: 'task-a', title: '任务 A pending' } }
    const taskB = { ...task, task: { ...task.task, task_id: 'task-b', title: '任务 B 完成' }, active_run: null, stages: [], artifacts: [] }
    const aRequest = deferred<TaskDetail>()
    const bRequest = deferred<TaskDetail>()
    vi.mocked(fetchTask).mockImplementation((id) => id === 'task-a' ? aRequest.promise : bRequest.promise)
    render(
      <MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} />
        </Routes>
      </MemoryRouter>,
    )
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    bRequest.resolve(taskB)
    await screen.findByText('任务 B 完成')
    if (outcome === 'resolve') aRequest.resolve(taskA)
    else aRequest.reject(new Error('late A task failure'))
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    expect(screen.getByText('任务 B 完成')).toBeInTheDocument()
    expect(screen.queryByText(/任务 A pending|late A task failure/)).toBeNull()
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

  it('ignores every late A resource success after B has completed', async () => {
    const taskA = { ...task, task: { ...task.task, task_id: 'task-a', title: '任务 A 资源延迟' }, active_run: { ...task.active_run!, run_id: 'run-a' } }
    const taskB = { ...task, task: { ...task.task, task_id: 'task-b', title: '任务 B 资源完成' }, active_run: { ...task.active_run!, run_id: 'run-b' }, artifacts: [{ artifact_key: 'artifact-b', relative_path: 'b', sha256: 'b', size_bytes: 1, producer_stage: 'compose-video', status: 'succeeded' }] }
    const aInputs = deferred<InputsReadback>()
    const aUnits = deferred<{ items: Array<Record<string, unknown>> }>()
    const aEvents = deferred<{ items: Record<string, unknown>[]; next_cursor: number }>()
    const aLogs = deferred<{ items: Record<string, unknown>[] }>()
    const bRequest = deferred<TaskDetail>()
    vi.mocked(fetchTask).mockImplementation((id) => id === 'task-a' ? Promise.resolve(taskA) : bRequest.promise)
    vi.mocked(fetchInputs).mockImplementation((id) => id === 'task-a' ? aInputs.promise : Promise.resolve({ ...inputs, task_id: 'task-b', inputs: { ...inputs.inputs!, script: '输入 B 保持' } }))
    vi.mocked(fetchUnits).mockImplementation((id) => id === 'task-a' ? aUnits.promise : Promise.resolve({ items: [{ unit_id: 'unit-b', order: 0, text: '单元 B 保持' }] }))
    vi.mocked(fetchEvents).mockImplementation((id) => id === 'task-a' ? aEvents.promise : Promise.resolve({ items: [{ event_type: '事件 B 保持', timestamp: '2026-09-02T00:00:00Z', sequence: 1 }], next_cursor: 1 }))
    vi.mocked(fetchLogs).mockImplementation((id) => id === 'task-a' ? aLogs.promise : Promise.resolve({ items: [{ level: 'INFO', message: '日志 B 保持', timestamp: '2026-09-02T00:00:00Z' }] }))
    render(
      <MemoryRouter initialEntries={['/tasks/task-a']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Route path="/tasks/:taskId" element={<><NavigateTo taskId="task-b" /><TaskWorkbenchPage /></>} />
        </Routes>
      </MemoryRouter>,
    )
    await screen.findByText('任务 A 资源延迟')
    await waitFor(() => {
      expect(fetchInputs).toHaveBeenCalledWith('task-a')
      expect(fetchUnits).toHaveBeenCalledWith('task-a', 'run-a')
      expect(fetchEvents).toHaveBeenCalledWith('task-a', 'run-a', 0)
      expect(fetchLogs).toHaveBeenCalledWith('task-a', 'run-a', undefined)
    })
    await userEvent.setup().click(screen.getByRole('button', { name: '切换任务' }))
    bRequest.resolve(taskB)
    await screen.findByText('任务 B 资源完成')
    await screen.findByText('artifact-b')
    await screen.findByText('单元 B 保持')
    await screen.findByText('事件 B 保持')
    await screen.findByText('日志 B 保持')
    aInputs.resolve({ ...inputs, task_id: 'task-a', inputs: { ...inputs.inputs!, script: '输入 A 迟到' } })
    aUnits.resolve({ items: [{ unit_id: 'unit-a', order: 0, text: '单元 A 迟到' }] })
    aEvents.resolve({ items: [{ event_type: '事件 A 迟到', timestamp: '2026-09-02T00:00:00Z', sequence: 1 }], next_cursor: 1 })
    aLogs.resolve({ items: [{ level: 'INFO', message: '日志 A 迟到', timestamp: '2026-09-02T00:00:00Z' }] })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    expect(screen.getByText('任务 B 资源完成')).toBeInTheDocument()
    expect(screen.queryByText(/输入 A 迟到|单元 A 迟到|事件 A 迟到|日志 A 迟到/)).toBeNull()
  })

  it('resets cursor, dedup, units, logs and artifacts for run-a to run-b with the same event sequence', async () => {
    vi.useFakeTimers()
    try {
      const runA = { ...task, task: { ...task.task, title: '同任务 run-a' }, active_run: { ...task.active_run!, run_id: 'run-a', trace_id: 'trace-a', status: 'running' as const }, artifacts: [{ artifact_key: 'artifact-a', relative_path: 'a', sha256: 'a', size_bytes: 1, producer_stage: 'compose-video', status: 'succeeded' }] }
      const runB = { ...task, task: { ...task.task, title: '同任务 run-b' }, active_run: { ...task.active_run!, run_id: 'run-b', trace_id: 'trace-b', status: 'running' as const }, artifacts: [{ artifact_key: 'artifact-b', relative_path: 'b', sha256: 'b', size_bytes: 1, producer_stage: 'compose-video', status: 'succeeded' }] }
      vi.mocked(fetchTask).mockResolvedValueOnce(runA).mockResolvedValue(runB)
      vi.mocked(fetchUnits).mockImplementation((_taskId, runId) => Promise.resolve({ items: [{ unit_id: runId, order: 0, text: `单元 ${runId}` }] }))
      vi.mocked(fetchEvents).mockImplementation((_taskId, runId) => Promise.resolve({ items: [{ event_type: `事件 ${runId}`, timestamp: '2026-09-02T00:00:00Z', sequence: 1 }], next_cursor: 1 }))
      vi.mocked(fetchLogs).mockImplementation((_taskId, runId) => Promise.resolve({ items: [{ level: 'INFO', message: `日志 ${runId}`, timestamp: '2026-09-02T00:00:00Z' }] }))
      renderPage()
      await flushAsync()
      expect(screen.getByText('同任务 run-a')).toBeInTheDocument()
      expect(screen.getByText('artifact-a')).toBeInTheDocument()
      expect(screen.getByText('单元 run-a')).toBeInTheDocument()
      expect(screen.getByText('事件 run-a')).toBeInTheDocument()
      expect(screen.getByText('日志 run-a')).toBeInTheDocument()
      await act(async () => { await vi.advanceTimersByTimeAsync(10_000) })
      await flushAsync()
      expect(screen.getByText('artifact-b')).toBeInTheDocument()
      expect(screen.getByText('单元 run-b')).toBeInTheDocument()
      expect(screen.getByText('事件 run-b')).toBeInTheDocument()
      expect(screen.getByText('日志 run-b')).toBeInTheDocument()
      expect(screen.queryByText(/artifact-a|单元 run-a|事件 run-a|日志 run-a/)).toBeNull()
      expect(fetchEvents).toHaveBeenCalledWith('task-1', 'run-b', 0)
    } finally {
      vi.useRealTimers()
    }
  })

  it('uses an unavailable status for missing stages instead of fabricating pending or attempt zero', async () => {
    vi.mocked(fetchTask).mockResolvedValue({ ...task, active_run: { ...task.active_run!, run_id: 'run-empty' }, stages: [] })
    renderPage()
    await screen.findByText('后端尚未报告 Stage 状态。')
    expect(screen.getAllByText('尚未报告')).toHaveLength(6)
    expect(screen.queryByText('attempt 0')).toBeNull()
  })

  it.each([
    ['pending', '待执行', 0], ['running', '运行中', 0], ['waiting-external', 'waiting-external', 0],
    ['waiting-review', 'waiting-review', 0], ['succeeded', '已成功', 1], ['failed', '失败', 0],
    ['skipped', '已跳过', 0], ['stale', '已过期', 0], ['cancelled', '已取消', 0],
  ] as const)('renders canonical %s status with attempt and completed count', async (status, label, completed) => {
    vi.mocked(fetchTask).mockResolvedValue({
      ...task,
      stages: [
        { stage: 'generate-visual-anchors', status, attempt: 7 },
        { stage: 'clone-voice', status: 'pending', attempt: 1 },
        { stage: 'plan-storyboard', status: 'pending', attempt: 1 },
        { stage: 'generate-illustrations', status: 'pending', attempt: 1 },
        { stage: 'render-visuals', status: 'pending', attempt: 1 },
        { stage: 'compose-video', status: 'pending', attempt: 1 },
        { stage: 'skipped-stage', status: 'skipped', attempt: 0 },
        { stage: 'stale-stage', status: 'stale', attempt: 0 },
        { stage: 'cancelled-stage', status: 'cancelled', attempt: 0 },
      ],
    })
    renderPage()
    await screen.findByText('手动阶段工作台测试')
    const firstCard = screen.getAllByRole('article')[0]
    expect(within(firstCard).getByText(label, { exact: true })).toBeInTheDocument()
    expect(within(firstCard).getByText('attempt 7', { exact: true })).toBeInTheDocument()
    expect(screen.getByText(`${completed}/6`, { exact: true })).toBeInTheDocument()
  })

  it('keeps the five resource requests safe after unmount for independent late resolve/reject', async () => {
    vi.useFakeTimers()
    const inputRequest = deferred<InputsReadback>()
    const unitsRequest = deferred<{ items: Array<Record<string, unknown>> }>()
    const eventsRequest = deferred<{ items: Record<string, unknown>[]; next_cursor: number }>()
    const logsRequest = deferred<{ items: Record<string, unknown>[] }>()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const unhandled = vi.fn()
    window.addEventListener('unhandledrejection', unhandled)
    try {
      vi.mocked(fetchTask).mockResolvedValue({ ...task, active_run: { ...task.active_run!, status: 'running' as const } })
      vi.mocked(fetchInputs).mockReturnValue(inputRequest.promise)
      vi.mocked(fetchUnits).mockReturnValue(unitsRequest.promise)
      vi.mocked(fetchEvents).mockReturnValue(eventsRequest.promise)
      vi.mocked(fetchLogs).mockReturnValue(logsRequest.promise)
      const view = renderPage()
      await flushAsync()
      expect(screen.getByText('手动阶段工作台测试')).toBeInTheDocument()
      expect(fetchInputs).toHaveBeenCalledWith('task-1')
      expect(fetchUnits).toHaveBeenCalledWith('task-1', 'run-1')
      expect(fetchEvents).toHaveBeenCalledWith('task-1', 'run-1', 0)
      expect(fetchLogs).toHaveBeenCalledWith('task-1', 'run-1', undefined)
      const timersBeforeUnmount = vi.getTimerCount()
      view.unmount()
      inputRequest.resolve(inputs)
      unitsRequest.reject(new Error('late units failure'))
      eventsRequest.resolve({ items: [], next_cursor: 0 })
      logsRequest.reject(new Error('late logs failure'))
      await act(async () => { await Promise.resolve(); await Promise.resolve(); vi.runOnlyPendingTimers() })
      expect(consoleError).not.toHaveBeenCalled()
      expect(unhandled).not.toHaveBeenCalled()
      expect(vi.getTimerCount()).toBe(0)
      expect(timersBeforeUnmount).toBeGreaterThanOrEqual(0)
      expect(screen.queryByText('手动阶段工作台测试')).toBeNull()
    } finally {
      window.removeEventListener('unhandledrejection', unhandled)
      consoleError.mockRestore()
      vi.useRealTimers()
    }
  })

  it('stops task and resource polling after terminal response, including StrictMode repeat render', async () => {
    vi.useFakeTimers()
    try {
      const running = { ...task, active_run: { ...task.active_run!, status: 'running' as const } }
      const terminal = { ...task, active_run: { ...task.active_run!, status: 'succeeded' as const } }
      vi.mocked(fetchTask).mockResolvedValueOnce(running).mockResolvedValueOnce(terminal)
      const view = render(
        <StrictMode><MemoryRouter initialEntries={['/tasks/task-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Route path="/tasks/:taskId" element={<TaskWorkbenchPage />} /></Routes></MemoryRouter></StrictMode>,
      )
      await flushAsync()
      expect(screen.getByText('手动阶段工作台测试')).toBeInTheDocument()
      await act(async () => { await vi.advanceTimersByTimeAsync(10_000) })
      await flushAsync()
      expect(screen.getAllByText('已成功').length).toBeGreaterThanOrEqual(1)
      const countsAtTerminal = [fetchTask, fetchUnits, fetchEvents, fetchLogs].map((fn) => vi.mocked(fn).mock.calls.length)
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
      expect([fetchTask, fetchUnits, fetchEvents, fetchLogs].map((fn) => vi.mocked(fn).mock.calls.length)).toEqual(countsAtTerminal)
      view.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not reschedule a resource request that completes after terminal polling stops', async () => {
    vi.useFakeTimers()
    const unitsRequest = deferred<{ items: Array<Record<string, unknown>> }>()
    const eventsRequest = deferred<{ items: Record<string, unknown>[]; next_cursor: number }>()
    const logsRequest = deferred<{ items: Record<string, unknown>[] }>()
    try {
      const running = { ...task, active_run: { ...task.active_run!, status: 'running' as const } }
      const terminal = { ...task, active_run: { ...task.active_run!, status: 'succeeded' as const } }
      vi.mocked(fetchTask).mockResolvedValueOnce(running).mockResolvedValueOnce(terminal)
      vi.mocked(fetchUnits).mockReturnValue(unitsRequest.promise)
      vi.mocked(fetchEvents).mockReturnValue(eventsRequest.promise)
      vi.mocked(fetchLogs).mockReturnValue(logsRequest.promise)
      renderPage()
      await flushAsync()
      expect(screen.getByText('手动阶段工作台测试')).toBeInTheDocument()
      expect(fetchUnits).toHaveBeenCalledTimes(1)
      expect(fetchEvents).toHaveBeenCalledTimes(1)
      expect(fetchLogs).toHaveBeenCalledTimes(1)
      await act(async () => { await vi.advanceTimersByTimeAsync(10_000) })
      await flushAsync()
      expect(screen.getAllByText('已成功').length).toBeGreaterThanOrEqual(1)
      unitsRequest.resolve({ items: [] })
      eventsRequest.reject(new Error('late events after terminal'))
      logsRequest.resolve({ items: [] })
      await flushAsync()
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
      expect(fetchTask).toHaveBeenCalledTimes(2)
      expect(fetchUnits).toHaveBeenCalledTimes(1)
      expect(fetchEvents).toHaveBeenCalledTimes(1)
      expect(fetchLogs).toHaveBeenCalledTimes(1)
    } finally {
      vi.useRealTimers()
    }
  })
})
