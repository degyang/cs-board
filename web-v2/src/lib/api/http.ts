/* ==========================================================================
   Mountain HTTP Client — Base fetch utilities
   All API modules use this for consistent error handling.

   Error format (backend):
   {
     "error": {
       "code": "ERROR_CODE",
       "message": "错误说明",
       "retryable": false,
       "details": {}
     }
   }

   Also compatible with FastAPI detail format.
   ========================================================================== */

// Keep every API module on the same-origin /api route by default. Vite proxies
// it in development; production may override it with VITE_API_BASE_URL.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class MountainApiError extends Error {
  public status: number
  public code: string
  public message: string
  public retryable: boolean
  public details: Record<string, unknown> | null

  constructor(
    status: number,
    code: string,
    message: string,
    retryable = false,
    details: Record<string, unknown> | null = null,
  ) {
    super(message)
    this.name = 'MountainApiError'
    this.status = status
    this.code = code
    this.message = message
    this.retryable = retryable
    this.details = details
  }
}

/**
 * Parse error response body.
 * Supports both new format (body.error) and FastAPI format (body.detail).
 */
function parseErrorBody(body: unknown): { code: string; message: string; retryable: boolean; details: Record<string, unknown> | null } {
  if (typeof body !== 'object' || body === null) {
    return { code: 'UNKNOWN_ERROR', message: 'Unknown error', retryable: false, details: null }
  }

  const obj = body as Record<string, unknown>

  // New format: { error: { code, message, retryable, details } }
  if (obj.error && typeof obj.error === 'object') {
    const err = obj.error as Record<string, unknown>
    return {
      code: typeof err.code === 'string' ? err.code : 'UNKNOWN_ERROR',
      message: typeof err.message === 'string' ? err.message : 'Unknown error',
      retryable: err.retryable === true,
      details: typeof err.details === 'object' ? err.details as Record<string, unknown> : null,
    }
  }

  // FastAPI format: { detail: "message" } or { detail: { ... } }
  if (obj.detail !== undefined) {
    if (typeof obj.detail === 'string') {
      return { code: 'API_ERROR', message: obj.detail, retryable: false, details: null }
    }
    if (typeof obj.detail === 'object' && obj.detail !== null) {
      const detail = obj.detail as Record<string, unknown>
      return {
        code: typeof detail.code === 'string' ? detail.code : 'API_ERROR',
        message: typeof detail.message === 'string' ? detail.message : JSON.stringify(detail),
        retryable: detail.retryable === true,
        details: typeof detail.details === 'object' ? detail.details as Record<string, unknown> : null,
      }
    }
  }

  // Fallback: { message: "..." }
  if (typeof obj.message === 'string') {
    return { code: 'API_ERROR', message: obj.message, retryable: false, details: null }
  }

  return { code: 'UNKNOWN_ERROR', message: 'Unknown error', retryable: false, details: null }
}

async function parseErrorResponse(res: Response): Promise<MountainApiError> {
  try {
    const body = await res.json()
    const parsed = parseErrorBody(body)
    return new MountainApiError(res.status, parsed.code, parsed.message, parsed.retryable, parsed.details)
  } catch {
    // Can't parse JSON — use status text
    return new MountainApiError(
      res.status,
      'HTTP_ERROR',
      `HTTP ${res.status}: ${res.statusText || 'Unknown error'}`,
      false,
      null,
    )
  }
}

/**
 * Create a network error (fetch failed, no response).
 */
function networkError(cause: unknown): MountainApiError {
  const message = cause instanceof Error ? cause.message : 'Network request failed'
  return new MountainApiError(0, 'NETWORK_ERROR', message, true, null)
}

/**
 * Core request function.
 * - Does NOT set Content-Type for GET requests
 * - Does NOT set Content-Type for FormData (browser sets boundary)
 * - Handles 204 No Content (returns undefined)
 * - Parses error responses using body.error or body.detail
 */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`

  // Build headers — don't set Content-Type for GET or FormData
  const headers: Record<string, string> = {}
  const isFormData = init?.body instanceof FormData
  const isGet = !init?.method || init.method === 'GET'

  if (!isGet && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  // Merge user headers
  if (init?.headers) {
    const userHeaders = init.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : typeof init.headers === 'object' ? init.headers as Record<string, string> : {}
    Object.assign(headers, userHeaders)
  }

  // Fix #9: For FormData, remove ALL case variants of Content-Type
  if (isFormData) {
    const contentTypeKeys = Object.keys(headers).filter(
      k => k.toLowerCase() === 'content-type'
    )
    for (const key of contentTypeKeys) {
      delete headers[key]
    }
  }

  let res: Response
  try {
    res = await fetch(url, {
      ...init,
      headers,
    })
  } catch (err) {
    throw networkError(err)
  }

  if (!res.ok) {
    throw await parseErrorResponse(res)
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}

export function get<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, init)
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
 * POST multipart/form-data — browser sets Content-Type with boundary.
 * Never set Content-Type manually.
 */
export function postForm<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: form,
  })
}

export function getBaseUrl(): string {
  return BASE
}

/**
 * Build URL for voice content streaming.
 */
export function getVoiceContentUrl(voiceId: string): string {
  return `${BASE}/assets/voices/${encodeURIComponent(voiceId)}/content`
}

/**
 * Build URL for asset blob content (style preview images, etc.).
 * Uses encoded asset_id in path; callers must encodeURIComponent.
 */
export function getAssetBlobUrl(assetId: string): string {
  return `${BASE}/assets/blobs/${encodeURIComponent(assetId)}`
}
