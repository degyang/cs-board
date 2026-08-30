import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createTask } from '../lib/api/client'
import { BackButton } from '../components/ui/BackButton'

export function CreateTaskPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [script, setScript] = useState('')
  const [engine, setEngine] = useState('whiteboard')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) {
      setError('请输入任务名称')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const res = await createTask({ title: title.trim(), engine })
      navigate(`/tasks/${res.task_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page page-narrow">
      <BackButton to="/" label="返回任务队列" />
      <div className="page-head">
        <h1 className="page-title">新建任务</h1>
        <p className="page-desc">输入任务名称和视频文案，选择渲染引擎后提交</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="card">
          <div className="field">
            <label htmlFor="title">任务名称</label>
            <input
              id="title"
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入视频任务名称"
              maxLength={120}
              disabled={submitting}
            />
          </div>

          <div className="field">
            <label htmlFor="script">视频文案</label>
            <textarea
              id="script"
              className="textarea"
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder="粘贴完整文案或按句分割，每句将生成独立配音和画面"
              rows={8}
              disabled={submitting}
            />
            <p className="hint">长文案将自动分段；也可用空行手动分段</p>
          </div>

          <div className="field">
            <label htmlFor="engine">渲染引擎</label>
            <select
              id="engine"
              className="select"
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              disabled={submitting}
            >
              <option value="whiteboard">白板动画</option>
              <option value="infographic-remotion">动态信息图</option>
            </select>
            <p className="hint">不同引擎适用于不同风格的视频内容</p>
          </div>

          {error && (
            <div className="error-card" style={{ marginTop: 12 }}>
              <span className="code">{error}</span>
            </div>
          )}

          <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="spinner" /> 创建中…
                </>
              ) : (
                '创建任务'
              )}
            </button>
            <Link to="/" className="btn btn-ghost">
              取消
            </Link>
          </div>
        </div>
      </form>
    </div>
  )
}
