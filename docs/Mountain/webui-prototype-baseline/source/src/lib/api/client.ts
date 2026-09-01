// API client — 统一入口
// 后端就绪前默认走 mock View；设置 VITE_USE_MOCK=off 后走真实 /api
// 命令统一走共享 Application Command（04 §6.4），前端不通过删文件等旁路表达「重做」
import * as mock from './mock'
import type {
  CapabilityView,
  CurrentRunInfo,
  DiagnosticBundleView,
  EngineKind,
  ErrorChainView,
  LogEntryView,
  ProjectDetailView,
  ProjectSummaryView,
  RunMetricsView,
  ServiceHealthView,
  SettingsSectionView,
  TraceEventView,
  VisualSourceKind,
} from './types'

const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'
const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK !== 'off'

async function get<T>(path: string, fallback: T): Promise<T> {
  if (USE_MOCK) return fallback
  try {
    const res = await fetch(API_BASE + path, { headers: { Accept: 'application/json' } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } catch {
    // 后端不可达时回退 mock，保证前端可独立开发
    return fallback
  }
}

export const fetchProjects = (): Promise<ProjectSummaryView[]> =>
  get<ProjectSummaryView[]>('/projects', mock.projects)

export const fetchProjectDetail = (projectId: string): Promise<ProjectDetailView> =>
  get<ProjectDetailView>(`/projects/${projectId}`, mock.projectDetail(projectId))

export const fetchCapability = (
  engine: EngineKind,
  visual_source: VisualSourceKind,
): Promise<CapabilityView> =>
  get<CapabilityView>(
    `/capabilities?engine=${engine}&visual_source=${visual_source}`,
    mock.capability(engine, visual_source),
  )

export const fetchServiceHealth = (): Promise<ServiceHealthView[]> =>
  get<ServiceHealthView[]>('/settings/health', mock.serviceHealth)

export const fetchSettingsSections = (): Promise<SettingsSectionView[]> =>
  get<SettingsSectionView[]>('/settings', mock.settingsSections)

export const fetchEvents = (projectId: string, runId: string, after = 0): Promise<TraceEventView[]> =>
  get<TraceEventView[]>(`/projects/${projectId}/runs/${runId}/events?after=${after}`, mock.events(after))

export const fetchLogs = (projectId: string, runId: string): Promise<LogEntryView[]> =>
  get<LogEntryView[]>(`/projects/${projectId}/runs/${runId}/logs`, mock.logs())

export const fetchMetrics = (projectId: string, runId: string): Promise<RunMetricsView> =>
  get<RunMetricsView>(`/projects/${projectId}/runs/${runId}/metrics`, mock.metrics)

export const fetchErrorChains = (projectId: string): Promise<ErrorChainView[]> =>
  get<ErrorChainView[]>(`/projects/${projectId}/errors`, mock.errorChains[projectId] ?? [])

export const fetchDiagnosticBundles = (projectId: string, runId: string): Promise<DiagnosticBundleView[]> =>
  get<DiagnosticBundleView[]>(`/projects/${projectId}/runs/${runId}/diagnostics`, mock.diagnosticBundles)

export const fetchCurrentRun = (): Promise<CurrentRunInfo | null> =>
  get<CurrentRunInfo | null>('/runs/current', mock.currentRun)

// 共享 Application Command：保存项目 / 创建并启动 Run / 取消 / 重试 / Stage 重跑 /
// Unit 重试 / Visual 重生成 / 重新合成 / 导出诊断包
export interface CommandResult {
  ok: boolean
  command_id?: string
  project_id?: string
  run_id?: string
  trace_id?: string
  message: string
}

export async function submitCommand(
  command: string,
  payload: Record<string, unknown>,
): Promise<CommandResult> {
  if (USE_MOCK) {
    return {
      ok: true,
      command_id: 'cmd-' + Math.random().toString(16).slice(2, 8),
      project_id: 'p-2402',
      run_id: 'run-78d0',
      trace_id: 'tr-new-' + Math.random().toString(16).slice(2, 6),
      message: `命令 ${command} 已受理（mock）`,
    }
  }
  try {
    const res = await fetch(`${API_BASE}/commands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, payload }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as CommandResult
  } catch {
    return { ok: false, message: `命令 ${command} 提交失败：后端不可达` }
  }
}

