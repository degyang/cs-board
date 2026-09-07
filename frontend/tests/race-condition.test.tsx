/**
 * Race condition behavior tests (§3C.3 item 8)
 *
 * Tests AssetManagementPage stale-request protection:
 * - Request A then B with tab/filter change: B returns first then A → only B shows
 * - Load-more old page can't pollute reset list
 * - Unmount doesn't setState
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AssetManagementPage } from '../src/pages/AssetManagementPage'

const ROUTER_FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true }

// Mock API modules
vi.mock('../src/lib/api/assets', () => ({
  fetchStyles: vi.fn(),
  fetchVoices: vi.fn(),
  createStyle: vi.fn(),
  updateStyle: vi.fn(),
  deleteStyle: vi.fn(),
  activateStyle: vi.fn(),
  deactivateStyle: vi.fn(),
  copyStyle: vi.fn(),
  createVoice: vi.fn(),
  updateVoice: vi.fn(),
  deleteVoice: vi.fn(),
  activateVoice: vi.fn(),
  deactivateVoice: vi.fn(),
  uploadAsset: vi.fn(),
}))

vi.mock('../src/lib/api/http', () => ({
  getVoiceContentUrl: vi.fn((id: string) => `http://test/audio/${id}`),
}))

import { fetchStyles, fetchVoices } from '../src/lib/api/assets'

function renderAssetPage() {
  return render(
    <MemoryRouter future={ROUTER_FUTURE}>
      <Routes>
        <Route path="*" element={<AssetManagementPage />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('race condition: tab/filter change', () => {
  it('when B returns after A due to tab change, only B results display', async () => {
    // Simulate: preset tab request (A) is slow, custom tab request (B) is fast
    let resolveA: (v: unknown) => void
    let resolveB: (v: unknown) => void

    const promiseA = new Promise(r => { resolveA = r })
    const promiseB = new Promise(r => { resolveB = r })

    let callCount = 0
    vi.mocked(fetchStyles).mockImplementation(async () => {
      callCount++
      if (callCount === 1) {
        // First call (preset): slow
        return promiseA.then(() => ({
          items: [{ style_id: 'preset-1', name: 'Preset Style', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }],
          next_cursor: null,
          total: 1,
        }))
      } else {
        // Second call (custom): fast
        return promiseB.then(() => ({
          items: [{ style_id: 'custom-1', name: 'Custom Style', kind: 'custom' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }],
          next_cursor: null,
          total: 1,
        }))
      }
    })

    renderAssetPage()

    // Wait for initial preset load to start
    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(1))

    // Switch to custom tab — triggers new request
    const user = userEvent.setup()
    await user.click(screen.getByText('自定义风格'))

    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(2))

    // B (custom) resolves first
    await act(async () => { resolveB!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // A (preset) resolves after — should be discarded
    await act(async () => { resolveA!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // Only custom results should show (B wins)
    await waitFor(() => {
      expect(screen.getAllByText('Custom Style')[0]).toBeTruthy()
    })
    expect(screen.queryByText('Preset Style')).toBeNull()
  })

  it('stale response from filter change does not overwrite newer results', async () => {
    let resolveFirst: (v: unknown) => void
    let resolveSecond: (v: unknown) => void

    const firstPromise = new Promise(r => { resolveFirst = r })
    const secondPromise = new Promise(r => { resolveSecond = r })

    let callCount = 0
    vi.mocked(fetchStyles).mockImplementation(async () => {
      callCount++
      if (callCount === 1) {
        return firstPromise.then(() => ({
          items: [{ style_id: 'old-1', name: 'Old Result', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }],
          next_cursor: null,
          total: 1,
        }))
      } else {
        return secondPromise.then(() => ({
          items: [{ style_id: 'new-1', name: 'New Result', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }],
          next_cursor: null,
          total: 1,
        }))
      }
    })

    renderAssetPage()

    // Wait for first request to start
    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(1))

    // Change filter — triggers second request
    const user = userEvent.setup()
    const statusSelect = screen.getByLabelText('状态筛选')
    await user.selectOptions(statusSelect, 'active')

    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(2))

    // Second request resolves first (newer)
    await act(async () => { resolveSecond!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // First request resolves after (stale — should be discarded)
    await act(async () => { resolveFirst!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // Only new results should show
    await waitFor(() => {
      expect(screen.getAllByText('New Result')[0]).toBeTruthy()
    })
    expect(screen.queryByText('Old Result')).toBeNull()
  })
})

describe('race condition: load-more vs reset', () => {
  it('load-more old page cannot pollute reset list after filter change', async () => {
    // Scenario: user loads page 1, clicks load more (page 2), then changes filter
    // Page 2 response arrives after reset — should be discarded

    const page1Items = [
      { style_id: 'p1-1', name: 'Page 1 Item', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' },
    ]
    const page2Items = [
      { style_id: 'p2-1', name: 'Page 2 Item', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' },
    ]
    const newItems = [
      { style_id: 'new-1', name: 'Filtered Item', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' },
    ]

    let resolvePage2: (v: unknown) => void
    let resolveFiltered: (v: unknown) => void

    const page2Promise = new Promise(r => { resolvePage2 = r })
    const filteredPromise = new Promise(r => { resolveFiltered = r })

    let callCount = 0
    vi.mocked(fetchStyles).mockImplementation(async (params) => {
      callCount++

      if (callCount === 1) {
        // Initial load — page 1 with cursor
        return { items: page1Items, next_cursor: 'cursor-1', total: 3 }
      }

      if (callCount === 2) {
        // Load more — page 2 (slow)
        return page2Promise.then(() => ({ items: page2Items, next_cursor: null, total: 3 }))
      }

      if (callCount === 3) {
        // Filter change — new results (fast)
        return filteredPromise.then(() => ({ items: newItems, next_cursor: null, total: 1 }))
      }

      return { items: [], next_cursor: null, total: 0 }
    })

    renderAssetPage()

    // Wait for page 1
    await waitFor(() => {
      expect(screen.getAllByText('Page 1 Item')[0]).toBeTruthy()
    })

    // Click load more
    const user = userEvent.setup()
    await user.click(screen.getByText('加载更多'))

    // Change filter before page 2 resolves
    const statusSelect = screen.getByLabelText('状态筛选')
    await user.selectOptions(statusSelect, 'active')

    // Filtered results resolve first
    await act(async () => { resolveFiltered!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // Page 2 resolves after — should be discarded
    await act(async () => { resolvePage2!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // Only filtered results should show, not page 2 items
    await waitFor(() => {
      expect(screen.getAllByText('Filtered Item')[0]).toBeTruthy()
    })
    expect(screen.queryByText('Page 1 Item')).toBeNull()
    expect(screen.queryByText('Page 2 Item')).toBeNull()
  })
})

describe('race condition: unmount safety', () => {
  it('unmount during fetch does not cause setState on unmounted component', async () => {
    let resolveFetch: (v: unknown) => void
    const fetchPromise = new Promise(r => { resolveFetch = r })

    vi.mocked(fetchStyles).mockImplementation(async () => {
      return fetchPromise.then(() => ({
        items: [{ style_id: 'late-1', name: 'Late Item', kind: 'preset' as const, status: 'active' as const, revision: 1, tags: [], engine: null, description: '', prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }],
        next_cursor: null,
        total: 1,
      }))
    })

    // Call-through spy: real console.error still prints to stderr (no
    // suppression), so any genuine warning still surfaces and is caught by
    // the gate's warning scan. We only record calls to assert the unmount
    // scenario stays clean.
    const errorSpy = vi.spyOn(console, 'error')

    const { unmount } = renderAssetPage()

    // Unmount before fetch completes
    unmount()

    // Resolve the fetch — the mounted guard must skip the state update
    await act(async () => { resolveFetch!(undefined) })
    await new Promise(r => setTimeout(r, 50))

    // Real assertion: resolving the fetch after unmount must not emit a
    // state-update-on-unmounted warning or an act violation.
    const leaked = errorSpy.mock.calls.filter(([msg]) =>
      typeof msg === 'string' &&
      /unmounted|can't perform a react state update|not wrapped in act/i.test(msg),
    )
    expect(leaked).toHaveLength(0)
    errorSpy.mockRestore()
  })
})

describe('race condition: request generation token', () => {
  it('rapid tab switching only shows last tab results', async () => {
    const resolves: ((v: unknown) => void)[] = []
    let callIndex = 0

    vi.mocked(fetchStyles).mockImplementation(async () => {
      const idx = callIndex++
      return new Promise(r => {
        resolves[idx] = r
      }).then(() => ({
        items: [{
          style_id: 'item-' + idx,
          name: 'Item ' + idx,
          kind: (idx === 0 ? 'preset' : idx === 1 ? 'custom' : 'preset') as 'preset' | 'custom',
          status: 'active' as const,
          revision: 1,
          tags: [],
          engine: null,
          description: '',
          prompt_text: null,
          negative_prompt: null,
          preview_asset_id: null,
          config: {},
          created_at: '',
          updated_at: '',
        }],
        next_cursor: null,
        total: 1,
      }))
    })

    renderAssetPage()

    const user = userEvent.setup()

    // Wait for initial load
    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(1))

    // Rapid tab switches
    await user.click(screen.getByText('自定义风格'))
    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(2))

    await user.click(screen.getByText('预置风格'))
    await waitFor(() => expect(fetchStyles).toHaveBeenCalledTimes(3))

    // Resolve in reverse order: last call first
    await act(async () => { resolves[2]?.(undefined) })
    await new Promise(r => setTimeout(r, 20))

    await act(async () => { resolves[1]?.(undefined) })
    await new Promise(r => setTimeout(r, 20))

    await act(async () => { resolves[0]?.(undefined) })
    await new Promise(r => setTimeout(r, 20))

    // Only the last tab's (preset, item-2) results should show
    await waitFor(() => {
      expect(screen.getAllByText('Item 2')[0]).toBeTruthy()
    })
    expect(screen.queryByText('Item 0')).toBeNull()
    expect(screen.queryByText('Item 1')).toBeNull()
  })
})
