/* ==========================================================================
   Mountain API Client — 集中式 fetch 封装
   所有组件通过此模块调用 /api/v1，禁止自行 fetch
   ========================================================================== */

import type {
  HealthResponse,
  CapabilitiesResponse,
  ProviderListResponse,
  ProviderDetail,
  UpdateConfigResponse,
  SecretStatusResponse,
  SetSecretRequest,
  SecretOperationResponse,
  ProjectListResponse,
  CreateProjectRequest,
  CreateProjectResponse,
  ProjectDetail,
  ApiError,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export class MountainApiError extends Error {
  constructor(
    public status: number,
    public apiError: ApiError | null,
    message: string,
  ) {
    super(message)
    this.name = 'MountainApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!res.ok) {
    let apiError: ApiError | null = null
    try {
      const body = await res.json()
      apiError = typeof body.detail === 'object' ? body.detail : null
    } catch {
      // ignore parse errors
    }
    throw new MountainApiError(
      res.status,
      apiError,
      apiError?.message ?? `API error: ${res.status}`,
    )
  }

  return res.json() as Promise<T>
}

function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

// ── Health ──────────────────────────────────────────────────────────────

export function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>('/health')
}

// ── Capabilities ────────────────────────────────────────────────────────

export function fetchCapabilities(): Promise<CapabilitiesResponse> {
  return get<CapabilitiesResponse>('/capabilities')
}

// ── Providers ───────────────────────────────────────────────────────────

export function fetchProviders(): Promise<ProviderListResponse> {
  return get<ProviderListResponse>('/providers')
}

export function fetchProvider(name: string): Promise<ProviderDetail> {
  return get<ProviderDetail>(`/providers/${encodeURIComponent(name)}`)
}

export function updateProviderConfig(
  name: string,
  config: Record<string, unknown>,
): Promise<UpdateConfigResponse> {
  return put<UpdateConfigResponse>(`/providers/${encodeURIComponent(name)}/config`, config)
}

export function fetchProviderSecrets(name: string): Promise<SecretStatusResponse> {
  return get<SecretStatusResponse>(`/providers/${encodeURIComponent(name)}/secrets`)
}

export function setProviderSecret(
  name: string,
  secret: SetSecretRequest,
): Promise<SecretOperationResponse> {
  return post<SecretOperationResponse>(
    `/providers/${encodeURIComponent(name)}/secrets`,
    secret,
  )
}

export function deleteProviderSecret(
  name: string,
  key: string,
): Promise<SecretOperationResponse> {
  return del<SecretOperationResponse>(
    `/providers/${encodeURIComponent(name)}/secrets/${encodeURIComponent(key)}`,
  )
}

// ── Projects ────────────────────────────────────────────────────────────

export function fetchProjects(limit = 50): Promise<ProjectListResponse> {
  return get<ProjectListResponse>(`/projects?limit=${limit}`)
}

export function createProject(
  req: CreateProjectRequest,
): Promise<CreateProjectResponse> {
  return post<CreateProjectResponse>('/projects', req)
}

export function fetchProject(id: string): Promise<ProjectDetail> {
  return get<ProjectDetail>(`/projects/${encodeURIComponent(id)}`)
}
