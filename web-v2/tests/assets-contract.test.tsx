/* ==========================================================================
   Component Contract Tests — Asset Management Page
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AssetManagementPage } from '../src/pages/AssetManagementPage'

vi.mock('../src/lib/api/assets', () => ({
  fetchStyles: vi.fn(),
  fetchVoices: vi.fn(),
  activateStyle: vi.fn(),
  deactivateStyle: vi.fn(),
  copyStyle: vi.fn(),
  activateVoice: vi.fn(),
  deactivateVoice: vi.fn(),
}))

import { fetchStyles, fetchVoices, activateStyle, deactivateStyle, copyStyle } from '../src/lib/api/assets'

const mockStyles = [
  { style_id: 's1', kind: 'preset', name: '水彩风', description: '水彩画风格', status: 'active', created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z' },
  { style_id: 's2', kind: 'preset', name: '油画风', description: '油画风格', status: 'inactive', created_at: '2025-01-02T00:00:00Z', updated_at: '2025-01-02T00:00:00Z' },
]

const mockVoices = [
  { voice_id: 'v1', name: '温柔女声', description: '适合讲故事', status: 'active', created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z' },
]

describe('AssetManagementPage', () => {
  beforeEach(() => {
    vi.mocked(fetchStyles).mockReset()
    vi.mocked(fetchVoices).mockReset()
    vi.mocked(activateStyle).mockReset()
    vi.mocked(deactivateStyle).mockReset()
    vi.mocked(copyStyle).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [] })
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)
    expect(screen.getByText('素材管理')).toBeInTheDocument()
  })

  it('renders all three tabs', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [] })
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)
    expect(screen.getByText('预置风格')).toBeInTheDocument()
    expect(screen.getByText('自定义风格')).toBeInTheDocument()
    expect(screen.getByText('音色库')).toBeInTheDocument()
  })

  it('loads and displays preset styles', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('水彩风')).toBeInTheDocument()
      expect(screen.getByText('油画风')).toBeInTheDocument()
    })
  })

  it('shows loading state', () => {
    vi.mocked(fetchStyles).mockImplementation(() => new Promise(() => {}))
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.mocked(fetchStyles).mockRejectedValue(new Error('Network error'))
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no items', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [] })
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('暂无数据')).toBeInTheDocument()
    })
  })

  it('selects an item and shows detail', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('水彩风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('水彩风'))

    await waitFor(() => {
      expect(screen.getByText('水彩画风格')).toBeInTheDocument()
    })
  })

  it('calls activateStyle when clicking activate button', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    vi.mocked(activateStyle).mockResolvedValue({ ...mockStyles[1], status: 'active' })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: mockStyles })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: mockStyles.map(s => s.style_id === 's2' ? { ...s, status: 'active' } : s) })

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('油画风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('油画风'))

    await waitFor(() => {
      expect(screen.getByText('启用')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('启用'))

    await waitFor(() => {
      expect(activateStyle).toHaveBeenCalledWith('s2')
    })
  })

  it('calls deactivateStyle when clicking deactivate button', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    vi.mocked(deactivateStyle).mockResolvedValue({ ...mockStyles[0], status: 'inactive' })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: mockStyles })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: mockStyles.map(s => s.style_id === 's1' ? { ...s, status: 'inactive' } : s) })

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('水彩风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('水彩风'))

    await waitFor(() => {
      expect(screen.getByText('停用')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('停用'))

    await waitFor(() => {
      expect(deactivateStyle).toHaveBeenCalledWith('s1')
    })
  })

  it('calls copyStyle when clicking copy button for preset styles', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    vi.mocked(copyStyle).mockResolvedValue({ ...mockStyles[0], style_id: 's3', kind: 'custom' })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: mockStyles })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [...mockStyles, { style_id: 's3', kind: 'custom', name: '水彩风 (副本)', status: 'active', created_at: '2025-01-03T00:00:00Z', updated_at: '2025-01-03T00:00:00Z' }] })

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('水彩风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('水彩风'))

    await waitFor(() => {
      expect(screen.getByText('复制为自定义')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('复制为自定义'))

    await waitFor(() => {
      expect(copyStyle).toHaveBeenCalledWith('s1')
    })
  })

  it('switches to voice tab and loads voices', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [] })
    vi.mocked(fetchVoices).mockResolvedValue({ items: mockVoices })

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await userEvent.click(screen.getByText('音色库'))

    await waitFor(() => {
      expect(fetchVoices).toHaveBeenCalled()
      expect(screen.getByText('温柔女声')).toBeInTheDocument()
    })
  })

  it('search input triggers fetch with query', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('水彩风')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('搜索...')
    await userEvent.type(searchInput, '水彩')

    await waitFor(() => {
      expect(fetchStyles).toHaveBeenCalledWith(expect.objectContaining({ q: '水彩' }))
    })
  })

  it('prevents double submit on activate', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles })
    vi.mocked(activateStyle).mockImplementation(() => new Promise(() => {}))

    render(<MemoryRouter><AssetManagementPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('油画风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('油画风'))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '启用' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '启用' }))

    await waitFor(() => {
      const processingButtons = screen.getAllByText('处理中...')
      expect(processingButtons.length).toBeGreaterThanOrEqual(1)
    })
  })
})
