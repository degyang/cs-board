/* ==========================================================================
   图风管理 — Style Management Page (§3I)

   Tabs: 预置风格 | 自定义风格 | 前置条件
   - Preset: inline create/edit/delete with preview upload
   - Custom: full CRUD with preview upload
   - Filtering: kind/status/engine/q for styles
   - Preconditions: read-only real catalog cards (kind/applies_to/status)
   - Cursor pagination with dedup
   ========================================================================== */

import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { Tabs } from '../components/ui/Tabs'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { getAssetBlobUrl } from '../lib/api/http'
import {
  fetchStyles, createStyle, updateStyle, deleteStyle,
  uploadAsset,
  fetchPreconditions,
} from '../lib/api/assets'
import type { StyleTemplate, StyleCharacter, StyleReferenceRoute, StyleReferenceRouting, Precondition } from '../lib/api/types'

const TAB_ITEMS = [
  { key: 'preset', label: '预置风格' },
  { key: 'custom', label: '自定义风格' },
  { key: 'precondition', label: '前置条件' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '已启用' },
  { value: 'inactive', label: '未启用' },
]

/* ── Preview Image with error placeholder ──────────────────────────────── */

function PreviewImage({ assetId, alt, errorLabel = '暂无预览图', compact = false }: { assetId: string | null; alt: string; errorLabel?: string; compact?: boolean }) {
  const [failed, setFailed] = useState(false)

  // Reset error state when assetId changes
  useEffect(() => { setFailed(false) }, [assetId])

  if (!assetId || failed) {
    return (
      <div className="am-preview-placeholder" role="img" aria-label={!assetId ? '暂无预览图' : errorLabel}>
        <span className="am-preview-placeholder-icon">🎨</span>
        {!compact && <span className="am-preview-placeholder-text">{!assetId ? '暂无预览图' : errorLabel}</span>}
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

/** The asset API exposes availability as `status`; it is not a Task selection. */
function AssetStatus({ status, enabled = true }: { status: 'active' | 'inactive'; enabled?: boolean }) {
  const active = status === 'active' && enabled
  return (
    <span
      className={`am-status ${active ? 'am-status--active' : 'am-status--inactive'}`}
      title={active ? '已启用' : '未启用'}
    >
      <span className="am-status-dot" aria-hidden="true" />
      {active ? '已启用' : '未启用'}
    </span>
  )
}

function AssetListHeader({
  search,
  onSearch,
  action,
  filters,
}: {
  search: string
  onSearch: (value: string) => void
  action?: ReactNode
  filters?: ReactNode
}) {
  return (
    <div className="am-list-head">
      <div className="am-search-wrap">
        <span className="am-search-ico" aria-hidden="true">🔍</span>
        <input
          type="search"
          placeholder="搜索资产…"
          value={search}
          onChange={e => onSearch(e.target.value)}
          className="input am-search-input"
          aria-label="搜索资产"
        />
      </div>
      {action && <div className="am-list-action">{action}</div>}
      {filters && <div className="am-list-filters">{filters}</div>}
    </div>
  )
}

function AssetListEmpty({ label }: { label: string }) {
  return <div className="am-list-empty">没有匹配的{label}</div>
}

function PreconditionCard({ item }: { item: Precondition }) {
  const kindLabel = item.kind === 'visual-explainer' ? 'visual-explainer · 通用讲解者' : 'renderer-hand · 白板绘制手'
  return (
    <article className="am-precondition-card">
      <div className="am-precondition-preview">
        <PreviewImage assetId={item.preview_asset_id} alt={item.name} errorLabel="预览图片读取失败" />
      </div>
      <div className="am-precondition-content">
        <div className="am-precondition-heading">
          <h2 className="am-detail-name">{item.name}</h2>
          <AssetStatus status={item.status} enabled={item.enabled} />
        </div>
        <div className="am-precondition-meta">
          <span className="am-preset-kind">kind: {kindLabel}</span>
          <span className="am-preset-kind">revision: {item.revision}</span>
          <span className="am-preset-kind">applies_to: {item.applies_to.join(', ')}</span>
        </div>
        <p className="am-detail-desc">{item.description || '暂无说明文字'}</p>
        <p className="am-precondition-condition"><strong>条件：</strong>{item.condition_text || '暂无条件说明'}</p>
        <div className="am-precondition-contract">目录状态：status={item.status} · enabled={String(item.enabled)} · 引擎：{item.engine_compatibility.join(', ') || '未声明'}</div>
      </div>
    </article>
  )
}

function StyleCharacterDetails({ style, editable = false, onChange }: { style: StyleTemplate; editable?: boolean; onChange?: (characters: StyleCharacter[]) => void }) {
  const characters = style.characters ?? []
  const change = (next: StyleCharacter[]) => onChange?.(next)
  return (
    <section className="am-character-details" aria-label="此风格修订的人物参考">
      <h3 className="am-section-title">人物组 <span>同一 Style revision</span></h3>
      {characters.length === 0 && <p className="am-empty">此 Style revision 暂无人​​物。</p>}
      <div className="am-character-reference-grid">
        {characters.map((character, index) => (
          <article className="am-character-reference am-character-card" key={character.character_id}>
            <div className="am-character-reference-images">
              {character.reference_asset_ids.map(assetId => <PreviewImage key={assetId} assetId={assetId} alt={character.name} />)}
            </div>
            <div className="am-character-content">
              {editable ? <input className="input" value={character.name} onChange={e => change(characters.map((item, i) => i === index ? { ...item, name: e.target.value } : item))} aria-label="人物名称" /> : <strong>{character.name}</strong>}
              {editable ? <textarea className="input" rows={2} value={character.description} onChange={e => change(characters.map((item, i) => i === index ? { ...item, description: e.target.value } : item))} aria-label="人物说明" /> : <p>{character.description}</p>}
              {editable && <input className="input" value={character.reference_asset_ids.join(', ')} onChange={e => change(characters.map((item, i) => i === index ? { ...item, reference_asset_ids: e.target.value.split(',').map(id => id.trim()).filter(Boolean) } : item))} placeholder="参考图 asset_id，以逗号分隔" aria-label="人物参考图 asset id" />}
              {editable && <button type="button" className="btn btn-danger btn-sm" onClick={() => change(characters.filter((_, i) => i !== index))}>删除人物</button>}
            </div>
          </article>
        ))}
      </div>
      {editable && <button type="button" className="btn btn-ghost btn-sm" onClick={() => change([...characters, { character_id: crypto.randomUUID(), name: '新人物', description: '', reference_asset_ids: [] }])}>+ 添加人物</button>}
    </section>
  )
}

function styleRouting(style: StyleTemplate): StyleReferenceRouting {
  const routing = style.config?.reference_routing
  return routing && Array.isArray(routing.rules)
    ? routing
    : { enabled: false, match_mode: 'first', rules: [] }
}

function StyleReferenceRoutingDetails({
  style,
  editable = false,
  onChange,
}: {
  style: StyleTemplate
  editable?: boolean
  onChange?: (routing: StyleReferenceRouting) => void
}) {
  const routing = styleRouting(style)
  const rules = routing.rules
  const [uploadingRule, setUploadingRule] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const changeRules = (next: StyleReferenceRoute[]) => onChange?.({ enabled: next.length > 0, match_mode: 'first', rules: next.map((rule, index) => ({ ...rule, order: index + 1 })) })
  const changeRule = (index: number, patch: Partial<StyleReferenceRoute>) => changeRules(rules.map((rule, current) => current === index ? { ...rule, ...patch } : rule))
  const moveRule = (index: number, offset: number) => {
    const target = index + offset
    if (target < 0 || target >= rules.length) return
    const next = [...rules]
    ;[next[index], next[target]] = [next[target], next[index]]
    changeRules(next)
  }
  const addReferenceImage = async (index: number, file: File | null) => {
    if (!file) return
    const rule = rules[index]
    if (rule.reference_asset_ids.length >= 3) {
      setUploadError('每条规则最多添加 3 张参考图片')
      return
    }
    setUploadingRule(rule.rule_id)
    setUploadError(null)
    try {
      const uploaded = await uploadAsset(file)
      changeRule(index, { reference_asset_ids: [...rule.reference_asset_ids, uploaded.asset_id] })
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : '参考图片上传失败')
    } finally {
      setUploadingRule(null)
    }
  }
  return (
    <section className="am-reference-routing" aria-label="参考图路由规则">
      <div className="am-reference-routing-head">
        <div><h3 className="am-section-title">参考图路由规则</h3><p>按分镜关键字从上到下匹配，首条命中规则提供生图参考；列表为空时不使用参考图。</p></div>
        {editable && <button type="button" className="btn btn-ghost btn-sm" onClick={() => changeRules([...rules, { rule_id: crypto.randomUUID(), name: '新规则', keywords: [], reference_asset_ids: [], order: rules.length + 1 }])}>＋ 添加规则</button>}
      </div>
      {uploadError && <div className="error-card" role="alert">{uploadError}</div>}
      {rules.length === 0 ? <p className="am-empty">未配置路由规则，生成时仅使用风格提示词。</p> : (
        <div className="am-reference-route-list">
          {rules.map((rule, index) => (
            <article className="am-reference-route" key={rule.rule_id}>
              <div className="am-reference-route-title">
                {editable ? <input className="input" aria-label={`规则 ${index + 1} 名称`} value={rule.name} onChange={event => changeRule(index, { name: event.target.value })} /> : <strong>{rule.name}</strong>}
                <span>规则 {index + 1}</span>
              </div>
              <div className="field">
                <label>关键字</label>
                {editable ? <input className="input" aria-label={`${rule.name}关键字`} value={rule.keywords.join('、')} placeholder="流程、系统、自动化" onChange={event => changeRule(index, { keywords: event.target.value.split(/[，,、\s]+/).map(value => value.trim()).filter(Boolean) })} /> : <div className="am-reference-keywords">{rule.keywords.map(keyword => <span className="am-tag" key={keyword}>{keyword}</span>)}</div>}
              </div>
              <div className="field">
                <label>对应图片</label>
                <div className="am-reference-images">
                  {rule.reference_asset_ids.map((assetId, imageIndex) => <div className="am-reference-image" key={assetId}><PreviewImage assetId={assetId} alt={`${rule.name}参考图 ${imageIndex + 1}`} />{editable && <button type="button" aria-label={`移除${rule.name}参考图 ${imageIndex + 1}`} onClick={() => changeRule(index, { reference_asset_ids: rule.reference_asset_ids.filter((_, current) => current !== imageIndex) })}>×</button>}</div>)}
                  {editable && rule.reference_asset_ids.length < 3 && <label className="am-reference-upload"><span>{uploadingRule === rule.rule_id ? '上传中…' : '＋ 添加图片'}</span><input type="file" accept="image/*" aria-label={`为${rule.name}添加参考图片`} disabled={uploadingRule !== null} onChange={event => void addReferenceImage(index, event.target.files?.[0] ?? null)} /></label>}
                </div>
              </div>
              {editable && <div className="am-reference-route-actions"><button type="button" className="btn btn-ghost btn-sm" aria-label={`上移${rule.name}`} onClick={() => moveRule(index, -1)} disabled={index === 0}>↑</button><button type="button" className="btn btn-ghost btn-sm" aria-label={`下移${rule.name}`} onClick={() => moveRule(index, 1)} disabled={index === rules.length - 1}>↓</button><button type="button" className="btn btn-danger btn-sm" onClick={() => changeRules(rules.filter((_, current) => current !== index))}>删除规则</button></div>}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

/* ── Preset Detail (managed asset, inline editing) ───────────────────── */

function ManagedStyleDetail({
  style: s,
  submitting,
  onSaved,
  onDelete,
}: {
  style: StyleTemplate
  submitting: string | null
  onSaved: () => void | Promise<void>
  onDelete: () => void
}) {
  const kindLabel = s.kind === 'preset' ? '预置风格' : '自定义风格'
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<StyleTemplate>(s)
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(s)
    setEditing(false)
    setPreviewFile(null)
    setEditError(null)
  }, [s.style_id, s.revision])

  const cancelEdit = () => {
    setDraft(s)
    setEditing(false)
    setPreviewFile(null)
    setEditError(null)
  }

  const uploadPreview = async () => {
    if (!previewFile) return
    setUploading(true)
    setEditError(null)
    try {
      const uploaded = await uploadAsset(previewFile)
      setDraft(current => ({ ...current, preview_asset_id: uploaded.asset_id }))
      setPreviewFile(null)
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '上传预览失败')
    } finally {
      setUploading(false)
    }
  }

  const saveEdit = async () => {
    if (!draft.name.trim()) {
      setEditError('风格名称不能为空')
      return
    }
    const invalidRoute = styleRouting(draft).rules.find(rule => !rule.name.trim() || rule.keywords.length === 0 || rule.reference_asset_ids.length === 0)
    if (invalidRoute) {
      setEditError('每条参考图路由都需要名称、至少一个关键字和至少一张图片')
      return
    }
    setSaving(true)
    setEditError(null)
    try {
      await updateStyle(s.style_id, {
        name: draft.name.trim(),
        description: draft.description,
        engine: draft.engine ?? '',
        prompt_text: draft.prompt_text ?? '',
        negative_prompt: draft.negative_prompt ?? '',
        tags: draft.tags,
        preview_asset_id: draft.preview_asset_id ?? '',
        characters: draft.characters ?? [],
        config: draft.config,
        expected_revision: s.revision,
      })
      setEditing(false)
      await onSaved()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="am-preset-detail am-golden-detail">
      <div className="am-detail-head">
        <div className="am-style-preview am-style-preview--head">
          <PreviewImage assetId={draft.preview_asset_id} alt={draft.name} compact={!draft.preview_asset_id} />
        </div>
        <div className="am-detail-heading">
          <h2 className="am-detail-name">{editing ? `编辑${kindLabel}` : s.name}</h2>
        </div>
        <div className="am-tools">
          {editing ? (
            <>
              <button type="button" className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving || uploading}>{saving ? '保存中...' : '保存'}</button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={cancelEdit} disabled={saving || uploading}>取消</button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing(true)} disabled={submitting !== null}>编辑</button>
              <button type="button" className="btn btn-danger btn-sm" onClick={onDelete} disabled={submitting !== null}>删除</button>
            </>
          )}
        </div>
      </div>

      <div className="am-preset-info">
        {editError && <div className="error-card" role="alert">{editError}</div>}
        <div className="field am-preview-field">
          <label>风格图片</label>
          <div className="am-preset-main-preview">
            <PreviewImage assetId={draft.preview_asset_id} alt={draft.name} errorLabel="预览图片读取失败" />
          </div>
          {editing && <div className="am-preview-upload"><input type="file" accept="image/*" aria-label="预览图片" onChange={event => setPreviewFile(event.target.files?.[0] ?? null)} />{previewFile && <button type="button" className="btn btn-ghost btn-sm" onClick={uploadPreview} disabled={uploading}>{uploading ? '上传中...' : '上传预览'}</button>}</div>}
        </div>
        <div className="field">
          <label>风格名称</label>
          {editing ? <input className="input" aria-label="风格名称" value={draft.name} onChange={event => setDraft(current => ({ ...current, name: event.target.value }))} /> : <p className="am-prose">{s.name}</p>}
        </div>

        <div className="field">
          <label>风格简介</label>
          {editing ? <input className="input" aria-label="风格简介" value={draft.description} onChange={event => setDraft(current => ({ ...current, description: event.target.value }))} /> : s.description ? <p className="am-prose">{s.description}</p> : <p className="am-prose">暂无简介</p>}
        </div>

        {editing ? (
          <div className="field"><label>标签（逗号分隔）</label><input className="input" aria-label="标签" value={draft.tags.join(', ')} onChange={event => setDraft(current => ({ ...current, tags: event.target.value.split(',').map(tag => tag.trim()).filter(Boolean) }))} /></div>
        ) : s.tags.length > 0 && (
          <div className="am-preset-tags">
            {s.tags.map(t => (
              <span key={t} className="am-tag">{t}</span>
            ))}
          </div>
        )}

        {editing ? (
          <div className="am-prompt-section"><label className="am-prompt-label">提示词</label><textarea className="input" aria-label="提示词" rows={4} value={draft.prompt_text ?? ''} onChange={event => setDraft(current => ({ ...current, prompt_text: event.target.value }))} /></div>
        ) : s.prompt_text && (
          <div className="am-prompt-section">
            <label className="am-prompt-label">提示词</label>
            <pre className="am-prompt-text">{s.prompt_text}</pre>
          </div>
        )}

        {editing ? (
          <div className="am-prompt-section"><label className="am-prompt-label">反向提示词</label><textarea className="input" aria-label="反向提示词" rows={3} value={draft.negative_prompt ?? ''} onChange={event => setDraft(current => ({ ...current, negative_prompt: event.target.value }))} /></div>
        ) : s.negative_prompt && (
          <div className="am-prompt-section">
            <label className="am-prompt-label">反向提示词</label>
            <pre className="am-prompt-text am-prompt-negative">{s.negative_prompt}</pre>
          </div>
        )}

        <StyleCharacterDetails style={editing ? draft : s} editable={editing} onChange={characters => setDraft(current => ({ ...current, characters }))} />
        {s.kind === 'preset' && <StyleReferenceRoutingDetails style={editing ? draft : s} editable={editing} onChange={referenceRouting => setDraft(current => ({ ...current, config: { ...current.config, reference_routing: referenceRouting } }))} />}

      </div>
    </div>
  )
}

/* ── Main Page ─────────────────────────────────────────────────────────── */

export function AssetManagementPage() {
  const [activeTab, setActiveTab] = useState('preset')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [items, setItems] = useState<StyleTemplate[]>([])
  const [preconditions, setPreconditions] = useState<Precondition[]>([])
  const [selected, setSelected] = useState<StyleTemplate | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<StyleTemplate | null>(null)

  // Cursor pagination state
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const loadedIdsRef = useRef<Set<string>>(new Set())
  const loadedTabRef = useRef<Set<string>>(new Set())
  const generationRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  // Reset cursor and items when filters change
  const resetAndLoad = useCallback(() => {
    setItems([])
    setPreconditions([])
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
      // Keep the list shell (and its focused search field) mounted while a
      // filter refreshes. A tab's first load still gets the explicit state.
      setLoading(!loadedTabRef.current.has(activeTab))
      resetAndLoad()
    }
    setError(null)
    try {
      if (activeTab === 'precondition') {
        const res = await fetchPreconditions()
        if (gen !== generationRef.current) return
        setPreconditions(res.items)
        setNextCursor(null)
        setHasMore(false)
        loadedTabRef.current.add(activeTab)
      } else {
        const kind = activeTab as 'preset' | 'custom'
        const res = await fetchStyles({
          kind,
          q: search || undefined,
          status: statusFilter as 'active' | 'inactive' | undefined || undefined,
          cursor,
          limit: 20,
        })
        // Stale-request guard: discard if a newer request was started
        if (gen !== generationRef.current) return
        // Dedup: only add items not already loaded
        const newItems = res.items.filter(s => !loadedIdsRef.current.has(s.style_id))
        for (const s of newItems) loadedIdsRef.current.add(s.style_id)
        setItems(prev => cursor ? [...prev, ...newItems] : newItems)
        if (!cursor) setSelected(newItems[0] ?? null)
        setNextCursor(res.next_cursor)
        setHasMore(res.next_cursor !== null)
        loadedTabRef.current.add(activeTab)
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
  }, [activeTab, search, statusFilter, resetAndLoad])

  // Load on mount and filter change
  useEffect(() => { loadItems() }, [activeTab, search, statusFilter])

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
  }, [activeTab])

  const getId = (item: StyleTemplate) => item.style_id

  const handleDelete = async () => {
    if (!deleteTarget) return
    const id = getId(deleteTarget)
    setSubmitting(id); setFeedback(null)
    try {
      await deleteStyle(id)
      setFeedback('已删除')
      setSelected(null)
      await loadItems()
    } catch (err) { setError(err instanceof Error ? err.message : '删除失败') }
    finally { setSubmitting(null); setDeleteTarget(null) }
  }

  const handleCreate = () => {
    setShowForm(true)
  }

  const handleFormClose = () => {
    setShowForm(false)
  }

  const handleFormSaved = async () => {
    setShowForm(false)
    setFeedback('已保存')
    await loadItems()
  }

  const handleInlineSaved = async () => {
    setFeedback('已保存')
    await loadItems()
  }

  const handleLoadMore = () => {
    if (nextCursor && !loadingMore) {
      loadItems(nextCursor)
    }
  }

  const isPreset = activeTab === 'preset'
  const isPrecondition = activeTab === 'precondition'

  return (
    <div className="page">
      <div className="page-head am-header">
        <h1 className="page-title">图风管理</h1>
        <p className="page-desc">集中维护视频生产所需的风格资产与前置条件。预置风格、自定义风格和前置条件分别用 Tab 分隔；每个 Tab 内左侧为资产列表、右侧为选中资产的具体内容。风格可在右侧详情区直接编辑。</p>
      </div>

      <Tabs items={TAB_ITEMS} active={activeTab} onChange={setActiveTab} />

      {feedback && <div className="am-feedback">{feedback}</div>}
      {error && <div className="am-error" role="alert">{error}</div>}

      {loading && isPrecondition ? (
        <div className="am-loading">加载中...</div>
      ) : isPrecondition ? (
        <>
          <span className="am-readonly-note">只读目录 · Task 选择将在后续冻结契约中提供</span>
          {preconditions.length === 0 ? <div className="am-empty">暂无前置条件</div> : (
            <div className="am-preconditions-grid">
              {preconditions.map(item => <PreconditionCard key={item.precondition_id} item={item} />)}
            </div>
          )}
        </>
      ) : (
        <div className="am-body am-layout">
          <div className="am-list">
            <AssetListHeader
              search={search}
              onSearch={setSearch}
              filters={
                <>
                  <select className="am-filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)} aria-label="状态筛选">
                    {STATUS_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                </>
              }
              action={activeTab === 'preset'
                ? <button type="button" className="btn btn-primary btn-sm" onClick={handleCreate}>+ 新建预置风格</button>
                : activeTab === 'custom'
                ? <button type="button" className="btn btn-primary btn-sm" onClick={handleCreate}>+ 新建自定义风格</button>
                : undefined}
            />
            {loading && <div className="am-loading">加载中...</div>}
            {!loading && items.length === 0 && <AssetListEmpty label={isPreset ? '预置风格' : '自定义风格'} />}
            {!loading && items.map(item => (
              <button
                key={getId(item)}
                type="button"
                className={`am-item am-list-item ${selected && getId(selected) === getId(item) ? 'on am-list-item--selected' : ''}`}
                onClick={() => setSelected(item)}
              >
                {item.preview_asset_id ? (
                  <div className="am-list-thumb">
                    <img
                      src={getAssetBlobUrl(item.preview_asset_id)}
                      alt=""
                      className="am-list-thumb-img"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                  </div>
                ) : (
                  <div className="am-list-thumb am-list-thumb-placeholder">
                    <span>🎨</span>
                  </div>
                )}
                <div className="am-item-main am-list-item-main">
                  <div className="am-list-item-name">{item.name}</div>
                  {isPreset && (
                    <div className="am-list-item-desc">{item.description || item.tags[0] || '暂无短说明'}</div>
                  )}
                  {!isPreset && (
                    <div className="am-list-item-desc">{item.characters?.length ?? 0} 个人物 · revision {item.revision}</div>
                  )}
                  {isPreset && item.tags.length > 0 && (
                    <div className="am-list-item-tags">
                      {item.tags.slice(0, 3).map(t => (
                        <span key={t} className="am-tag am-tag-sm">{t}</span>
                      ))}
                      {item.tags.length > 3 && (
                        <span className="am-tag am-tag-sm am-tag-more">+{item.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                  {isPreset && <div className="am-list-item-status"><AssetStatus status={item.status} /></div>}
                </div>
              </button>
            ))}

            {!loading && hasMore && (
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
              <ManagedStyleDetail
                style={selected}
                submitting={submitting}
                onSaved={handleInlineSaved}
                onDelete={() => setDeleteTarget(selected)}
              />
            ) : (
              <div className="am-detail-empty">
                <strong>{items.length === 0 ? '暂无数据' : '从左侧列表选择一项'}</strong>
                <span>{activeTab === 'custom' ? '可从左侧新建自定义风格。' : '可从左侧新建预置风格。'}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <StyleFormDialog
          style={null}
          kind={activeTab === 'preset' ? 'preset' : 'custom'}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除风格"
        message={deleteTarget ? `确定将「${deleteTarget.name}」移出资产目录？服务端会保留历史修订与审计记录。` : ''}
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
  kind,
  onClose,
  onSaved,
}: {
  style: StyleTemplate | null
  kind: 'preset' | 'custom'
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = !!existing
  const [name, setName] = useState(existing?.name ?? '')
  const [description, setDescription] = useState(existing?.description ?? '')
  const [promptText, setPromptText] = useState(existing?.prompt_text ?? '')
  const [negativePrompt, setNegativePrompt] = useState(existing?.negative_prompt ?? '')
  const [tags, setTags] = useState(existing?.tags?.join(', ') ?? '')
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [previewAssetId, setPreviewAssetId] = useState(existing?.preview_asset_id ?? '')
  const [characters, setCharacters] = useState<StyleCharacter[]>(existing?.characters ?? [])
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
        prompt_text: promptText || undefined,
        negative_prompt: negativePrompt || undefined,
        tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
        preview_asset_id: previewAssetId || undefined,
        characters,
      }
      if (isEdit && existing) {
        await updateStyle(existing.style_id, { ...payload, expected_revision: existing.revision })
      } else {
        await createStyle({ ...payload, kind })
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
        <h2 className="modal-title">{isEdit ? `编辑${kind === 'preset' ? '预置' : '自定义'}风格` : `新建${kind === 'preset' ? '预置' : '自定义'}风格`}</h2>
        {error && <div className="error-card" role="alert"><div>{error}</div></div>}
        <form onSubmit={handleSubmit} className="style-form">
          <div className="form-field">
            <label className="form-label" htmlFor="style-name">名称 *</label>
            <input id="style-name" type="text" className="input" required value={name} onChange={e => setName(e.target.value)} />
          </div>

          <StyleCharacterDetails
            style={{ ...(existing ?? { style_id: '', kind: 'custom', name, description: '', engine: null, status: 'inactive', revision: 0, tags: [], prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, created_at: '', updated_at: '' }), characters }}
            editable
            onChange={setCharacters}
          />
          <div className="form-field">
            <label className="form-label" htmlFor="style-desc">描述</label>
            <input id="style-desc" type="text" className="input" value={description} onChange={e => setDescription(e.target.value)} />
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
