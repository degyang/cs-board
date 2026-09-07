/* ==========================================================================
   Mountain Tasks API
   All task lifecycle endpoints — create, fetch, run, cancel, retry.
   ========================================================================== */

import { get, post, del, postForm } from './http'
import type {
  Task,
  TaskDetail,
  TaskQueueItem,
  RunDetail,
  StageState,
  Artifact,
  ArtifactListResponse,
  UnitListResponse,
  EventsResponse,
  LogsResponse,
} from './types'

// ---------------------------------------------------------------------------
// Health & Capabilities
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string
  version: string
  components?: Record<string, string>
}

export interface CapabilitiesResponse {
  available: boolean
  providers: string[]
  capabilities: Record<string, unknown>
}

export function fetchHealth(): Promise<HealthResponse> {
  return get('/health')
}

export function fetchCapabilities(): Promise<CapabilitiesResponse> {
  return get('/capabilities')
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export function fetchTasks(signal?: AbortSignal): Promise<Task[]> {
  return get('/tasks', signal ? { signal } : undefined)
}

export function createTask(title: string, description?: string): Promise<TaskDetail> {
  return post('/tasks', { title, description })
}

export function fetchTask(taskId: string): Promise<TaskDetail> {
  return get(`/tasks/${encodeURIComponent(taskId)}`)
}

export function deleteTask(taskId: string): Promise<void> {
  return del(`/tasks/${encodeURIComponent(taskId)}`).then(() => undefined)
}

export function uploadInputs(taskId: string, files: File[]): Promise<{ artifacts: Artifact[] }> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return postForm(`/tasks/${encodeURIComponent(taskId)}/inputs`, form)
}

export function fetchInputs(taskId: string): Promise<Artifact[]> {
  return get(`/tasks/${encodeURIComponent(taskId)}/inputs`)
}

export function fetchQueue(): Promise<TaskQueueItem[]> {
  return get('/tasks/queue')
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export function startRun(taskId: string): Promise<RunDetail> {
  return post(`/tasks/${encodeURIComponent(taskId)}/runs`)
}

export function fetchRun(taskId: string, runId: string): Promise<RunDetail> {
  return get(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}`)
}

export function cancelRun(taskId: string, runId: string): Promise<void> {
  return post(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/cancel`).then(
    () => undefined,
  )
}

export function retryRun(taskId: string, runId: string): Promise<RunDetail> {
  return post(`/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/retry`)
}

// ---------------------------------------------------------------------------
// Stages
// ---------------------------------------------------------------------------

export function fetchStages(taskId: string, runId: string): Promise<Record<string, StageState>> {
  return get(
    `/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages`,
  )
}

export function runStage(
  taskId: string,
  runId: string,
  stage: string,
): Promise<StageState> {
  return post(
    `/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(stage)}/run`,
  )
}

export function retryStage(
  taskId: string,
  runId: string,
  stage: string,
): Promise<StageState> {
  return post(
    `/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(stage)}/retry`,
  )
}

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

export function fetchUnits(taskId: string): Promise<UnitListResponse> {
  return get(`/tasks/${encodeURIComponent(taskId)}/units`)
}

// ---------------------------------------------------------------------------
// Artifacts
// ---------------------------------------------------------------------------

export function fetchArtifacts(taskId: string): Promise<ArtifactListResponse> {
  return get(`/tasks/${encodeURIComponent(taskId)}/artifacts`)
}

export function getFinalUrl(taskId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
  return `${base}/tasks/${encodeURIComponent(taskId)}/final`
}

// ---------------------------------------------------------------------------
// Events & Logs
// ---------------------------------------------------------------------------

export function fetchEvents(taskId: string): Promise<EventsResponse> {
  return get(`/tasks/${encodeURIComponent(taskId)}/events`)
}

export function fetchLogs(taskId: string, runId?: string): Promise<LogsResponse> {
  const path = runId
    ? `/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/logs`
    : `/tasks/${encodeURIComponent(taskId)}/logs`
  return get(path)
}
