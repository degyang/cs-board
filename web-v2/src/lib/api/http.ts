/* ==========================================================================
   Mountain HTTP Client — Base fetch utilities
   All API modules use this for consistent error handling.
   ========================================================================== */

import type { ApiError } from './types'

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

async function parseError(res: Response): Promise<MountainApiError> {
  let apiError: ApiError | null = null
  try {
    const body = await res.json()
    apiError = typeof body.detail === 'object' ? body.detail : null
  } catch {
    // ignore parse errors
  }
  return new MountainApiError(
    res.status,
    apiError,
    apiError?.message ?? `API error: ${res.status}`,
  )
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!res.ok) {
    throw await parseError(res)
  }

  return res.json() as Promise<T>
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

/**
 * POST multipart/form-data — browser auto-sets Content-Type with boundary.
 * Never set Content-Type manually.
 */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    throw await parseError(res)
  }

  return res.json() as Promise<T>
}

/**
 * POST multipart/form-data returning raw Response (for file uploads).
 */
export async function postFormRaw(path: string, form: FormData): Promise<Response> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    throw await parseError(res)
  }

  return res
}

export function getBaseUrl(): string {
  return BASE
}
