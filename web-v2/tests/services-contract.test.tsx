/* ==========================================================================
   Component Contract Tests — Services & Settings Pages
   Tests the actual Router-used components (§3A.3, §3B.2)
   Uses production-equivalent route tree with future flags
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom'
import { MountainApiError } from '../src/lib/api/http'
import type { ToolchainComponent } from '../src/lib/api/types'
import { SettingsLayout } from '../src/pages/SettingsLayout'
import { ModelServicesPage } from '../src/pages/ModelServicesPage'
import { ServiceDetailPage } from '../src/pages/ServiceDetailPage'
import { ServiceFormPage } from '../src/pages/ServiceFormPage'
import { VoiceAlignmentPage } from '../src/pages/VoiceAlignmentPage'
import { ToolchainPage } from '../src/pages/ToolchainPage'
import { StoragePage } from '../src/pages/StoragePage'
import { DiagnosticsPage } from '../src/pages/DiagnosticsPage'

vi.mock('../src/lib/api/services', () => ({
  fetchServices: vi.fn(),
  fetchService: vi.fn(),
  createService: vi.fn(),
  updateService: vi.fn(),
  probeService: vi.fn(),
  activateService: vi.fn(),
  deactivateService: vi.fn(),
  setDefaultService: vi.fn(),
  deleteService: vi.fn(),
  fetchServiceSecrets: vi.fn(),
  setServiceSecret: vi.fn(),
  deleteServiceSecret: vi.fn(),
}))

vi.mock('../src/lib/api/settings', () => ({
  fetchRuntimeSettings: vi.fn(),
  fetchVoiceAlignment: vi.fn(),
  fetchToolchain: vi.fn(),
  fetchStorage: vi.fn(),
  fetchDiagnostics: vi.fn(),
  fetchVoiceAlignmentSettings: vi.fn(),
  fetchToolchainSettings: vi.fn(),
  fetchStorageSettings: vi.fn(),
  fetchDiagnosticsSettings: vi.fn(),
}))

import {
  fetchServices,
  fetchService,
  createService,
  probeService,
  activateService,
  deactivateService,
  setDefaultService,
  deleteService,
  fetchServiceSecrets,
} from '../src/lib/api/services'
import { fetchVoiceAlignmentSettings, fetchToolchainSettings, fetchStorageSettings, fetchDiagnosticsSettings } from '../src/lib/api/settings'

const mockService = {
  schema_version: 1,
  revision: 1,
  service_id: 'svc1',
  display_name: 'OpenAI GPT-4',
  capability: 'text_generation',
  adapter_type: 'openai_compatible',
  endpoint: 'https://api.openai.com',
  model: 'gpt-4',
  enabled: true,
  priority: 10,
  is_default: true,
  config: {},
  config_status: { configured: true, missing_fields: [], missing_secrets: [] },
  availability: { available: true, checked_at: '2025-01-01T00:00:00Z', latency_ms: 150, component: null, error_code: null, suggestion: null },
  secret_status: { configured: true, required: ['api_key'], missing: [] },
  required_secrets: ['api_key'],
  optional_secrets: ['org_id'],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

const mockSecrets = {
  items: [
    { secret_key: 'api_key', configured: true, masked_value: 'sk-...abc', updated_at: '2025-01-01T00:00:00Z' },
  ],
  total: 1,
}

/** React Router v7 future flags — suppresses all Future Flag warnings */
const ROUTER_FUTURE = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}

/**
 * Production-equivalent route tree matching app/router.tsx.
 * Uses MemoryRouter with future flags to eliminate all Router warnings.
 */
function renderWithRouter(ui: React.ReactElement, initialRoute = '/settings/models') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]} future={ROUTER_FUTURE}>
      <Routes>
        <Route path="/settings" element={<SettingsLayout />}>
          <Route path="models" element={ui} />
          <Route path="models/new" element={<ServiceFormPage />} />
          <Route path="models/:serviceId" element={<ServiceDetailPage />} />
          <Route path="models/:serviceId/edit" element={<ServiceFormPage />} />
          <Route path="voice-alignment" element={<VoiceAlignmentPage />} />
          <Route path="toolchain" element={<ToolchainPage />} />
          <Route path="storage" element={<StoragePage />} />
          <Route path="diagnostics" element={<DiagnosticsPage />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('SettingsLayout with ModelServicesPage (production Router)', () => {
  beforeEach(() => {
    vi.mocked(fetchServices).mockReset()
    vi.mocked(probeService).mockReset()
    vi.mocked(activateService).mockReset()
    vi.mocked(deactivateService).mockReset()
    vi.mocked(setDefaultService).mockReset()
    vi.mocked(deleteService).mockReset()
    vi.mocked(fetchServiceSecrets).mockReset()
  })

  it('renders SettingsLayout with all navigation tabs', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })
    expect(screen.getByText('设置')).toBeInTheDocument()
    expect(screen.getByText('模型服务')).toBeInTheDocument()
    expect(screen.getByText('语音与对齐')).toBeInTheDocument()
    expect(screen.getByText('工具链')).toBeInTheDocument()
    expect(screen.getByText('存储')).toBeInTheDocument()
    expect(screen.getByText('诊断')).toBeInTheDocument()
  })

  it('loads and displays services', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })
  })

  it('shows default badge for default service', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('默认')).toBeInTheDocument()
    })
  })

  it('shows loading state', async () => {
    vi.mocked(fetchServices).mockImplementation(() => new Promise(() => {}))
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.mocked(fetchServices).mockRejectedValue(new MountainApiError(0, 'NETWORK_ERROR', 'Network error', true))
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no services', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })

    await waitFor(() => {
      expect(screen.getByText('暂无服务')).toBeInTheDocument()
    })
  })

  it('displays service capability as Chinese label', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />)
    })

    await waitFor(() => {
      const capabilityLabels = screen.getAllByText('文本生成')
      expect(capabilityLabels.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('OpenAI 兼容')).toBeInTheDocument()
    })
  })
})

describe('ServiceDetailPage', () => {
  beforeEach(() => {
    vi.mocked(fetchService).mockReset()
    vi.mocked(fetchServiceSecrets).mockReset()
    vi.mocked(probeService).mockReset()
    vi.mocked(activateService).mockReset()
    vi.mocked(deactivateService).mockReset()
    vi.mocked(setDefaultService).mockReset()
    vi.mocked(deleteService).mockReset()
  })

  it('renders service details with structured config_status and secret_status', async () => {
    vi.mocked(fetchService).mockResolvedValue(mockService)
    vi.mocked(fetchServiceSecrets).mockResolvedValue(mockSecrets)

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/svc1']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models/:serviceId" element={<ServiceDetailPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await waitFor(() => {
      const titleElements = screen.getAllByText('OpenAI GPT-4')
      expect(titleElements.length).toBeGreaterThanOrEqual(1)
      const svcIdElements = screen.getAllByText('svc1')
      expect(svcIdElements.length).toBeGreaterThanOrEqual(1)
      // Both config_status and secret_status show "已配置"
      const configuredBadges = screen.getAllByText('已配置')
      expect(configuredBadges.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('shows secrets with masked values', async () => {
    vi.mocked(fetchService).mockResolvedValue(mockService)
    vi.mocked(fetchServiceSecrets).mockResolvedValue(mockSecrets)

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/svc1']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models/:serviceId" element={<ServiceDetailPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await waitFor(() => {
      expect(screen.getByText('sk-...abc')).toBeInTheDocument()
    })
  })

  it('calls probeService and displays ServiceAvailability result', async () => {
    vi.mocked(fetchService).mockResolvedValue(mockService)
    vi.mocked(fetchServiceSecrets).mockResolvedValue(mockSecrets)
    vi.mocked(probeService).mockResolvedValue({
      available: true,
      checked_at: '2025-03-20T14:25:00Z',
      latency_ms: 120,
      component: 'openai',
      error_code: null,
      suggestion: null,
    })

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/svc1']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models/:serviceId" element={<ServiceDetailPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await waitFor(() => {
      const titleElements = screen.getAllByText('OpenAI GPT-4')
      expect(titleElements.length).toBeGreaterThanOrEqual(1)
    })

    await userEvent.click(screen.getByRole('button', { name: '探测' }))

    await waitFor(() => {
      expect(probeService).toHaveBeenCalledWith('svc1')
      expect(screen.getByText('探测完成')).toBeInTheDocument()
    })
  })

  it('delete failure stays on page', async () => {
    vi.mocked(fetchService).mockResolvedValue(mockService)
    vi.mocked(fetchServiceSecrets).mockResolvedValue(mockSecrets)
    vi.mocked(deleteService).mockRejectedValue(new MountainApiError(400, 'DELETE_FAILED', 'Cannot delete default service'))

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/svc1']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models/:serviceId" element={<ServiceDetailPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await waitFor(() => {
      const titleElements = screen.getAllByText('OpenAI GPT-4')
      expect(titleElements.length).toBeGreaterThanOrEqual(1)
    })

    // Click the first "删除" button (the one in the page, not the dialog)
    const deleteButtons = screen.getAllByRole('button', { name: '删除' })
    await userEvent.click(deleteButtons[0])

    // Confirm dialog should appear
    await waitFor(() => {
      expect(screen.getByText('确定删除服务「OpenAI GPT-4」？此操作不可恢复。')).toBeInTheDocument()
    })

    // Re-query buttons after dialog appears
    const dialogDeleteButtons = screen.getAllByRole('button', { name: '删除' })
    // Click the last "删除" button (the one in the dialog)
    await userEvent.click(dialogDeleteButtons[dialogDeleteButtons.length - 1])

    // Should stay on page with error
    await waitFor(() => {
      expect(screen.getByText(/删除失败/)).toBeInTheDocument()
      // Service should still be visible
      const titleElements = screen.getAllByText('OpenAI GPT-4')
      expect(titleElements.length).toBeGreaterThanOrEqual(1)
    })
  })
})

describe('ServiceFormPage (create)', () => {
  beforeEach(() => {
    vi.mocked(createService).mockReset()
  })

  it('renders create form with all required fields', async () => {
    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/new']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models" element={<div>models-index</div>} />
              <Route path="models/new" element={<ServiceFormPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    expect(screen.getByText('新建服务')).toBeInTheDocument()
    expect(screen.getByLabelText('服务 ID *')).toBeInTheDocument()
    expect(screen.getByLabelText('显示名称 *')).toBeInTheDocument()
    expect(screen.getByLabelText('能力 *')).toBeInTheDocument()
    expect(screen.getByLabelText('适配器 *')).toBeInTheDocument()
  })

  it('submits service_id, display_name, capability, adapter_type and optional fields', async () => {
    vi.mocked(createService).mockResolvedValue(mockService)

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/new']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models" element={<div>models-index</div>} />
              <Route path="models/new" element={<ServiceFormPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await userEvent.type(screen.getByLabelText('服务 ID *'), 'my-service')
    await userEvent.type(screen.getByLabelText('显示名称 *'), 'My Service')
    await userEvent.clear(screen.getByLabelText('能力 *'))
    await userEvent.type(screen.getByLabelText('能力 *'), 'text_generation')
    await userEvent.clear(screen.getByLabelText('适配器 *'))
    await userEvent.type(screen.getByLabelText('适配器 *'), 'openai_compatible')

    await userEvent.click(screen.getByRole('button', { name: '创建服务' }))

    await waitFor(() => {
      expect(createService).toHaveBeenCalledWith(expect.objectContaining({
        service_id: 'my-service',
        display_name: 'My Service',
        capability: 'text_generation',
        adapter_type: 'openai_compatible',
      }))
    })
  })

  it('allows custom capability and adapter_type values', async () => {
    vi.mocked(createService).mockResolvedValue(mockService)

    await act(async () => {
      render(
        <MemoryRouter initialEntries={['/settings/models/new']} future={ROUTER_FUTURE}>
          <Routes>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route path="models" element={<div>models-index</div>} />
              <Route path="models/new" element={<ServiceFormPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      )
    })

    await userEvent.type(screen.getByLabelText('服务 ID *'), 'custom-svc')
    await userEvent.type(screen.getByLabelText('显示名称 *'), 'Custom Service')
    await userEvent.clear(screen.getByLabelText('能力 *'))
    await userEvent.type(screen.getByLabelText('能力 *'), 'custom_capability')
    await userEvent.clear(screen.getByLabelText('适配器 *'))
    await userEvent.type(screen.getByLabelText('适配器 *'), 'custom_adapter')

    await userEvent.click(screen.getByRole('button', { name: '创建服务' }))

    await waitFor(() => {
      expect(createService).toHaveBeenCalledWith(expect.objectContaining({
        capability: 'custom_capability',
        adapter_type: 'custom_adapter',
      }))
    })
  })
})

describe('VoiceAlignmentPage (production route)', () => {
  beforeEach(() => {
    vi.mocked(fetchVoiceAlignmentSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: null,
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })

    await act(async () => {
      renderWithRouter(<VoiceAlignmentPage />, '/settings/voice-alignment')
    })

    await waitFor(() => {
      // Title appears in both tab and page content
      expect(screen.getAllByText('语音与对齐').length).toBeGreaterThanOrEqual(1)
    })
  })
})

describe('ToolchainPage (production route)', () => {
  beforeEach(() => {
    vi.mocked(fetchToolchainSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({ tools: [] })

    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })

    await waitFor(() => {
      expect(screen.getByText('系统工具链')).toBeInTheDocument()
    })
  })

  it('renders available and unavailable components without environment details', async () => {
    const unavailableTool = {
      component: 'renderer', available: false, version: null, error_code: 'E-RENDER-NODE-OFFLINE',
      suggestion: '请确认本地渲染服务已启动。', path: '/private/runtime/renderer', command: 'renderer --token secret-value', token: 'secret-value',
    }
    vi.mocked(fetchToolchainSettings).mockResolvedValue({
      tools: [
        { component: 'ffmpeg', available: true, version: '6.1.1', error_code: null, suggestion: null },
        unavailableTool,
      ],
    })

    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })

    await waitFor(() => expect(screen.getByText('FFmpeg 音画合成')).toBeInTheDocument())
    expect(screen.getByText('将配音、对齐字幕与画面合成为最终成片。')).toBeInTheDocument()
    expect(screen.getByText('6.1.1')).toBeInTheDocument()
    expect(screen.getByText('白板渲染器')).toBeInTheDocument()
    expect(screen.getByText('E-RENDER-NODE-OFFLINE')).toBeInTheDocument()
    expect(screen.getByText('请确认本地渲染服务已启动。')).toBeInTheDocument()
    expect(screen.queryByText('/private/runtime/renderer')).not.toBeInTheDocument()
    expect(screen.queryByText('renderer --token secret-value')).not.toBeInTheDocument()
    expect(screen.queryByText('secret-value')).not.toBeInTheDocument()
  })

  it('keeps unknown components visible with their DTO status', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({
      tools: [{ component: 'new-runtime-tool', available: false, version: null, error_code: 'NOT_READY', suggestion: '等待组件就绪。' }],
    })
    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })

    await waitFor(() => expect(screen.getByText('new-runtime-tool')).toBeInTheDocument())
    expect(screen.getByText('不可用')).toBeInTheDocument()
    expect(screen.getByText('NOT_READY')).toBeInTheDocument()
  })

  it('renders skeleton and empty states separately', async () => {
    let resolveRequest: ((value: { tools: [] }) => void) | undefined
    vi.mocked(fetchToolchainSettings).mockImplementationOnce(() => new Promise(resolve => {
      resolveRequest = resolve
    }))
    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })
    expect(screen.getByLabelText('正在加载系统工具链')).toBeInTheDocument()

    await act(async () => resolveRequest?.({ tools: [] }))
    await waitFor(() => expect(screen.getByText('未探测到工具链组件')).toBeInTheDocument())
  })

  it('retries the API request after an error and clears the old error', async () => {
    vi.mocked(fetchToolchainSettings)
      .mockRejectedValueOnce(new Error('网络不可达'))
      .mockResolvedValueOnce({ tools: [{ component: 'ffprobe', available: true, version: '6.1.1', error_code: null, suggestion: null }] })
    const user = userEvent.setup()
    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('网络不可达'))
    await user.click(screen.getByRole('button', { name: '重新加载' }))
    await waitFor(() => expect(screen.getByText('FFprobe')).toBeInTheDocument())
    expect(fetchToolchainSettings).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /保存|编辑|探测|刷新/i })).not.toBeInTheDocument()
  })

  it('ignores a delayed response after unmount', async () => {
    let resolveRequest: ((value: { tools: ToolchainComponent[] }) => void) | undefined
    vi.mocked(fetchToolchainSettings).mockImplementationOnce(() => new Promise(resolve => {
      resolveRequest = resolve
    }))
    let rendered: ReturnType<typeof render> | undefined
    await act(async () => {
      rendered = renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })

    rendered?.unmount()
    await act(async () => resolveRequest?.({ tools: [{ component: 'ffmpeg', available: true, version: null, error_code: null, suggestion: null }] }))
    expect(screen.queryByText('FFmpeg 音画合成')).not.toBeInTheDocument()
  })
})

describe('StoragePage (production route)', () => {
  beforeEach(() => {
    vi.mocked(fetchStorageSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true,
      assets_available: true,
      tasks_available: true,
      temp_available: true,
      free_bytes: 50000000000,
      used_bytes: 50000000000,
      cleanup_policy: 'auto',
      error_code: null,
      suggestion: null,
    })

    await act(async () => {
      renderWithRouter(<StoragePage />, '/settings/storage')
    })

    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })
  })
})

describe('DiagnosticsPage (production route)', () => {
  beforeEach(() => {
    vi.mocked(fetchDiagnosticsSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'healthy', endpoint: null, latency_ms: null },
      services: { total: 1, available: 1, unavailable: 0 },
      toolchain: { total: 2, available: 2, missing: 0 },
      storage: { writable: true, free_bytes: null, used_bytes: null },
      telemetry: { enabled: false, endpoint: null },
      logs: { recent_errors: 0, log_path: null },
    })

    await act(async () => {
      renderWithRouter(<DiagnosticsPage />, '/settings/diagnostics')
    })

    await waitFor(() => {
      expect(screen.getAllByText('诊断').length).toBeGreaterThanOrEqual(1)
    })
  })
})

describe('Production route tree verification', () => {
  beforeEach(() => {
    vi.mocked(fetchServices).mockReset()
    vi.mocked(fetchService).mockReset()
    vi.mocked(fetchServiceSecrets).mockReset()
    vi.mocked(fetchVoiceAlignmentSettings).mockReset()
    vi.mocked(fetchToolchainSettings).mockReset()
    vi.mocked(fetchStorageSettings).mockReset()
    vi.mocked(fetchDiagnosticsSettings).mockReset()
  })

  it('renders /settings/models through production-equivalent route tree', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    await act(async () => {
      renderWithRouter(<ModelServicesPage />, '/settings/models')
    })
    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })
  })

  it('renders /settings/models/new through production-equivalent route tree', async () => {
    vi.mocked(createService).mockResolvedValue(mockService)
    await act(async () => {
      renderWithRouter(<ServiceFormPage />, '/settings/models/new')
    })
    expect(screen.getByText('新建服务')).toBeInTheDocument()
  })

  it('renders /settings/models/:serviceId through production-equivalent route tree', async () => {
    vi.mocked(fetchService).mockResolvedValue(mockService)
    vi.mocked(fetchServiceSecrets).mockResolvedValue(mockSecrets)
    await act(async () => {
      renderWithRouter(<ServiceDetailPage />, '/settings/models/svc1')
    })
    await waitFor(() => {
      expect(screen.getAllByText('OpenAI GPT-4').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders /settings/voice-alignment through production-equivalent route tree', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: null, speech_alignment: null, indextts: null, whisper: null,
    })
    await act(async () => {
      renderWithRouter(<VoiceAlignmentPage />, '/settings/voice-alignment')
    })
    await waitFor(() => {
      expect(screen.getAllByText('语音与对齐').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders /settings/toolchain through production-equivalent route tree', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({ tools: [] })
    await act(async () => {
      renderWithRouter(<ToolchainPage />, '/settings/toolchain')
    })
    await waitFor(() => {
      expect(screen.getAllByText('工具链').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders /settings/storage through production-equivalent route tree', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true, assets_available: true, tasks_available: true, temp_available: true,
      free_bytes: null, used_bytes: null, cleanup_policy: null, error_code: null, suggestion: null,
    })
    await act(async () => {
      renderWithRouter(<StoragePage />, '/settings/storage')
    })
    await waitFor(() => {
      expect(screen.getByText('运行时存储状态')).toBeInTheDocument()
    })
  })

  it('renders /settings/diagnostics through production-equivalent route tree', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'healthy', endpoint: null, latency_ms: null },
      services: { total: 0, available: 0, unavailable: 0 },
      toolchain: { total: 0, available: 0, missing: 0 },
      storage: { writable: true, free_bytes: null, used_bytes: null },
      telemetry: null, logs: null, recent_errors: [],
    })
    await act(async () => {
      renderWithRouter(<DiagnosticsPage />, '/settings/diagnostics')
    })
    await waitFor(() => {
      expect(screen.getAllByText('诊断').length).toBeGreaterThanOrEqual(1)
    })
  })
})
