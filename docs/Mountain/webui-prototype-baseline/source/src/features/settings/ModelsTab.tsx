import { useState } from 'react'
import {
  useModelProviders,
  MODEL_CATEGORIES,
  categoryLabel,
  maskApiKey,
  type ModelProvider,
} from './modelProvidersStore'

/* 设置-模型 · 模型服务商列表
   列表卡片（名称 + 类别徽标 + 模型 chips + 掩码 API Key + Base URL），
   新增/编辑走内联表单；API Key 缺省 password 掩码，点眼睛图标切换明文。 */

const EMPTY_DRAFT = (id: string): ModelProvider => ({
  id,
  name: '',
  categories: [],
  models: [],
  apiKey: '',
  baseUrl: '',
})

export function ModelsTab() {
  const { providers, addProvider, updateProvider, removeProvider, uid } = useModelProviders()

  /* editingId：'new' = 新建中；其它 = 正在编辑该 id；null = 全部只读 */
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<ModelProvider | null>(null)
  const [modelsText, setModelsText] = useState('') // 本地缓冲：允许输入尾逗号不被吞
  const [showKey, setShowKey] = useState(false) // API Key 明/暗切换（表单内）
  const [revealedId, setRevealedId] = useState<string | null>(null) // 列表内临时显示完整 Key
  const [confirmId, setConfirmId] = useState<string | null>(null) // 两步删除确认
  const [nameErr, setNameErr] = useState('')

  const startNew = () => {
    setDraft(EMPTY_DRAFT(uid('mp')))
    setModelsText('')
    setEditingId('new')
    setShowKey(false)
    setNameErr('')
  }
  const startEdit = (p: ModelProvider) => {
    setDraft({ ...p })
    setModelsText(p.models.join(', '))
    setEditingId(p.id)
    setShowKey(false)
    setNameErr('')
  }
  const cancel = () => {
    setEditingId(null)
    setDraft(null)
    setNameErr('')
  }
  const save = () => {
    if (!draft) return
    if (!draft.name.trim()) {
      setNameErr('名称为必填')
      return
    }
    if (editingId === 'new') addProvider(draft)
    else updateProvider(draft)
    setEditingId(null)
    setDraft(null)
  }

  return (
    <div className="card">
      <h2 className="card-title">模型服务</h2>
      <p className="card-sub">
        维护文本 / 图片 / 视频 / 语音各类模型服务的接入信息；每个服务可包含多个模型（逗号分隔）。API Key 缺省隐藏，点眼睛图标可显示完整内容。
      </p>

      <div className="mp-toolbar">
        <button type="button" className="btn btn-primary btn-sm" onClick={startNew} disabled={editingId !== null}>
          ＋ 添加模型服务
        </button>
        <span className="hint" style={{ margin: 0 }}>{providers.length} 个服务</span>
      </div>

      <div className="mp-list">
        {providers.map((p) =>
          editingId === p.id && draft ? (
            <ProviderForm
              key={p.id}
              draft={draft}
              setDraft={setDraft}
              modelsText={modelsText}
              setModelsText={setModelsText}
              showKey={showKey}
              setShowKey={setShowKey}
              nameErr={nameErr}
              onSave={save}
              onCancel={cancel}
              isNew={false}
            />
          ) : (
            <div key={p.id} className="mp-card">
              <div className="mp-head">
                <span className="mp-name">{p.name}</span>
                <span className="mp-cats">
                  {p.categories.map((c) => (
                    <span key={c} className="badge">{categoryLabel(c)}</span>
                  ))}
                </span>
                <span className="mp-actions">
                  {confirmId === p.id ? (
                    <>
                      <span className="mp-confirm-text">确认删除？</span>
                      <button
                        type="button"
                        className="btn btn-sm set-danger"
                        onClick={() => {
                          removeProvider(p.id)
                          setConfirmId(null)
                        }}
                      >
                        删除
                      </button>
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmId(null)}>
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => startEdit(p)} disabled={editingId !== null}>
                        编辑
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm set-danger"
                        onClick={() => setConfirmId(p.id)}
                        disabled={editingId !== null}
                      >
                        删除
                      </button>
                    </>
                  )}
                </span>
              </div>
              {p.models.length > 0 && (
                <div className="mp-models">
                  {p.models.map((m) => (
                    <span key={m} className="badge tag-neutral mono">{m}</span>
                  ))}
                </div>
              )}
              <div className="mp-meta">
                <span className="mp-meta-item">
                  API Key：
                  {p.apiKey ? (
                    <>
                      <span className="mono">{revealedId === p.id ? p.apiKey : maskApiKey(p.apiKey)}</span>
                      <button
                        type="button"
                        className="mp-eye"
                        title={revealedId === p.id ? '隐藏' : '显示完整 Key'}
                        onClick={() => setRevealedId(revealedId === p.id ? null : p.id)}
                      >
                        <EyeIcon open={revealedId === p.id} />
                      </button>
                    </>
                  ) : (
                    <span className="hint" style={{ display: 'inline' }}>未设置</span>
                  )}
                </span>
                {p.baseUrl && (
                  <span className="mp-meta-item">
                    Base URL：<span className="mono">{p.baseUrl}</span>
                  </span>
                )}
              </div>
            </div>
          ),
        )}

        {editingId === 'new' && draft && (
          <ProviderForm
            draft={draft}
            setDraft={setDraft}
            modelsText={modelsText}
            setModelsText={setModelsText}
            showKey={showKey}
            setShowKey={setShowKey}
            nameErr={nameErr}
            onSave={save}
            onCancel={cancel}
            isNew
          />
        )}

        {providers.length === 0 && editingId === null && (
          <div className="mp-empty">暂无模型服务，点击上方「添加模型服务」创建。</div>
        )}
      </div>
    </div>
  )
}

/* ---------------- 内联新增/编辑表单 ---------------- */
function ProviderForm({
  draft,
  setDraft,
  modelsText,
  setModelsText,
  showKey,
  setShowKey,
  nameErr,
  onSave,
  onCancel,
  isNew,
}: {
  draft: ModelProvider
  setDraft: (p: ModelProvider) => void
  modelsText: string
  setModelsText: (v: string) => void
  showKey: boolean
  setShowKey: (v: boolean) => void
  nameErr: string
  onSave: () => void
  onCancel: () => void
  isNew: boolean
}) {
  const toggleCat = (key: string) => {
    const has = draft.categories.includes(key)
    setDraft({
      ...draft,
      categories: has ? draft.categories.filter((c) => c !== key) : [...draft.categories, key],
    })
  }

  return (
    <div className="mp-card mp-form">
      <div className="mp-form-title">{isNew ? '添加模型服务' : `编辑：${draft.name || '（未命名）'}`}</div>

      <div className="field">
        <label>名称 *</label>
        <input
          className={`input${nameErr ? ' is-error' : ''}`}
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          placeholder="例如：OpenAI 官方 / 阿里云百炼 / 本地 vLLM"
          autoFocus
        />
        {nameErr && <div className="set-error">{nameErr}</div>}
      </div>

      <div className="field">
        <label>类别（可多选）</label>
        <div className="mp-cat-row">
          {MODEL_CATEGORIES.map((c) => (
            <button
              key={c.key}
              type="button"
              className={'mp-cat' + (draft.categories.includes(c.key) ? ' on' : '')}
              onClick={() => toggleCat(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label>模型</label>
        <input
          className="input mono"
          value={modelsText}
          onChange={(e) => {
            setModelsText(e.target.value)
            setDraft({
              ...draft,
              models: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
            })
          }}
          placeholder="多个模型以逗号分隔，例如：gpt-4o, gpt-4o-mini"
        />
        <div className="hint">
          {draft.models.length > 0 ? `已解析 ${draft.models.length} 个模型` : '输入模型名称，逗号分隔'}
        </div>
      </div>

      <div className="field">
        <label>API Key</label>
        <div className="mp-key-row">
          <input
            className="input mono"
            type={showKey ? 'text' : 'password'}
            value={draft.apiKey}
            onChange={(e) => setDraft({ ...draft, apiKey: e.target.value })}
            placeholder="输入 API Key"
            autoComplete="off"
          />
          <button
            type="button"
            className="mp-eye"
            title={showKey ? '隐藏' : '显示完整 Key'}
            onClick={() => setShowKey(!showKey)}
          >
            <EyeIcon open={showKey} />
          </button>
        </div>
        <div className="hint">原型阶段保存在本机浏览器；正式版将迁入系统密钥库，日志与诊断包不含密钥。</div>
      </div>

      <div className="field">
        <label>Base URL</label>
        <input
          className="input mono"
          value={draft.baseUrl}
          onChange={(e) => setDraft({ ...draft, baseUrl: e.target.value })}
          placeholder="https://api.example.com/v1"
        />
      </div>

      <div className="mp-form-actions">
        <button type="button" className="btn btn-primary btn-sm" onClick={onSave} disabled={!draft.name.trim()}>
          保存
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  )
}

/* 眼睛图标（开=明文显示，闭=掩码） */
function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )
}

