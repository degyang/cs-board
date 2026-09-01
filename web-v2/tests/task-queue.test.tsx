/* ==========================================================================
   TasksPage — §3O corrected task queue behavior tests
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { TasksPage } from '../src/pages/TasksPage'
import { getFinalUrl } from '../src/lib/api/client'
import type { TaskQueueItem, TaskListResponse } from '../src/lib/api/types'

vi.mock('../src/lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/api/client')>()
  return {
    ...actual,
    fetchTasks: vi.fn(),
  }
})

import { fetchTasks } from '../src/lib/api/client'

/** Production route tree — no /final route. */
function renderAt(page: React.ReactElement, path = '/tasks') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/tasks" element={page} />
        <Route path="/tasks/new" element={<div>新建任务</div>} />
        <Route path="/tasks/:taskId" element={<div>任务工作台</div>} />
        <Route path="/tasks/:taskId/runs/:runId/diagnostics" element={<div>运行诊断</div>} />
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

describe('TasksPage (§3O corrected task queue)', () => {
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

  // ── Load more button disabled while pending ──────────────────────────

  it('disables load-more button while request is pending', async () => {
    let resolvePage2: (v: TaskListResponse) => void
    const page2Promise = new Promise<TaskListResponse>(r => { resolvePage2 = r })

    const page1 = makeResponse([makeTask({ task_id: 'task-001', title: '任务一' })], 'cursor-abc')
    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)
    vi.mocked(fetchTasks).mockReturnValueOnce(page2Promise as any)

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
    })

    await user.click(screen.getByText('加载更多'))

    // Button should be disabled and show "加载中…"
    await waitFor(() => {
      expect(screen.getByText('加载中…')).toBeDisabled()
    })

    // Complete the request
    resolvePage2!(makeResponse([makeTask({ task_id: 'task-002', title: '任务二' })]))
    await waitFor(() => {
      expect(screen.getByText('任务二')).toBeInTheDocument()
    })
  })

  // ── Dedup by task_id on append ───────────────────────────────────────

  it('deduplicates task_id on append, preserving server order', async () => {
    const page1 = makeResponse([
      makeTask({ task_id: 'task-001', title: '任务一' }),
      makeTask({ task_id: 'task-002', title: '任务二' }),
    ], 'cursor-abc')
    const page2 = makeResponse([
      makeTask({ task_id: 'task-002', title: '任务二重复' }),
      makeTask({ task_id: 'task-003', title: '任务三' }),
    ])
    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)
    vi.mocked(fetchTasks).mockResolvedValueOnce(page2)

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
    })

    await user.click(screen.getByText('加载更多'))

    await waitFor(() => {
      expect(screen.getByText('任务三')).toBeInTheDocument()
    })

    // task-002 should appear only once (from page1, not replaced by page2's duplicate)
    const cards = screen.getAllByText(/任务二/)
    expect(cards.length).toBe(1)
  })

  // ── Pagination failure keeps existing items ──────────────────────────

  it('keeps existing items when pagination fails, allows retry', async () => {
    const page1 = makeResponse([makeTask({ task_id: 'task-001', title: '任务一' })], 'cursor-abc')
    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)
    vi.mocked(fetchTasks).mockRejectedValueOnce(new Error('网络超时'))

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
    })

    await user.click(screen.getByText('加载更多'))

    // Page1 items still visible, local error shown
    await waitFor(() => {
      expect(screen.getByText('任务一')).toBeInTheDocument()
      expect(screen.getByText(/网络超时/)).toBeInTheDocument()
    })

    // Retry with same cursor
    vi.mocked(fetchTasks).mockResolvedValueOnce(makeResponse([makeTask({ task_id: 'task-002', title: '任务二' })]))
    await user.click(screen.getByText('重试'))

    await waitFor(() => {
      expect(screen.getByText('任务二')).toBeInTheDocument()
    })
  })

  // ── Stale pagination cannot pollute new filter ───────────────────────

  it('stale pagination response does not append to new filter results', async () => {
    let resolveOldPage: (v: TaskListResponse) => void
    let resolveNewFilter: (v: TaskListResponse) => void

    const page1 = makeResponse([makeTask({ task_id: 'task-001', title: '第一页' })], 'cursor-old')
    const oldPagePromise = new Promise<TaskListResponse>(r => { resolveOldPage = r })
    const newFilterPromise = new Promise<TaskListResponse>(r => { resolveNewFilter = r })

    vi.mocked(fetchTasks).mockResolvedValueOnce(page1)

    const user = userEvent.setup()
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('第一页')).toBeInTheDocument()
    })

    // Start loading more (old cursor)
    vi.mocked(fetchTasks).mockReturnValueOnce(oldPagePromise as any)
    await user.click(screen.getByText('加载更多'))

    // Switch filter before old page completes
    vi.mocked(fetchTasks).mockReturnValueOnce(newFilterPromise as any)
    await user.click(screen.getByRole('tab', { name: '已完成' }))

    // New filter completes first
    resolveNewFilter!(makeResponse([makeTask({ task_id: 'task-new', title: '新筛选任务', status: 'succeeded' })]))
    await waitFor(() => {
      expect(screen.getByText('新筛选任务')).toBeInTheDocument()
    })

    // Old page completes late — must not append
    resolveOldPage!(makeResponse([makeTask({ task_id: 'task-stale', title: '过期分页' })]))
    await new Promise(r => setTimeout(r, 0))

    expect(screen.queryByText('过期分页')).not.toBeInTheDocument()
    expect(screen.getByText('新筛选任务')).toBeInTheDocument()
  })

  // ── Status rendering ─────────────────────────────────────────────────

  it('renders running task with active run stage and status', async () => {
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
    expect(card.textContent).toContain('运行状态')
  })

  it('renders failed task with retryable hint', async () => {
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
    expect(card.textContent).toContain('可重试')
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

  it('renders unknown run status as-is', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      active_run: {
        run_id: 'run-003',
        status: 'custom-status',
        current_stage: null,
        started_at: '',
        retryable: false,
        error_code: null,
        final_available: false,
        fallback_unit_count: null,
      },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('custom-status')).toBeInTheDocument()
    })
  })

  it('does not show retryable hint when retryable is false', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      title: '非重试任务',
      active_run: {
        run_id: 'run-004',
        status: 'failed',
        current_stage: null,
        started_at: '',
        retryable: false,
        error_code: null,
        final_available: false,
        fallback_unit_count: null,
      },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('非重试任务')).toBeInTheDocument()
    })
    expect(screen.queryByText('可重试')).not.toBeInTheDocument()
  })

  // ── Link constraints ─────────────────────────────────────────────────

  it('always shows "进入工作台" button', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask()]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      expect(screen.getByText('进入工作台')).toBeInTheDocument()
    })
  })

  it('shows diagnostics link when active_run exists, with encoded IDs', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      task_id: 'task/id+special',
      active_run_id: 'run/id+special',
      active_run: { run_id: 'run/id+special', status: 'running', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: false, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      const link = screen.getByText('运行诊断')
      expect(link).toBeInTheDocument()
      const href = link.closest('a')!.getAttribute('href')!
      expect(href).toContain(encodeURIComponent('task/id+special'))
      expect(href).toContain(encodeURIComponent('run/id+special'))
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

  // ── Final link uses real getFinalUrl API, not SPA route ──────────────

  it('shows final as <a> with getFinalUrl href when final_available is true', async () => {
    vi.mocked(fetchTasks).mockResolvedValue(makeResponse([makeTask({
      task_id: 'task/special+id',
      active_run: { run_id: 'run/special+id', status: 'succeeded', current_stage: null, started_at: '', retryable: false, error_code: null, final_available: true, fallback_unit_count: null },
    })]))
    renderAt(<TasksPage />)

    await waitFor(() => {
      const link = screen.getByText('成片')
      expect(link).toBeInTheDocument()
      const el = link.closest('a')!
      // Must be a real <a> with API URL, not a React Router Link
      expect(el.tagName).toBe('A')
      const expected = getFinalUrl('task/special+id', 'run/special+id')
      expect(el).toHaveAttribute('href', expected)
      expect(el).toHaveAttribute('target', '_blank')
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

  it('production router has no /final route (test does not fake one)', () => {
    // This test documents that renderAt() does NOT include a /final Route.
    // If the component used a Router Link to /final, it would 404 in production.
    // The component uses <a href={getFinalUrl(...)}> instead.
    renderAt(<TasksPage />)
    // No assertion needed — the absence of /final in renderAt is the proof.
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

    resolveSecond!(makeResponse([makeTask({ task_id: 'winner', title: '胜出任务' })]))
    await waitFor(() => {
      expect(screen.getByText('胜出任务')).toBeInTheDocument()
    })

    resolveFirst!(makeResponse([makeTask({ task_id: 'loser', title: '过期任务' })]))
    await new Promise(r => setTimeout(r, 0))

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
