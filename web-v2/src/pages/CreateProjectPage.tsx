import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../lib/api/client'

export function CreateProjectPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = title.trim().length >= 2 && !submitting

  const handleSubmit = async () => {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await createProject({
        title: title.trim(),
        engine: 'whiteboard',
        pipeline_id: 'mountain-av-v1',
      })
      navigate(`/projects/${res.project_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">创建项目</h1>
        <p className="page-desc">
          填写项目信息，创建后可上传文案与参考音频，启动视频制作流程。
        </p>
      </div>

      <div className="card">
        <div className="card-title">项目信息</div>
        <div className="card-sub">基础配置，引擎与 Pipeline 使用当前标准设置。</div>

        <div className="field">
          <label htmlFor="title">项目标题</label>
          <input
            id="title"
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：量子计算十分钟科普"
            disabled={submitting}
            maxLength={200}
          />
          <div className="hint">至少 2 个字符</div>
        </div>

        <div className="field">
          <label>引擎</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="badge tag-info" style={{ padding: '4px 12px' }}>
              白板动画 (whiteboard)
            </span>
          </div>
          <div className="hint">当前仅支持白板动画引擎。</div>
        </div>

        <div className="field">
          <label>Pipeline</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="badge tag-neutral" style={{ padding: '4px 12px', fontFamily: 'var(--nt-font-mono)' }}>
              mountain-av-v1
            </span>
          </div>
        </div>

        {error && (
          <div className="error-card" style={{ marginTop: 12 }}>
            <div className="code">创建失败</div>
            <div className="sug">{error}</div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!canSubmit}
          onClick={handleSubmit}
        >
          {submitting ? (
            <>
              <span className="spinner" />
              创建中…
            </>
          ) : (
            '创建项目'
          )}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => navigate('/')}
          disabled={submitting}
        >
          取消
        </button>
      </div>
    </div>
  )
}
