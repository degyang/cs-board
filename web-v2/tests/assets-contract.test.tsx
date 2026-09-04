/* ==========================================================================
   Component Contract Tests — Asset Management Page
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AssetManagementPage } from '../src/pages/AssetManagementPage'

/** React Router v7 future flags — suppresses all Future Flag warnings */
const ROUTER_FUTURE = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}

vi.mock('../src/lib/api/assets', () => ({
  fetchStyles: vi.fn(),
  createStyle: vi.fn(),
  updateStyle: vi.fn(),
  deleteStyle: vi.fn(),
  fetchPreconditions: vi.fn(),
}))

import {
  fetchStyles,
  createStyle, updateStyle, deleteStyle,
  fetchPreconditions,
} from '../src/lib/api/assets'

const mockStyles = [
  {
    style_id: 's1', kind: 'preset' as const, name: '水彩风', description: '水彩画风格',
    engine: 'sdxl', status: 'active' as const, revision: 1, tags: ['水彩'],
    prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {},
    created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
  },
  {
    style_id: 's2', kind: 'preset' as const, name: '油画风', description: '油画风格',
    engine: 'sdxl', status: 'inactive' as const, revision: 1, tags: ['油画'],
    prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {},
    created_at: '2025-01-02T00:00:00Z', updated_at: '2025-01-02T00:00:00Z',
  },
]

describe('AssetManagementPage', () => {
  beforeEach(() => {
    vi.mocked(fetchStyles).mockReset()
    vi.mocked(createStyle).mockReset()
    vi.mocked(updateStyle).mockReset()
    vi.mocked(deleteStyle).mockReset()
    vi.mocked(fetchPreconditions).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    expect(screen.getByText('图风管理')).toBeInTheDocument()
  })

  it('isolates the baseline search wrapper from the legacy am-search input class', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    const input = screen.getByPlaceholderText('搜索资产…')
    expect(input).toHaveClass('input', 'am-search-input')
    expect(input.parentElement).toHaveClass('am-search-wrap')
    expect(input.parentElement).not.toHaveClass('am-search')
    expect(input.parentElement?.querySelector('.am-search-ico')).toHaveTextContent('🔍')
  })

  it('renders style tabs without voice tab', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    expect(screen.getByText('预置风格')).toBeInTheDocument()
    expect(screen.getByText('自定义风格')).toBeInTheDocument()
    expect(screen.getByText('前置条件')).toBeInTheDocument()
    expect(screen.queryByText('音色库')).not.toBeInTheDocument()
  })

  it('loads read-only precondition cards with real contract fields and no Task selection control', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchPreconditions).mockResolvedValue({
      items: [
        {
          precondition_id: 'precondition-explainer', revision: 1, name: '通用讲解者', kind: 'visual-explainer',
          applies_to: ['storyboard', 'illustration'], status: 'active', enabled: true,
          engine_compatibility: ['whiteboard'], preview_asset_id: 'preview-explainer',
          description: '未指定人物时使用的视觉约束。', condition_text: '不覆盖 Style revision 内的人物约束。',
        },
        {
          precondition_id: 'precondition-hand', revision: 1, name: '白板绘制手', kind: 'renderer-hand',
          applies_to: ['whiteboard'], status: 'inactive', enabled: false,
          engine_compatibility: ['whiteboard'], preview_asset_id: null,
          description: '渲染阶段的基础绘制手。', condition_text: '品牌文字仍属于 Task 设置。',
        },
      ], next_cursor: null, total: 2,
    })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    await userEvent.click(screen.getByText('前置条件'))
    await waitFor(() => {
      expect(fetchPreconditions).toHaveBeenCalledWith()
      expect(screen.getByText('通用讲解者')).toBeInTheDocument()
      expect(screen.getByText('白板绘制手')).toBeInTheDocument()
      expect(screen.getByText(/kind: visual-explainer/)).toBeInTheDocument()
      expect(screen.getByText(/kind: renderer-hand/)).toBeInTheDocument()
      expect(screen.getByText(/applies_to: storyboard, illustration/)).toBeInTheDocument()
      expect(screen.getByText('不覆盖 Style revision 内的人物约束。')).toBeInTheDocument()
      expect(screen.getByText(/Task 选择将在后续冻结契约中提供/)).toBeInTheDocument()
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    })
  })

  it('shows precondition API and preview-image failure states', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchPreconditions).mockResolvedValue({
      items: [{
        precondition_id: 'precondition-explainer', revision: 1, name: '通用讲解者', kind: 'visual-explainer',
        applies_to: ['illustration'], status: 'active', enabled: true,
        engine_compatibility: ['whiteboard'], preview_asset_id: 'broken-preview',
        description: '说明', condition_text: '条件',
      }], next_cursor: null, total: 1,
    })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    await userEvent.click(screen.getByText('前置条件'))
    await waitFor(() => expect(screen.getByAltText('通用讲解者')).toBeInTheDocument())
    const image = screen.getByAltText('通用讲解者')
    act(() => image.dispatchEvent(new Event('error')))
    await waitFor(() => expect(screen.getByText('预览图片读取失败')).toBeInTheDocument())

    vi.mocked(fetchPreconditions).mockRejectedValueOnce(new Error('目录读取失败'))
    await userEvent.click(screen.getByText('预置风格'))
    await userEvent.click(screen.getByText('前置条件'))
    await waitFor(() => expect(screen.getByText('目录读取失败')).toBeInTheDocument())
  })

  it('loads and displays preset styles', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles, next_cursor: null, total: 2 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument()
      expect(screen.getAllByText('油画风')[0]).toBeInTheDocument()
    })
  })

  it('shows loading state', async () => {
    vi.mocked(fetchStyles).mockImplementation(() => new Promise(() => {}))
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.mocked(fetchStyles).mockRejectedValue(new Error('Network error'))
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no items', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('暂无数据')).toBeInTheDocument()
    })
  })

  it('selects an item and shows detail', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles, next_cursor: null, total: 2 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('水彩风')[0])

    await waitFor(() => {
      // Description appears in both list and detail
      const matches = screen.getAllByText('水彩画风格')
      expect(matches.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('shows only edit and delete controls for custom styles', async () => {
    const customStyles = [{ ...mockStyles[1], kind: 'custom' as const, status: 'inactive' as const }]
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: customStyles, next_cursor: null, total: 1 })

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    // Switch to custom tab
    await userEvent.click(screen.getByText('自定义风格'))

    await waitFor(() => {
      expect(screen.getAllByText('油画风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('油画风')[0])

    const detail = document.querySelector('.am-detail') as HTMLElement
    expect(within(detail).getByRole('button', { name: '编辑' })).toBeInTheDocument()
    expect(within(detail).getByRole('button', { name: '删除' })).toBeInTheDocument()
    expect(within(detail).queryByRole('button', { name: '启用' })).not.toBeInTheDocument()
    expect(within(detail).queryByRole('button', { name: '停用' })).not.toBeInTheDocument()
    expect(within(detail).queryByText('复制为自定义')).not.toBeInTheDocument()
  })

  it('edits and saves a custom style inline without opening a dialog', async () => {
    const customStyles = [{ ...mockStyles[0], kind: 'custom' as const }]
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchStyles).mockResolvedValue({ items: customStyles, next_cursor: null, total: 1 })
    vi.mocked(updateStyle).mockResolvedValue({ ...customStyles[0], name: '自定义水彩新版', revision: 2 })

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    // Switch to custom tab
    await userEvent.click(screen.getByText('自定义风格'))

    await waitFor(() => {
      expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('水彩风')[0])

    const detail = document.querySelector('.am-detail') as HTMLElement
    await userEvent.click(within(detail).getByRole('button', { name: '编辑' }))
    expect(within(detail).getByText('编辑自定义风格')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    const name = within(detail).getByLabelText('风格名称')
    await userEvent.clear(name)
    await userEvent.type(name, '自定义水彩新版')
    await userEvent.click(within(detail).getByRole('button', { name: '保存' }))

    await waitFor(() => expect(updateStyle).toHaveBeenCalledWith('s1', expect.objectContaining({
      name: '自定义水彩新版', expected_revision: 1,
    })))
  })

  it('creates preset styles through the real API contract and keeps failures explicit', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(createStyle).mockRejectedValue(new Error('预置写入接口尚未就绪'))
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await userEvent.click(screen.getByRole('button', { name: '+ 新建预置风格' }))
    expect(screen.getByRole('heading', { name: '新建预置风格' })).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('名称 *'), '新的预置风格')
    await userEvent.click(screen.getByRole('button', { name: '创建' }))

    await waitFor(() => {
      expect(createStyle).toHaveBeenCalledWith(expect.objectContaining({ kind: 'preset', name: '新的预置风格' }))
      expect(screen.getByRole('alert')).toHaveTextContent('预置写入接口尚未就绪')
      expect(screen.getByRole('heading', { name: '新建预置风格' })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(screen.queryByRole('heading', { name: '新建预置风格' })).not.toBeInTheDocument()
  })

  it('edits and saves preset styles with optimistic revision protection', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: [mockStyles[0]], next_cursor: null, total: 1 })
    vi.mocked(updateStyle).mockResolvedValue({ ...mockStyles[0], name: '水彩风新版', revision: 2 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    await waitFor(() => expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument())
    await userEvent.click(screen.getAllByText('水彩风')[0])
    await userEvent.click(screen.getByRole('button', { name: '编辑' }))
    const detail = document.querySelector('.am-detail') as HTMLElement
    expect(within(detail).getByText('编辑预置风格')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    const name = within(detail).getByLabelText('风格名称')
    await userEvent.clear(name)
    await userEvent.type(name, '水彩风新版')
    await userEvent.click(within(detail).getByRole('button', { name: '保存' }))

    await waitFor(() => expect(updateStyle).toHaveBeenCalledWith('s1', expect.objectContaining({
      name: '水彩风新版',
      expected_revision: 1,
    })))
  })

  it('keeps character groups and references inside the selected style revision', async () => {
    const customStyle = {
      ...mockStyles[0], kind: 'custom' as const, preview_asset_id: 'style-preview',
      characters: [{ character_id: 'character-1', name: '讲解者', description: '圆润粗线、固定红色围巾', reference_asset_ids: ['character-preview'] }],
    }
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [customStyle], next_cursor: null, total: 1 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })
    await userEvent.click(screen.getByText('自定义风格'))
    await waitFor(() => expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument())
    await userEvent.click(screen.getAllByText('水彩风')[0])
    await waitFor(() => {
      expect(screen.getByText('圆润粗线、固定红色围巾')).toBeInTheDocument()
      expect(screen.getByText('讲解者')).toBeInTheDocument()
      expect(document.querySelectorAll('.am-preview-img').length).toBeGreaterThanOrEqual(2)
    })
  })

  it('keeps each tab action in its left asset list and shows an empty real character group', async () => {
    const customWithoutCharacters = { ...mockStyles[0], kind: 'custom' as const, characters: [] }
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [customWithoutCharacters], next_cursor: null, total: 1 })
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>
      )
    })
    await userEvent.click(screen.getByText('自定义风格'))
    await waitFor(() => expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument())
    expect(document.querySelector('.am-list-head')?.textContent).toContain('新建自定义风格')
    await userEvent.click(screen.getAllByText('水彩风')[0])
    await waitFor(() => {
      expect(document.querySelector('.am-detail')?.textContent).toContain('此 Style revision 暂无人')
    })
  })

  it('search input triggers fetch with query', async () => {
    vi.mocked(fetchStyles).mockResolvedValue({ items: mockStyles, next_cursor: null, total: 2 })

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('水彩风')[0]).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('搜索资产…')
    await userEvent.type(searchInput, '水彩')

    await waitFor(() => {
      expect(fetchStyles).toHaveBeenCalledWith(expect.objectContaining({ q: '水彩' }))
    })
  })
})
