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
    expect(screen.getByRole('heading', { name: '创建项目' })).toBeInTheDocument()
    expect(screen.getByLabelText('项目标题')).toBeInTheDocument()
    expect(screen.getByText('白板动画 (whiteboard)')).toBeInTheDocument()
    expect(screen.getByText('mountain-av-v1')).toBeInTheDocument()
  })

  it('disables submit when title is too short', () => {
    renderPage()
    const btn = screen.getByRole('button', { name: '创建项目' })
    expect(btn).toBeDisabled()

    fireEvent.change(screen.getByLabelText('项目标题'), { target: { value: 'a' } })
    expect(btn).toBeDisabled()
  })

  it('calls API and navigates on success', async () => {
    vi.mocked(api.createProject).mockResolvedValue({ id: 'proj-1', status: 'created' } as any)
    renderPage()

    fireEvent.change(screen.getByLabelText('项目标题'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建项目' }))

    await waitFor(() => {
      expect(api.createProject).toHaveBeenCalledWith({
        title: '量子计算科普',
        engine: 'whiteboard',
        pipeline_id: 'mountain-av-v1',
      })
    })
    await waitFor(() => {
      expect(screen.getByText('project-detail')).toBeInTheDocument()
    })
  })

  it('shows error message on failure', async () => {
    vi.mocked(api.createProject).mockRejectedValue(new Error('网络错误'))
    renderPage()

    fireEvent.change(screen.getByLabelText('项目标题'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建项目' }))

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
  })

  it('shows loading state', async () => {
    vi.mocked(api.createProject).mockImplementation(() => new Promise(() => {}))
    renderPage()

    fireEvent.change(screen.getByLabelText('项目标题'), { target: { value: '量子计算科普' } })
    fireEvent.click(screen.getByRole('button', { name: '创建项目' }))

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
