import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Tabs } from '../components/ui/Tabs'
import { StatusBadge, statusText } from '../components/ui/StatusBadge'
import { useAsync } from '../lib/api/queries'
import { fetchProjects, submitCommand } from '../lib/api/client'
import { ENGINE_NAMES, STAGE_NAMES, VISUAL_SOURCE_NAMES, type ProjectSummaryView } from '../lib/api/types'
import { formatTime, shortId } from '../lib/formatting'

// 项目列表 /projects：状态过滤 Tabs + 项目卡片（04 §5）
// 取消、重试和下载使用独立按钮，不与整卡点击冲突
type FilterKey = 'all' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'legacy'

export function ProjectsPage() {
  const { data, loading } = useAsync(() => fetchProjects(), [], 15000)
  const [filter, setFilter] = useState<FilterKey>('all')
  const [query, setQuery] = useState('')

  const projects = data ?? []
  const counts = useMemo(() => {
    const c: Record<FilterKey, number> = { all: projects.length, running: 0, succeeded: 0, failed: 0, cancelled: 0, legacy: 0 }
    for (const p of projects) {
      if (p.legacy) c.legacy++
      else if (p.run) {
        const s = p.run.status
        if (s === 'running' || s === 'succeeded' || s === 'failed' || s === 'cancelled') c[s]++
      }
    }
    return c
  }, [projects])

  const tabs = [
    { key: 'all', label: '全部', count: counts.all },
    { key: 'running', label: '进行中', count: counts.running },
    { key: 'succeeded', label: '已完成', count: counts.succeeded },
    { key: 'failed', label: '失败', count: counts.failed },
    { key: 'cancelled', label: '已取消', count: counts.cancelled },
    { key: 'legacy', label: '旧版任务', count: counts.legacy },
  ]

  const visible = projects.filter((p) => {
    if (filter === 'all') return true
    if (filter === 'legacy') return !!p.legacy
    return p.run?.status === filter
  }).filter((p) => (query ? p.name.includes(query) : true))

  const cmd = (command: string, payload: Record<string, unknown>) => {
    void submitCommand(command, payload).then((r) => window.alert(r.message))
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">任务队列</h1>
        <p className="page-desc">全部任务与共享队列。取消、重试、下载为独立按钮；点击任务名进入工作台。</p>
      </div>

      <div className="filter-row">
        <div className="search">
          <input className="input" style={{ borderRadius: 'var(--nt-radius-full)', paddingLeft: 16 }} placeholder="搜索任务名…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>

      <Tabs items={tabs} active={filter} onChange={(k) => setFilter(k as FilterKey)} />

      <div style={{ marginTop: 18 }}>
        {loading && <p style={{ color: 'var(--nt-text-muted)' }}>加载中…</p>}
        {!loading && visible.length === 0 && <p style={{ color: 'var(--nt-text-muted)' }}>当前筛选下没有项目。</p>}
        {visible.map((p) => (
          <ProjectCard key={p.project_id} project={p} onCommand={cmd} />
        ))}
      </div>
    </div>
  )
}

function ProjectCard({ project, onCommand }: { project: ProjectSummaryView; onCommand: (c: string, p: Record<string, unknown>) => void }) {
  const run = project.run
  return (
    <div className="proj-card">
      <div className="proj-top">
        <h3 className="proj-name">
          <Link to={`/projects/${project.project_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
            {project.name}
          </Link>
        </h3>
        {project.legacy && <span className="badge tag-legacy">旧版 · 同步精度为等分切图</span>}
        {run && <StatusBadge status={run.status} />}
        <span className="proj-time">更新于 {formatTime(project.updated_at)}</span>
      </div>

      <div className="proj-meta">
        <span className="m">{ENGINE_NAMES[project.engine]}</span>
        <span className="m">{VISUAL_SOURCE_NAMES[project.visual_source]}</span>
        <span className="m mono">{project.pipeline_version}</span>
        {run?.current_stage && <span className="m">当前阶段：{STAGE_NAMES[run.current_stage]}</span>}
        {run && <span className="m badge tag-neutral">入口 {run.last_entry}</span>}
        {run && <span className="m mono" title={run.trace_id}>trace {shortId(run.trace_id, 12)}</span>}
      </div>

      {run && (
        <div className="proj-progress">
          <div className="progress">
            Voice Unit {run.voice_done}/{run.voice_total}
            <div className="bar"><i style={{ width: `${(run.voice_total ? run.voice_done / run.voice_total : 0) * 100}%` }} /></div>
          </div>
          <div className="progress">
            Visual Item {run.visual_done}/{run.visual_total}
            <div className="bar"><i style={{ width: `${(run.visual_total ? run.visual_done / run.visual_total : 0) * 100}%` }} /></div>
          </div>
          <div className="progress" style={{ flex: 'none', minWidth: 220 }}>
            同步质量：Whisper 成功 {run.whisper_aligned} / fallback {run.fallback}
            <div className="bar"><i style={{ width: `${run.voice_total ? (run.whisper_aligned / run.voice_total) * 100 : 0}%`, background: 'var(--nt-info-500)' }} /></div>
          </div>
        </div>
      )}

      <div className="proj-actions">
        <Link className="btn btn-ghost btn-sm" to={`/projects/${project.project_id}`}>进入工作台</Link>
        {run && (
          <Link className="btn btn-ghost btn-sm" to={`/projects/${project.project_id}/runs/${run.run_id}/diagnostics`}>
            诊断
          </Link>
        )}
        {run?.status === 'failed' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => onCommand('run.retry', { run_id: run.run_id })}>
            重试
          </button>
        )}
        {run?.status === 'running' && (
          <button type="button" className="btn btn-danger btn-sm" onClick={() => onCommand('run.cancel', { run_id: run.run_id })}>
            取消
          </button>
        )}
        {project.final_video_artifact && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.alert(`下载 ${project.final_video_artifact}（mock）`)}>
            下载成片
          </button>
        )}
        {project.legacy && (
          <span style={{ fontSize: 12, color: 'var(--nt-text-muted)', marginLeft: 4 }}>
            旧任务可查看与下载；需重渲染时显式迁移为新 Run（{statusText('stale')} → 新 pipeline）
          </span>
        )}
      </div>
    </div>
  )
}

