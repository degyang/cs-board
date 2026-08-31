/* ==========================================================================
   Mountain API Client — 集中式 fetch 封装
   所有组件通过此模块调用 /api/v1，禁止自行 fetch
   ========================================================================== */

import type {
  HealthResponse,
  CapabilitiesResponse,
  TaskListResponse,
  CreateTaskRequest,
  CreateTaskResponse,
  TaskDetail,
  RunDetail,
  UnitListResponse,
  ArtifactListResponse,
  EventsResponse,
  LogsResponse,
  PipelineRunResponse,
  CancelRunResponse,
  SaveInputsResponse,
  InputsReadback,
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

/**
 * POST multipart/form-data — 必须由浏览器自动设置 Content-Type（含 boundary）。
 * 禁止手工设置 Content-Type。
 */
async function postForm<T>(path: string, form: FormData): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    method: 'POST',
    body: form,
    // 不设置 Content-Type，浏览器自动设置 multipart/form-data + boundary
  })

  if (!res.ok) {
    let apiError: ApiError | null = null
    try {
      const body = await res.json()
      apiError = typeof body.detail === 'object' ? body.detail : null
    } catch {
      // ignore
    }
    throw new MountainApiError(
      res.status,
      apiError,
      apiError?.message ?? `API error: ${res.status}`,
    )
  }

  return res.json() as Promise<T>
}

// ── Inputs ──────────────────────────────────────────────────────────────

/**
 * 保存制作输入（multipart/form-data）
 * 禁止手工设置 Content-Type — 浏览器自动设置 boundary。
 * 禁止读取/缓存/打印参考音频内容。
 */
export function uploadInputs(taskId: string, form: FormData): Promise<SaveInputsResponse> {
  return postForm<SaveInputsResponse>(
    `/tasks/${encodeURIComponent(taskId)}/inputs`,
    form,
  )
}

/**
 * 读取已保存的任务制作输入。
 * 返回 saved:false + inputs:null 表示尚未保存。
 */
export function fetchInputs(taskId: string): Promise<InputsReadback> {
  return get<InputsReadback>(`/tasks/${encodeURIComponent(taskId)}/inputs`)
}

// ── Health ──────────────────────────────────────────────────────────────

export function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>('/health')
}

// ── Capabilities ────────────────────────────────────────────────────────

export function fetchCapabilities(): Promise<CapabilitiesResponse> {
  return get<CapabilitiesResponse>('/capabilities')
}

// ── Tasks ────────────────────────────────────────────────────────────

export function fetchTasks(params?: { limit?: number; cursor?: string; status?: string; q?: string }): Promise<TaskListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.cursor) searchParams.set('cursor', params.cursor)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.q) searchParams.set('q', params.q)
  const qs = searchParams.toString()
  return get<TaskListResponse>(`/tasks${qs ? '?' + qs : ''}`)
}

export function createTask(
  req: CreateTaskRequest,
): Promise<CreateTaskResponse> {
  return post<CreateTaskResponse>('/tasks', req)
}

export function fetchTask(id: string): Promise<TaskDetail> {
  return get<TaskDetail>(`/tasks/${encodeURIComponent(id)}`)
}

// ── Runs ────────────────────────────────────────────────────────────────

export function fetchRun(taskId: string, runId: string): Promise<RunDetail> {
  return get<RunDetail>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}`)
}

export function startRun(taskId: string, runId: string): Promise<PipelineRunResponse> {
  return post<PipelineRunResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/start`)
}

export function cancelRun(taskId: string, runId: string): Promise<CancelRunResponse> {
  return post<CancelRunResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/cancel`)
}

export function retryRun(taskId: string, runId: string): Promise<PipelineRunResponse> {
  return post<PipelineRunResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/retry`)
}

// ── Stages ──────────────────────────────────────────────────────────────

export function fetchStages(taskId: string, runId: string): Promise<{ items: Array<{ stage: string } & Record<string, unknown>> }> {
  return get(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages`)
}

export function runStage(taskId: string, runId: string, stage: string): Promise<PipelineRunResponse> {
  return post<PipelineRunResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(stage)}/run`)
}

export function retryStage(taskId: string, runId: string, stage: string): Promise<PipelineRunResponse> {
  return post<PipelineRunResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(stage)}/retry`)
}

// ── Units ───────────────────────────────────────────────────────────────

export function fetchUnits(taskId: string, runId: string): Promise<UnitListResponse> {
  return get<UnitListResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/units`)
}

// ── Artifacts ───────────────────────────────────────────────────────────

export function fetchArtifacts(taskId: string, runId: string): Promise<ArtifactListResponse> {
  return get<ArtifactListResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/artifacts`)
}

// ── Events ──────────────────────────────────────────────────────────────

export function fetchEvents(taskId: string, runId: string, after = 0): Promise<EventsResponse> {
  return get<EventsResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/events?after=${after}`)
}

// ── Logs ────────────────────────────────────────────────────────────────

export function fetchLogs(taskId: string, runId: string, filters?: { level?: string; component?: string; stage?: string }): Promise<LogsResponse> {
  const params = new URLSearchParams()
  if (filters?.level) params.set('level', filters.level)
  if (filters?.component) params.set('component', filters.component)
  if (filters?.stage) params.set('stage', filters.stage)
  const qs = params.toString()
  return get<LogsResponse>(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/logs${qs ? '?' + qs : ''}`)
}

// ── Final Video ─────────────────────────────────────────────────────────

export function getFinalUrl(taskId: string, runId: string): string {
  return `${BASE}/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/final`
}
