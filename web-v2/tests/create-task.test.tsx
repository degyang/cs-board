/**
 * M07 PR-2 — CreateTaskPage tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { CreateTaskPage } from '../src/pages/CreateTaskPage'
import * as api from '../src/lib/api/client'

vi.mock('../src/lib/api/client', () => ({
  createTask: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tasks/new']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/tasks/new" element={<CreateTaskPage />} />
        <Route path="/tasks/:id" element={<div>task-detail</div>} />
        <Route path="/" element={<div>task-list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CreateTaskPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the create task form', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: '新建任务' })).toBeInTheDocument()
    expect(screen.getByLabelText('任务名称')).toBeInTheDocument()
    expect(screen.getByText('白板动画')).toBeInTheDocument()
    expect(screen.getByText('动态信息图')).toBeInTheDocument()
  })

  it('shows error when title is empty', async () => {
    renderPage()
    const btn = screen.getByRole('button', { name: '创建任务' })
    fireEvent.click(btn)

    await waitFor(() => {
      expect(screen.getByText('请输入任务名称')).toBeInTheDocument()
    })
  })

  it('calls API and navigates on success', async () => {
    vi.mocked(api.createTask).mockResolvedValue({ task_id: 'proj-1', run_id: 'run-1', trace_id: 'tr-1', command_id: 'cmd-1' })
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(api.createTask).toHaveBeenCalledWith({
        title: '量子计算科普',
        engine: 'whiteboard',
      })
    })
    await waitFor(() => {
      expect(screen.getByText('task-detail')).toBeInTheDocument()
    })
  })

  it('shows error message on failure', async () => {
    vi.mocked(api.createTask).mockRejectedValue(new Error('网络错误'))
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
  })

  it('shows loading state', async () => {
    vi.mocked(api.createTask).mockImplementation(() => new Promise(() => {}))
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(screen.getByText('创建中…')).toBeInTheDocument()
    })
  })

  it('cancel navigates to task list', () => {
    renderPage()
    fireEvent.click(screen.getByText('取消'))
    expect(screen.getByText('task-list')).toBeInTheDocument()
  })
})
