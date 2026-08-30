import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProviderDetailPage } from '../src/pages/ProviderDetailPage'

// Mock API client
vi.mock('../src/lib/api/client', () => ({
  fetchProvider: vi.fn(),
  updateProviderConfig: vi.fn(),
  fetchProviderSecrets: vi.fn(),
  setProviderSecret: vi.fn(),
  deleteProviderSecret: vi.fn(),
}))

const {
  fetchProvider,
  updateProviderConfig,
  fetchProviderSecrets,
} = await import('../src/lib/api/client')

const mockFetchProvider = vi.mocked(fetchProvider)
const mockUpdateProviderConfig = vi.mocked(updateProviderConfig)
const mockFetchProviderSecrets = vi.mocked(fetchProviderSecrets)

// ── Fixtures ────────────────────────────────────────────────────────────

const TEXT_MODEL_DETAIL = {
  name: 'text_model',
  profile: {
    provider_type: 'text_model',
    name: 'Text Model (OpenAI-compatible)',
    description: 'OpenAI-compatible Chat Completions API',
    required_secrets: ['api_key'],
    optional_secrets: [],
    config: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o', api_mode: 'chat-completions' },
  },
  config: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o', api_mode: 'chat-completions' },
  config_status: { configured: true, missing_secrets: [], configured_secrets: ['api_key'], is_encrypted: false },
  availability: { available: true, error_code: null, suggestion: null },
}

const IMAGE_MODEL_DETAIL = {
  name: 'image_model',
  profile: {
    provider_type: 'image_model',
    name: 'Image Model (OpenAI-compatible)',
    description: 'OpenAI-compatible Images API',
    required_secrets: ['api_key'],
    optional_secrets: [],
    config: { base_url: 'https://api.openai.com/v1', model: 'gpt-image-1' },
  },
  config: { base_url: 'https://api.openai.com/v1', model: 'gpt-image-1' },
  config_status: { configured: true, missing_secrets: [], configured_secrets: ['api_key'], is_encrypted: false },
  availability: { available: true, error_code: null, suggestion: null },
}

const TEXT_MODEL_SECRETS = {
  provider: 'text_model',
  secrets: {
    api_key: { configured: true, masked_value: 'sk-***2345' },
  },
}

const IMAGE_MODEL_SECRETS = {
  provider: 'image_model',
  secrets: {
    api_key: { configured: true, masked_value: 'sk-***6789' },
  },
}

// ── Helpers ─────────────────────────────────────────────────────────────

function setupMocks() {
  mockFetchProvider.mockImplementation((name: string) => {
    if (name === 'text_model') return Promise.resolve(TEXT_MODEL_DETAIL)
    if (name === 'image_model') return Promise.resolve(IMAGE_MODEL_DETAIL)
    return Promise.reject(new Error('Unknown provider'))
  })
  mockFetchProviderSecrets.mockImplementation((name: string) => {
    if (name === 'text_model') return Promise.resolve(TEXT_MODEL_SECRETS)
    if (name === 'image_model') return Promise.resolve(IMAGE_MODEL_SECRETS)
    return Promise.resolve({ provider: name, secrets: {} })
  })
  mockUpdateProviderConfig.mockResolvedValue({ ok: true, provider: '', config: {} })
}

function renderAt(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/settings/providers/:name" element={<ProviderDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// ── Tests ───────────────────────────────────────────────────────────────

describe('ProviderDetailPage: draft lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupMocks()
  })

  it('initializes config draft from detail.config on load', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      // base_url input should show text_model's value
      const baseInput = screen.getByDisplayValue('https://api.openai.com/v1')
      expect(baseInput).toBeInTheDocument()
    })
    // model input should show gpt-4o
    expect(screen.getByDisplayValue('gpt-4o')).toBeInTheDocument()
  })

  it('clears draft when switching from text_model to image_model', async () => {
    const { unmount } = renderAt('/settings/providers/text_model')

    // Wait for text_model to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('gpt-4o')).toBeInTheDocument()
    })

    unmount()

    // Now render at image_model
    renderAt('/settings/providers/image_model')

    // Wait for image_model to load
    await waitFor(() => {
      // model should show gpt-image-1, NOT gpt-4o
      expect(screen.getByDisplayValue('gpt-image-1')).toBeInTheDocument()
    })

    // gpt-4o should NOT be present
    expect(screen.queryByDisplayValue('gpt-4o')).not.toBeInTheDocument()
  })

  it('saves only current provider config', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByDisplayValue('gpt-4o')).toBeInTheDocument()
    })

    // Click save
    const saveBtn = screen.getByText('保存配置')
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(mockUpdateProviderConfig).toHaveBeenCalledWith(
        'text_model',
        expect.objectContaining({
          base_url: 'https://api.openai.com/v1',
          model: 'gpt-4o',
          api_mode: 'chat-completions',
        }),
      )
    })
  })

  it('shows category badge from provider_type', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByText('文本')).toBeInTheDocument()
    })
  })

  it('shows model chip', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    })
  })

  it('shows availability status', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByText('可用')).toBeInTheDocument()
    })
  })

  it('shows secret masked value', async () => {
    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByText('sk-***2345')).toBeInTheDocument()
    })
  })

  it('shows error_code when unavailable', async () => {
    mockFetchProvider.mockResolvedValue({
      ...TEXT_MODEL_DETAIL,
      availability: { available: false, error_code: 'SECRET_NOT_CONFIGURED', suggestion: '请配置 API Key' },
    })

    renderAt('/settings/providers/text_model')

    await waitFor(() => {
      expect(screen.getByText('Provider 不可用')).toBeInTheDocument()
      expect(screen.getByText(/SECRET_NOT_CONFIGURED/)).toBeInTheDocument()
      expect(screen.getByText(/请配置 API Key/)).toBeInTheDocument()
    })
  })
})
