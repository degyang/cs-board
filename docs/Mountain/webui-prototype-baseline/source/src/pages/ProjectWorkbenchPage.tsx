import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { CopyButton } from '../components/ui/CopyButton'
import { BackButton } from '../components/ui/BackButton'
import { useAsync } from '../lib/api/queries'
import { fetchProjectDetail, submitCommand } from '../lib/api/client'
import { STAGE_KEYS, type StageKey } from '../lib/api/types'
import { StageTimeline } from '../features/stage-timeline/StageTimeline'
import { VoiceUnitList } from '../features/voice-units/VoiceUnitList'
import { ArtifactPanel } from '../features/artifact-gallery/ArtifactPanel'
import { StageWorkspace } from '../features/project-workbench/StageWorkspace'
import { RunActivityPanel } from '../features/run-activity/RunActivityPanel'
import { ENGINE_NAMES, VISUAL_SOURCE_NAMES } from '../lib/api/types'
import { formatTime } from '../lib/formatting'

// 项目工作台 /projects/:projectId（04 §6）
// 布局：标题/Run 状态/操作 → 六阶段时间线 → Unit 列表 | 阶段工作区 | 产物栏 → 活动与诊断（可折叠）
export function ProjectWorkbenchPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data, loading } = useAsync(() => fetchProjectDetail(projectId ?? ''), [projectId], 15000)
  const [stage, setStage] = useState<StageKey | null>(null)
  const [unitId, setUnitId] = useState<string | null>(null)

  if (loading || !data) return <div className="page"><p style={{ color: 'var(--nt-text-muted)' }}>加载中…</p></div>

  const { project, run } = data
  const currentStage = run.stages.find((s) => s.status === 'running')?.stage
    ?? [...run.stages].reverse().find((s) => s.status === 'succeeded')?.stage
    ?? STAGE_KEYS[0]
  const activeStage = stage ?? currentStage

  const cmd = (command: string, payload: Record<string, unknown>) => {
    void submitCommand(command, payload).then((r) => window.alert(r.message))
  }

  return (
    <>
      <div className="topbar">
        <BackButton to="/projects" label="返回任务队列" />
        <span className="crumb">
          <Link to="/projects">任务队列</Link> / <span style={{ color: 'var(--nt-text)' }}>{project.name}</span>
        </span>
        <span className="crumb mono" style={{ marginLeft: 'auto', fontSize: 12 }}>
          {ENGINE_NAMES[project.engine]} · {VISUAL_SOURCE_NAMES[project.visual_source]} · {project.pipeline_version} · 更新 {formatTime(project.updated_at)}
        </span>
      </div>

      <div className="page">
        <div className="wb-header">
          <h1 className="page-title" style={{ fontSize: 20 }}>{project.name}</h1>
          <StatusBadge status={run.status} />
          <span className="trace-chip">
            run <span className="mono">{run.run_id}</span>
          </span>
          <span className="trace-chip">
            trace <span className="mono">{run.trace_id}</span>
            <CopyButton text={run.trace_id} />
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {run.status === 'running' && (
              <button type="button" className="btn btn-danger btn-sm" onClick={() => cmd('run.cancel', { run_id: run.run_id })}>取消</button>
            )}
            {run.status === 'failed' && (
              <button type="button" className="btn btn-primary btn-sm" onClick={() => cmd('run.retry', { run_id: run.run_id })}>重试</button>
            )}
            {project.final_video_artifact && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.alert('下载成片（mock）')}>下载成片</button>
            )}
          </div>
        </div>

        <StageTimeline stages={run.stages} selected={activeStage} onSelect={setStage} />

        <div className="wb-body">
          <VoiceUnitList run={run} selectedUnit={unitId} onSelectUnit={setUnitId} />
          <StageWorkspace run={run} stage={activeStage} selectedUnitId={unitId} />
          <ArtifactPanel artifacts={run.artifacts} />
        </div>

        <RunActivityPanel projectId={project.project_id} runId={run.run_id} traceId={run.trace_id} collapsible initialOpen={false} />
      </div>
    </>
  )
}

