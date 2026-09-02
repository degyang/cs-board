import { useParams, Link } from 'react-router-dom'
import { useState, useCallback, useEffect, useRef } from 'react'
import { useAsync } from '../lib/api/queries'
import {
  fetchTask, fetchCapabilities, fetchUnits, fetchEvents, fetchLogs,
  cancelRun,
  uploadInputs, fetchInputs, getFinalUrl,
} from '../lib/api/client'
import { formatTime, shortId, formatBytes, formatMs } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { CopyButton } from '../components/ui/CopyButton'
import { BackButton } from '../components/ui/BackButton'
import { STAGE_KEYS, STAGE_NAMES } from '../lib/api/types'
import type { StageKey } from '../lib/api/types'

// ── Polling helper ──────────────────────────────────────────────────────

function isTerminal(status: string): boolean {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled'
}

export type StageContractMetadata = {
  id: StageKey
  title: string
  entry: string
  persistedInputs: string
  outputs: string
  exit: string
  operations: string
}

/** One typed source of truth for the six first-phase stage contract cards. */
export const STAGE_CONTRACTS: readonly StageContractMetadata[] = [
  {
    id: 'generate-visual-anchors', title: STAGE_NAMES['generate-visual-anchors'],
    entry: '已保存视频文案', persistedInputs: '文案、风格', outputs: '画面锚点数据',
    exit: '画面锚定可供分镜使用', operations: '人工检查锚点后等待 Gate',
  },
  {
    id: 'clone-voice', title: STAGE_NAMES['clone-voice'],
    entry: '文案已分段且参考音频已保存', persistedInputs: '文案、参考音频', outputs: '配音单元与音频',
    exit: '配音单元与时长可供后续阶段使用', operations: '人工确认声音结果后等待 Gate',
  },
  {
    id: 'plan-storyboard', title: STAGE_NAMES['plan-storyboard'],
    entry: '画面锚点与配音单元可用', persistedInputs: '画面锚点、配音单元', outputs: '分镜计划',
    exit: '每个单元都有分镜计划', operations: '人工检查分镜后等待 Gate',
  },
  {
    id: 'generate-illustrations', title: STAGE_NAMES['generate-illustrations'],
    entry: '分镜计划已完成', persistedInputs: '分镜计划、风格', outputs: 'Codex 生成的插画候选',
    exit: '人工选择候选插画并确认', operations: '生成候选 → 人工选择 → 等待 Gate',
  },
  {
    id: 'render-visuals', title: STAGE_NAMES['render-visuals'],
    entry: '已选择插画且分镜通过 Gate', persistedInputs: '分镜计划、已选插画', outputs: '视觉序列',
    exit: '视觉序列渲染完成', operations: '人工检查渲染后等待 Gate',
  },
  {
    id: 'compose-video', title: STAGE_NAMES['compose-video'],
    entry: '视觉序列与配音均通过 Gate', persistedInputs: '视觉序列、音频', outputs: '最终视频',
    exit: '成片可下载并通过最终检查', operations: '人工验收成片后等待 Gate',
  },
]

const GATE_UNAVAILABLE = '后端 Gate 契约正在收口，CCB-25 通过后启用'

// ── Component ───────────────────────────────────────────────────────────

export function TaskWorkbenchPage() {
  const { taskId } = useParams<{ taskId: string }>()

  // ── Task data (10s poll, stop on terminal) ────────────────────────
  const [pollMs, setPollMs] = useState<number | undefined>(10_000)
  const taskLoader = useCallback(() => fetchTask(taskId!), [taskId])
  const { data: taskData, loading: taskLoading, error: taskError } = useAsync(taskLoader, [taskId], pollMs)

  const taskIdentityMatches = Boolean(taskId && taskData?.task.task_id === taskId)
  const task = taskIdentityMatches ? taskData?.task : undefined
  const activeRun = taskIdentityMatches ? taskData?.active_run ?? null : null
  const stages = taskIdentityMatches ? taskData?.stages ?? [] : []
  const artifacts = taskIdentityMatches ? taskData?.artifacts ?? [] : []
  const trace = taskIdentityMatches ? taskData?.trace ?? null : null
  const runId = activeRun?.run_id

  // Stop polling on terminal state
  useEffect(() => {
    if (activeRun && isTerminal(activeRun.status)) {
      setPollMs(undefined)
    }
  }, [activeRun?.status])

  // ── Capabilities ─────────────────────────────────────────────────────
  const capLoader = useCallback(() => fetchCapabilities(), [])
  const { data: capData } = useAsync(capLoader, [])

  const unavailableProviders = capData?.providers.unavailable ?? []
  const hasCapability = capData !== null && capData.providers.all_available === true

  // ── Saved inputs readback ──────────────────────────────────────────────
  const inputsLoader = useCallback(() => {
    if (!taskId) return Promise.resolve(null)
    return fetchInputs(taskId)
  }, [taskId])
  const { data: inputsDataRaw } = useAsync(inputsLoader, [taskId])
  const inputsData = inputsDataRaw?.task_id === taskId ? inputsDataRaw : null

  // ── Units (poll with task) ────────────────────────────────────────
  const unitsLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve({ items: [] })
    return fetchUnits(taskId, runId)
  }, [taskId, runId])
  const { data: unitsData } = useAsync(unitsLoader, [taskId, runId], pollMs)
  const units = unitsData?.items ?? []

  // ── Events (cursor pagination) ───────────────────────────────────────
  const [eventCursor, setEventCursor] = useState(0)
  const [allEvents, setAllEvents] = useState<Record<string, unknown>[]>([])
  const eventIdsRef = useRef(new Set<string>())
  const eventIdentity = `${taskId ?? ''}:${runId ?? ''}`
  const eventIdentityRef = useRef(eventIdentity)
  const eventIdentityMatches = eventIdentityRef.current === eventIdentity

  useEffect(() => {
    if (eventIdentityRef.current === eventIdentity) return
    eventIdentityRef.current = eventIdentity
    setEventCursor(0)
    setAllEvents([])
    eventIdsRef.current.clear()
  }, [eventIdentity])

  const eventsLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve({ items: [], next_cursor: 0 })
    return fetchEvents(taskId, runId, eventIdentityMatches ? eventCursor : 0)
  }, [taskId, runId, eventCursor, eventIdentityMatches])
  const { data: eventsData } = useAsync(eventsLoader, [taskId, runId, eventIdentityMatches ? eventCursor : 0], pollMs)

  // Append new events (dedup by sequence or index)
  useEffect(() => {
    if (!eventIdentityMatches || !eventsData?.items?.length) return
    const newEvents = eventsData.items.filter((ev) => {
      const key = String(ev.sequence ?? ev.timestamp ?? JSON.stringify(ev))
      if (eventIdsRef.current.has(key)) return false
      eventIdsRef.current.add(key)
      return true
    })
    if (newEvents.length > 0) {
      setAllEvents((prev) => [...prev, ...newEvents])
    }
    if (eventsData.next_cursor > eventCursor) {
      setEventCursor(eventsData.next_cursor)
    }
  }, [eventsData, eventIdentityMatches])

  // ── Logs ─────────────────────────────────────────────────────────────
  const [logFilter, setLogFilter] = useState({ level: '', component: '', stage: '' })
  const logsLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve({ items: [] })
    return fetchLogs(taskId, runId, logFilter.level || logFilter.component || logFilter.stage ? logFilter : undefined)
  }, [taskId, runId, logFilter])
  const { data: logsData } = useAsync(logsLoader, [taskId, runId, logFilter], pollMs)
  const logs = logsData?.items ?? []

  // ── Activity panel state ──────────────────────────────────────────────
  const [showActivity, setShowActivity] = useState(true)

  // ── Inputs state ─────────────────────────────────────────────────────
  const [inputsSaved, setInputsSaved] = useState(false)
  const [script, setScript] = useState('')
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [savedAudioFilename, setSavedAudioFilename] = useState<string | null>(null)
  const [savedAudioSize, setSavedAudioSize] = useState<number | null>(null)
  const [style, setStyle] = useState('')
  const [includeSubtitles, setIncludeSubtitles] = useState(false)
  const [penText, setPenText] = useState('')
  const [strokeDetail, setStrokeDetail] = useState('')

  // Restore saved inputs when readback data arrives.
  // Only initializes on first load (inputsSaved is false) to avoid overwriting edits.
  useEffect(() => {
    if (!inputsData?.saved || !inputsData.inputs || inputsSaved) return
    setScript(inputsData.inputs.script)
    setStyle(inputsData.inputs.style)
    setIncludeSubtitles(inputsData.inputs.include_subtitles)
    setPenText(inputsData.inputs.pen_text)
    setStrokeDetail(inputsData.inputs.stroke_detail)
    if (inputsData.reference_audio.uploaded) {
      setSavedAudioFilename(inputsData.reference_audio.filename)
      setSavedAudioSize(inputsData.reference_audio.size_bytes)
    }
    setInputsSaved(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputsData])

  // ── Action state ─────────────────────────────────────────────────────
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  function clearFeedback() {
    setActionError(null)
    setActionSuccess(null)
  }

  // ── Save inputs ──────────────────────────────────────────────────────
  async function handleSaveInputs() {
    if (!taskId) return
    if (!script.trim()) {
      setActionError('请输入视频文案')
      return
    }
    if (!referenceFile && !savedAudioFilename) {
      setActionError('请上传参考音频')
      return
    }
    setActionLoading('inputs')
    clearFeedback()
    try {
      const form = new FormData()
      form.set('script', script)
      if (referenceFile) form.set('reference', referenceFile)
      if (style) form.set('style', style)
      form.set('include_subtitles', String(includeSubtitles))
      if (penText) form.set('pen_text', penText)
      if (strokeDetail) form.set('stroke_detail', strokeDetail)
      const res = await uploadInputs(taskId, form)
      if (res.ok) {
        setInputsSaved(true)
        setActionSuccess('制作输入已保存')
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setActionLoading(null)
    }
  }

  // ── Cancel / Retry ───────────────────────────────────────────────────
  async function handleCancel() {
    if (!taskId || !runId) return
    setActionLoading('cancel')
    clearFeedback()
    try {
      await cancelRun(taskId, runId)
      setActionSuccess('已取消')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '取消失败')
    } finally {
      setActionLoading(null)
    }
  }


  // ── Loading / Error states ───────────────────────────────────────────
  if (taskLoading && !taskData) {
    return <div className="page"><p className="loading"><span className="spinner" />加载中…</p></div>
  }
  if (taskError) {
    return (
      <div className="page">
        <BackButton to="/" label="返回任务队列" />
        <div className="error-card"><span className="code">加载失败</span><p className="sug">{taskError}</p></div>
      </div>
    )
  }
  if (!task) {
    return (
      <div className="page">
        <BackButton to="/" label="返回任务队列" />
        <div className="empty-state"><div className="empty-illu">🔍</div><div className="empty-title">任务不存在</div></div>
      </div>
    )
  }

  // ── Derived state ────────────────────────────────────────────────────
  const stageStatuses: Record<string, string> = {}
  for (const s of stages) stageStatuses[s.stage] = s.status
  for (const key of STAGE_KEYS) if (!stageStatuses[key]) stageStatuses[key] = 'unreported'

  const completedCount = STAGE_KEYS.filter((k) => stageStatuses[k] === 'succeeded').length
  const stageStatusLabel = (status: string) => status === 'unreported' ? '尚未报告' : status
  const visibleEvents = eventIdentityMatches ? allEvents : []
  const hasFinal = artifacts.some((a) => a.producer_stage === 'compose-video' && a.status === 'succeeded')
  const runStatus = activeRun?.status ?? task.status
  const isRunning = activeRun?.status === 'running'

  return (
    <div className="page">
      <BackButton to="/" label="返回任务队列" />

      {/* ── Top bar ────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h1 className="page-title">{task.title || `任务 ${shortId(task.task_id)}`}</h1>
          <StatusBadge status={runStatus} />
          <span style={{ fontSize: 12, color: 'var(--nt-text-muted)' }}>创建于 {formatTime(task.created_at)}</span>
        </div>

        <div className="chip-ids">
          <span className="id-chip">task: {shortId(task.task_id)}<CopyButton text={task.task_id} /></span>
          {activeRun && (
            <>
              <span className="id-chip">run: {shortId(activeRun.run_id)}<CopyButton text={activeRun.run_id} /></span>
              <span className="id-chip">trace: {shortId(activeRun.trace_id)}<CopyButton text={activeRun.trace_id} /></span>
            </>
          )}
          {!activeRun && trace && (
            <span className="id-chip">trace: {shortId(trace.trace_id)}<CopyButton text={trace.trace_id} /></span>
          )}
        </div>

        {/* Capability warning */}
        {!hasCapability && capData && (
          <div className="notice notice-warn" style={{ marginTop: 8 }}>
            <strong>Provider 不可用：</strong>
            {unavailableProviders.map((name) => {
              const info = capData.providers.providers[name]
              return (
                <span key={name} style={{ display: 'block', marginTop: 4 }}>
                  <Link to={`/settings/models/${name}`} style={{ fontWeight: 600 }}>{name}</Link>
                  {info?.error_code && <span> — {info.error_code}</span>}
                  {info?.suggestion && <span style={{ display: 'block', fontSize: 12, color: 'var(--nt-text-muted)', marginLeft: 16 }}>💡 {info.suggestion}</span>}
                </span>
              )
            })}
          </div>
        )}

        {/* Run control buttons */}
        <div className="run-actions" style={{ marginTop: 12 }}>
          {activeRun?.status === 'pending' && (
            <span className="hint">运行等待人工逐阶段操作；Gate 契约就绪后才能执行阶段。</span>
          )}
          {isRunning && (
            <button className="btn btn-danger btn-sm" onClick={handleCancel} disabled={actionLoading !== null}>
              {actionLoading === 'cancel' ? <><span className="spinner" />取消中…</> : '取消'}
            </button>
          )}
          {hasFinal && activeRun && (
            <a href={getFinalUrl(task.task_id, activeRun.run_id)} className="btn btn-ghost btn-sm" download>
              下载成片
            </a>
          )}
          {activeRun && (
            <Link to={`/tasks/${task.task_id}/runs/${activeRun.run_id}/diagnostics`} className="btn btn-ghost btn-sm">
              诊断
            </Link>
          )}
        </div>

        {/* Feedback */}
        {actionError && <div className="error-card" style={{ marginTop: 8 }}><span className="code">{actionError}</span></div>}
        {actionSuccess && <div className="notice notice-ok" style={{ marginTop: 8 }}>{actionSuccess}</div>}
      </div>

      {/* ── Inputs section ─────────────────────────────────────────────── */}
      {activeRun && activeRun.status === 'pending' && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="card-title">制作输入</h3>
          <p className="card-sub">配置视频文案、参考音频和视觉参数后保存</p>

          <div className="field">
            <label htmlFor="input-script">视频文案</label>
            <textarea
              id="input-script"
              className="textarea"
              value={script}
              onChange={(e) => { setScript(e.target.value); setInputsSaved(false) }}
              placeholder="粘贴完整文案，保存时自动整理为 Voice Units"
              rows={6}
              disabled={actionLoading === 'inputs'}
            />
          </div>

          <div className="field">
            <label htmlFor="input-reference">参考音频</label>
            <input
              id="input-reference"
              type="file"
              accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null
                setReferenceFile(file)
                setInputsSaved(false)
                if (file) { setSavedAudioFilename(null); setSavedAudioSize(null) }
              }}
              disabled={actionLoading === 'inputs'}
              style={{ fontSize: 13 }}
            />
            {referenceFile && (
              <p className="hint">已选择：{referenceFile.name} ({formatBytes(referenceFile.size)})</p>
            )}
            {!referenceFile && savedAudioFilename && (
              <p className="hint">已保存参考音频：{savedAudioFilename}{savedAudioSize != null ? `（${formatBytes(savedAudioSize)}）` : ''}</p>
            )}
            <p className="hint">用于克隆配音的声音参考，支持 WAV/MP3/M4A/OGG/FLAC</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="field">
              <label htmlFor="input-style">风格</label>
              <input id="input-style" className="input" value={style} onChange={(e) => { setStyle(e.target.value); setInputsSaved(false) }} placeholder="如：手绘、水彩" disabled={actionLoading === 'inputs'} />
            </div>
            <div className="field">
              <label htmlFor="input-pen">画笔文字</label>
              <input id="input-pen" className="input" value={penText} onChange={(e) => { setPenText(e.target.value); setInputsSaved(false) }} placeholder="白板动画中的手写文字" disabled={actionLoading === 'inputs'} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="field">
              <label htmlFor="input-stroke">笔触细节</label>
              <input id="input-stroke" className="input" value={strokeDetail} onChange={(e) => { setStrokeDetail(e.target.value); setInputsSaved(false) }} placeholder="笔触粗细、颜色等" disabled={actionLoading === 'inputs'} />
            </div>
            <div className="field" style={{ display: 'flex', alignItems: 'center', paddingTop: 20 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={includeSubtitles} onChange={(e) => { setIncludeSubtitles(e.target.checked); setInputsSaved(false) }} disabled={actionLoading === 'inputs'} />
                <span>包含字幕</span>
              </label>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <button className="btn btn-primary btn-sm" onClick={handleSaveInputs} disabled={actionLoading !== null}>
              {actionLoading === 'inputs' ? <><span className="spinner" />保存中…</> : '保存制作输入'}
            </button>
            {inputsSaved && <span style={{ marginLeft: 12, fontSize: 12, color: 'var(--nt-primary-700)' }}>✓ 已保存</span>}
            {!inputsSaved && <span style={{ marginLeft: 12, fontSize: 12, color: 'var(--nt-text-muted)' }}>未保存</span>}
          </div>
        </div>
      )}

      {/* ── Stage Timeline ─────────────────────────────────────────────── */}
      <div className="timeline">
        {STAGE_KEYS.map((key, i) => (
          <div key={key} style={{ display: 'contents' }}>
            <div className={`timeline-node st-${stageStatuses[key]}`}>
              <span className="node-label">{STAGE_NAMES[key]}</span>
            </div>
            {i < STAGE_KEYS.length - 1 && <div className="timeline-connector" />}
          </div>
        ))}
      </div>

      {/* ── 3-column workbench grid ────────────────────────────────────── */}
      <div className="workbench-grid">
        {/* Left: Units */}
        <div className="panel">
          <div className="panel-title">
            配音单元
            {units.length > 0 && <span className="badge">{units.length}</span>}
          </div>
          {units.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-sub">暂无配音单元</div>
              <p style={{ fontSize: 12, color: 'var(--nt-text-muted)' }}>需先运行 clone-voice 阶段</p>
            </div>
          ) : (
            <ul className="unit-list">
              {units.map((u) => {
                const timing = u.timing as Record<string, unknown> | null | undefined
                return (
                  <li key={u.unit_id} className="unit-item">
                    <div className="unit-label">{u.unit_id} · 单元 {(u.order ?? 0) + 1}</div>
                    <div className="unit-text">{(u.text as string) ?? '—'}</div>
                    {timing && (
                      <div style={{ fontSize: 11, color: 'var(--nt-text-muted)', marginTop: 4 }}>
                        {timing.duration_ms != null && <span>时长: {formatMs(Number(timing.duration_ms))} </span>}
                        {timing.alignment_source != null && <span>对齐: {String(timing.alignment_source)} </span>}
                        {timing.fallback === true && <span style={{ color: 'var(--nt-accent-700)' }}>⚠ 回退</span>}
                      </div>
                    )}
                    {!timing && (
                      <div style={{ fontSize: 11, color: 'var(--nt-text-muted)', marginTop: 4 }}>暂无同步信息</div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Center: Stage Workspace */}
        <div className="panel">
          <div className="panel-title">
            阶段工作区
            <span className="badge">{completedCount}/{STAGE_KEYS.length}</span>
          </div>
          <div>
            {!activeRun && <p className="hint" style={{ marginBottom: 12 }}><span>任务尚未启动运行</span>（没有 active Run）；以下契约卡仅展示真实阶段基线。</p>}
            {activeRun && stages.length === 0 && <p className="hint" style={{ marginBottom: 12 }}>后端尚未报告 Stage 状态。</p>}
            {STAGE_CONTRACTS.map((contract) => {
              const st = stageStatuses[contract.id]
              const stageData = stages.find((s) => s.stage === contract.id)
              return (
                <article key={contract.id} className="stage-contract-card" style={{ padding: '14px 0', borderBottom: '1px solid var(--nt-border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <StatusBadge status={st} label={stageStatusLabel(st)} />
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{contract.title}</span>
                    <code style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>{contract.id}</code>
                    {stageData && <span style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>attempt {stageData.attempt}</span>}
                  </div>
                  <dl className="stage-contract-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '6px 16px', margin: '10px 0 8px', fontSize: 12 }}>
                    <div><dt className="hint">入口条件</dt><dd>{contract.entry}</dd></div>
                    <div><dt className="hint">持久化输入</dt><dd>{contract.persistedInputs}</dd></div>
                    <div><dt className="hint">预期输出</dt><dd>{contract.outputs}</dd></div>
                    <div><dt className="hint">出口条件</dt><dd>{contract.exit}</dd></div>
                  </dl>
                  <div className="notice notice-warn" style={{ marginTop: 8 }}>
                    <strong><span>人工 Gate</span>：</strong> {GATE_UNAVAILABLE}。{contract.operations}
                  </div>
                </article>
              )
            })}
            {stages.filter((stage) => !STAGE_KEYS.includes(stage.stage as StageKey)).map((stage, index) => (
              <article key={`unknown-${stage.stage}-${index}`} className="stage-contract-card" style={{ padding: '14px 0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <StatusBadge status={stage.status || 'unknown'} />
                  <strong>未知阶段</strong>
                  <code>{stage.stage}</code>
                </div>
                <p className="hint">后端返回了未登记的阶段，未执行任何前端操作。</p>
              </article>
            ))}
          </div>
        </div>

        {/* Right: Artifacts */}
        <div className="panel">
          <div className="panel-title">
            产物
            {artifacts.length > 0 && <span className="badge">{artifacts.length}</span>}
          </div>
          {artifacts.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-sub">暂无产物</div>
            </div>
          ) : (
            <table className="artifact-table">
              <thead>
                <tr><th>产物</th><th>阶段</th><th>状态</th><th>大小</th></tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.artifact_key}>
                    <td style={{ fontFamily: 'var(--nt-font-mono)', fontSize: 12 }}>{a.artifact_key}</td>
                    <td style={{ fontSize: 12 }}>{a.producer_stage}</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td style={{ fontSize: 12 }}>{formatBytes(a.size_bytes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Video preview ──────────────────────────────────────────────── */}
      {hasFinal && activeRun && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 className="card-title">成片预览</h3>
          <video
            controls
            style={{ width: '100%', maxWidth: 640, borderRadius: 'var(--nt-radius-md)', marginTop: 8 }}
            src={getFinalUrl(task.task_id, activeRun.run_id)}
          >
            您的浏览器不支持视频播放
          </video>
          <div style={{ marginTop: 8 }}>
            <a href={getFinalUrl(task.task_id, activeRun.run_id)} className="btn btn-ghost btn-sm" download>
              下载 final.mp4
            </a>
          </div>
        </div>
      )}

      {/* ── Activity Panel ─────────────────────────────────────────────── */}
      <div className="activity-panel" style={{ marginTop: 16 }}>
        <button className="activity-toggle" onClick={() => setShowActivity(!showActivity)}>
          <span className={`chevron ${showActivity ? 'open' : ''}`}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M5 2l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          运行日志 & 事件
        </button>
        {showActivity && (
          <div className="activity-body">
            {/* Log filters */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <select className="select" value={logFilter.level} onChange={(e) => setLogFilter({ ...logFilter, level: e.target.value })} style={{ width: 100 }}>
                <option value="">全部级别</option>
                <option value="ERROR">ERROR</option>
                <option value="WARN">WARN</option>
                <option value="INFO">INFO</option>
              </select>
              <input className="input" placeholder="组件筛选" value={logFilter.component} onChange={(e) => setLogFilter({ ...logFilter, component: e.target.value })} style={{ width: 120 }} />
              <select className="select" value={logFilter.stage} onChange={(e) => setLogFilter({ ...logFilter, stage: e.target.value })} style={{ width: 140 }}>
                <option value="">全部阶段</option>
                {STAGE_KEYS.map((k) => <option key={k} value={k}>{STAGE_NAMES[k]}</option>)}
              </select>
            </div>

            {/* Events */}
            <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--nt-text-muted)', marginBottom: 4 }}>事件 ({visibleEvents.length})</h4>
            {visibleEvents.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', padding: '4px 0' }}>暂无事件</p>
            ) : (
              <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: 12 }}>
                {visibleEvents.map((ev, i) => (
                  <div key={i} style={{ padding: '3px 0', fontSize: 12, borderBottom: '1px solid var(--nt-border)' }}>
                    <span style={{ color: 'var(--nt-text-muted)', fontFamily: 'var(--nt-font-mono)', marginRight: 8 }}>
                      {ev.timestamp ? formatTime(String(ev.timestamp)) : ''}
                    </span>
                    <span style={{ fontWeight: 600 }}>{String(ev.event_type ?? '')}</span>
                    {ev.stage != null && <span style={{ color: 'var(--nt-text-secondary)' }}> [{String(ev.stage)}]</span>}
                  </div>
                ))}
              </div>
            )}

            {/* Logs */}
            <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--nt-text-muted)', marginBottom: 4 }}>日志 ({logs.length})</h4>
            {logs.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', padding: '4px 0' }}>暂无日志</p>
            ) : (
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {logs.map((log, i) => (
                  <div key={i} className="log-line">
                    <span className="log-ts">{log.timestamp ? formatTime(String(log.timestamp)) : ''}</span>
                    <span className={`log-level-${String(log.level ?? '')}`}>[{String(log.level ?? '')}]</span>
                    {log.component != null && <span> {String(log.component)}</span>}
                    {log.stage != null && <span> [{String(log.stage)}]</span>}
                    <span> {String(log.message ?? '')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
