import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProvidersPage } from '../src/pages/ProvidersPage'

// Mock API client
vi.mock('../src/lib/api/client', () => ({
  fetchProviders: vi.fn(),
}))

const { fetchProviders } = await import('../src/lib/api/client')
const mockFetchProviders = vi.mocked(fetchProviders)

const mockProviderData = {
  providers: {
    text_model: {
      profile: {
        provider_type: 'text_model',
        name: 'Text Model (OpenAI-compatible)',
        description: 'OpenAI-compatible Chat Completions API',
        required_secrets: ['api_key'],
        optional_secrets: [],
        config: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
      },
      config_status: {
        configured: false,
        missing_secrets: ['api_key'],
        configured_secrets: [],
        is_encrypted: false,
      },
      availability: { available: false, error_code: 'MISSING_API_KEY', suggestion: '请配置 API Key' },
    },
    tts: {
      profile: {
        provider_type: 'tts',
        name: 'Text-to-Speech (IndexTTS)',
        description: 'IndexTTS 语音克隆服务',
        required_secrets: [],
        optional_secrets: [],
        config: { url: 'http://127.0.0.1:7860', mode: 'gradio' },
      },
      config_status: {
        configured: true,
        missing_secrets: [],
        configured_secrets: [],
        is_encrypted: false,
      },
      availability: { available: true },
    },
  },
  all_configured: false,
  all_available: false,
}

describe('ProvidersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    mockFetchProviders.mockReturnValue(new Promise(() => {}))
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(/加载中/)).toBeInTheDocument()
  })

  it('renders provider list after loading', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Text Model (OpenAI-compatible)')).toBeInTheDocument()
      expect(screen.getByText('Text-to-Speech (IndexTTS)')).toBeInTheDocument()
    })
  })

  it('shows "模型服务" as page title', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('模型服务')).toBeInTheDocument()
    })
  })

  it('shows category badges from provider_type', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      // text_model → 文本
      expect(screen.getByText('文本')).toBeInTheDocument()
      // tts → 语音
      expect(screen.getByText('语音')).toBeInTheDocument()
    })
  })

  it('shows model chip from config.model', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    })
  })

  it('shows Base URL from config', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('https://api.openai.com/v1')).toBeInTheDocument()
    })
  })

  it('shows TTS URL from config', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('http://127.0.0.1:7860')).toBeInTheDocument()
    })
  })

  it('shows warning when not all providers are available', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/部分 Provider 服务不可用/)).toBeInTheDocument()
    })
  })

  it('shows success when all providers are available', async () => {
    mockFetchProviders.mockResolvedValue({
      ...mockProviderData,
      all_configured: true,
      all_available: true,
    })
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/所有 Provider 已就绪/)).toBeInTheDocument()
    })
  })

  it('shows configured/unconfigured badges correctly', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      const unconfigured = screen.getAllByText('未配置')
      expect(unconfigured.length).toBeGreaterThan(0)
      const configured = screen.getAllByText('已配置')
      expect(configured.length).toBeGreaterThan(0)
    })
  })

  it('shows error_code when provider unavailable', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('MISSING_API_KEY')).toBeInTheDocument()
    })
  })

  it('shows suggestion when provider unavailable', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/请配置 API Key/)).toBeInTheDocument()
    })
  })

  it('renders links to provider detail pages', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      const links = screen.getAllByText('配置 →')
      expect(links.length).toBe(2)
    })
  })

  it('shows CRUD gap notice', async () => {
    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/当前版本由后端管理 Provider Profile/)).toBeInTheDocument()
    })
  })

  it('shows error state on fetch failure', async () => {
    mockFetchProviders.mockRejectedValueOnce(new Error('网络错误'))
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument()
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
  })

  it('does not use localStorage or sessionStorage', () => {
    const lsSpy = vi.spyOn(Storage.prototype, 'getItem')
    const ssSpy = vi.spyOn(Storage.prototype, 'setItem')

    mockFetchProviders.mockResolvedValue(mockProviderData)
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    )

    // No business state should use localStorage
    expect(lsSpy).not.toHaveBeenCalled()
    expect(ssSpy).not.toHaveBeenCalled()

    lsSpy.mockRestore()
    ssSpy.mockRestore()
  })
})
