/* ==========================================================================
   Sidebar interaction behavior evidence for prototype alignment
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor, cleanup, within, act, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '../src/components/layout/AppShell'
import type { Task } from '../src/lib/api/types'

vi.mock('../src/lib/api/tasks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/api/tasks')>()
  return { ...actual, fetchTasks: vi.fn() }
})

import { fetchTasks } from '../src/lib/api/tasks'

const PIN_KEY = 'mountain.ui.sidebarPinned'

const EMPTY_TASK: Task[] = []

const RUNNING_TASK: Task[] = [
  {
    task_id: 'task-001',
    title: 'Demo 任务',
    pipeline_id: 'default',
    engine: 'whiteboard',
    status: 'running',
    created_at: '2026-08-31T10:00:00Z',
    updated_at: '2026-08-31T10:00:10Z',
    active_run_id: null,
    revision: 1,
    schema_version: 1,
  },
]

function renderShell(path = '/tasks') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<div>主页</div>} />
          <Route path="tasks" element={<div>任务页面</div>} />
          <Route path="tasks/new" element={<div>创建任务</div>} />
          <Route path="assets" element={<div>素材</div>} />
          <Route path="settings" element={<div>设置</div>} />
          <Route path="help" element={<div>帮助</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('Sidebar prototype interaction', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(fetchTasks).mockReset()
    vi.mocked(fetchTasks).mockResolvedValue(EMPTY_TASK)
  })

  afterEach(() => {
    cleanup()
  })

  it('defaults to pinned state when pin preference is not persisted', async () => {
    const { container } = renderShell()

    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    const shell = container.querySelector('.app-shell')
    expect(shell).toHaveClass('is-pinned')
    expect(shell).not.toHaveClass('is-rail')
  })

  it('exposes accessible pin and rail controls and expands only from the two rail triggers', async () => {
    localStorage.setItem(PIN_KEY, '0')
    vi.mocked(fetchTasks).mockResolvedValue(RUNNING_TASK)

    const user = userEvent.setup()
    const { container } = renderShell()
    const sidebar = container.querySelector('.sidebar')!
    const brand = container.querySelector('.brand')!

    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    expect(sidebar).not.toHaveClass('rail-peeking')

    const pin = within(sidebar).getByRole('button', { name: '钉住侧边栏' })
    expect(pin).toHaveAttribute('aria-pressed', 'false')
    expect(within(sidebar).getByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(within(sidebar).getByRole('link', { name: '任务队列' })).toHaveAttribute('title', '任务队列')
    expect(within(sidebar).getByRole('link', { name: /Demo 任务/ })).toHaveAttribute('href', '/tasks/task-001')

    await user.hover(brand)
    expect(sidebar).not.toHaveClass('rail-peeking')

    const triggers = within(sidebar).getAllByRole('button', { name: '展开侧边栏' })
    expect(triggers).toHaveLength(2)
    expect(triggers[0]).toHaveAttribute('aria-controls', 'mountain-sidebar')
    expect(triggers[1]).toHaveAttribute('aria-controls', 'mountain-sidebar')

    await user.tab()
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))
    await user.unhover(sidebar)
    await waitFor(() => expect(sidebar).not.toHaveClass('rail-peeking'))

    await user.hover(triggers[0])
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))

    await user.unhover(triggers[0])
    await waitFor(() => expect(sidebar).not.toHaveClass('rail-peeking'))

    await user.hover(triggers[1])
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))

    const pinWhilePeeking = within(sidebar).getByRole('button', { name: '钉住侧边栏' })
    await user.click(pinWhilePeeking)
    await waitFor(() => expect(container.querySelector('.app-shell')).toHaveClass('is-pinned'))
    expect(localStorage.getItem(PIN_KEY)).toBe('1')
    expect(sidebar).not.toHaveClass('rail-peeking')

    await user.click(within(sidebar).getByRole('button', { name: '取消钉住侧边栏' }))
    await waitFor(() => expect(container.querySelector('.app-shell')).toHaveClass('is-rail'))
    expect(localStorage.getItem(PIN_KEY)).toBe('0')
    expect(sidebar).not.toHaveClass('rail-peeking')

    await user.hover(triggers[0])
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))
    await user.unhover(sidebar)
    await waitFor(() => expect(sidebar).not.toHaveClass('rail-peeking'))
  })

  it('does not expand when hovering nav, footer, or blank sidebar area', async () => {
    localStorage.setItem(PIN_KEY, '0')
    const { container } = renderShell()
    const user = userEvent.setup()
    const sidebar = container.querySelector('.sidebar')!
    const brand = container.querySelector('.brand')!

    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    await user.unhover(brand)
    expect(sidebar).not.toHaveClass('rail-peeking')

    const navHint = container.querySelector('.nav')!
    await user.hover(navHint)
    expect(sidebar).not.toHaveClass('rail-peeking')

    const footer = container.querySelector('.sidebar-footer')!
    await user.hover(footer)
    expect(sidebar).not.toHaveClass('rail-peeking')

    await user.hover(sidebar)
    expect(sidebar).not.toHaveClass('rail-peeking')
  })

  it('keeps peek open while moving inside the sidebar and collapses only on sidebar leave', async () => {
    localStorage.setItem(PIN_KEY, '0')
    const { container } = renderShell()
    const user = userEvent.setup()
    const sidebar = container.querySelector('.sidebar')!

    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    await user.hover(within(sidebar).getAllByRole('button', { name: '展开侧边栏' })[0])
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))

    fireEvent.mouseOver(container.querySelector('.nav')!, { relatedTarget: within(sidebar).getAllByRole('button', { name: '展开侧边栏' })[0] })
    expect(sidebar).toHaveClass('rail-peeking')
    fireEvent.mouseOver(container.querySelector('.sidebar-footer')!, { relatedTarget: container.querySelector('.nav') })
    expect(sidebar).toHaveClass('rail-peeking')

    await user.unhover(sidebar)
    await waitFor(() => expect(sidebar).not.toHaveClass('rail-peeking'))
  })

  it('aborts the runtime task request on sidebar unmount', async () => {
    let resolveFetch!: (value: Task[]) => void
    let requestSignal: AbortSignal | undefined
    vi.mocked(fetchTasks).mockImplementationOnce((signal?: AbortSignal) => {
      requestSignal = signal
      return new Promise<Task[]>((resolve) => {
        resolveFetch = resolve
      })
    })

    const { unmount } = renderShell()
    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    expect(requestSignal).toBeInstanceOf(AbortSignal)

    unmount()
    expect(requestSignal?.aborted).toBe(true)
    await act(async () => resolveFetch(EMPTY_TASK))
  })
})
