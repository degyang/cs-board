/* ==========================================================================
   资产管理 — Asset Management Page (§3I)

   Tabs: 预置风格 | 自定义风格 | 音色库
   - Preset: read-only browse with real preview image, copy-as-custom only
   - Custom: full CRUD with preview upload
   - Voice: upload, edit, play, activate/deactivate, delete
   - Filtering: kind/status/engine/q for styles, status/q for voices
   - Cursor pagination with dedup
   ========================================================================== */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Tabs } from '../components/ui/Tabs'
import { CopyButton } from '../components/ui/CopyButton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { getVoiceContentUrl, getAssetBlobUrl } from '../lib/api/http'
import {
  fetchStyles, createStyle, updateStyle, deleteStyle,
  activateStyle, deactivateStyle, copyStyle,
  fetchVoices, createVoice, updateVoice, deleteVoice,
  activateVoice, deactivateVoice,
  uploadAsset,
} from '../lib/api/assets'
import type { StyleTemplate, VoiceDefinition } from '../lib/api/types'

const TAB_ITEMS = [
  { key: 'preset', label: '预置风格' },
  { key: 'custom', label: '自定义风格' },
  { key: 'voice', label: '音色库' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '已启用' },
  { value: 'inactive', label: '未启用' },
]

const ENGINE_OPTIONS = [
  { value: '', label: '全部引擎' },
  { value: 'whiteboard', label: '白板动画' },
  { value: 'infographic-remotion', label: '动态信息图' },
]

/* ── Preview Image with error placeholder ──────────────────────────────── */

function PreviewImage({ assetId, alt }: { assetId: string | null; alt: string }) {
  const [failed, setFailed] = useState(false)

  // Reset error state when assetId changes
  useEffect(() => { setFailed(false) }, [assetId])

  if (!assetId || failed) {
    return (
      <div className="am-preview-placeholder" role="img" aria-label="暂无预览图">
        <span className="am-preview-placeholder-icon">🎨</span>
        <span className="am-preview-placeholder-text">暂无预览图</span>
      </div>
    )
  }

  return (
    <img
      className="am-preview-img"
      src={getAssetBlobUrl(assetId)}
      alt={alt}
      onError={() => setFailed(true)}
      draggable={false}
    />
  )
}

/* ── Preset Detail (read-only) ─────────────────────────────────────────── */

function PresetDetail({
  style: s,
  submitting,
  onCopy,
}: {
  style: StyleTemplate
  submitting: string | null
  onCopy: (id: string) => void
}) {
  return (
    <div className="am-preset-detail">
      <div className="am-preset-preview">
        <PreviewImage assetId={s.preview_asset_id} alt={s.name} />
      </div>

      <div className="am-preset-info">
        <h2 className="am-detail-name">{s.name}</h2>

        {s.description && (
          <p className="am-preset-description">{s.description}</p>
        )}

        <div className="am-preset-meta">
          {s.engine && <span className="am-preset-engine">{s.engine}</span>}
          <span className="am-preset-kind">预置风格</span>
        </div>

        {s.tags.length > 0 && (
          <div className="am-preset-tags">
            {s.tags.map(t => (
              <span key={t} className="am-tag">{t}</span>
            ))}
          </div>
        )}

        {s.prompt_text && (
          <div className="am-prompt-section">
            <label className="am-prompt-label">提示词</label>
            <pre className="am-prompt-text">{s.prompt_text}</pre>
          </div>
        )}

        {s.negative_prompt && (
          <div className="am-prompt-section">
            <label className="am-prompt-label">反向提示词</label>
            <pre className="am-prompt-text am-prompt-negative">{s.negative_prompt}</pre>
          </div>
        )}

        <div className="am-preset-actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={submitting !== null}
            onClick={() => onCopy(s.style_id)}
          >
            {submitting === s.style_id ? '复制中...' : '复制为自定义'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Style Detail (custom — full CRUD) ─────────────────────────────────── */

function StyleDetail({
  style: s,
  submitting,
  onActivate,
  onDeactivate,
  onEdit,
  onDelete,
}: {
  style: StyleTemplate
  submitting: string | null
  onActivate: (id: string) => void
  onDeactivate: (id: string) => void
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <>
      <h2 className="am-detail-name">{s.name}</h2>
      <div className="am-detail-meta">
        <span>状态: {s.status === 'active' ? '已启用' : '未启用'}</span>
        <span>类型: 自定义</span>
        <span>修订: {s.revision}</span>
        <span>创建: {new Date(s.created_at).toLocaleDateString()}</span>
      </div>
      {s.description && <p className="am-detail-desc">{s.description}</p>}
      {s.engine && <div className="am-detail-field"><span className="am-detail-label">引擎:</span> {s.engine}</div>}
      {s.tags.length > 0 && (
        <div className="am-detail-field">
          <span className="am-detail-label">标签:</span>
          {s.tags.map(t => <span key={t} className="badge" style={{ marginRight: 4 }}>{t}</span>)}
        </div>
      )}
      {s.prompt_text && (
        <div className="am-detail-field">
          <span className="am-detail-label">提示词:</span>
          <div className="am-detail-prompt">{s.prompt_text}</div>
        </div>
      )}
      {s.negative_prompt && (
        <div className="am-detail-field">
          <span className="am-detail-label">反向提示词:</span>
          <div className="am-detail-prompt">{s.negative_prompt}</div>
        </div>
      )}

      <div className="am-detail-actions">
        <button type="button" className="btn btn-ghost" onClick={onEdit}>编辑</button>
        {s.status === 'active' ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting !== null}
            onClick={() => onDeactivate(s.style_id)}
          >
            {submitting === s.style_id ? '处理中...' : '停用'}
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            disabled={submitting !== null}
            onClick={() => onActivate(s.style_id)}
          >
            {submitting === s.style_id ? '处理中...' : '启用'}
          </button>
        )}
        <button
          type="button"
          className="btn btn-danger"
          disabled={submitting !== null}
          onClick={onDelete}
        >
          删除
        </button>
      </div>
    </>
  )
}

/* ── Voice Detail ──────────────────────────────────────────────────────── */

function VoiceDetail({
  voice: v,
  submitting,
  onActivate,
  onDeactivate,
  onEdit,
  onDelete,
}: {
  voice: VoiceDefinition
  submitting: string | null
  onActivate: (id: string) => void
  onDeactivate: (id: string) => void
  onEdit: () => void
  onDelete: () => void
}) {
  const audioUrl = getVoiceContentUrl(v.voice_id)

  return (
    <>
      <h2 className="am-detail-name">{v.name}</h2>
      <div className="am-detail-meta">
        <span>状态: {v.status === 'active' ? '已启用' : '未启用'}</span>
        <span>修订: {v.duration_ms ? `${(v.duration_ms / 1000).toFixed(1)}s` : '—'}</span>
        <span>创建: {new Date(v.created_at).toLocaleDateString()}</span>
      </div>
      {v.tags.length > 0 && (
        <div className="am-detail-field">
          <span className="am-detail-label">标签:</span>
          {v.tags.map(t => <span key={t} className="badge" style={{ marginRight: 4 }}>{t}</span>)}
        </div>
      )}
      <div className="am-detail-field">
        <span className="am-detail-label">采样率:</span> {v.sample_rate ? `${v.sample_rate} Hz` : '—'}
      </div>
      <div className="am-detail-field">
        <span className="am-detail-label">声道:</span> {v.channels ?? '—'}
      </div>
      <div className="am-detail-field">
        <span className="am-detail-label">格式:</span> {v.format ?? '—'}
      </div>
      {v.duration_ms && (
        <div className="am-detail-field">
          <span className="am-detail-label">时长:</span> {(v.duration_ms / 1000).toFixed(1)}s
        </div>
      )}

      <div className="am-detail-field">
        <audio controls src={audioUrl} preload="metadata" style={{ width: '100%', marginTop: 8 }}>
          您的浏览器不支持音频播放
        </audio>
      </div>

      <div className="am-detail-actions">
        <button type="button" className="btn btn-ghost" onClick={onEdit}>编辑</button>
        {v.status === 'active' ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting !== null}
            onClick={() => onDeactivate(v.voice_id)}
          >
            {submitting === v.voice_id ? '处理中...' : '停用'}
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            disabled={submitting !== null}
            onClick={() => onActivate(v.voice_id)}
          >
            {submitting === v.voice_id ? '处理中...' : '启用'}
          </button>
        )}
        <CopyButton text={audioUrl}>复制链接</CopyButton>
        <button
          type="button"
          className="btn btn-danger"
          disabled={submitting !== null}
          onClick={onDelete}
        >
          删除
        </button>
      </div>
    </>
  )
}

/* ── Main Page ─────────────────────────────────────────────────────────── */

export function AssetManagementPage() {
  const [activeTab, setActiveTab] = useState('preset')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [engineFilter, setEngineFilter] = useState('')
  const [items, setItems] = useState<(StyleTemplate | VoiceDefinition)[]>([])
  const [selected, setSelected] = useState<StyleTemplate | VoiceDefinition | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState<StyleTemplate | VoiceDefinition | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<StyleTemplate | VoiceDefinition | null>(null)

  // Cursor pagination state
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const loadedIdsRef = useRef<Set<string>>(new Set())
  const generationRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  // Reset cursor and items when filters change
  const resetAndLoad = useCallback(() => {
    setItems([])
    setNextCursor(null)
    setHasMore(false)
    loadedIdsRef.current = new Set()
    setSelected(null)
    setFeedback(null)
  }, [])

  // Load items with cursor pagination and stale-request protection
  const loadItems = useCallback(async (cursor?: string) => {
    // Abort any in-flight request
    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller
    const gen = cursor ? generationRef.current : ++generationRef.current

    if (cursor) {
      setLoadingMore(true)
    } else {
      setLoading(true)
      resetAndLoad()
    }
    setError(null)
    try {
      if (activeTab === 'voice') {
        const res = await fetchVoices({
          q: search || undefined,
          status: statusFilter as 'active' | 'inactive' | undefined || undefined,
          cursor,
          limit: 20,
        })
        // Stale-request guard: discard if a newer request was started
        if (gen !== generationRef.current) return
        // Dedup: only add items not already loaded
        const newItems = res.items.filter(v => !loadedIdsRef.current.has(v.voice_id))
        for (const v of newItems) loadedIdsRef.current.add(v.voice_id)
        setItems(prev => cursor ? [...prev, ...newItems] : newItems)
        setNextCursor(res.next_cursor)
        setHasMore(res.next_cursor !== null)
      } else {
        const kind = activeTab as 'preset' | 'custom'
        const res = await fetchStyles({
          kind,
          q: search || undefined,
          status: statusFilter as 'active' | 'inactive' | undefined || undefined,
          engine: engineFilter || undefined,
          cursor,
          limit: 20,
        })
        // Stale-request guard: discard if a newer request was started
        if (gen !== generationRef.current) return
        // Dedup: only add items not already loaded
        const newItems = res.items.filter(s => !loadedIdsRef.current.has(s.style_id))
        for (const s of newItems) loadedIdsRef.current.add(s.style_id)
        setItems(prev => cursor ? [...prev, ...newItems] : newItems)
        setNextCursor(res.next_cursor)
        setHasMore(res.next_cursor !== null)
      }
    } catch (err) {
      // Don't update state if this request was superseded
      if (gen !== generationRef.current) return
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      if (gen === generationRef.current) {
        setLoading(false)
        setLoadingMore(false)
      }
    }
  }, [activeTab, search, statusFilter, engineFilter, resetAndLoad])

  // Load on mount and filter change
  useEffect(() => { loadItems() }, [activeTab, search, statusFilter, engineFilter])

  // Cleanup: abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  // Reset selected item and filters when tab changes
  useEffect(() => {
    setSelected(null)
    setFeedback(null)
    setSearch('')
    setStatusFilter('')
    setEngineFilter('')
  }, [activeTab])

  const isVoice = (item: StyleTemplate | VoiceDefinition): item is VoiceDefinition =>
    'voice_id' in item

  const getId = (item: StyleTemplate | VoiceDefinition) =>
    isVoice(item) ? item.voice_id : item.style_id

  const handleActivate = async (id: string) => {
    setSubmitting(id); setFeedback(null)
    try {
      if (activeTab === 'voice') await activateVoice(id)
      else await activateStyle(id)
      setFeedback('已启用')
      await loadItems()
    } catch (err) { setError(err instanceof Error ? err.message : '操作失败') }
    finally { setSubmitting(null) }
  }

  const handleDeactivate = async (id: string) => {
    setSubmitting(id); setFeedback(null)
    try {
      if (activeTab === 'voice') await deactivateVoice(id)
      else await deactivateStyle(id)
      setFeedback('已停用')
      await loadItems()
    } catch (err) { setError(err instanceof Error ? err.message : '操作失败') }
    finally { setSubmitting(null) }
  }

  // Copy preset → custom, then switch to custom tab
  const handleCopy = async (id: string) => {
    setSubmitting(id); setFeedback(null)
    try {
      const copied = await copyStyle(id)
      setFeedback(`已复制为自定义风格「${copied.name}」`)
      // Switch to custom tab and select the new item
      setActiveTab('custom')
      // After tab switch, loadItems will fire; select the copied item
      // Use a small delay to let the tab switch and load complete
      setTimeout(() => {
        setSelected(copied)
      }, 100)
    } catch (err) {
      setError(err instanceof Error ? err.message : '复制失败')
    } finally {
      setSubmitting(null)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    const id = getId(deleteTarget)
    setSubmitting(id); setFeedback(null)
    try {
      if (isVoice(deleteTarget)) await deleteVoice(id)
      else await deleteStyle(id)
      setFeedback('已删除')
      setSelected(null)
      await loadItems()
    } catch (err) { setError(err instanceof Error ? err.message : '删除失败') }
    finally { setSubmitting(null); setDeleteTarget(null) }
  }

  const handleEdit = (item: StyleTemplate | VoiceDefinition) => {
    setEditingItem(item)
    setShowForm(true)
  }

  const handleCreate = () => {
    setEditingItem(null)
    setShowForm(true)
  }

  const handleFormClose = () => {
    setShowForm(false)
    setEditingItem(null)
  }

  const handleFormSaved = async () => {
    setShowForm(false)
    setEditingItem(null)
    setFeedback('已保存')
    await loadItems()
  }

  const handleLoadMore = () => {
    if (nextCursor && !loadingMore) {
      loadItems(nextCursor)
    }
  }

  const isPreset = activeTab === 'preset'
  const showFilters = activeTab === 'preset' || activeTab === 'custom'

  return (
    <div className="page-container">
      <div className="am-header">
        <h1 className="am-title">资产管理</h1>
        <p className="am-description">管理预置风格、自定义风格和音色库</p>
      </div>

      <Tabs items={TAB_ITEMS} active={activeTab} onChange={setActiveTab} />

      {feedback && <div className="am-feedback">{feedback}</div>}
      {error && <div className="am-error" role="alert">{error}</div>}

      <div className="am-toolbar">
        <input
          type="text"
          placeholder="搜索..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="am-search-input"
          aria-label="搜索"
        />

        {showFilters && (
          <>
            <select
              className="am-filter-select"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              aria-label="状态筛选"
            >
              {STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            {activeTab === 'preset' && (
              <select
                className="am-filter-select"
                value={engineFilter}
                onChange={e => setEngineFilter(e.target.value)}
                aria-label="引擎筛选"
              >
                {ENGINE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            )}
          </>
        )}

        {activeTab === 'voice' && (
          <select
            className="am-filter-select"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            aria-label="状态筛选"
          >
            {STATUS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        )}

        {activeTab === 'custom' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={handleCreate}>新建风格</button>
        )}
        {activeTab === 'voice' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={handleCreate}>上传音色</button>
        )}
      </div>

      {loading ? (
        <div className="am-loading">加载中...</div>
      ) : items.length === 0 ? (
        <div className="am-empty">暂无数据</div>
      ) : (
        <div className="am-layout">
          <div className="am-list">
            {items.map(item => (
              <div
                key={getId(item)}
                className={`am-list-item ${selected && getId(selected) === getId(item) ? 'am-list-item--selected' : ''}`}
                onClick={() => setSelected(item)}
                role="button"
                tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setSelected(item) }}
              >
                {isPreset && !isVoice(item) && (item as StyleTemplate).preview_asset_id ? (
                  <div className="am-list-thumb">
                    <img
                      src={getAssetBlobUrl((item as StyleTemplate).preview_asset_id!)}
                      alt=""
                      className="am-list-thumb-img"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                  </div>
                ) : isPreset && !isVoice(item) ? (
                  <div className="am-list-thumb am-list-thumb-placeholder">
                    <span>🎨</span>
                  </div>
                ) : null}
                <div className="am-list-item-main">
                  <div className="am-list-item-name">{item.name}</div>
                  {!isVoice(item) && isPreset && (item as StyleTemplate).description && (
                    <div className="am-list-item-desc">{(item as StyleTemplate).description}</div>
                  )}
                  {!isVoice(item) && isPreset && (item as StyleTemplate).tags.length > 0 && (
                    <div className="am-list-item-tags">
                      {(item as StyleTemplate).tags.slice(0, 3).map(t => (
                        <span key={t} className="am-tag am-tag-sm">{t}</span>
                      ))}
                      {(item as StyleTemplate).tags.length > 3 && (
                        <span className="am-tag am-tag-sm am-tag-more">+{(item as StyleTemplate).tags.length - 3}</span>
                      )}
                    </div>
                  )}
                  {(!isPreset || isVoice(item)) && (
                    <div className="am-list-item-status">{item.status === 'active' ? '已启用' : '未启用'}</div>
                  )}
                </div>
              </div>
            ))}

            {hasMore && (
              <button
                type="button"
                className="btn btn-ghost btn-sm am-load-more"
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? '加载中...' : '加载更多'}
              </button>
            )}
          </div>

          <div className="am-detail">
            {selected ? (
              isVoice(selected) ? (
                <VoiceDetail
                  voice={selected}
                  submitting={submitting}
                  onActivate={handleActivate}
                  onDeactivate={handleDeactivate}
                  onEdit={() => handleEdit(selected)}
                  onDelete={() => setDeleteTarget(selected)}
                />
              ) : isPreset ? (
                <PresetDetail
                  style={selected}
                  submitting={submitting}
                  onCopy={handleCopy}
                />
              ) : (
                <StyleDetail
                  style={selected}
                  submitting={submitting}
                  onActivate={handleActivate}
                  onDeactivate={handleDeactivate}
                  onEdit={() => handleEdit(selected)}
                  onDelete={() => setDeleteTarget(selected)}
                />
              )
            ) : (
              <div className="am-detail-empty">选择一项查看详情</div>
            )}
          </div>
        </div>
      )}

      {showForm && (
        activeTab === 'voice' ? (
          <VoiceFormDialog
            voice={editingItem as VoiceDefinition | null}
            onClose={handleFormClose}
            onSaved={handleFormSaved}
          />
        ) : (
          <StyleFormDialog
            style={editingItem as StyleTemplate | null}
            onClose={handleFormClose}
            onSaved={handleFormSaved}
          />
        )
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title={deleteTarget && isVoice(deleteTarget) ? '删除音色' : '删除风格'}
        message={deleteTarget ? `确定删除「${deleteTarget.name}」？此操作不可恢复。` : ''}
        confirmLabel="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

/* ── Style Form Dialog ─────────────────────────────────────────────────── */

function StyleFormDialog({
  style: existing,
  onClose,
  onSaved,
}: {
  style: StyleTemplate | null
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = !!existing
  const [name, setName] = useState(existing?.name ?? '')
  const [description, setDescription] = useState(existing?.description ?? '')
  const [engine, setEngine] = useState(existing?.engine ?? '')
  const [promptText, setPromptText] = useState(existing?.prompt_text ?? '')
  const [negativePrompt, setNegativePrompt] = useState(existing?.negative_prompt ?? '')
  const [tags, setTags] = useState(existing?.tags?.join(', ') ?? '')
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [previewAssetId, setPreviewAssetId] = useState(existing?.preview_asset_id ?? '')
  const [uploading, setUploading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handlePreviewUpload = async () => {
    if (!previewFile) return
    setUploading(true)
    setError(null)
    try {
      const res = await uploadAsset(previewFile)
      setPreviewAssetId(res.asset_id)
      setPreviewFile(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传预览失败')
    } finally {
      setUploading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        name,
        description: description || undefined,
        engine: engine || undefined,
        prompt_text: promptText || undefined,
        negative_prompt: negativePrompt || undefined,
        tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
        preview_asset_id: previewAssetId || undefined,
      }
      if (isEdit && existing) {
        await updateStyle(existing.style_id, payload)
      } else {
        await createStyle(payload)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">{isEdit ? '编辑风格' : '新建自定义风格'}</h2>
        {error && <div className="error-card" role="alert"><div>{error}</div></div>}
        <form onSubmit={handleSubmit} className="style-form">
          <div className="form-field">
            <label className="form-label" htmlFor="style-name">名称 *</label>
            <input id="style-name" type="text" className="input" required value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="style-desc">描述</label>
            <input id="style-desc" type="text" className="input" value={description} onChange={e => setDescription(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="style-engine">引擎</label>
            <input id="style-engine" type="text" className="input" value={engine} onChange={e => setEngine(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="style-prompt">提示词</label>
            <textarea id="style-prompt" className="input" rows={3} value={promptText} onChange={e => setPromptText(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="style-neg">反向提示词</label>
            <textarea id="style-neg" className="input" rows={2} value={negativePrompt} onChange={e => setNegativePrompt(e.target.value)} />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="style-tags">标签（逗号分隔）</label>
            <input id="style-tags" type="text" className="input" value={tags} onChange={e => setTags(e.target.value)} />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="style-preview">预览图片</label>
            <div className="am-preview-upload">
              <input
                id="style-preview"
                type="file"
                accept="image/*"
                onChange={e => setPreviewFile(e.target.files?.[0] ?? null)}
              />
              {previewFile && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={uploading}
                  onClick={handlePreviewUpload}
                >
                  {uploading ? '上传中...' : '上传预览'}
                </button>
              )}
              {previewAssetId && (
                <span className="badge">已上传: {previewAssetId.slice(0, 8)}...</span>
              )}
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '保存中...' : (isEdit ? '保存修改' : '创建')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Voice Form Dialog ─────────────────────────────────────────────────── */

function VoiceFormDialog({
  voice: existing,
  onClose,
  onSaved,
}: {
  voice: VoiceDefinition | null
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = !!existing
  const [name, setName] = useState(existing?.name ?? '')
  const [tags, setTags] = useState(existing?.tags?.join(', ') ?? '')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      if (isEdit && existing) {
        await updateVoice(existing.voice_id, {
          name,
          tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
        })
      } else {
        if (!audioFile) { setError('请选择音频文件'); setSaving(false); return }
        const form = new FormData()
        form.append('file', audioFile)
        form.append('name', name)
        if (tags) {
          const tagList = tags.split(',').map(t => t.trim()).filter(Boolean)
          for (const t of tagList) form.append('tags', t)
        }
        await createVoice(form)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">{isEdit ? '编辑音色' : '上传音色'}</h2>
        {error && <div className="error-card" role="alert"><div>{error}</div></div>}
        <form onSubmit={handleSubmit} className="style-form">
          <div className="form-field">
            <label className="form-label" htmlFor="voice-name">名称 *</label>
            <input id="voice-name" type="text" className="input" required value={name} onChange={e => setName(e.target.value)} />
          </div>
          {!isEdit && (
            <div className="form-field">
              <label className="form-label" htmlFor="voice-file">音频文件 *</label>
              <input id="voice-file" type="file" accept="audio/*" onChange={e => setAudioFile(e.target.files?.[0] ?? null)} />
            </div>
          )}
          <div className="form-field">
            <label className="form-label" htmlFor="voice-tags">标签（逗号分隔）</label>
            <input id="voice-tags" type="text" className="input" value={tags} onChange={e => setTags(e.target.value)} />
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '保存中...' : (isEdit ? '保存修改' : '上传')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
