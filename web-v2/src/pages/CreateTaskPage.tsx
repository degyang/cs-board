import { useEffect, useRef, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createTask, uploadInputs } from '../lib/api/client'
import { BackButton } from '../components/ui/BackButton'

// 标准 whiteboard 配置（固定，非用户可选）
const ENGINE = 'whiteboard'
const PIPELINE_ID = 'mountain-av-v1'
const STYLE_DEFAULT = '极简粗线简笔白板风'
const PEN_TEXT_DEFAULT = ''
const STROKE_DETAIL_DEFAULT = 'detailed'

function parseIntField(t: string): number | null {
  const s = t.trim()
  if (s === '') return null
  const n = Number(s)
  if (!Number.isFinite(n) || !Number.isInteger(n)) return null
  return n
}

interface SafeError {
  message: string
  code: string | null
}

// 只暴露 MountainApiError 的安全 message/code；不渲染 path、command、token、secret、traceback 或参考音频内容
function safeErrorText(err: unknown): SafeError {
  if (err && typeof err === 'object' && 'apiError' in err) {
    const e = err as { message: string; apiError: { code: string } | null }
    return { message: e.message, code: e.apiError?.code ?? null }
  }
  if (err instanceof Error) return { message: err.message, code: null }
  return { message: '请求失败', code: null }
}

interface CreatedTask {
  task_id: string
  run_id: string
}

export function CreateTaskPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [script, setScript] = useState('')
  const [targetChars, setTargetChars] = useState('80')
  const [minChars, setMinChars] = useState('35')
  const [maxChars, setMaxChars] = useState('140')
  const [visualAnchorEnabled, setVisualAnchorEnabled] = useState(true)
  const [includeSubtitles, setIncludeSubtitles] = useState(true)
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string> | null>(null)
  const [createdTask, setCreatedTask] = useState<CreatedTask | null>(null)
  const [createErr, setCreateErr] = useState<SafeError | null>(null)
  const [uploadErr, setUploadErr] = useState<SafeError | null>(null)

  const submittingRef = useRef(false)
  const mountedRef = useRef(true)
  useEffect(() => () => { mountedRef.current = false }, [])

  function validate(): Record<string, string> | null {
    const errors: Record<string, string> = {}
    if (!title.trim()) errors.title = '请输入任务名称'
    if (!script.trim()) errors.script = '请输入文案'
    const min = parseIntField(minChars)
    const target = parseIntField(targetChars)
    const max = parseIntField(maxChars)
    if (min === null || target === null || max === null) {
      errors.chars = '字数必须为整数'
    } else if (min < 1 || max > 500) {
      errors.chars = '字数范围超出合理界限（1–500）'
    } else if (min > target || target > max) {
      errors.chars = '需满足 1 ≤ 最小 ≤ 目标 ≤ 最大 ≤ 500'
    }
    return Object.keys(errors).length ? errors : null
  }

  function buildFormData(): FormData {
    const form = new FormData()
    form.set('script', script)
    if (referenceFile) form.set('reference', referenceFile)
    form.set('style', STYLE_DEFAULT)
    form.set('pen_text', PEN_TEXT_DEFAULT)
    form.set('stroke_detail', STROKE_DETAIL_DEFAULT)
    form.set('include_subtitles', String(includeSubtitles))
    form.set('target_chars', targetChars)
    form.set('min_chars', minChars)
    form.set('max_chars', maxChars)
    form.set('visual_anchor_enabled', String(visualAnchorEnabled))
    return form
  }

  async function runUpload(taskId: string) {
    submittingRef.current = true
    setSubmitting(true)
    setUploadErr(null)
    try {
      await uploadInputs(taskId, buildFormData())
      if (!mountedRef.current) return
      navigate(`/tasks/${encodeURIComponent(taskId)}`)
    } catch (err) {
      if (mountedRef.current) setUploadErr(safeErrorText(err))
    } finally {
      if (mountedRef.current) setSubmitting(false)
      submittingRef.current = false
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (submittingRef.current) return
    const errs = validate()
    if (errs) { setFieldErrors(errs); return }
    setFieldErrors(null)
    // 已创建过任务（安全网）：表单重复提交时只重试上传，不重复创建 Task
    if (createdTask) { return runUpload(createdTask.task_id) }

    submittingRef.current = true
    setSubmitting(true)
    setCreateErr(null)
    setUploadErr(null)
    let res
    try {
      res = await createTask({ title: title.trim(), engine: ENGINE, pipeline_id: PIPELINE_ID })
    } catch (err) {
      if (mountedRef.current) { setCreateErr(safeErrorText(err)); setSubmitting(false) }
      submittingRef.current = false
      return
    }
    if (!mountedRef.current) { submittingRef.current = false; return }
    setCreatedTask({ task_id: res.task_id, run_id: res.run_id })
    await runUpload(res.task_id)
  }

  async function handleRetryUpload() {
    if (submittingRef.current) return
    const errs = validate()
    if (errs) { setFieldErrors(errs); return }
    setFieldErrors(null)
    if (createdTask) await runUpload(createdTask.task_id)
  }

  function enterWorkbench() {
    if (createdTask) navigate(`/tasks/${encodeURIComponent(createdTask.task_id)}`)
  }

  return (
    <div className="page page-narrow">
      <BackButton to="/" label="返回" />
      <header className="page-head">
        <h1 className="page-title">新建任务</h1>
        <p className="page-desc">填写任务名称与文案，提交后创建任务并保存制作输入。引擎固定为白板动画，不自动启动运行。</p>
      </header>

      <form onSubmit={handleSubmit} noValidate>
        <div className="card">
          <div className="field">
            <label htmlFor="title">任务名称</label>
            <input
              id="title"
              className="input"
              value={title}
              onChange={e => setTitle(e.target.value)}
              disabled={submitting || !!createdTask}
              autoComplete="off"
            />
            {fieldErrors?.title && <div className="hint error" role="alert">{fieldErrors.title}</div>}
          </div>

          <div className="field">
            <label htmlFor="script">文案</label>
            <textarea
              id="script"
              className="textarea"
              rows={6}
              value={script}
              onChange={e => setScript(e.target.value)}
              disabled={submitting}
              placeholder="输入完整文案（不少于 10 字）"
            />
            {fieldErrors?.script && <div className="hint error" role="alert">{fieldErrors.script}</div>}
          </div>

          <div className="field">
            <label>字数规则</label>
            <div className="chars-row">
              <label htmlFor="min_chars" className="chip-label">最小</label>
              <input
                id="min_chars"
                className="input input-sm"
                type="number"
                min={1}
                value={minChars}
                onChange={e => setMinChars(e.target.value)}
                disabled={submitting}
              />
              <label htmlFor="target_chars" className="chip-label">目标</label>
              <input
                id="target_chars"
                className="input input-sm"
                type="number"
                min={1}
                value={targetChars}
                onChange={e => setTargetChars(e.target.value)}
                disabled={submitting}
              />
              <label htmlFor="max_chars" className="chip-label">最大</label>
              <input
                id="max_chars"
                className="input input-sm"
                type="number"
                max={500}
                value={maxChars}
                onChange={e => setMaxChars(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="hint">1 ≤ 最小 ≤ 目标 ≤ 最大 ≤ 500</div>
            {fieldErrors?.chars && <div className="hint error" role="alert">{fieldErrors.chars}</div>}
          </div>

          <div className="field">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={visualAnchorEnabled}
                onChange={e => setVisualAnchorEnabled(e.target.checked)}
                disabled={submitting}
              />
              启用画面锚定（visual_anchor_enabled）
            </label>
          </div>

          <div className="field">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={includeSubtitles}
                onChange={e => setIncludeSubtitles(e.target.checked)}
                disabled={submitting}
              />
              包含字幕（include_subtitles）
            </label>
          </div>

          <div className="field">
            <label htmlFor="reference">参考音频（可选）</label>
            <input
              id="reference"
              className="input"
              type="file"
              accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"
              onChange={e => setReferenceFile(e.target.files?.[0] ?? null)}
              disabled={submitting}
            />
            <div className="hint">首次保存需提供参考音频；浏览器不会读取、打印、缓存或 base64 化音频内容。</div>
          </div>

          <div className="field">
            <span className="hint">引擎：白板动画（固定）</span>
            <br />
            <span className="hint">标准白板配置：style={STYLE_DEFAULT} / stroke_detail={STROKE_DETAIL_DEFAULT}</span>
          </div>
        </div>

        {createErr && (
          <div className="error-card" role="alert">
            <span className="code">{createErr.message}</span>
            {createErr.code && <span className="sug">代码：{createErr.code}</span>}
          </div>
        )}

        {uploadErr && (
          <div className="error-card" role="alert">
            <span className="code">任务已创建、输入保存失败</span>
            <span className="sug">{uploadErr.message}</span>
            {uploadErr.code && <span className="sug">代码：{uploadErr.code}</span>}
          </div>
        )}

        <div className="actions">
          {!createdTask ? (
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? '创建中…' : '创建任务'}
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleRetryUpload}
                disabled={submitting}
              >
                {submitting ? '保存中…' : '重试保存输入'}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={enterWorkbench}
              >
                进入任务工作台
              </button>
            </>
          )}
          <Link to="/" className="btn btn-ghost">取消</Link>
        </div>
      </form>
    </div>
  )
}
