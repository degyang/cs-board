/**
 * M07 PR-2 — CreateProjectPage tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { CreateProjectPage } from '../src/pages/CreateProjectPage'
import * as api from '../src/lib/api/client'

vi.mock('../src/lib/api/client', () => ({
  createProject: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/new']}>
      <Routes>
        <Route path="/projects/new" element={<CreateProjectPage />} />
        <Route path="/projects/:id" element={<div>project-detail</div>} />
        <Route path="/" element={<div>project-list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CreateProjectPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the create project form', () => {
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
    vi.mocked(api.createProject).mockResolvedValue({ project_id: 'proj-1', run_id: 'run-1', trace_id: 'tr-1', command_id: 'cmd-1' })
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(api.createProject).toHaveBeenCalledWith({
        title: '量子计算科普',
        engine: 'whiteboard',
      })
    })
    await waitFor(() => {
      expect(screen.getByText('project-detail')).toBeInTheDocument()
    })
  })

  it('shows error message on failure', async () => {
    vi.mocked(api.createProject).mockRejectedValue(new Error('网络错误'))
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
  })

  it('shows loading state', async () => {
    vi.mocked(api.createProject).mockImplementation(() => new Promise(() => {}))
    renderPage()

    fireEvent.change(screen.getByLabelText('任务名称'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    await waitFor(() => {
      expect(screen.getByText('创建中…')).toBeInTheDocument()
    })
  })

  it('cancel navigates to project list', () => {
    renderPage()
    fireEvent.click(screen.getByText('取消'))
    expect(screen.getByText('project-list')).toBeInTheDocument()
  })
})
