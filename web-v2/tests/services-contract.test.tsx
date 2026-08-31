/* ==========================================================================
   Component Contract Tests — Services & Settings Pages
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { MountainApiError } from '../src/lib/api/http'
import { SettingsPage } from '../src/pages/SettingsPage'
import { ServiceDetailPage } from '../src/pages/ServiceDetailPage'
import { VoiceAlignmentPage } from '../src/pages/VoiceAlignmentPage'
import { ToolchainPage } from '../src/pages/ToolchainPage'
import { StoragePage } from '../src/pages/StoragePage'
import { DiagnosticsPage } from '../src/pages/DiagnosticsPage'

vi.mock('../src/lib/api/services', () => ({
  fetchServices: vi.fn(),
  fetchService: vi.fn(),
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

import { fetchServices, probeService, activateService, deactivateService, setDefaultService } from '../src/lib/api/services'
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
  config_status: 'ok',
  availability: { available: true, checked_at: '2025-01-01T00:00:00Z', latency_ms: 150, component: null, error_code: null, suggestion: null },
  secret_status: 'ok',
  required_secrets: ['api_key'],
  optional_secrets: ['org_id'],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('SettingsPage (Models tab)', () => {
  beforeEach(() => {
    vi.mocked(fetchServices).mockReset()
    vi.mocked(probeService).mockReset()
    vi.mocked(activateService).mockReset()
    vi.mocked(deactivateService).mockReset()
    vi.mocked(setDefaultService).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)
    expect(screen.getByText('设置')).toBeInTheDocument()
  })

  it('renders all settings tabs', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)
    expect(screen.getByText('模型服务')).toBeInTheDocument()
    expect(screen.getByText('语音与对齐')).toBeInTheDocument()
    expect(screen.getByText('工具链')).toBeInTheDocument()
    expect(screen.getByText('存储')).toBeInTheDocument()
    expect(screen.getByText('诊断')).toBeInTheDocument()
  })

  it('loads and displays services', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })
  })

  it('shows default badge for default service', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('默认')).toBeInTheDocument()
    })
  })

  it('calls probeService when clicking probe button', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    vi.mocked(probeService).mockResolvedValue(mockService)

    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: 'Probe' }))

    await waitFor(() => {
      expect(probeService).toHaveBeenCalledWith('svc1')
    })
  })

  it('calls deactivateService when clicking toggle on enabled service', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    vi.mocked(deactivateService).mockResolvedValue({ ...mockService, enabled: false })

    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '停用' }))

    await waitFor(() => {
      expect(deactivateService).toHaveBeenCalledWith('svc1')
    })
  })

  it('calls activateService when clicking toggle on disabled service', async () => {
    const disabledService = { ...mockService, enabled: false }
    vi.mocked(fetchServices).mockResolvedValue({ items: [disabledService], next_cursor: null, total: 1 })
    vi.mocked(activateService).mockResolvedValue({ ...disabledService, enabled: true })

    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '启用' }))

    await waitFor(() => {
      expect(activateService).toHaveBeenCalledWith('svc1')
    })
  })

  it('calls setDefaultService when clicking set default', async () => {
    const nonDefaultService = { ...mockService, is_default: false }
    vi.mocked(fetchServices).mockResolvedValue({ items: [nonDefaultService], next_cursor: null, total: 1 })
    vi.mocked(setDefaultService).mockResolvedValue({ ...nonDefaultService, is_default: true })

    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '设为默认' }))

    await waitFor(() => {
      expect(setDefaultService).toHaveBeenCalledWith('svc1')
    })
  })

  it('shows loading state', () => {
    vi.mocked(fetchServices).mockImplementation(() => new Promise(() => {}))
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.mocked(fetchServices).mockRejectedValue(new MountainApiError(0, 'NETWORK_ERROR', 'Network error', true))
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no services', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('暂无服务')).toBeInTheDocument()
    })
  })

  it('displays service capability as Chinese label', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [mockService], next_cursor: null, total: 1 })
    render(<MemoryRouter initialEntries={['/settings/models']}><SettingsPage /></MemoryRouter>)

    await waitFor(() => {
      const capabilityLabels = screen.getAllByText('文本生成')
      expect(capabilityLabels.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('OpenAI 兼容')).toBeInTheDocument()
    })
  })
})

describe('VoiceAlignmentPage', () => {
  beforeEach(() => {
    vi.mocked(fetchVoiceAlignmentSettings).mockReset()
    vi.mocked(probeService).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: null,
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('声音对齐')).toBeInTheDocument()
    })
  })

  it('displays TTS service card', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: {
        ...mockService,
        capability: 'speech_synthesis',
        timeout: null,
      },
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('语音合成 (TTS)')).toBeInTheDocument()
      expect(screen.getByText('OpenAI GPT-4')).toBeInTheDocument()
    })
  })

  it('displays alignment service card', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: null,
      speech_alignment: {
        ...mockService,
        capability: 'speech_alignment',
        timeout: null,
      },
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('语音对齐')).toBeInTheDocument()
    })
  })

  it('shows probe button on service cards', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: {
        ...mockService,
        capability: 'speech_synthesis',
        timeout: null,
      },
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '探测' })).toBeInTheDocument()
    })
  })

  it('calls probeService when clicking probe', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: {
        ...mockService,
        capability: 'speech_synthesis',
        timeout: null,
      },
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    vi.mocked(probeService).mockResolvedValue(mockService)

    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '探测' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '探测' }))

    await waitFor(() => {
      expect(probeService).toHaveBeenCalledWith('svc1')
    })
  })

  it('shows empty state when no services configured', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: null,
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('未配置语音服务')).toBeInTheDocument()
    })
  })

  it('displays service metadata', async () => {
    vi.mocked(fetchVoiceAlignmentSettings).mockResolvedValue({
      speech_synthesis: {
        ...mockService,
        capability: 'speech_synthesis',
        timeout: null,
      },
      speech_alignment: null,
      indextts: null,
      whisper: null,
    })
    render(<MemoryRouter><VoiceAlignmentPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText(/https:\/\/api.openai.com/)).toBeInTheDocument()
      expect(screen.getByText(/gpt-4/)).toBeInTheDocument()
    })
  })
})

describe('ToolchainPage', () => {
  beforeEach(() => {
    vi.mocked(fetchToolchainSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({ tools: [] })
    render(<MemoryRouter><ToolchainPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('工具链')).toBeInTheDocument()
    })
  })

  it('displays tool items', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({
      tools: [
        { component: 'ffmpeg', available: true, version: '6.0', error_code: null, suggestion: null },
        { component: 'ImageMagick', available: false, version: null, error_code: 'NOT_FOUND', suggestion: 'Install via apt' },
      ],
    })
    render(<MemoryRouter><ToolchainPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('ffmpeg')).toBeInTheDocument()
      expect(screen.getByText('ImageMagick')).toBeInTheDocument()
      expect(screen.getByText('版本: 6.0')).toBeInTheDocument()
      expect(screen.getByText(/NOT_FOUND/)).toBeInTheDocument()
    })
  })

  it('shows available/unavailable status', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({
      tools: [
        { component: 'ffmpeg', available: true, version: null, error_code: null, suggestion: null },
        { component: 'missing-tool', available: false, version: null, error_code: null, suggestion: null },
      ],
    })
    render(<MemoryRouter><ToolchainPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('可用')).toBeInTheDocument()
      expect(screen.getByText('不可用')).toBeInTheDocument()
    })
  })

  it('does not display paths', async () => {
    vi.mocked(fetchToolchainSettings).mockResolvedValue({
      tools: [{ component: 'ffmpeg', available: true, version: null, error_code: null, suggestion: null }],
    })
    render(<MemoryRouter><ToolchainPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('ffmpeg')).toBeInTheDocument()
    })

    expect(screen.queryByText(/\/usr\/bin/)).not.toBeInTheDocument()
  })
})

describe('StoragePage', () => {
  beforeEach(() => {
    vi.mocked(fetchStorageSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true,
      assets_available: true,
      tasks_available: true,
      temp_available: true,
      free_bytes: null,
      used_bytes: null,
      cleanup_policy: null,
      error_code: null,
      suggestion: null,
    })
    render(<MemoryRouter><StoragePage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('存储')).toBeInTheDocument()
    })
  })

  it('displays storage status items', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true,
      assets_available: true,
      tasks_available: true,
      temp_available: false,
      free_bytes: 1024 * 1024 * 1024,
      used_bytes: 512 * 1024 * 1024,
      cleanup_policy: 'auto',
      error_code: null,
      suggestion: null,
    })
    render(<MemoryRouter><StoragePage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('可写')).toBeInTheDocument()
      expect(screen.getByText('素材存储')).toBeInTheDocument()
      expect(screen.getByText('任务存储')).toBeInTheDocument()
      expect(screen.getByText('临时存储')).toBeInTheDocument()
      expect(screen.getByText('1.0 GB')).toBeInTheDocument()
      expect(screen.getByText('512.0 MB')).toBeInTheDocument()
      expect(screen.getByText('auto')).toBeInTheDocument()
    })
  })

  it('shows available/unavailable status', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true,
      assets_available: true,
      tasks_available: false,
      temp_available: false,
      free_bytes: null,
      used_bytes: null,
      cleanup_policy: null,
      error_code: null,
      suggestion: null,
    })
    render(<MemoryRouter><StoragePage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('可写')).toBeInTheDocument()
      const unavailable = screen.getAllByText('不可用')
      expect(unavailable.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('does not display data_dir or path', async () => {
    vi.mocked(fetchStorageSettings).mockResolvedValue({
      writable: true,
      assets_available: true,
      tasks_available: true,
      temp_available: true,
      free_bytes: null,
      used_bytes: null,
      cleanup_policy: null,
      error_code: null,
      suggestion: null,
    })
    render(<MemoryRouter><StoragePage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('存储')).toBeInTheDocument()
    })

    expect(screen.queryByText(/data_dir/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\/var\/data/)).not.toBeInTheDocument()
  })
})

describe('DiagnosticsPage', () => {
  beforeEach(() => {
    vi.mocked(fetchDiagnosticsSettings).mockReset()
  })

  it('renders the page title', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'ok', endpoint: null, latency_ms: null },
      services: { total: 5, available: 4, unavailable: 1 },
      toolchain: { total: 3, available: 3, missing: 0 },
      storage: { writable: true, free_bytes: null, used_bytes: null },
      telemetry: null,
      logs: null,
      recent_errors: [],
    })
    render(<MemoryRouter><DiagnosticsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('诊断')).toBeInTheDocument()
    })
  })

  it('displays all diagnostic items', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'ok', endpoint: null, latency_ms: null },
      services: { total: 5, available: 4, unavailable: 1 },
      toolchain: { total: 3, available: 3, missing: 0 },
      storage: { writable: true, free_bytes: 1024 * 1024 * 1024, used_bytes: null },
      telemetry: { enabled: true, endpoint: null },
      logs: { recent_errors: 2, log_path: null },
      recent_errors: [],
    })
    render(<MemoryRouter><DiagnosticsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('API 状态')).toBeInTheDocument()
      expect(screen.getByText('服务')).toBeInTheDocument()
      expect(screen.getByText('工具链')).toBeInTheDocument()
      expect(screen.getByText('存储')).toBeInTheDocument()
      expect(screen.getByText('遥测')).toBeInTheDocument()
      expect(screen.getByText('近期错误')).toBeInTheDocument()
    })
  })

  it('has a refresh button', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'ok', endpoint: null, latency_ms: null },
      services: { total: 0, available: 0, unavailable: 0 },
      toolchain: { total: 0, available: 0, missing: 0 },
      storage: { writable: true, free_bytes: null, used_bytes: null },
      telemetry: null,
      logs: null,
      recent_errors: [],
    })
    render(<MemoryRouter><DiagnosticsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('刷新')).toBeInTheDocument()
    })
  })

  it('does not display secrets or tokens', async () => {
    vi.mocked(fetchDiagnosticsSettings).mockResolvedValue({
      api: { status: 'ok', endpoint: null, latency_ms: null },
      services: { total: 0, available: 0, unavailable: 0 },
      toolchain: { total: 0, available: 0, missing: 0 },
      storage: { writable: true, free_bytes: null, used_bytes: null },
      telemetry: null,
      logs: null,
      recent_errors: [],
    })
    render(<MemoryRouter><DiagnosticsPage /></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByText('诊断')).toBeInTheDocument()
    })

    expect(screen.queryByText(/api_key/)).not.toBeInTheDocument()
    expect(screen.queryByText(/token/)).not.toBeInTheDocument()
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument()
  })
})
