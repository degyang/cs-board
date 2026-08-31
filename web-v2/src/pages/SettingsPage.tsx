/* ==========================================================================
   Settings Page — Route-based sub-navigation.
   /settings redirects to /settings/models.
   ========================================================================== */

import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { StatusBadge } from '../components/ui/StatusBadge'
import { MountainApiError } from '../lib/api/http'
import { fetchServices, probeService, setDefaultService, activateService, deactivateService, deleteService } from '../lib/api/services'
import { fetchVoiceAlignment, fetchToolchain, fetchStorage, fetchDiagnostics } from '../lib/api/settings'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type {
  ServiceDefinition,
  VoiceAlignmentSettings,
  ToolchainSettings,
  StorageSettings,
  DiagnosticsSettings,
} from '../lib/api/types'

const SETTINGS_TABS = [
  { to: '/settings/models', label: '模型服务' },
  { to: '/settings/voice-alignment', label: '语音与对齐' },
  { to: '/settings/toolchain', label: '工具链' },
  { to: '/settings/storage', label: '存储' },
  { to: '/settings/diagnostics', label: '诊断' },
]

export function SettingsPage() {
  const location = useLocation()
  const currentPath = location.pathname

  // Determine which section to show based on route
  const section = SETTINGS_TABS.find(t => currentPath.startsWith(t.to))?.to ?? '/settings/models'

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">设置</h1>
        <p className="page-desc">管理系统服务和配置</p>
      </div>

      <div className="set-tabs">
        {SETTINGS_TABS.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) => `set-tab-btn${isActive ? ' active' : ''}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      <div className="set-content">
        {section === '/settings/models' && <ModelsSection />}
        {section === '/settings/voice-alignment' && <VoiceAlignmentSection />}
        {section === '/settings/toolchain' && <ToolchainSection />}
        {section === '/settings/storage' && <StorageSection />}
        {section === '/settings/diagnostics' && <DiagnosticsSection />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Models Section
// ---------------------------------------------------------------------------

function ModelsSection() {
  const [services, setServices] = useState<ServiceDefinition[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [capabilityFilter, setCapabilityFilter] = useState('')
  const [search, setSearch] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [actingId, setActingId] = useState<string | null>(null)

  const load = () => {
    setIsLoading(true)
    setError(null)
    fetchServices({ capability: capabilityFilter || undefined, q: search || undefined })
      .then(r => setServices(r.items))
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [capabilityFilter, search])

  const doAction = async (id: string, label: string, fn: () => Promise<unknown>) => {
    setActingId(id)
    setActionError(null)
    setActionSuccess(null)
    try {
      await fn()
      setActionSuccess(`${label}成功`)
      load()
    } catch (err) {
      setActionError(err instanceof MountainApiError ? `${label}失败: ${err.message}` : `${label}失败`)
    } finally {
      setActingId(null)
    }
  }

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    // §3.8: 只在 UI 输出 code/message/request_id，details 仅输出到 DevTools
    if (error.details) console.error('[Settings error details]', error.details)
    const requestId = error.details && typeof error.details === 'object' && 'request_id' in error.details
      ? (error.details as Record<string, unknown>).request_id as string
      : undefined
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        {requestId && <div className="sug">请求 ID: {requestId}</div>}
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }

  return (
    <div className="set-models">
      <div className="set-filter-row">
        <input
          type="text"
          className="input"
          placeholder="搜索服务..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          aria-label="搜索服务"
        />
        <select
          className="select"
          value={capabilityFilter}
          onChange={e => setCapabilityFilter(e.target.value)}
          aria-label="按能力筛选"
        >
          <option value="">全部能力</option>
          {Object.entries(KNOWN_CAPABILITIES).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {actionError && (
        <div className="error-card" role="alert">
          <div>{actionError}</div>
        </div>
      )}
      {actionSuccess && (
        <div className="notice notice-ok" role="status">{actionSuccess}</div>
      )}

      {services.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">暂无服务</div>
          <div className="empty-sub">尚未配置任何模型服务</div>
        </div>
      ) : (
        <div className="mp-list">
          {services.map(svc => (
            <div key={svc.service_id} className="mp-card">
              <div className="mp-card-head">
                <div className="mp-card-icon">{svc.display_name[0] ?? '?'}</div>
                <div>
                  <div className="mp-card-title">{svc.display_name}</div>
                  <div className="mp-card-desc">{svc.service_id}</div>
                </div>
                <div className="mp-card-actions" style={{ marginLeft: 'auto' }}>
                  <span className="mp-category-badge">{KNOWN_CAPABILITIES[svc.capability] ?? svc.capability}</span>
                  {svc.is_default && <span className="badge tag-info">默认</span>}
                  <StatusBadge status={svc.enabled ? 'running' : 'pending'} label={svc.enabled ? '已启用' : '已停用'} />
                </div>
              </div>
              <div className="mp-card-body">
                <span className="mp-model-chip">{KNOWN_ADAPTERS[svc.adapter_type] ?? svc.adapter_type}</span>
                {svc.model && <span className="mp-model-chip">{svc.model}</span>}
                {svc.endpoint && <span className="mp-url">{svc.endpoint}</span>}
                {svc.availability.error_code && (
                  <span className="badge st-failed">{svc.availability.error_code}</span>
                )}
                {svc.availability.suggestion && (
                  <span className="mp-info">{svc.availability.suggestion}</span>
                )}
                {svc.availability.checked_at && (
                  <span style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>
                    上次检查: {new Date(svc.availability.checked_at).toLocaleString('zh-CN')}
                    {svc.availability.latency_ms != null && ` (${svc.availability.latency_ms}ms)`}
                  </span>
                )}
              </div>
              <div className="mp-card-actions">
                <a href={`/settings/models/${svc.service_id}`} className="btn btn-ghost btn-sm">详情</a>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => doAction(svc.service_id, svc.enabled ? '停用' : '启用', () => svc.enabled ? deactivateService(svc.service_id) : activateService(svc.service_id))}
                >
                  {svc.enabled ? '停用' : '启用'}
                </button>
                {!svc.is_default && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={actingId === svc.service_id}
                    onClick={() => doAction(svc.service_id, '设为默认', () => setDefaultService(svc.service_id))}
                  >
                    设为默认
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => doAction(svc.service_id, 'Probe', () => probeService(svc.service_id))}
                >
                  Probe
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => {
                    if (window.confirm(`确定删除服务 ${svc.display_name}？`)) {
                      doAction(svc.service_id, '删除', () => deleteService(svc.service_id))
                    }
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Voice Alignment Section
// ---------------------------------------------------------------------------

function VoiceAlignmentSection() {
  const [data, setData] = useState<VoiceAlignmentSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [probing, setProbing] = useState<string | null>(null)
  const [probeResult, setProbeResult] = useState<string | null>(null)

  const load = () => {
    setIsLoading(true)
    fetchVoiceAlignment()
      .then(setData)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [])

  const doProbe = async (serviceId: string, label: string) => {
    setProbing(serviceId)
    setProbeResult(null)
    try {
      await probeService(serviceId)
      setProbeResult(`${label}测试成功`)
    } catch (err) {
      setProbeResult(err instanceof MountainApiError ? `${label}测试失败: ${err.message}` : `${label}测试失败`)
    } finally {
      setProbing(null)
    }
  }

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }
  if (!data) return <div className="empty-state"><div className="empty-title">无法获取语音与对齐状态</div></div>

  return (
    <div className="va-page">
      {probeResult && <div className="notice notice-info" role="status">{probeResult}</div>}

      <div className="card">
        <div className="card-title">语音合成</div>
        <div className="card-sub">当前默认 speech_synthesis 服务</div>
        {data.speech_synthesis ? (
          <div>
            <div className="settings-row">
              <span className="k">服务名称</span>
              <span className="v">{data.speech_synthesis.display_name}</span>
            </div>
            <div className="settings-row">
              <span className="k">端点</span>
              <span className="v mono">{data.speech_synthesis.endpoint || '—'}</span>
            </div>
            <div className="settings-row">
              <span className="k">模型</span>
              <span className="v mono">{data.speech_synthesis.model || '—'}</span>
            </div>
            <div className="settings-row">
              <span className="k">可用性</span>
              <span className="v">
                <StatusBadge status={data.speech_synthesis.availability.available ? 'succeeded' : 'failed'} />
                {data.speech_synthesis.availability.checked_at && (
                  <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--nt-text-muted)' }}>
                    {new Date(data.speech_synthesis.availability.checked_at).toLocaleString('zh-CN')}
                  </span>
                )}
              </span>
            </div>
            {data.speech_synthesis.availability.error_code && (
              <div className="settings-row">
                <span className="k">错误</span>
                <span className="v" style={{ color: 'var(--nt-danger)' }}>{data.speech_synthesis.availability.error_code}</span>
              </div>
            )}
            {data.speech_synthesis.availability.suggestion && (
              <div className="settings-row">
                <span className="k">建议</span>
                <span className="v">{data.speech_synthesis.availability.suggestion}</span>
              </div>
            )}
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <a href={`/settings/models/${data.speech_synthesis.service_id}`} className="btn btn-ghost btn-sm">查看详情</a>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={probing === data.speech_synthesis.service_id}
                onClick={() => doProbe(data.speech_synthesis!.service_id, '语音合成')}
              >
                {probing === data.speech_synthesis.service_id ? '测试中...' : '测试语音服务'}
              </button>
            </div>
          </div>
        ) : (
          <div className="empty-sub">未配置默认语音合成服务</div>
        )}
      </div>

      <div className="card">
        <div className="card-title">语音对齐</div>
        <div className="card-sub">当前默认 speech_alignment 服务</div>
        {data.speech_alignment ? (
          <div>
            <div className="settings-row">
              <span className="k">服务名称</span>
              <span className="v">{data.speech_alignment.display_name}</span>
            </div>
            <div className="settings-row">
              <span className="k">端点</span>
              <span className="v mono">{data.speech_alignment.endpoint || '—'}</span>
            </div>
            <div className="settings-row">
              <span className="k">模型</span>
              <span className="v mono">{data.speech_alignment.model || '—'}</span>
            </div>
            <div className="settings-row">
              <span className="k">可用性</span>
              <span className="v">
                <StatusBadge status={data.speech_alignment.availability.available ? 'succeeded' : 'failed'} />
                {data.speech_alignment.availability.checked_at && (
                  <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--nt-text-muted)' }}>
                    {new Date(data.speech_alignment.availability.checked_at).toLocaleString('zh-CN')}
                  </span>
                )}
              </span>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <a href={`/settings/models/${data.speech_alignment.service_id}`} className="btn btn-ghost btn-sm">查看详情</a>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={probing === data.speech_alignment.service_id}
                onClick={() => doProbe(data.speech_alignment!.service_id, '语音对齐')}
              >
                {probing === data.speech_alignment.service_id ? '测试中...' : '测试对齐服务'}
              </button>
            </div>
          </div>
        ) : (
          <div className="empty-sub">未配置默认语音对齐服务</div>
        )}
      </div>

      {data.indextts && (
        <div className="card">
          <div className="card-title">IndexTTS</div>
          <div className="settings-row">
            <span className="k">状态</span>
            <span className="v"><StatusBadge status={data.indextts.available ? 'succeeded' : 'failed'} /></span>
          </div>
          {data.indextts.component && (
            <div className="settings-row">
              <span className="k">组件</span>
              <span className="v mono">{data.indextts.component}</span>
            </div>
          )}
          {data.indextts.error_code && (
            <div className="settings-row">
              <span className="k">错误</span>
              <span className="v" style={{ color: 'var(--nt-danger)' }}>{data.indextts.error_code}</span>
            </div>
          )}
          {data.indextts.suggestion && (
            <div className="settings-row">
              <span className="k">建议</span>
              <span className="v">{data.indextts.suggestion}</span>
            </div>
          )}
        </div>
      )}

      {data.whisper && (
        <div className="card">
          <div className="card-title">Whisper</div>
          <div className="settings-row">
            <span className="k">状态</span>
            <span className="v"><StatusBadge status={data.whisper.available ? 'succeeded' : 'failed'} /></span>
          </div>
          {data.whisper.component && (
            <div className="settings-row">
              <span className="k">组件</span>
              <span className="v mono">{data.whisper.component}</span>
            </div>
          )}
          {data.whisper.error_code && (
            <div className="settings-row">
              <span className="k">错误</span>
              <span className="v" style={{ color: 'var(--nt-danger)' }}>{data.whisper.error_code}</span>
            </div>
          )}
          {data.whisper.suggestion && (
            <div className="settings-row">
              <span className="k">建议</span>
              <span className="v">{data.whisper.suggestion}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Toolchain Section
// ---------------------------------------------------------------------------

function ToolchainSection() {
  const [data, setData] = useState<ToolchainSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  const load = () => {
    setIsLoading(true)
    fetchToolchain()
      .then(setData)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [])

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }
  if (!data) return <div className="empty-state"><div className="empty-title">无法获取工具链状态</div></div>

  return (
    <div className="tc-page">
      {data.tools.map(tool => (
        <div key={tool.component} className="card">
          <div className="card-title">{tool.component}</div>
          <div className="settings-row">
            <span className="k">状态</span>
            <span className="v"><StatusBadge status={tool.available ? 'succeeded' : 'failed'} /></span>
          </div>
          {tool.version && (
            <div className="settings-row">
              <span className="k">版本</span>
              <span className="v mono">{tool.version}</span>
            </div>
          )}
          {tool.error_code && (
            <div className="settings-row">
              <span className="k">错误</span>
              <span className="v" style={{ color: 'var(--nt-danger)' }}>{tool.error_code}</span>
            </div>
          )}
          {tool.suggestion && (
            <div className="settings-row">
              <span className="k">建议</span>
              <span className="v">{tool.suggestion}</span>
            </div>
          )}
        </div>
      ))}
      {data.tools.length === 0 && (
        <div className="empty-state"><div className="empty-title">暂无工具链信息</div></div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Storage Section
// ---------------------------------------------------------------------------

function StorageSection() {
  const [data, setData] = useState<StorageSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  const load = () => {
    setIsLoading(true)
    fetchStorage()
      .then(setData)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [])

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }
  if (!data) return <div className="empty-state"><div className="empty-title">无法获取存储状态</div></div>

  return (
    <div className="st-page">
      <div className="card">
        <div className="card-title">存储状态</div>
        <div className="settings-row">
          <span className="k">可写</span>
          <span className="v"><StatusBadge status={data.writable ? 'succeeded' : 'failed'} /></span>
        </div>
        <div className="settings-row">
          <span className="k">素材可用</span>
          <span className="v"><StatusBadge status={data.assets_available ? 'succeeded' : 'failed'} /></span>
        </div>
        <div className="settings-row">
          <span className="k">任务可用</span>
          <span className="v"><StatusBadge status={data.tasks_available ? 'succeeded' : 'failed'} /></span>
        </div>
        <div className="settings-row">
          <span className="k">临时目录可用</span>
          <span className="v"><StatusBadge status={data.temp_available ? 'succeeded' : 'failed'} /></span>
        </div>
        {data.free_bytes != null && (
          <div className="settings-row">
            <span className="k">可用空间</span>
            <span className="v">{formatBytes(data.free_bytes)}</span>
          </div>
        )}
        {data.used_bytes != null && (
          <div className="settings-row">
            <span className="k">已用空间</span>
            <span className="v">{formatBytes(data.used_bytes)}</span>
          </div>
        )}
        {data.cleanup_policy && (
          <div className="settings-row">
            <span className="k">清理策略</span>
            <span className="v">{data.cleanup_policy}</span>
          </div>
        )}
        {data.error_code && (
          <div className="settings-row">
            <span className="k">错误</span>
            <span className="v" style={{ color: 'var(--nt-danger)' }}>{data.error_code}</span>
          </div>
        )}
        {data.suggestion && (
          <div className="settings-row">
            <span className="k">建议</span>
            <span className="v">{data.suggestion}</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Diagnostics Section
// ---------------------------------------------------------------------------

function DiagnosticsSection() {
  const [data, setData] = useState<DiagnosticsSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  const load = () => {
    setIsLoading(true)
    fetchDiagnostics()
      .then(setData)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [])

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }
  if (!data) return <div className="empty-state"><div className="empty-title">无法获取诊断状态</div></div>

  return (
    <div className="dg-page">
      <div className="card">
        <div className="card-title">诊断检查</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginBottom: 12 }}>刷新</button>
        <div className="settings-row">
          <span className="k">API 状态</span>
          <span className="v">
            <StatusBadge status={data.api.status === 'ok' ? 'succeeded' : 'failed'} />
            {data.api.latency_ms != null && <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--nt-text-muted)' }}>{data.api.latency_ms}ms</span>}
          </span>
        </div>
        <div className="settings-row">
          <span className="k">服务</span>
          <span className="v">总计 {data.services.total} | 可用 {data.services.available} | 不可用 {data.services.unavailable}</span>
        </div>
        <div className="settings-row">
          <span className="k">工具链</span>
          <span className="v">总计 {data.toolchain.total} | 可用 {data.toolchain.available} | 缺失 {data.toolchain.missing}</span>
        </div>
        <div className="settings-row">
          <span className="k">存储</span>
          <span className="v">
            <StatusBadge status={data.storage.writable ? 'succeeded' : 'failed'} />
            {data.storage.free_bytes != null && <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--nt-text-muted)' }}>{formatBytes(data.storage.free_bytes)}</span>}
          </span>
        </div>
        {data.telemetry && (
          <div className="settings-row">
            <span className="k">遥测</span>
            <span className="v">{data.telemetry.enabled ? '已启用' : '未启用'}</span>
          </div>
        )}
        {data.logs && (
          <div className="settings-row">
            <span className="k">近期错误</span>
            <span className="v">
              <StatusBadge status={data.logs.recent_errors > 0 ? 'pending' : 'succeeded'} />
              <span style={{ marginLeft: 8 }}>{data.logs.recent_errors}</span>
            </span>
          </div>
        )}
      </div>

      {data.recent_errors.length > 0 && (
        <div className="card">
          <div className="card-title">最近错误</div>
          {data.recent_errors.map((err, i) => (
            <div key={i} className="settings-row">
              <span className="k" style={{ width: 140 }}>{new Date(err.timestamp).toLocaleString('zh-CN')}</span>
              <span className="v">
                <span className="badge st-failed" style={{ marginRight: 8 }}>{err.component}</span>
                {err.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(n?: number | null): string {
  if (!n || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}
