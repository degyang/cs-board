/* ==========================================================================
   Preset Style Browser — Behavior Tests (§3I)

   Covers:
   - Preset list renders thumbnails, description, tags from real DTO
   - Blob URL uses encoded preview_asset_id
   - Preview empty and onError placeholder behavior
   - Detail shows complete prompt/negative prompt, copy button, no edit/delete
   - Copy API success → feedback + custom tab switch
   - Copy failure → stays on preset, shows error
   - Fast switch between presets → final detail matches last selection
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AssetManagementPage } from '../src/pages/AssetManagementPage'
import { getAssetBlobUrl } from '../src/lib/api/http'

const ROUTER_FUTURE = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}

vi.mock('../src/lib/api/assets', () => ({
  fetchStyles: vi.fn(),
  fetchVoices: vi.fn(),
  activateStyle: vi.fn(),
  deactivateStyle: vi.fn(),
  copyStyle: vi.fn(),
  activateVoice: vi.fn(),
  deactivateVoice: vi.fn(),
  createStyle: vi.fn(),
  updateStyle: vi.fn(),
  deleteStyle: vi.fn(),
  createVoice: vi.fn(),
  updateVoice: vi.fn(),
  deleteVoice: vi.fn(),
  uploadAsset: vi.fn(),
}))

import {
  fetchStyles, copyStyle,
} from '../src/lib/api/assets'

/* ── Fixtures ──────────────────────────────────────────────────────────── */

const presetWithPreview = {
  style_id: 'ps-1',
  kind: 'preset' as const,
  name: '极简粗线简笔白板风',
  description: '粗黑线 · 少量配色 · 清爽留白',
  engine: 'sdxl',
  status: 'active' as const,
  revision: 1,
  tags: ['白板', '粗线', '马克笔', '知识科普'],
  prompt_text: '暖白色纯净背景，圆润有亲和力的粗黑马克笔轮廓，人物和物体高度概括。',
  negative_prompt: '禁止写实摄影、3D 渲染、光滑渐变。',
  preview_asset_id: 'abc123def456',
  config: {},
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

const presetWithoutPreview = {
  style_id: 'ps-2',
  kind: 'preset' as const,
  name: '国风动态信息图',
  description: '暖米宣纸 · 朱红重点 · 国风淡彩',
  engine: null,
  status: 'active' as const,
  revision: 1,
  tags: ['国风', '信息图', '淡彩'],
  prompt_text: '暖米白宣纸背景，深灰正文与朱红重点。',
  negative_prompt: null,
  preview_asset_id: null,
  config: {},
  created_at: '2025-01-02T00:00:00Z',
  updated_at: '2025-01-02T00:00:00Z',
}

function mockFetchPresets(...presets: typeof presetWithPreview[]) {
  vi.mocked(fetchStyles).mockResolvedValue({
    items: presets,
    next_cursor: null,
    total: presets.length,
  })
}

/** Find the detail panel (am-detail) for scoped queries */
function getDetailPanel(): HTMLElement {
  return document.querySelector('.am-detail') as HTMLElement
}

/* ── Tests ─────────────────────────────────────────────────────────────── */

describe('Preset Style Browser', () => {
  beforeEach(() => {
    vi.mocked(fetchStyles).mockReset()
    vi.mocked(copyStyle).mockReset()
  })

  // ── List rendering ────────────────────────────────────────────────────

  it('renders preset list with name, description, and tags', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
      // Description in list
      expect(screen.getByText('粗黑线 · 少量配色 · 清爽留白')).toBeInTheDocument()
      // Tags in list (first 3)
      expect(screen.getByText('白板')).toBeInTheDocument()
      expect(screen.getByText('粗线')).toBeInTheDocument()
      expect(screen.getByText('马克笔')).toBeInTheDocument()
    })
  })

  it('renders preview thumbnail in list when preview_asset_id is set', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      const img = document.querySelector('.am-list-thumb-img') as HTMLImageElement
      expect(img).not.toBeNull()
      const expectedUrl = getAssetBlobUrl('abc123def456')
      expect(img.src).toBe(expectedUrl)
    })
  })

  it('renders placeholder thumbnail when preview_asset_id is null', async () => {
    mockFetchPresets(presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('国风动态信息图')).toBeInTheDocument()
      // No img element in list
      const imgs = document.querySelectorAll('.am-list-thumb-img')
      expect(imgs.length).toBe(0)
      // Placeholder present
      const placeholders = document.querySelectorAll('.am-list-thumb-placeholder')
      expect(placeholders.length).toBe(1)
    })
  })

  // ── Blob URL encoding ─────────────────────────────────────────────────

  it('builds blob URL with properly encoded asset ID', () => {
    const url = getAssetBlobUrl('id/with?special&chars')
    expect(url).toContain('/assets/blobs/')
    expect(url).toContain(encodeURIComponent('id/with?special&chars'))
    // Should NOT contain raw special chars in path segment
    expect(url).not.toMatch(/\/assets\/blobs\/id\//)
  })

  // ── Detail view ───────────────────────────────────────────────────────

  it('shows detail with description, engine badge, tags, and full prompt', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      // Description in detail
      expect(within(detail).getByText('粗黑线 · 少量配色 · 清爽留白')).toBeInTheDocument()
      // Engine badge
      expect(within(detail).getByText('sdxl')).toBeInTheDocument()
      // Kind badge
      expect(within(detail).getByText('预置风格')).toBeInTheDocument()
      // Tags in detail
      expect(within(detail).getByText('知识科普')).toBeInTheDocument()
      // Prompt text
      expect(within(detail).getByText(/暖白色纯净背景/)).toBeInTheDocument()
      // Negative prompt text
      expect(within(detail).getByText(/禁止写实摄影/)).toBeInTheDocument()
    })
  })

  it('shows copy button but no edit/delete/activate/deactivate for presets', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('复制为自定义')).toBeInTheDocument()
      expect(within(detail).queryByText('编辑')).not.toBeInTheDocument()
      expect(within(detail).queryByText('删除')).not.toBeInTheDocument()
      expect(within(detail).queryByText('启用')).not.toBeInTheDocument()
      expect(within(detail).queryByText('停用')).not.toBeInTheDocument()
    })
  })

  // ── Preview image error placeholder ───────────────────────────────────

  it('shows placeholder in detail when preview_asset_id is null', async () => {
    mockFetchPresets(presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('国风动态信息图')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('国风动态信息图'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('暂无预览图')).toBeInTheDocument()
    })
  })

  it('shows placeholder when preview image fires onError', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    // Find the preview image in the detail and trigger error
    await waitFor(() => {
      const previewImg = detail.querySelector('.am-preview-img') as HTMLImageElement
      expect(previewImg).not.toBeNull()
      act(() => {
        previewImg.dispatchEvent(new Event('error'))
      })
    })

    // Should show placeholder after error
    await waitFor(() => {
      expect(within(detail).getByText('暂无预览图')).toBeInTheDocument()
    })
    // Page doesn't crash — detail still shows content
    expect(within(detail).getByText('极简粗线简笔白板风')).toBeInTheDocument()
  })

  // ── Copy as custom ────────────────────────────────────────────────────

  it('copies preset to custom and switches to custom tab', async () => {
    const copiedStyle = {
      ...presetWithPreview,
      style_id: 'custom-1',
      kind: 'custom' as const,
      name: '极简粗线简笔白板风 (副本)',
    }
    mockFetchPresets(presetWithPreview)
    vi.mocked(copyStyle).mockResolvedValue(copiedStyle)

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('复制为自定义')).toBeInTheDocument()
    })

    await userEvent.click(within(detail).getByText('复制为自定义'))

    await waitFor(() => {
      // Copy API called with correct ID
      expect(copyStyle).toHaveBeenCalledWith('ps-1')
      // Tab switched to custom — fetchStyles called with kind='custom'
      expect(fetchStyles).toHaveBeenCalledWith(expect.objectContaining({ kind: 'custom' }))
      // Copied item shown in detail (custom detail view with edit/activate/delete)
      expect(screen.getByText('极简粗线简笔白板风 (副本)')).toBeInTheDocument()
    })
  })

  it('shows error and stays on preset tab when copy fails', async () => {
    mockFetchPresets(presetWithPreview)
    vi.mocked(copyStyle).mockRejectedValue(new Error('服务器内部错误'))

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('复制为自定义')).toBeInTheDocument()
    })

    await userEvent.click(within(detail).getByText('复制为自定义'))

    await waitFor(() => {
      // Error message shown
      expect(screen.getByRole('alert')).toHaveTextContent('服务器内部错误')
      // Preset still visible in list and detail (not navigated away)
      const matches = screen.getAllByText('极简粗线简笔白板风')
      expect(matches.length).toBeGreaterThanOrEqual(2) // list + detail
      // Copy button still present (not switched to custom tab)
      expect(screen.getByText('复制为自定义')).toBeInTheDocument()
    })
  })

  // ── Fast switch race condition ────────────────────────────────────────

  it('shows correct detail when quickly switching between two presets', async () => {
    mockFetchPresets(presetWithPreview, presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
      expect(screen.getByText('国风动态信息图')).toBeInTheDocument()
    })

    // Click first preset
    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    // Immediately click second preset (fast switch)
    await userEvent.click(screen.getByText('国风动态信息图'))

    const detail = getDetailPanel()
    // Detail should show the second preset's content
    await waitFor(() => {
      expect(within(detail).getByText('暖米宣纸 · 朱红重点 · 国风淡彩')).toBeInTheDocument()
      expect(within(detail).getByText(/暖米白宣纸背景/)).toBeInTheDocument()
    })

    // Should NOT show first preset's description in detail
    expect(within(detail).queryByText('粗黑线 · 少量配色 · 清爽留白')).not.toBeInTheDocument()
  })

  // ── No negative prompt when null ──────────────────────────────────────

  it('does not show negative prompt section when negative_prompt is null', async () => {
    mockFetchPresets(presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('国风动态信息图')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('国风动态信息图'))

    const detail = getDetailPanel()
    await waitFor(() => {
      // Prompt section exists
      expect(within(detail).getByText('提示词')).toBeInTheDocument()
      // No negative prompt
      expect(within(detail).queryByText('反向提示词')).not.toBeInTheDocument()
    })
  })

  it('does not show prompt section when prompt_text is null', async () => {
    const presetNoPrompt = { ...presetWithPreview, prompt_text: null, preview_asset_id: null }
    mockFetchPresets(presetNoPrompt)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('复制为自定义')).toBeInTheDocument()
      expect(within(detail).queryByText('提示词')).not.toBeInTheDocument()
    })
  })

  // ── Tags truncation in list ───────────────────────────────────────────

  it('shows at most 3 tags in list with +N indicator', async () => {
    mockFetchPresets(presetWithPreview) // 4 tags
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      // List item tags container
      const listItem = document.querySelector('.am-list-item')!
      const listTags = listItem.querySelectorAll('.am-tag-sm')
      // 3 visible tags + 1 "+1" indicator
      expect(listTags.length).toBe(4)
      expect(listTags[0].textContent).toBe('白板')
      expect(listTags[1].textContent).toBe('粗线')
      expect(listTags[2].textContent).toBe('马克笔')
      expect(listTags[3].textContent).toBe('+1')
    })
  })

  // ── Detail shows ALL tags ─────────────────────────────────────────────

  it('shows all tags in detail view', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      // All 4 tags present in detail
      expect(within(detail).getByText('白板')).toBeInTheDocument()
      expect(within(detail).getByText('粗线')).toBeInTheDocument()
      expect(within(detail).getByText('马克笔')).toBeInTheDocument()
      expect(within(detail).getByText('知识科普')).toBeInTheDocument()
    })
  })

  // ── Copy button disabled while submitting ─────────────────────────────

  it('disables copy button while request is in flight', async () => {
    mockFetchPresets(presetWithPreview)
    vi.mocked(copyStyle).mockImplementation(() => new Promise(() => {})) // Never resolves

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getByText('极简粗线简笔白板风')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('极简粗线简笔白板风'))

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('复制为自定义')).toBeInTheDocument()
    })

    await userEvent.click(within(detail).getByText('复制为自定义'))

    await waitFor(() => {
      expect(within(detail).getByText('复制中...')).toBeInTheDocument()
    })
  })

  // ── Custom and voice tabs still work (regression) ────────────────────

  it('custom tab still loads custom styles (regression)', async () => {
    const customStyles = [{
      ...presetWithPreview,
      style_id: 'cs-1',
      kind: 'custom' as const,
      name: '我的科普风',
      prompt_text: null,
      negative_prompt: null,
      preview_asset_id: null,
      tags: ['科普'],
    }]
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchStyles).mockResolvedValueOnce({ items: customStyles, next_cursor: null, total: 1 })

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await userEvent.click(screen.getByText('自定义风格'))

    await waitFor(() => {
      expect(screen.getByText('我的科普风')).toBeInTheDocument()
    })

    // Click the custom style
    await userEvent.click(screen.getByText('我的科普风'))

    // Detail should show edit/activate/delete buttons (not copy)
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
      expect(screen.queryByText('复制为自定义')).not.toBeInTheDocument()
    })
  })
})
