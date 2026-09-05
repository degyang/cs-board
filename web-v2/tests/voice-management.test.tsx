import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { dedupePresetProfiles, PRESET_PREVIEW_TIMEOUT_MS, VoiceManagementPage } from '../src/pages/VoiceManagementPage'

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
  createPresetVoiceProfile: vi.fn(),
  createVoiceProfile: vi.fn(),
  createVoiceStyleProfile: vi.fn(),
  previewVoiceProfile: vi.fn(),
  updateVoiceProfile: vi.fn(),
}))

import { fetchVoices } from '../src/lib/api/assets'
import { fetchServices } from '../src/lib/api/services'
import { createPresetVoiceProfile, createVoiceProfile, createVoiceStyleProfile, fetchVoiceProfiles, fetchVoiceStyleProfiles, previewVoiceProfile, updateVoiceProfile } from '../src/lib/api/voiceProfiles'

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
  model: 'mimo-v2.5-tts, mimo-v2.5-tts-voicedesign',
}

describe('VoiceManagementPage provider information architecture', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(fetchVoices).mockResolvedValue({ items: [voice], next_cursor: null, total: 1 })
    vi.mocked(fetchServices).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    vi.mocked(fetchVoiceProfiles).mockRejectedValue(new Error('404'))
    vi.mocked(fetchVoiceStyleProfiles).mockRejectedValue(new Error('404'))
    vi.mocked(createVoiceProfile).mockRejectedValue(new Error('接口尚未就绪'))
    vi.mocked(createPresetVoiceProfile).mockRejectedValue(new Error('接口尚未就绪'))
    vi.mocked(createVoiceStyleProfile).mockRejectedValue(new Error('接口尚未就绪'))
    vi.mocked(previewVoiceProfile).mockRejectedValue(new Error('预览接口尚未就绪'))
    vi.mocked(updateVoiceProfile).mockRejectedValue(new Error('接口尚未就绪'))
  })

  it('shows one deterministic directory row per normalized vendor and remote voice while retaining its Provider binding', () => {
    const source = [
      { profile_id: 'z-provider', vendor_id: 'MiMo', remote_voice_id: 'BingTang', provider_id: 'provider-z' },
      { profile_id: 'a-provider', vendor_id: ' mimo ', remote_voice_id: ' bingtang ', provider_id: 'provider-a' },
      { profile_id: 'different-voice', vendor_id: 'mimo', remote_voice_id: 'chloe', provider_id: 'provider-a' },
      { profile_id: 'incomplete', vendor_id: '', remote_voice_id: 'bingtang', provider_id: 'provider-a' },
    ] as unknown as Parameters<typeof dedupePresetProfiles>[0]
    expect(dedupePresetProfiles(source).map(profile => [profile.profile_id, profile.provider_id])).toEqual([
      ['a-provider', 'provider-a'], ['different-voice', 'provider-a'], ['incomplete', 'provider-a'],
    ])
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

  it('groups selectable preset profiles by vendor and renders the required detail fields', async () => {
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
    await userEvent.click(await screen.findByText('远程预置音色'))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'MiMo' })).toBeInTheDocument()
      expect(screen.getAllByText('远程预置音色')).toHaveLength(3)
      expect(screen.getByText('女')).toBeInTheDocument()
      expect(screen.getByText('中文')).toBeInTheDocument()
      expect(screen.queryByText('zh-CN')).not.toBeInTheDocument()
      expect(screen.queryByText('female')).not.toBeInTheDocument()
      expect(screen.getByText('语音 Provider')).toBeInTheDocument()
      expect(screen.getByText('tts-model')).toBeInTheDocument()
      expect(screen.getByLabelText('示例朗读文本')).toHaveValue('这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。')
      expect(fetchVoiceProfiles).toHaveBeenCalledWith({ kind: 'provider-preset' })
    })
    await userEvent.click(screen.getByText('Dean'))
    expect(screen.getByText('英文')).toBeInTheDocument()
    expect(screen.getByText('男')).toBeInTheDocument()
    expect(screen.queryByText('en-US')).not.toBeInTheDocument()
    expect(screen.queryByText('male')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('未知规范值'))
    expect(within(screen.getByRole('article', { name: '预置音色详情' })).getAllByText('—')).toHaveLength(2)
    expect(screen.getByRole('button', { name: '编辑' })).toBeInTheDocument()
    expect(screen.queryByRole('audio')).not.toBeInTheDocument()
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
    await userEvent.click(await screen.findByText('冰糖'))
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
    await userEvent.click(await screen.findByText('冰糖'))
    await userEvent.click(screen.getByRole('button', { name: '生成试听' }))

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
    await userEvent.click(await screen.findByText('冰糖'))
    await userEvent.click(screen.getByRole('button', { name: '生成试听' }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('预览生成失败：预览接口尚未就绪'))
    expect(document.querySelector('audio')).toBeNull()
  })

  it('derives preset Provider choices only from enabled audio/TTS service capabilities', async () => {
    const textOnlyProvider = { ...provider, service_id: 'text-only', display_name: '文本模型', capability: 'text_generation' }
    vi.mocked(fetchServices).mockResolvedValue({ items: [textOnlyProvider, legacyAudioProvider], next_cursor: null, total: 2 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await userEvent.click(await screen.findByRole('button', { name: '+ 新增预置音色' }))
    expect(screen.getByRole('option', { name: 'MiMo 音色 Provider' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: '文本模型' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('模型 *')).toHaveValue('mimo-v2.5-tts')
    expect(fetchServices).toHaveBeenCalledWith({ enabled: true })
  })

  it('creates and edits a preset using Provider identity fields', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    const preset = {
      profile_id: 'preset-1', revision: 1, name: '初始音色', kind: 'provider-preset' as const, vendor_name: '任意服务',
      provider_id: 'provider-speech', model_id: 'tts-model', remote_voice_id: 'remote-1', language: 'zh-CN', tags: [], status: 'active' as const, capability_snapshot: {},
    }
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [preset], next_cursor: null, total: 1 })
    vi.mocked(createPresetVoiceProfile).mockResolvedValue(preset)
    vi.mocked(updateVoiceProfile).mockResolvedValue({ ...preset, name: '已编辑音色' })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await userEvent.click(await screen.findByRole('button', { name: '+ 新增预置音色' }))
    await userEvent.type(screen.getByLabelText('名称 *'), '新建音色')
    await userEvent.type(screen.getByLabelText('模型 *'), 'provider-model')
    await userEvent.type(screen.getByLabelText('远端音色 ID *'), 'remote-new')
    await userEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(createPresetVoiceProfile).toHaveBeenCalledWith(expect.objectContaining({ name: '新建音色', provider_id: 'provider-speech', model_id: 'provider-model', remote_voice_id: 'remote-new' })))
    await userEvent.click(screen.getByText('初始音色'))
    await userEvent.click(screen.getByRole('button', { name: '编辑' }))
    const name = screen.getByLabelText('名称 *')
    await userEvent.clear(name)
    await userEvent.type(name, '已编辑音色')
    await userEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(updateVoiceProfile).toHaveBeenCalledWith('preset-1', expect.objectContaining({ name: '已编辑音色', provider_id: 'provider-speech' })))
  })

  it('stops an edit locally when its Provider has no declared usable model instead of issuing a 400 PATCH', async () => {
    const modelLessProvider = { ...provider, service_id: 'local-indextts', display_name: '本地 IndexTTS', model: '' }
    const preset = {
      profile_id: 'legacy-local', revision: 1, name: '旧本地预置', kind: 'provider-preset' as const,
      provider_id: 'local-indextts', model_id: 'indextts-2', remote_voice_id: 'legacy', language: 'zh-CN', tags: [], status: 'active' as const, capability_snapshot: {},
    }
    vi.mocked(fetchServices).mockResolvedValue({ items: [modelLessProvider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [preset], next_cursor: null, total: 1 })
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    await userEvent.click(await screen.findByText('旧本地预置'))
    await userEvent.click(screen.getByRole('button', { name: '编辑' }))
    await userEvent.click(screen.getByRole('button', { name: '保存' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('当前 Provider 未声明可用模型')
    expect(updateVoiceProfile).not.toHaveBeenCalled()
  })

  it('binds editable preview text to the selection and invalidates stale audio on a new selection', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [
      { profile_id: 'one', revision: 1, name: '音色一', kind: 'provider-preset', vendor_name: '服务', provider_id: 'provider-speech', model_id: 'tts', remote_voice_id: 'one', tags: [], status: 'active', capability_snapshot: {} },
      { profile_id: 'two', revision: 1, name: '音色二', kind: 'provider-preset', vendor_name: '服务', provider_id: 'provider-speech', model_id: 'tts', remote_voice_id: 'two', tags: [], status: 'active', capability_snapshot: {} },
    ], next_cursor: null, total: 2 })
    let resolvePreview: ((value: { audio_url: string; content_type: string }) => void) | undefined
    vi.mocked(previewVoiceProfile).mockImplementation(() => new Promise(resolve => { resolvePreview = resolve }))
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    await userEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    expect(screen.getByRole('button', { name: '生成试听' })).toBeDisabled()
    await userEvent.click(await screen.findByText('音色一'))
    const text = screen.getByLabelText('示例朗读文本')
    expect(text).toHaveValue('这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。')
    await userEvent.clear(text)
    await userEvent.type(text, '自定义试听文本')
    await userEvent.click(screen.getByRole('button', { name: '生成试听' }))
    expect(previewVoiceProfile).toHaveBeenCalledWith('one', '自定义试听文本')
    await userEvent.click(screen.getByText('音色二'))
    await act(async () => { resolvePreview?.({ audio_url: '/old.wav', content_type: 'audio/wav' }) })
    expect(screen.queryByText('/old.wav')).not.toBeInTheDocument()
    expect(document.querySelector('audio')).toBeNull()
  })

  it('keeps a desktop-safe preset master/detail structure and ends a stalled preview with a visible timeout error', async () => {
    vi.mocked(fetchServices).mockResolvedValue({ items: [provider], next_cursor: null, total: 1 })
    vi.mocked(fetchVoiceProfiles).mockResolvedValue({ items: [{
      profile_id: 'timeout', revision: 1, name: '不会竖排的预置音色', kind: 'provider-preset', vendor_name: '服务', provider_id: 'provider-speech', model_id: 'tts', remote_voice_id: 'timeout', tags: [], status: 'active', capability_snapshot: {},
    }], next_cursor: null, total: 1 })
    vi.mocked(previewVoiceProfile).mockImplementation(() => new Promise(() => undefined))
    await act(async () => { render(<MemoryRouter><VoiceManagementPage /></MemoryRouter>) })
    fireEvent.click(screen.getByRole('tab', { name: '预置音色' }))
    const item = await screen.findByText('不会竖排的预置音色')
    fireEvent.click(item)
    expect(screen.getByRole('region', { name: '预置音色' }).querySelector('.am-layout')).toHaveClass('am-layout')
    expect(screen.getByRole('article', { name: '预置音色详情' })).toBeInTheDocument()
    vi.useFakeTimers()
    try {
      fireEvent.click(screen.getByRole('button', { name: '生成试听' }))
      await act(async () => { await vi.advanceTimersByTimeAsync(PRESET_PREVIEW_TIMEOUT_MS) })
      expect(screen.getByRole('alert')).toHaveTextContent('预览生成失败：试听生成超时，请检查 Provider 后重试。')
      expect(screen.getByRole('button', { name: '生成试听' })).toBeEnabled()
      expect(document.querySelector('audio')).toBeNull()
    } finally {
      vi.useRealTimers()
    }
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
