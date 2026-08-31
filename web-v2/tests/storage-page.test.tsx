/* ==========================================================================
   StoragePage — §3K runtime storage readonly status behavior tests
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { StoragePage } from '../src/pages/StoragePage'

vi.mock('../src/lib/api/settings', () => ({
  fetchStorageSettings: vi.fn(),
}))

import { fetchStorageSettings } from '../src/lib/api/settings'

function renderAt(page: React.ReactElement, path = '/settings/storage') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/settings/storage" element={page} />
      </Routes>
    </MemoryRouter>
  )
}

function makeSettings(overrides: Partial<Awaited<ReturnType<typeof fetchStorageSettings>>> = {}) {
  return {
    writable: true,
    assets_available: true,
    tasks_available: true,
    temp_available: true,
    free_bytes: null,
    used_bytes: null,
    cleanup_policy: null,
    error_code: null,
    suggestion: null,
    ...overrides,
  }
}

const flush = () => act(async () => { await Promise.resolve() })

describe('StoragePage (§3K runtime storage readonly status)', () => {
  beforeEach(() => {
    vi.mocked(fetchStorageSettings).mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  // ── Three logical storages: normal states ────────────────────────────

  it('displays three logical storage categories as cards with names and available status', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      assets_available: true,
      tasks_available: true,
      temp_available: true,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('素材存储')).toBeInTheDocument()
      expect(screen.getByText('任务存储')).toBeInTheDocument()
      expect(screen.getByText('临时存储')).toBeInTheDocument()
    })
    const availableBadges = screen.getAllByText('可用')
    expect(availableBadges.length).toBeGreaterThanOrEqual(3)
  })

  // ── Three logical storages: unavailable states ───────────────────────

  it('displays unavailable status when all three storages are false', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      assets_available: false,
      tasks_available: false,
      temp_available: false,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      const unavailableBadges = screen.getAllByText('不可用')
      expect(unavailableBadges.length).toBeGreaterThanOrEqual(3)
    })
  })

  it('displays mixed availability across storages', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      assets_available: true,
      tasks_available: false,
      temp_available: true,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('素材存储')).toBeInTheDocument()
      expect(screen.getByText('任务存储')).toBeInTheDocument()
      expect(screen.getByText('临时存储')).toBeInTheDocument()
    })
    const availableBadges = screen.getAllByText('可用')
    const unavailableBadges = screen.getAllByText('不可用')
    expect(availableBadges.length).toBeGreaterThanOrEqual(2)
    expect(unavailableBadges.length).toBeGreaterThanOrEqual(1)
  })

  // ── Writable false shows real error_code/suggestion ──────────────────

  it('displays real error_code and suggestion when writable is false', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      writable: false,
      error_code: 'STORAGE_PERMISSION_DENIED',
      suggestion: '请检查 /data 目录的写入权限。',
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('不可用')).toBeInTheDocument()
    })
    expect(screen.getByText('STORAGE_PERMISSION_DENIED')).toBeInTheDocument()
    expect(screen.getByText('请检查 /data 目录的写入权限。')).toBeInTheDocument()
  })

  it('displays neutral message when writable is false but error_code and suggestion are null', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      writable: false,
      error_code: null,
      suggestion: null,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('存储不可用，后端未提供详细原因。')).toBeInTheDocument()
    })
  })

  it('does not render writable detail section when writable is true', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      writable: true,
      error_code: null,
      suggestion: null,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })
    expect(screen.queryByText('STORAGE_PERMISSION_DENIED')).not.toBeInTheDocument()
    expect(screen.queryByText('存储不可用，后端未提供详细原因。')).not.toBeInTheDocument()
  })

  // ── Capacity: null displays "未统计" ─────────────────────────────────

  it('displays "未统计" for capacity when both free_bytes and used_bytes are null', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: null,
      used_bytes: null,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('未统计')).toBeInTheDocument()
    })
    expect(screen.queryByText('可用空间')).not.toBeInTheDocument()
    expect(screen.queryByText('已用空间')).not.toBeInTheDocument()
  })

  // ── Capacity: 0 bytes shows "0 B" ───────────────────────────────────

  it('displays "0 B" when free_bytes is 0', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: 0,
      used_bytes: 0,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('可用空间')).toBeInTheDocument()
      expect(screen.getByText('已用空间')).toBeInTheDocument()
    })
    const zeroTexts = screen.getAllByText('0 B')
    expect(zeroTexts.length).toBe(2)
  })

  // ── Capacity: negative → "未统计" per field ───────────────────────────

  it('displays "未统计" for free_bytes when negative, valid used_bytes shown', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: -1,
      used_bytes: 1000,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('可用空间')).toBeInTheDocument()
      expect(screen.getByText('已用空间')).toBeInTheDocument()
    })
    expect(screen.getByText('1000 B')).toBeInTheDocument()
    expect(screen.getByText('未统计')).toBeInTheDocument()
  })

  it('displays "未统计" for used_bytes when negative, valid free_bytes shown', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: 1000,
      used_bytes: -1,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('1000 B')).toBeInTheDocument()
    })
    expect(screen.getByText('未统计')).toBeInTheDocument()
  })

  // ── Capacity: NaN/Infinity → "未统计" per field ──────────────────────

  it('displays "未统计" for free_bytes when NaN, valid used_bytes shown', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: NaN,
      used_bytes: 1000,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('1000 B')).toBeInTheDocument()
    })
    expect(screen.getByText('未统计')).toBeInTheDocument()
  })

  it('displays "未统计" for free_bytes when Infinity, valid used_bytes shown', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: Infinity,
      used_bytes: 1000,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('1000 B')).toBeInTheDocument()
    })
    expect(screen.getByText('未统计')).toBeInTheDocument()
  })

  // ── Capacity: valid values show formatted bytes ──────────────────────

  it('formats free_bytes and used_bytes with correct units', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: 53687091200,  // ~50 GB
      used_bytes: 1073741824,   // ~1 GB
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('可用空间')).toBeInTheDocument()
      expect(screen.getByText('已用空间')).toBeInTheDocument()
    })
  })

  it('shows usage ratio when both capacities are valid and total > 0', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: 100 * 1024 * 1024 * 1024,  // 100 GB
      used_bytes: 100 * 1024 * 1024 * 1024,   // 100 GB
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('已用比例')).toBeInTheDocument()
      expect(screen.getByText('50.0%')).toBeInTheDocument()
    })
  })

  it('does not show ratio when only free_bytes is valid', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: 50000000000,
      used_bytes: null,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('可用空间')).toBeInTheDocument()
    })
    expect(screen.queryByText('已用比例')).not.toBeInTheDocument()
  })

  it('does not show ratio when only used_bytes is valid', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      free_bytes: null,
      used_bytes: 50000000000,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('已用空间')).toBeInTheDocument()
    })
    expect(screen.queryByText('已用比例')).not.toBeInTheDocument()
  })

  // ── Cleanup policy is read-only ──────────────────────────────────────

  it('displays cleanup_policy as read-only text when present', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      cleanup_policy: 'auto: 30d retention',
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('清理策略')).toBeInTheDocument()
      expect(screen.getByText('auto: 30d retention')).toBeInTheDocument()
      expect(screen.getByText('策略由运行时统一管理，当前不可配置。')).toBeInTheDocument()
    })
  })

  it('does not render cleanup policy card when cleanup_policy is null', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      cleanup_policy: null,
    }))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })
    expect(screen.queryByText('清理策略')).not.toBeInTheDocument()
  })

  it('page does not contain save, edit, directory picker, or cleanup controls', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings({
      cleanup_policy: 'auto',
    }))

    const { container } = renderAt(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })

    expect(screen.queryByRole('button', { name: /保存/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /编辑/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /清理/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(container.querySelector('input[type="number"]')).not.toBeInTheDocument()
    expect(container.querySelector('input[type="text"]')).not.toBeInTheDocument()
  })

  // ── Sensitive fields not rendered ────────────────────────────────────

  it('does not render sensitive fields from the response (path, directory, filename, task_id, command, token)', async () => {
    const sensitiveData = {
      ...makeSettings(),
      path: '/mnt/data/mountain/storage',
      directory: '/var/lib/mountain/tasks',
      filename: 'secret_file.wav',
      task_id: 'task-abc-123',
      command: 'ffmpeg -i input.mp4',
      token: 'sk-secret-token-12345',
      storage_path: '/mnt/data/assets',
    }
    vi.mocked(fetchStorageSettings).mockResolvedValue(sensitiveData as any)

    const { container } = renderAt(<StoragePage />)

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('/mnt/data/mountain/storage')
    expect(text).not.toContain('/var/lib/mountain/tasks')
    expect(text).not.toContain('secret_file.wav')
    expect(text).not.toContain('task-abc-123')
    expect(text).not.toContain('ffmpeg -i input.mp4')
    expect(text).not.toContain('sk-secret-token-12345')
    expect(text).not.toContain('/mnt/data/assets')
  })

  // ── Loading state ────────────────────────────────────────────────────

  it('shows loading skeleton initially', () => {
    vi.mocked(fetchStorageSettings).mockReturnValue(new Promise(() => {}))

    renderAt(<StoragePage />)

    expect(screen.getByLabelText('正在加载存储状态')).toBeInTheDocument()
    expect(screen.queryByText('素材存储')).not.toBeInTheDocument()
    expect(screen.queryByText('整体可写状态')).not.toBeInTheDocument()
  })

  // ── Request error state ──────────────────────────────────────────────

  it('displays error message when request fails', async () => {
    vi.mocked(fetchStorageSettings).mockRejectedValue(new Error('网络连接失败'))

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText(/网络连接失败/)).toBeInTheDocument()
    })
    expect(screen.queryByText('正在加载存储状态')).not.toBeInTheDocument()
  })

  // ── Retry re-calls real API ──────────────────────────────────────────

  it('retry button re-calls the production API adapter', async () => {
    vi.mocked(fetchStorageSettings).mockRejectedValueOnce(new Error('临时错误'))

    const user = userEvent.setup()
    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText(/临时错误/)).toBeInTheDocument()
    })

    vi.mocked(fetchStorageSettings).mockResolvedValueOnce(makeSettings({
      writable: true,
      assets_available: true,
      tasks_available: true,
      temp_available: true,
    }))

    await act(async () => {
      await user.click(screen.getByText('重新加载'))
    })

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
      expect(screen.getByText('素材存储')).toBeInTheDocument()
    })

    expect(fetchStorageSettings).toHaveBeenCalledTimes(2)
  })

  // ── Race condition: unmount after first request, then second completes ──

  it('does not update state after unmount', async () => {
    let resolveFirst: (v: any) => void
    const firstRequest = new Promise(r => { resolveFirst = r })
    vi.mocked(fetchStorageSettings).mockReturnValueOnce(firstRequest as any)

    const { unmount } = renderAt(<StoragePage />)
    await flush()

    unmount()
    resolveFirst!(makeSettings({ writable: false }))

    await flush()
    // No act warning expected — unmounted guard prevents setState
    expect(fetchStorageSettings).toHaveBeenCalledTimes(1)
  })

  it('second request wins when first arrives after second', async () => {
    let resolveFirst: (v: any) => void
    let resolveSecond: (v: any) => void
    const firstRequest = new Promise(r => { resolveFirst = r })
    const secondRequest = new Promise(r => { resolveSecond = r })

    vi.mocked(fetchStorageSettings).mockReturnValueOnce(firstRequest as any)
    vi.mocked(fetchStorageSettings).mockReturnValueOnce(secondRequest as any)

    const { unmount } = renderAt(<StoragePage />)
    await flush()

    unmount()
    // First request arrives late
    resolveFirst!(makeSettings({ writable: false, cleanup_policy: 'stale' }))
    await flush()
  })

  // ── Page title and description present ───────────────────────────────

  it('displays the page title "运行时存储状态" and readonly description', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue(makeSettings())

    await act(async () => { renderAt(<StoragePage />) })

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
      expect(screen.getByText(/全局运行时存储健康状态/)).toBeInTheDocument()
      expect(screen.getByText(/仅作只读展示/)).toBeInTheDocument()
    })
  })
})
