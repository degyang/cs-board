/* ==========================================================================
   TasksPage — §3N real task queue behavior tests
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { TasksPage } from '../src/pages/TasksPage'
import type { TaskQueueItem, TaskListResponse } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', () => ({
  fetchTasks: vi.fn(),
}))

import { fetchTasks } from '../src/lib/api/client'

function renderAt(page: React.ReactElement, path = '/tasks') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/tasks" element={page} />
        <Route path="/tasks/new" element={<div>新建任务</div>} />
        <Route path="/tasks/:taskId" element={<div>任务工作台</div>} />
        <Route path="/tasks/:taskId/runs/:runId/diagnostics" element={<div>运行诊断</div>} />
        <Route path="/tasks/:taskId/runs/:runId/final" element={<div>成片</div>} />
      </Routes>
    </MemoryRouter>
  )
}

function makeTask(overrides: Partial<TaskQueueItem> = {}): TaskQueueItem {
  return {
    task_id: 'task-abc-123',
    title: '测试任务',
    pipeline_id: 'default',
    engine: 'whiteboard',
    status: 'running',
    created_at: '2025-03-20T10:00:00Z',
    updated_at: '2025-03-20T14:30:00Z',
    active_run_id: 'run-001',
    revision: 1,
    schema_version: 1,
    active_run: {
      run_id: 'run-001',
      status: 'running',
      current_stage: 'generate-illustrations',
      started_at: '2025-03-20T10:00:00Z',
      retryable: false,
      error_code: null,
      final_available: false,
      fallback_unit_count: null,
    },
    ...overrides,
  }
}

function makeResponse(items: TaskQueueItem[], nextCursor: string | null = null): TaskListResponse {
  return { items, next_cursor: nextCursor }
}

describe('TasksPage (§3N real task queue)', () => {
  beforeEach(() => {
    vi.mocked(fetchTasks).mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  // ── Initial request params ───────────────────────────────────────────

  it('sends limit param on initial load', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(fetchTasks).toHaveBeenCalledWith(expect.objectContaining({ limit: 20 }))
    })
  })

  // ── Status filter sends to server ────────────────────────────────────

  it('sends status param when a tab is selected', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('tab', { name: '运行中' }))

    await waitFor(() => {
      expect(fetchTasks).toHaveBeenCalledWith(expect.objectContaining({ status: 'running' }))
    })
  })

  // ── Search sends q param to server ───────────────────────────────────

  it('sends q param when search is submitted', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText('搜索标题或 Task ID…'), '测试')
    await user.click(screen.getByText('搜索'))

    await waitFor(() => {
      expect(fetchTasks).toHaveBeenCalledWith(expect.objectContaining({ q: '测试' }))
    })
  })

  // ── Cursor reset on status change ────────────────────────────────────

  it('resets cursor and items when status changes', async () => {
    const page1 = makeResponse([makeTask({ task_id: 'task-001', title: '任务一' })], 'cursor-1')
    const page2 = makeResponse([makeTask({ task_id: 'task-002', title: '任务二', status: 'failed' })])
    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)
    vi.mocked(fetchTasks).mockResolvedValueOnce(page2)

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
    })

    // Switch tab → resets
    await user.click(screen.getByRole('tab', { name: '失败' }))

    await waitFor(() => {
      expect(fetchTasks).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'failed' }))
      expect(fetchTasks).toHaveBeenLastCalledWith(expect.not.objectContaining({ cursor: expect.anything() }))
    })
  })

  // ── next_cursor pagination ───────────────────────────────────────────

  it('loads more items using next_cursor', async () => {
    const page1 = makeResponse([makeTask({ task_id: 'task-001', title: '任务一' })], 'cursor-abc')
    const page2 = makeResponse([makeTask({ task_id: 'task-002', title: '任务二' })])
    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)
    vi.mocked(fetchTasks).mockResolvedValueOnce(page2)

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
    })

    await user.click(screen.getByText('加载更多'))

    await waitFor(() => {
      expect(fetchTasks).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: 'cursor-abc' }))
      expect(screen.getByText('任务二')).toBeInTheDocument()
    })
  })

  it('shows "已显示全部任务" when no next_cursor', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask()]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('已显示全部任务')).toBeInTheDocument()
    })
    expect(screen.queryByText('加载更多')).not.toBeInTheDocument()
  })

  // ── Status rendering ─────────────────────────────────────────────────

  it('renders running task with active run stage', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      status: 'running',
      title: '运行中任务',
      active_run: {
        run_id: 'run-001',
        status: 'running',
        current_stage: 'generate-illustrations',
        started_at: '2025-03-20T10:00:00Z',
        retryable: false,
        error_code: null,
        final_available: false,
        fallback_unit_count: null,
      },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('运行中任务')).toBeInTheDocument()
    })
    const card = screen.getByText('运行中任务').closest('article')!
    expect(card.textContent).toContain('生成插画')
  })

  it('renders completed task', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      status: 'succeeded',
      active_run: null,
      active_run_id: null,
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('已成功')).toBeInTheDocument()
    })
  })

  it('renders failed task', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      status: 'failed',
      title: '失败任务',
      active_run: {
        run_id: 'run-002',
        status: 'failed',
        current_stage: 'compose-video',
        started_at: '2025-03-20T10:00:00Z',
        retryable: true,
        error_code: 'PIPELINE_ERROR',
        final_available: false,
        fallback_unit_count: null,
      },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('失败任务')).toBeInTheDocument()
    })
    const card = screen.getByText('失败任务').closest('article')!
    expect(card.textContent).toContain('合成成片')
  })

  it('shows "尚未运行" when active_run is null', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run: null,
      active_run_id: null,
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('尚未运行')).toBeInTheDocument()
    })
  })

  it('renders unknown status as-is', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      status: 'stale',
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('已过期')).toBeInTheDocument()
    })
  })

  it('renders unknown stage as raw value', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run: {
        run_id: 'run-003',
        status: 'running',
        current_stage: 'custom-future-stage',
        started_at: '2025-03-20T10:00:00Z',
        retryable: false,
        error_code: null,
        final_available: false,
        fallback_unit_count: null,
      },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText(/custom-future-stage/)).toBeInTheDocument()
    })
  })

  // ── Link constraints ─────────────────────────────────────────────────

  it('always shows "进入工作台" link', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask()]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('进入工作台')).toBeInTheDocument()
    })
  })

  it('shows diagnostics link when active_run exists', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run_id: 'run-001',
      active_run: { run_id: 'run-001', status: 'running', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: false, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      const link = screen.getByText('运行诊断')
      expect(link).toBeInTheDocument()
      expect(link.closest('a')).toHaveAttribute('href', expect.stringContaining('run-001'))
    })
  })

  it('hides diagnostics link when no active_run', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({ active_run: null, active_run_id: null })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })
    expect(screen.queryByText('运行诊断')).not.toBeInTheDocument()
  })

  it('shows final link when final_available is true and run_id exists', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run: { run_id: 'run-001', status: 'succeeded', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: true, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      const link = screen.getByText('成片')
      expect(link).toBeInTheDocument()
      expect(link.closest('a')).toHaveAttribute('href', expect.stringContaining('run-001'))
    })
  })

  it('hides final link when final_available is false', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run: { run_id: 'run-001', status: 'running', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: false, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })
    expect(screen.queryByText('成片')).not.toBeInTheDocument()
  })

  it('URL-encodes task_id and run_id in links', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      task_id: 'task/id+special',
      active_run_id: 'run/id+special',
      active_run: { run_id: 'run/id+special', status: 'running', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: true, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      const diagLink = screen.getByText('运行诊断').closest('a')!
      expect(diagLink.getAttribute('href')).toContain(encodeURIComponent('task/id+special'))
      expect(diagLink.getAttribute('href')).toContain(encodeURIComponent('run/id+special'))

      const finalLink = screen.getByText('成片').closest('a')!
      expect(finalLink.getAttribute('href')).toContain(encodeURIComponent('task/id+special'))
    })
  })

  // ── Loading skeleton ─────────────────────────────────────────────────

  it('shows loading skeleton initially', () => {
    vi.mocked(fetchTasks).mockReturnValue(new Promise(() => {}))
    renderAt(<TasksPage />)

    expect(screen.getByLabelText('正在加载任务列表')).toBeInTheDocument()
    expect(screen.queryByText('暂无任务')).not.toBeInTheDocument()
  })

  // ── Request error + retry ────────────────────────────────────────────

  it('displays error when request fails', async () => {
    vi.mocked(fetchTasks).mockRejectedValue(new Error('网络连接失败'))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText(/网络连接失败/)).toBeInTheDocument()
    })
  })

  it('retry button re-calls fetchTasks', async () => {
    vi.mocked(fetchTasks).mockRejectedValueOnce(new Error('临时错误'))
    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText(/临时错误/)).toBeInTheDocument()
    })

    vi.mocked(fetchTasks).mockResolvedValueOnce(makeResponse([makeTask()]))
    await user.click(screen.getByText('重新加载'))

    await waitFor(() => {
      expect(screen.getByText('测试任务')).toBeInTheDocument()
    })
    expect(fetchTasks).toHaveBeenCalledTimes(2)
  })

  // ── Empty queue ──────────────────────────────────────────────────────

  it('shows empty state when no tasks', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('暂无任务')).toBeInTheDocument()
      expect(screen.getByText(/新建任务.*开始制作/)).toBeInTheDocument()
    })
  })

  it('shows filtered empty state when search has no results', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText('搜索标题或 Task ID…'), '不存在')
    await user.click(screen.getByText('搜索'))

    await waitFor(() => {
      expect(screen.getByText('当前筛选条件下没有任务')).toBeInTheDocument()
    })
  })

  // ── Race protection: second request wins ──────────────────────────────

  it('second request wins when first arrives after second', async () => {
    let resolveFirst: (v: TaskListResponse) => void
    let resolveSecond: (v: TaskListResponse) => void
    const firstRequest = new Promise<TaskListResponse>(r => { resolveFirst = r })
    const secondRequest = new Promise<TaskListResponse>(r => { resolveSecond = r })

    vi.mocked(fetchTasks).mockReturnValueOnce(firstRequest as any)

    const { unmount } = renderAt(<TasksPage />)
    await new Promise(r => setTimeout(r, 0))

    unmount()

    vi.mocked(fetchTasks).mockReturnValueOnce(secondRequest as any)
    renderAt(<TasksPage />)
    await new Promise(r => setTimeout(r, 0))

    // Second completes first
    resolveSecond!(makeResponse([makeTask({ task_id: 'winner', title: '胜出任务' })]))
    await waitFor(() => {
      expect(screen.getByText('胜出任务')).toBeInTheDocument()
    })

    // First arrives late
    resolveFirst!(makeResponse([makeTask({ task_id: 'loser', title: '过期任务' })]))
    await new Promise(r => setTimeout(r, 0))

    // DOM must still show second response
    expect(screen.getByText('胜出任务')).toBeInTheDocument()
    expect(screen.queryByText('过期任务')).not.toBeInTheDocument()
    expect(fetchTasks).toHaveBeenCalledTimes(2)
  })

  it('unmount prevents setState from late response', async () => {
    let resolve: (v: TaskListResponse) => void
    const pending = new Promise<TaskListResponse>(r => { resolve = r })
    vi.mocked(fetchTasks).mockReturnValueOnce(pending as any)

    const { unmount } = renderAt(<TasksPage />)
    await new Promise(r => setTimeout(r, 0))

    unmount()
    resolve!(makeResponse([makeTask({ task_id: 'late' })]))
    await new Promise(r => setTimeout(r, 0))

    expect(fetchTasks).toHaveBeenCalledTimes(1)
  })

  // ── Sensitive fields not rendered ─────────────────────────────────────

  it('does not render sensitive extra fields from response', async () => {
    const sensitiveTask = makeTask({
      path: '/mnt/data/tasks/abc',
      command: 'ffmpeg -i input.mp4',
      token: 'sk-secret-token-12345',
      secret: 'api-key-abcdef',
      logs: 'ERROR: connection refused',
    })
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([sensitiveTask as any]))
    const { container } = renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('/mnt/data/tasks/abc')
    expect(text).not.toContain('ffmpeg -i input.mp4')
    expect(text).not.toContain('sk-secret-token-12345')
    expect(text).not.toContain('api-key-abcdef')
    expect(text).not.toContain('ERROR: connection refused')
  })

  // ── Page title ───────────────────────────────────────────────────────

  it('displays page title "任务队列"', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务队列')).toBeInTheDocument()
      expect(screen.getByText(/所有视频制作任务/)).toBeInTheDocument()
    })
  })
})
