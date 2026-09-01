/* ==========================================================================
   DiagnosticsPage — §3M system diagnostics summary behavior tests
   ========================================================================== */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DiagnosticsPage } from '../src/pages/DiagnosticsPage'

vi.mock('../src/lib/api/settings', () => ({
  fetchDiagnosticsSettings: vi.fn(),
}))

import { fetchDiagnosticsSettings } from '../src/lib/api/settings'

function renderAt(page: React.ReactElement, path = '/settings/diagnostics') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/settings/diagnostics" element={page} />
        <Route path="/tasks" element={<div>任务队列</div>} />
      </Routes>
    </MemoryRouter>
  )
}

function makeDiagnostics(overrides: Record<string, unknown> = {}) {
  return {
    api: { status: 'healthy', endpoint: null, latency_ms: null },
    services: { total: 3, available: 2, unavailable: 1 },
    toolchain: { total: 4, available: 3, missing: 1 },
    storage: { writable: true, free_bytes: 53687091200, used_bytes: 1073741824 },
    telemetry: { enabled: false, endpoint: null },
    logs: { recent_errors: 2, log_path: '/var/log/mountain/app.log' },
    recent_errors: [
      { timestamp: '2025-03-20T14:00:00Z', component: 'pipeline', message: 'Stage failed: timeout' },
    ],
    ...overrides,
  }
}

describe('DiagnosticsPage (§3M system diagnostics summary)', () => {
  beforeEach(() => {
    vi.mocked(fetchDiagnosticsSettings).mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  // ── Six categories rendered ──────────────────────────────────────────

  it('renders all six summary categories from full DTO', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics() as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('API')).toBeInTheDocument()
      expect(screen.getByText('动态服务')).toBeInTheDocument()
      expect(screen.getByText('工具链')).toBeInTheDocument()
      expect(screen.getByText('存储')).toBeInTheDocument()
      expect(screen.getByText('遥测')).toBeInTheDocument()
      expect(screen.getByText('近期错误')).toBeInTheDocument()
    })
  })

  // ── Empty registry:0/0/0 is valid ────────────────────────────────────

  it('renders empty service/toolchain counts as valid state', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      services: { total: 0, available: 0, unavailable: 0 },
      toolchain: { total: 0, available: 0, missing: 0 },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('动态服务')).toBeInTheDocument()
    })
    // The counts are in separate text nodes within the <p>; check the parent
    const servicesCard = screen.getByText('动态服务').closest('article')!
    expect(servicesCard.textContent).toContain('0')
    expect(servicesCard.textContent).toContain('可用')
    expect(servicesCard.textContent).toContain('不可用')

    const toolchainCard = screen.getByText('工具链').closest('article')!
    expect(toolchainCard.textContent).toContain('缺失')
  })

  // ── API status mapping ───────────────────────────────────────────────

  it('maps healthy → 正常', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'healthy', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('正常')).toBeInTheDocument()
    })
  })

  it('maps ok → 正常', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'ok', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('正常')).toBeInTheDocument()
    })
  })

  it('maps degraded → 降级', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'degraded', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('降级')).toBeInTheDocument()
    })
  })

  it('maps failed → 不可用', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'failed', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('不可用')).toBeInTheDocument()
    })
  })

  it('maps down → 不可用', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'down', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('不可用')).toBeInTheDocument()
    })
  })

  it('shows unknown API status string as-is', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'maintenance', endpoint: null, latency_ms: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('maintenance')).toBeInTheDocument()
    })
  })

  // ── Services/toolchain counts from backend ───────────────────────────

  it('displays service counts as returned by backend', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      services: { total: 10, available: 7, unavailable: 3 },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('动态服务').closest('article')!
      expect(card.textContent).toContain('10')
      expect(card.textContent).toContain('7')
      expect(card.textContent).toContain('3')
    })
  })

  it('displays toolchain counts as returned by backend', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      toolchain: { total: 6, available: 5, missing: 1 },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('工具链').closest('article')!
      expect(card.textContent).toContain('6')
      expect(card.textContent).toContain('5')
      expect(card.textContent).toContain('1')
    })
  })

  // ── Storage capacity uses shared helper ──────────────────────────────

  it('displays storage writable status and formatted capacity', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      storage: { writable: true, free_bytes: 53687091200, used_bytes: 1073741824 },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('存储').closest('article')!
      expect(card.textContent).toContain('可写')
      expect(card.textContent).toContain('50.0 GB')
      expect(card.textContent).toContain('1.0 GB')
    })
  })

  it('displays 不可写 when storage.writable is false', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      storage: { writable: false, free_bytes: null, used_bytes: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('存储').closest('article')!
      expect(card.textContent).toContain('不可写')
    })
  })

  it('does not show capacity when free_bytes and used_bytes are null', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      storage: { writable: true, free_bytes: null, used_bytes: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('存储').closest('article')!
      expect(card.textContent).toContain('可写')
    })
    // No capacity text rendered
    const card = screen.getByText('存储').closest('article')!
    expect(card.textContent).not.toContain('可用')
    expect(card.textContent).not.toContain('已用')
  })

  it('handles NaN/Infinity/negative capacity safely', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      storage: { writable: true, free_bytes: NaN, used_bytes: -1 },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const card = screen.getByText('存储').closest('article')!
      expect(card.textContent).toContain('可写')
      // NaN and negative are not valid capacity
      expect(card.textContent).not.toContain('可用')
      expect(card.textContent).not.toContain('已用')
    })
  })

  // ── Telemetry: only enabled/disabled ─────────────────────────────────

  it('shows telemetry enabled', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      telemetry: { enabled: true, endpoint: 'http://collector:4317' },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('已启用')).toBeInTheDocument()
    })
    // Must not show endpoint
    expect(screen.queryByText('http://collector:4317')).not.toBeInTheDocument()
  })

  it('shows telemetry disabled', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      telemetry: { enabled: false, endpoint: null },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('未启用')).toBeInTheDocument()
    })
  })

  it('shows 未配置 when telemetry is null', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      telemetry: null,
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('未配置')).toBeInTheDocument()
    })
  })

  // ── Logs: only recent_errors count, no log_path or error details ─────

  it('shows recent_errors count', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      logs: { recent_errors: 5, log_path: '/var/log/mountain/app.log' },
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument()
    })
    expect(screen.queryByText('/var/log/mountain/app.log')).not.toBeInTheDocument()
  })

  it('shows 0 when logs is null', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      logs: null,
    }) as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('0')).toBeInTheDocument()
    })
  })

  // ── Redaction note and /tasks link ───────────────────────────────────

  it('displays redaction/privacy note', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics() as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText(/不包含端点地址、日志路径、错误详情或敏感配置/)).toBeInTheDocument()
    })
  })

  it('provides a real /tasks link', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics() as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      const link = screen.getByText('前往任务队列')
      expect(link).toBeInTheDocument()
      expect(link.closest('a')).toHaveAttribute('href', '/tasks')
    })
  })

  // ── No capability matrix ─────────────────────────────────────────────

  it('does not render a capability matrix section', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics() as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('系统诊断')).toBeInTheDocument()
    })
    expect(screen.queryByText('能力矩阵')).not.toBeInTheDocument()
    expect(screen.queryByText('capability')).not.toBeInTheDocument()
  })

  // ── Loading skeleton ─────────────────────────────────────────────────

  it('shows loading skeleton initially', () => {
    vi.mocked(fetchDiagnosticsSettings).mockReturnValue(new Promise(() => {}))
    renderAt(<DiagnosticsPage />)

    expect(screen.getByLabelText('正在加载诊断信息')).toBeInTheDocument()
    expect(screen.queryByText('API')).not.toBeInTheDocument()
    expect(screen.queryByText('动态服务')).not.toBeInTheDocument()
  })

  // ── Error state ──────────────────────────────────────────────────────

  it('displays error when request fails', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockRejectedValue(new Error('网络连接失败'))
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText(/网络连接失败/)).toBeInTheDocument()
    })
    expect(screen.queryByText('正在加载诊断信息')).not.toBeInTheDocument()
  })

  // ── Retry re-calls real API ──────────────────────────────────────────

  it('retry button re-calls the production API adapter', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockRejectedValueOnce(new Error('临时错误'))
    const user = userEvent.setup()
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText(/临时错误/)).toBeInTheDocument()
    })

    vi.mocked(fetchDiagnosticsSettings).mockResolvedValueOnce(makeDiagnostics() as any)
    await user.click(screen.getByText('重新加载'))

    await waitFor(() => {
      expect(screen.getByText('系统诊断')).toBeInTheDocument()
      expect(screen.getByText('API')).toBeInTheDocument()
    })
    expect(fetchDiagnosticsSettings).toHaveBeenCalledTimes(2)
  })

  // ── Real two-lifecycle race protection ────────────────────────────────

  it('second request wins when first arrives after second', async () => {
    let resolveFirst: (v: any) => void
    let resolveSecond: (v: any) => void
    const firstRequest = new Promise(r => { resolveFirst = r })
    const secondRequest = new Promise(r => { resolveSecond = r })

    vi.mocked(fetchDiagnosticsSettings).mockReturnValueOnce(firstRequest as any)

    const { unmount } = renderAt(<DiagnosticsPage />)
    await new Promise(r => setTimeout(r, 0))

    // Unmount first instance
    unmount()

    // Re-mount second instance
    vi.mocked(fetchDiagnosticsSettings).mockReturnValueOnce(secondRequest as any)
    renderAt(<DiagnosticsPage />)
    await new Promise(r => setTimeout(r, 0))

    // Second completes first
    resolveSecond!(makeDiagnostics({
      services: { total: 5, available: 5, unavailable: 0 },
      logs: { recent_errors: 0, log_path: null },
    }))
    await waitFor(() => {
      const svcCard = screen.getByText('动态服务').closest('article')!
      expect(svcCard.textContent).toContain('5')
    })

    // First arrives late
    resolveFirst!(makeDiagnostics({
      services: { total: 99, available: 0, unavailable: 99 },
      logs: { recent_errors: 100, log_path: '/stale/path' },
    }))
    await new Promise(r => setTimeout(r, 0))

    // DOM must still show second response
    const svcCard = screen.getByText('动态服务').closest('article')!
    expect(svcCard.textContent).toContain('5')
    expect(svcCard.textContent).not.toContain('99')
    expect(screen.queryByText('/stale/path')).not.toBeInTheDocument()

    // Both API calls were made
    expect(fetchDiagnosticsSettings).toHaveBeenCalledTimes(2)
  })

  // ── Sensitive extra fields not rendered ───────────────────────────────

  it('does not render sensitive fields from the response', async () => {
    const sensitiveData = makeDiagnostics({
      path: '/mnt/data/mountain',
      storage_path: '/mnt/data/assets',
      command: 'ffmpeg -i input.mp4',
      token: 'sk-secret-token-12345',
      secret: 'api-key-abcdef',
      credential: 'bearer xyz',
    })
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(sensitiveData as any)
    const { container } = renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('系统诊断')).toBeInTheDocument()
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('/mnt/data/mountain')
    expect(text).not.toContain('/mnt/data/assets')
    expect(text).not.toContain('ffmpeg -i input.mp4')
    expect(text).not.toContain('sk-secret-token-12345')
    expect(text).not.toContain('api-key-abcdef')
    expect(text).not.toContain('bearer xyz')
  })

  it('does not render api.endpoint, telemetry.endpoint, logs.log_path, or recent error messages', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics({
      api: { status: 'ok', endpoint: 'http://api.internal:8000', latency_ms: 12 },
      telemetry: { enabled: true, endpoint: 'http://otel:4317' },
      logs: { recent_errors: 1, log_path: '/var/log/mountain/app.log' },
      recent_errors: [
        { timestamp: '2025-03-20T14:00:00Z', component: 'pipeline', message: 'Stage failed: timeout' },
      ],
    }) as any)
    const { container } = renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('系统诊断')).toBeInTheDocument()
    })

    const text = container.textContent ?? ''
    expect(text).not.toContain('http://api.internal:8000')
    expect(text).not.toContain('http://otel:4317')
    expect(text).not.toContain('/var/log/mountain/app.log')
    expect(text).not.toContain('Stage failed: timeout')
  })

  // ── Page title and description ───────────────────────────────────────

  it('displays page title "系统诊断" and readonly description', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue(makeDiagnostics() as any)
    renderAt(<DiagnosticsPage />)

    await waitFor(() => {
      expect(screen.getByText('系统诊断')).toBeInTheDocument()
      expect(screen.getByText(/当前运行环境的系统级摘要/)).toBeInTheDocument()
      expect(screen.getByText(/仅作只读展示/)).toBeInTheDocument()
    })
  })
})
