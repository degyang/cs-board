/* ==========================================================================
   Preset Style Browser — Behavior Tests (§3I)

   Covers:
   - Preset list renders thumbnails, description, tags from real DTO
   - Blob URL uses encoded preview_asset_id
   - Preview empty and onError placeholder behavior
   - Detail shows complete prompt/negative prompt and only edit/delete actions
   - Editing happens inline with save, cancel, and pending protection
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
  createStyle: vi.fn(),
  updateStyle: vi.fn(),
  deleteStyle: vi.fn(),
  createVoice: vi.fn(),
  updateVoice: vi.fn(),
  deleteVoice: vi.fn(),
  uploadAsset: vi.fn(),
}))

import { fetchStyles, updateStyle, uploadAsset } from '../src/lib/api/assets'

/* ── Fixtures ──────────────────────────────────────────────────────────── */

const presetWithPreview = {
  style_id: 'ps-1',
  kind: 'preset' as const,
  name: '极简粗线简笔白板风',
  description: '粗黑线 · 少量配色 · 清爽留白',
  engine: 'whiteboard',
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

const routedPreset = {
  ...presetWithPreview,
  style_id: 'ps-routed',
  name: '纸感隐喻拼贴风',
  config: {
    reference_routing: {
      enabled: true as const,
      match_mode: 'first' as const,
      rules: [{ rule_id: 'route-process', name: '流程', keywords: ['流程', '系统', '自动化'], reference_asset_ids: ['route-image-1'], order: 1 }],
    },
  },
}

/** Live oil-visual fixture with 5 routing rules (matches real 5182 data). */
const oilVisualPreset = {
  ...presetWithPreview,
  style_id: 'ps-cs-10',
  name: '漫画墨线解释风',
  description: '漫画 · 墨线 · 半调 · 机制',
  tags: ['漫画', '墨线', '半调', '机制'],
  preview_asset_id: 'oil-preview-asset',
  config: {
    reference_routing: {
      enabled: true as const,
      match_mode: 'first' as const,
      rules: [
        { rule_id: 'oil-compare', name: '机制对比', keywords: ['对比', '差异', '两种', '成本', '取舍'], reference_asset_ids: ['oil-img-compare'], order: 1 },
        { rule_id: 'oil-cycle', name: '机制循环', keywords: ['循环', '反馈', '闭环'], reference_asset_ids: ['oil-img-cycle'], order: 2 },
        { rule_id: 'oil-process', name: '机制流程', keywords: ['流程', '步骤', '瓶颈', '管线', '机制'], reference_asset_ids: ['oil-img-process'], order: 3 },
        { rule_id: 'oil-character', name: '角色场景', keywords: ['人物', '角色', '讲解者', '陪伴', '团队', '主人公'], reference_asset_ids: ['oil-img-character'], order: 4 },
        { rule_id: 'oil-default', name: '概念解释', keywords: ['概念', '解释', '观点', '其它'], reference_asset_ids: ['oil-img-default'], order: 5 },
      ],
    },
  },
}

/** Live paper-metaphor fixture with 9 routing rules (matches real 5182 data). */
const paperMetaphorPreset = {
  ...presetWithPreview,
  style_id: 'ps-cs-9',
  name: '纸感隐喻拼贴风',
  description: '剪纸 · 隐喻 · 因果 · 矩阵',
  tags: ['剪纸', '隐喻', '因果', '矩阵'],
  preview_asset_id: 'paper-preview-asset',
  config: {
    reference_routing: {
      enabled: true as const,
      match_mode: 'first' as const,
      rules: [
        { rule_id: 'paper-process', name: '流程', keywords: ['流程', '系统', '自动化', '生产', '步骤', '机器', '效率'], reference_asset_ids: ['paper-img-process'], order: 1 },
        { rule_id: 'paper-compare', name: '对比', keywords: ['对比', '选择', '判断', '黑白', '两种', '不是', '而是'], reference_asset_ids: ['paper-img-compare-1', 'paper-img-compare-2'], order: 2 },
        { rule_id: 'paper-cause', name: '因果', keywords: ['因果', '原因', '结果', '影响', '关系'], reference_asset_ids: ['paper-img-cause'], order: 3 },
        { rule_id: 'paper-hierarchy', name: '层级', keywords: ['层级', '成长', '方向', '阶段', '进阶'], reference_asset_ids: ['paper-img-hierarchy'], order: 4 },
        { rule_id: 'paper-list', name: '清单', keywords: ['清单', '资源', '经验', '多个', '要素'], reference_asset_ids: ['paper-img-list'], order: 5 },
        { rule_id: 'paper-matrix', name: '矩阵', keywords: ['矩阵', '四象限', '双维度'], reference_asset_ids: ['paper-img-matrix'], order: 6 },
        { rule_id: 'paper-value', name: '价值权衡', keywords: ['价值', '权衡', '平衡', '责任', '收益'], reference_asset_ids: ['paper-img-value'], order: 7 },
        { rule_id: 'paper-pressure', name: '压力过载', keywords: ['压力', '过载', '诱惑', '信息'], reference_asset_ids: ['paper-img-pressure-1', 'paper-img-pressure-2'], order: 8 },
        { rule_id: 'paper-boundary', name: '边界冲突', keywords: ['边界', '群体', '立场', '冲突'], reference_asset_ids: ['paper-img-boundary'], order: 9 },
      ],
    },
  },
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
    vi.mocked(updateStyle).mockReset()
    vi.mocked(uploadAsset).mockReset()
  })

  // ── List rendering ────────────────────────────────────────────────────

  it('renders preset list with name, description, and tags', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
      // Description in list
      expect(screen.getAllByText('粗黑线 · 少量配色 · 清爽留白')[0]).toBeInTheDocument()
      // Tags in list (first 3)
    expect(screen.getAllByText('白板')[0]).toBeInTheDocument()
    expect(screen.getAllByText('粗线')[0]).toBeInTheDocument()
    expect(screen.getAllByText('马克笔')[0]).toBeInTheDocument()
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
      // Browser DOM properties resolve same-origin relative URLs; inspect the
      // authored attribute so this remains a contract check for the proxy path.
      expect(img.getAttribute('src')).toBe(expectedUrl)
    })
  })

  it('renders placeholder thumbnail when preview_asset_id is null', async () => {
    mockFetchPresets(presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('国风动态信息图')[0]).toBeInTheDocument()
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

  it('shows style detail without binding the asset to an output engine', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await waitFor(() => {
      // Description in detail
      expect(within(detail).getByText('粗黑线 · 少量配色 · 清爽留白')).toBeInTheDocument()
      expect(within(detail).queryByRole('group', { name: '输出引擎' })).not.toBeInTheDocument()
      expect(detail.querySelector('.am-detail-tag')).toBeNull()
      expect(detail.querySelector('.am-preset-meta')).toBeNull()
      // Tags in detail
      expect(within(detail).getByText('知识科普')).toBeInTheDocument()
      // Prompt text
      expect(within(detail).getByText(/暖白色纯净背景/)).toBeInTheDocument()
      // Negative prompt text
      expect(within(detail).getByText(/禁止写实摄影/)).toBeInTheDocument()
    })
  })

  it('renders migrated keyword routes and edits the ordered rule list inline', async () => {
    mockFetchPresets(routedPreset)
    vi.mocked(updateStyle).mockResolvedValue({ ...routedPreset, revision: 2 })
    vi.mocked(uploadAsset).mockResolvedValue({ asset_id: 'route-image-2' } as never)
    await act(async () => { render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>) })
    await waitFor(() => expect(screen.getAllByText('纸感隐喻拼贴风')[0]).toBeInTheDocument())
    await userEvent.click(screen.getAllByText('纸感隐喻拼贴风')[0])
    const detail = getDetailPanel()
    expect(within(detail).getByRole('region', { name: '参考图路由规则' })).toHaveTextContent('流程系统自动化')
    expect(within(detail).getByAltText('流程参考图 1')).toHaveAttribute('src', expect.stringContaining('route-image-1'))
    await userEvent.click(within(detail).getByRole('button', { name: '编辑' }))
    const addedImage = new File([new Uint8Array([137, 80, 78, 71])], 'route.png', { type: 'image/png' })
    await userEvent.upload(within(detail).getByLabelText('为流程添加参考图片'), addedImage)
    await waitFor(() => expect(uploadAsset).toHaveBeenCalledWith(addedImage))
    expect(within(detail).getByAltText('流程参考图 2')).toHaveAttribute('src', expect.stringContaining('route-image-2'))
    await userEvent.click(within(detail).getByRole('button', { name: '＋ 添加规则' }))
    expect(within(detail).getByLabelText('规则 2 名称')).toHaveValue('新规则')
    await userEvent.click(within(detail).getAllByRole('button', { name: '删除规则' })[1])
    await userEvent.click(within(detail).getByRole('button', { name: '保存' }))
    await waitFor(() => expect(updateStyle).toHaveBeenCalledWith('ps-routed', expect.objectContaining({
      config: expect.objectContaining({ reference_routing: expect.objectContaining({ enabled: true, match_mode: 'first', rules: [expect.objectContaining({ name: '流程', keywords: ['流程', '系统', '自动化'], reference_asset_ids: ['route-image-1', 'route-image-2'] })] }) }),
    })))
  })

  it('shows only edit and delete controls for presets', async () => {
    mockFetchPresets(presetWithPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('编辑')).toBeInTheDocument()
      expect(within(detail).getByText('删除')).toBeInTheDocument()
      expect(within(detail).queryByText('复制为自定义')).not.toBeInTheDocument()
      expect(within(detail).queryByRole('button', { name: '停用' })).not.toBeInTheDocument()
      expect(within(detail).queryByRole('button', { name: '启用' })).not.toBeInTheDocument()
    })
  })

  // ── Preview image error placeholder ───────────────────────────────────

  it('shows placeholder in detail when preview_asset_id is null', async () => {
    mockFetchPresets(presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('国风动态信息图')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('国风动态信息图')[0])

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
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

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
    expect(within(detail).getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
  })

  // ── Inline editing ────────────────────────────────────────────────────

  it('edits a preset inline and saves through the optimistic revision contract', async () => {
    mockFetchPresets(presetWithPreview)
    vi.mocked(updateStyle).mockResolvedValue({ ...presetWithPreview, name: '极简白板风新版', revision: 2 })

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await userEvent.click(within(detail).getByRole('button', { name: '编辑' }))
    expect(within(detail).getByText('编辑预置风格')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    const name = within(detail).getByLabelText('风格名称')
    await userEvent.clear(name)
    await userEvent.type(name, '极简白板风新版')
    await userEvent.click(within(detail).getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(updateStyle).toHaveBeenCalledWith('ps-1', expect.objectContaining({
        name: '极简白板风新版',
        expected_revision: 1,
      }))
    })
  })

  it('cancels inline preset edits without calling the API', async () => {
    mockFetchPresets(presetWithPreview)

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await userEvent.click(within(detail).getByRole('button', { name: '编辑' }))
    const name = within(detail).getByLabelText('风格名称')
    await userEvent.clear(name)
    await userEvent.type(name, '不应保存')
    await userEvent.click(within(detail).getByRole('button', { name: '取消' }))

    expect(updateStyle).not.toHaveBeenCalled()
    expect(within(detail).getAllByText('极简粗线简笔白板风').length).toBeGreaterThan(0)
    expect(within(detail).queryByLabelText('风格名称')).not.toBeInTheDocument()
  })

  // ── Fast switch race condition ────────────────────────────────────────

  it('shows correct detail when quickly switching between two presets', async () => {
    mockFetchPresets(presetWithPreview, presetWithoutPreview)
    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
      expect(screen.getAllByText('国风动态信息图')[0]).toBeInTheDocument()
    })

    // Click first preset
    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    // Immediately click second preset (fast switch)
    await userEvent.click(screen.getAllByText('国风动态信息图')[0])

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
      expect(screen.getAllByText('国风动态信息图')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('国风动态信息图')[0])

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
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await waitFor(() => {
      expect(within(detail).getByText('编辑')).toBeInTheDocument()
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
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await waitFor(() => {
      // All 4 tags present in detail
      expect(within(detail).getByText('白板')).toBeInTheDocument()
      expect(within(detail).getByText('粗线')).toBeInTheDocument()
      expect(within(detail).getByText('马克笔')).toBeInTheDocument()
      expect(within(detail).getByText('知识科普')).toBeInTheDocument()
    })
  })

  // ── Save button disabled while submitting ─────────────────────────────

  it('disables inline save and cancel while the update request is in flight', async () => {
    mockFetchPresets(presetWithPreview)
    vi.mocked(updateStyle).mockImplementation(() => new Promise(() => {}))

    await act(async () => {
      render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>)
    })

    await waitFor(() => {
      expect(screen.getAllByText('极简粗线简笔白板风')[0]).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByText('极简粗线简笔白板风')[0])

    const detail = getDetailPanel()
    await userEvent.click(within(detail).getByRole('button', { name: '编辑' }))
    await userEvent.click(within(detail).getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(within(detail).getByRole('button', { name: '保存中...' })).toBeDisabled()
      expect(within(detail).getByRole('button', { name: '取消' })).toBeDisabled()
    })
  })

  // ── Custom and voice tabs still work (regression) ────────────────────

  // ── Oil-visual routing: 5 rules display and sync on style switch ───────

  it('displays all 5 oil-visual routing rules with keyword tags and images', async () => {
    mockFetchPresets(oilVisualPreset)
    await act(async () => { render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>) })
    await waitFor(() => expect(screen.getAllByText('漫画墨线解释风')[0]).toBeInTheDocument())
    await userEvent.click(screen.getAllByText('漫画墨线解释风')[0])
    const detail = getDetailPanel()
    const routing = within(detail).getByRole('region', { name: '参考图路由规则' })
    // All 5 rule names
    expect(within(routing).getByText('机制对比')).toBeInTheDocument()
    expect(within(routing).getByText('机制循环')).toBeInTheDocument()
    expect(within(routing).getByText('机制流程')).toBeInTheDocument()
    expect(within(routing).getByText('角色场景')).toBeInTheDocument()
    expect(within(routing).getByText('概念解释')).toBeInTheDocument()
    // Sample keywords
    expect(within(routing).getByText('对比')).toBeInTheDocument()
    expect(within(routing).getByText('循环')).toBeInTheDocument()
    expect(within(routing).getByText('流程')).toBeInTheDocument()
    expect(within(routing).getByText('人物')).toBeInTheDocument()
    expect(within(routing).getByText('概念')).toBeInTheDocument()
    // 5 reference images
    expect(within(routing).getByAltText('机制对比参考图 1')).toHaveAttribute('src', expect.stringContaining('oil-img-compare'))
    expect(within(routing).getByAltText('机制循环参考图 1')).toHaveAttribute('src', expect.stringContaining('oil-img-cycle'))
    expect(within(routing).getByAltText('机制流程参考图 1')).toHaveAttribute('src', expect.stringContaining('oil-img-process'))
    expect(within(routing).getByAltText('角色场景参考图 1')).toHaveAttribute('src', expect.stringContaining('oil-img-character'))
    expect(within(routing).getByAltText('概念解释参考图 1')).toHaveAttribute('src', expect.stringContaining('oil-img-default'))
  })

  it('syncs rule list when switching from paper-metaphor to oil-visual', async () => {
    mockFetchPresets(paperMetaphorPreset, oilVisualPreset)
    await act(async () => { render(<MemoryRouter future={ROUTER_FUTURE}><AssetManagementPage /></MemoryRouter>) })
    await waitFor(() => {
      expect(screen.getAllByText('纸感隐喻拼贴风')[0]).toBeInTheDocument()
      expect(screen.getAllByText('漫画墨线解释风')[0]).toBeInTheDocument()
    })

    // Select paper-metaphor — shows 9 rules
    await userEvent.click(screen.getAllByText('纸感隐喻拼贴风')[0])
    const detail = getDetailPanel()
    await waitFor(() => {
      // "流程" appears as both rule name and keyword tag
      expect(within(detail).getAllByText('流程').length).toBeGreaterThanOrEqual(2)
      expect(within(detail).getByText('边界冲突')).toBeInTheDocument()
    })

    // Switch to oil-visual — rule list must sync to 5 rules
    await userEvent.click(screen.getAllByText('漫画墨线解释风')[0])
    await waitFor(() => {
      // Oil-visual rules present
      expect(within(detail).getByText('机制对比')).toBeInTheDocument()
      expect(within(detail).getByText('概念解释')).toBeInTheDocument()
      // Paper-metaphor-specific rules gone
      expect(within(detail).queryByText('边界冲突')).not.toBeInTheDocument()
      expect(within(detail).queryByText('压力过载')).not.toBeInTheDocument()
      expect(within(detail).queryByText('矩阵')).not.toBeInTheDocument()
    })
  })

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
      expect(screen.getAllByText('我的科普风')[0]).toBeInTheDocument()
    })

    // Click the custom style
    await userEvent.click(screen.getAllByText('我的科普风')[0])

    // Detail uses the same edit/delete-only contract as preset styles.
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
      expect(screen.getByText('删除')).toBeInTheDocument()
      expect(screen.queryByText('复制为自定义')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '停用' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '启用' })).not.toBeInTheDocument()
    })
  })
})
