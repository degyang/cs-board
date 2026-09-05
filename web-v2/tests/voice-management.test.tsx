import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { VoiceManagementPage } from '../src/pages/VoiceManagementPage'

vi.mock('../src/lib/api/assets', () => ({
  fetchVoices: vi.fn(),
  createVoice: vi.fn(),
  updateVoice: vi.fn(),
  deleteVoice: vi.fn(),
}))
vi.mock('../src/lib/api/services', () => ({ fetchServices: vi.fn() }))
vi.mock('../src/lib/api/voiceProfiles', () => ({
  fetchVoiceProfiles: vi.fn(),
  fetchVoiceStyleProfiles: vi.fn(),
  createVoiceProfile: vi.fn(),
  createVoiceStyleProfile: vi.fn(),
  previewVoiceProfile: vi.fn(),
}))

import { fetchVoices } from '../src/lib/api/assets'
import { fetchServices } from '../src/lib/api/services'
import { createVoiceProfile, createVoiceStyleProfile, fetchVoiceProfiles, fetchVoiceStyleProfiles, previewVoiceProfile } from '../src/lib/api/voiceProfiles'

const voice = {
  voice_id: 'voice-local', name: '本地真实音色', description: '', tags: ['中文'],
  duration_ms: 2100, sample_rate: 44100, channels: 1, format: 'wav', enabled: true,
  status: 'active' as const, created_at: '2026-09-05T00:00:00Z', updated_at: '2026-09-05T00:00:00Z',
}

const provider = {
  schema_version: 1, revision: 1, service_id: 'provider-speech', display_name: '语音 Provider',
  capability: 'speech.synthesize', adapter_type: 'provider-adapter', endpoint: null, model: null,
  enabled: true, priority: 10, is_default: true, config: {}, required_secrets: [], optional_secrets: [],
  config_status: { configured: true, missing_fields: [], missing_secrets: [] },
  availability: { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
  secret_status: { configured: true, required: [], missing: [] }, created_at: '', updated_at: '',
}

const legacyAudioProvider = {
  ...provider,
  service_id: 'provider-mimo',
  display_name: 'MiMo 音色 Provider',
  capability: 'audio_generation',
}

describe('VoiceManagementPage provider information architecture', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(fetchVoices).mockResolvedValue({ items: [voice], next_cursor: null, total: 1 })
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchVoiceProfiles).mockRejectedValue(new Error('404'))
    vi.mocked(fetchVoiceStyleProfiles).mockRejectedValue(new Error('404'))
    vi.mocked(createVoiceProfile).mockRejectedValue(new Error('接口尚未就绪'))
    vi.mocked(createVoiceStyleProfile).mockRejectedValue(new Error('接口尚未就绪'))
    vi.mocked(previewVoiceProfile).mockRejectedValue(new Error('预览接口尚未就绪'))
  })

  it('renders four tabs and directly retains the local voice library behavior', async () => {
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    expect(screen.getAllByRole('tab').map(tab => tab.textContent)).toEqual(['音色库', '预置音色', '音色设计', '发音风格'])
    await waitFor(() => expect(screen.getAllByText('本地真实音色').length).toBeGreaterThan(0))
    expect(fetchVoices).toHaveBeenCalledWith()
    expect(screen.getByPlaceholderText('搜索音色…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ 上传音色' })).toBeInTheDocument()
    expect(document.querySelector('audio')).toHaveAttribute('src', expect.stringContaining('/assets/voices/voice-local/content'))
    expect(fetchVoiceProfiles).not.toHaveBeenCalled()
  })

  it('uses explicit provider/profile hooks and shows controlled unavailable states', async () => {
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await waitFor(() => {
      expect(fetchServices).toHaveBeenCalledWith({ enabled: true })
      expect(fetchVoiceProfiles).toHaveBeenCalledWith({ kind: 'provider-preset' })
      expect(screen.getByRole('alert')).toHaveTextContent('接口尚未就绪')
    })

    await userEvent.click(screen.getByRole('tab', { name: '音色设计' }))
    await waitFor(() => {
      expect(fetchVoiceProfiles).toHaveBeenCalledWith({ kind: 'provider-designed', provider_id: undefined })
      expect(screen.getByText('Provider 未配置', { selector: 'strong' })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('tab', { name: '发音风格' }))
    await waitFor(() => expect(fetchVoiceStyleProfiles).toHaveBeenCalledWith({ provider_id: undefined }))
  })

  it('groups read-only preset profiles by vendor and renders the required detail fields', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({
      items: [{
        profile_id: 'profile-1', revision: 2, name: '远程预置音色', kind: 'provider-preset',
        vendor_id: 'mimo', vendor_name: 'MiMo', gender: 'female', example_text: null,
        provider_id: 'provider-speech', model_id: 'tts-model', remote_voice_id: 'remote-voice-1',
        language: 'zh-CN', tags: ['自然'], status: 'active', capability_snapshot: {}, created_at: '', updated_at: '',
      }, {
        profile_id: 'profile-2', revision: 1, name: 'Dean', kind: 'provider-preset',
        vendor_id: 'mimo', vendor_name: 'MiMo', gender: 'male', provider_id: 'provider-speech',
        model_id: 'tts-model', remote_voice_id: 'Dean', language: 'en-US', tags: [], status: 'active', capability_snapshot: {},
      }, {
        profile_id: 'profile-3', revision: 1, name: '未知规范值', kind: 'provider-preset',
        vendor_id: 'mimo', vendor_name: 'MiMo', gender: 'unknown', provider_id: 'provider-speech',
        model_id: 'tts-model', remote_voice_id: 'unknown', language: 'unknown', tags: [], status: 'active', capability_snapshot: {},
      }], next_cursor: null, total: 3,
    })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'MiMo' })).toBeInTheDocument()
      expect(screen.getAllByText('远程预置音色')).toHaveLength(2)
      expect(screen.getByText('女')).toBeInTheDocument()
      expect(screen.getByText('中文')).toBeInTheDocument()
      expect(screen.queryByText('zh-CN')).not.toBeInTheDocument()
      expect(screen.queryByText('female')).not.toBeInTheDocument()
      expect(screen.getByText('语音 Provider')).toBeInTheDocument()
      expect(screen.getByText('tts-model')).toBeInTheDocument()
      expect(screen.getByText('这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。')).toBeInTheDocument()
      expect(fetchVoiceProfiles).toHaveBeenCalledWith({ kind: 'provider-preset' })
    })
    await userEvent.click(screen.getByText('Dean'))
    expect(screen.getByText('英文')).toBeInTheDocument()
    expect(screen.getByText('男')).toBeInTheDocument()
    expect(screen.queryByText('en-US')).not.toBeInTheDocument()
    expect(screen.queryByText('male')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('未知规范值'))
    expect(within(screen.getByRole('article', { name: '预置音色详情' })).getAllByText('—')).toHaveLength(2)
    expect(screen.queryByRole('button', { name: /上传|编辑/ })).not.toBeInTheDocument()
    expect(document.querySelector('audio')).not.toHaveAttribute('src')
  })

  it('recognizes a legacy audio_generation service in preset detail and both Provider selectors', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [legacyAudioProvider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockImplementation(async params => ({
      items: params.kind === 'provider-preset' ? [{
        profile_id: 'mimo-preset', revision: 1, name: '冰糖', kind: 'provider-preset',
        vendor_id: 'mimo', vendor_name: 'MiMo', provider_id: 'provider-mimo', model_id: 'mimo-v2.5-tts',
        remote_voice_id: '冰糖', language: 'zh-CN', gender: '女', tags: [], status: 'active', capability_snapshot: {},
      }] : [],
      next_cursor: null,
      total: params.kind === 'provider-preset' ? 1 : 0,
    }))
    vi.mocked(fetchVoiceStyleProfiles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })

    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await waitFor(() => expect(screen.getByText('MiMo 音色 Provider')).toBeInTheDocument())
    for (const tabName of ['音色设计', '发音风格']) {
      await userEvent.click(screen.getByRole('tab', { name: tabName }))
      await waitFor(() => expect(screen.getByRole('option', { name: 'MiMo 音色 Provider' })).toBeInTheDocument())
    }
  })

  it('requests a real backend preview and only renders audio from its returned URL', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [{
      profile_id: 'profile/voice', revision: 1, name: '冰糖', kind: 'provider-preset', vendor_id: 'mimo', vendor_name: 'MiMo',
      provider_id: 'provider-speech', model_id: 'mimo-v2.5-tts', remote_voice_id: '冰糖', language: 'zh-CN',
      tags: [], status: 'active', capability_snapshot: {},
    }], next_cursor: null, total: 1 })
    vi.mocked(previewVoiceProfile).mockResolvedValue({
      audio_url: '/api/v1/voice-profile-previews/preview-1/content', content_type: 'audio/wav', duration_ms: 8405,
    })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await userEvent.click(await screen.findByRole('button', { name: '生成预览' }))

    const text = '这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。'
    await waitFor(() => expect(previewVoiceProfile).toHaveBeenCalledWith('profile/voice', text))
    expect(document.querySelector('audio')).toHaveAttribute('src', '/api/v1/voice-profile-previews/preview-1/content')
  })

  it('shows a controlled error and no audio when the preview API is unavailable', async () => {
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [{
      profile_id: 'mimo-bingtang', revision: 1, name: '冰糖', kind: 'provider-preset', vendor_id: 'mimo', vendor_name: 'MiMo',
      provider_id: 'provider-mimo', model_id: 'mimo-v2.5-tts', remote_voice_id: '冰糖', tags: [], status: 'active', capability_snapshot: {},
    }], next_cursor: null, total: 1 })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await userEvent.click(await screen.findByRole('button', { name: '生成预览' }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('预览生成失败：预览接口尚未就绪'))
    expect(document.querySelector('audio')).not.toHaveAttribute('src')
  })

  it('creates designs and speaking styles with an explicit Provider and no secret fields', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchVoiceStyleProfiles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })

    await userEvent.click(screen.getByRole('tab', { name: '音色设计' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '+ 新建音色设计' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: '+ 新建音色设计' }))
    expect(screen.getAllByRole('option', { name: '语音 Provider' })).toHaveLength(2)
    await userEvent.type(screen.getByLabelText('名称 *'), '温暖讲解声')
    await userEvent.type(screen.getByLabelText('模型 *'), 'voice-design-model')
    await userEvent.type(screen.getByLabelText('设计描述 *'), '温暖、清晰、适合知识讲解')
    await userEvent.type(screen.getByLabelText('标签（逗号分隔）'), '温暖, 讲解')
    await userEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => {
      expect(createVoiceProfile).toHaveBeenCalledWith({
        name: '温暖讲解声', kind: 'provider-designed', provider_id: 'provider-speech',
        model_id: 'voice-design-model', design_prompt: '温暖、清晰、适合知识讲解', tags: ['温暖', '讲解'],
      })
      expect(screen.getByRole('alert')).toHaveTextContent('接口尚未就绪')
    })
    expect(JSON.stringify(vi.mocked(createVoiceProfile).mock.calls[0][0]).toLowerCase()).not.toContain('key')
    await userEvent.click(screen.getByRole('button', { name: '取消' }))

    await userEvent.click(screen.getByRole('tab', { name: '发音风格' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '+ 新建发音风格' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: '+ 新建发音风格' }))
    await userEvent.type(screen.getByLabelText('名称 *'), '沉稳叙述')
    await userEvent.type(screen.getByLabelText('风格指令 *'), '语速适中，语气沉稳')
    await userEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(createVoiceStyleProfile).toHaveBeenCalledWith({
      name: '沉稳叙述', provider_id: 'provider-speech', instruction: '语速适中，语气沉稳', tags: [],
    }))
  })
})
