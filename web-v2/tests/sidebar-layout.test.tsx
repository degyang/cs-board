/* ==========================================================================
   Sidebar interaction behavior evidence for prototype alignment
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor, cleanup } from '@testing-library/react'
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

  it('expands only when hovering the brand area in rail mode', async () => {
    localStorage.setItem(PIN_KEY, '0')
    vi.mocked(fetchTasks).mockResolvedValue(RUNNING_TASK)

    const user = userEvent.setup()
    const { container } = renderShell()
    const sidebar = container.querySelector('.sidebar')!
    const brand = container.querySelector('.brand')!

    await waitFor(() => expect(vi.mocked(fetchTasks)).toHaveBeenCalled())
    expect(sidebar).not.toHaveClass('rail-peeking')

    await user.hover(brand)
    await waitFor(() => expect(sidebar).toHaveClass('rail-peeking'))

    await user.unhover(brand)
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
})
