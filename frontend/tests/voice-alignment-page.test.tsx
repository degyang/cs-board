import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VoiceAlignmentPage } from '../src/pages/VoiceAlignmentPage'
import type { ServiceDefinition } from '../src/lib/api/types'

vi.mock('../src/lib/api/services', () => ({
  fetchServices: vi.fn(),
  createService: vi.fn(),
  updateService: vi.fn(),
  deleteService: vi.fn(),
  probeService: vi.fn(),
  setServiceSecret: vi.fn(),
  fetchServiceSecrets: vi.fn(),
}))

import {
  fetchServices,
  createService,
  updateService,
  probeService,
  fetchServiceSecrets,
} from '../src/lib/api/services'

const availability = {
  available: true,
  checked_at: '2026-09-05T10:00:00Z',
  latency_ms: 18,
  component: null,
  error_code: null,
  suggestion: null,
}

function service(overrides: Partial<ServiceDefinition> = {}): ServiceDefinition {
  return {
    schema_version: 1,
    revision: 1,
    service_id: 'local-tts',
    display_name: '本地 TTS',
    capability: 'speech_synthesis',
    adapter_type: 'openai_compatible',
    endpoint: 'http://127.0.0.1:9000/v1',
    model: 'tts-local',
    enabled: true,
    priority: 10,
    is_default: false,
    config: {},
    required_secrets: [],
    optional_secrets: [],
    config_status: { configured: true, missing_fields: [], missing_secrets: [] },
    availability,
    secret_status: { configured: false, required: [], missing: [] },
    created_at: '2026-09-05T10:00:00Z',
    updated_at: '2026-09-05T10:00:00Z',
    ...overrides,
  }
}

describe('VoiceAlignmentPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(fetchServiceSecrets).mockResolvedValue({ items: [], total: 0 })
  })

  it('shows only local services and switches the detail preview from the list', async () => {
    const tts = service()
    const alignment = service({ service_id: 'local-align', display_name: '强制对齐', capability: 'speech_alignment' })
    const excluded = service({ service_id: 'local-stt', display_name: 'Whisper 本地识别', capability: 'speech_recognition' })
    vi.mocked(fetchServices).mockResolvedValue({ items: [tts, alignment, excluded], next_cursor: null, total: 3 })

    render(<VoiceAlignmentPage />)

    expect(await screen.findByRole('heading', { name: '本地服务' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /本地 TTS/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /强制对齐/ })).toBeInTheDocument()
    expect(screen.queryByText('Whisper 本地识别')).not.toBeInTheDocument()
    expect(screen.getByRole('region', { name: '服务预览' })).toHaveTextContent('本地 TTS')

    await userEvent.click(screen.getByRole('button', { name: /强制对齐/ }))
    expect(screen.getByRole('region', { name: '服务预览' })).toHaveTextContent('强制对齐')
  })

  it('excludes Whisper from local services by adapter_type and service_id, not display name', async () => {
    const normalAlignment = service({
      service_id: 'local-align',
      display_name: '强制对齐',
      capability: 'speech_alignment',
    })
    const whisperService = service({
      service_id: 'local-whisper',
      display_name: '本地 Whisper 对齐',
      capability: 'speech_alignment',
      adapter_type: 'whisper',
    })
    vi.mocked(fetchServices).mockResolvedValue({
      items: [normalAlignment, whisperService],
      next_cursor: null,
      total: 2,
    })

    render(<VoiceAlignmentPage />)

    expect(await screen.findByRole('button', { name: /强制对齐/ })).toBeInTheDocument()
    expect(screen.queryByText('本地 Whisper 对齐')).not.toBeInTheDocument()
    expect(screen.queryByText('local-whisper')).not.toBeInTheDocument()
  })

  it('creates a local service through the real create action', async () => {
    let items: ServiceDefinition[] = []
    vi.mocked(fetchServices).mockImplementation(async () => ({ items, next_cursor: null, total: items.length }))
    const created = service({ service_id: 'local-new', display_name: '新增 TTS' })
    vi.mocked(createService).mockImplementation(async () => {
      items = [created]
      return created
    })
    const user = userEvent.setup()
    render(<VoiceAlignmentPage />)

    await user.click(await screen.findByRole('button', { name: '+ 新建本地服务' }))
    await user.clear(screen.getByLabelText('服务 ID *'))
    await user.type(screen.getByLabelText('服务 ID *'), 'local-new')
    await user.type(screen.getByLabelText('显示名称 *'), '新增 TTS')
    await user.click(screen.getByRole('button', { name: '创建服务' }))

    await waitFor(() => expect(createService).toHaveBeenCalledWith(expect.objectContaining({
      service_id: 'local-new', display_name: '新增 TTS', capability: 'speech_synthesis',
    })))
    expect(await screen.findByText('已创建本地服务')).toBeInTheDocument()
  })

  it('edits and saves the selected service', async () => {
    const current = service()
    vi.mocked(fetchServices).mockResolvedValue({ items: [current], next_cursor: null, total: 1 })
    vi.mocked(updateService).mockResolvedValue(service({ display_name: '已更新 TTS', revision: 2 }))
    const user = userEvent.setup()
    render(<VoiceAlignmentPage />)

    await user.click(await screen.findByRole('button', { name: '编辑' }))
    expect(screen.getByRole('region', { name: '服务预览' })).toHaveTextContent('正在编辑')
    await user.clear(screen.getByLabelText('显示名称'))
    await user.type(screen.getByLabelText('显示名称'), '已更新 TTS')
    await user.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => expect(updateService).toHaveBeenCalledWith('local-tts', expect.objectContaining({
      display_name: '已更新 TTS', capability: 'speech_synthesis',
    })))
    expect(await screen.findByText('已保存')).toBeInTheDocument()
  })

  it('runs the selected service probe and displays its real result', async () => {
    const current = service()
    vi.mocked(fetchServices).mockResolvedValue({ items: [current], next_cursor: null, total: 1 })
    vi.mocked(probeService).mockResolvedValue({ ...availability, available: false, latency_ms: 42, error_code: 'OFFLINE' })
    const user = userEvent.setup()
    render(<VoiceAlignmentPage />)

    await user.click(await screen.findByRole('button', { name: '探测连通性' }))

    await waitFor(() => expect(probeService).toHaveBeenCalledWith('local-tts'))
    expect(await screen.findByText('探测完成')).toBeInTheDocument()
    expect(screen.getByText('不可用', { selector: 'span' })).toBeInTheDocument()
    expect(screen.getByText('· 42ms')).toBeInTheDocument()
  })
})
