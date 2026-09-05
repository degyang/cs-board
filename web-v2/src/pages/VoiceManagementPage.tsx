/* ==========================================================================
   音色管理 — Voice Management Page

   Standalone page for voice asset CRUD: list, search, filter, playback,
   upload, edit, and delete. Uses the same real API contract as the former
   voice tab in AssetManagementPage — no mock or duplicated state logic.
   ========================================================================== */

import { useState, useEffect, useCallback, useRef } from 'react'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Tabs } from '../components/ui/Tabs'
import { getVoiceContentUrl } from '../lib/api/http'
import {
  fetchVoices, createVoice, updateVoice, deleteVoice,
} from '../lib/api/assets'
import { fetchServices } from '../lib/api/services'
import { createVoiceProfile, createVoiceStyleProfile, fetchVoiceProfiles, fetchVoiceStyleProfiles, previewVoiceProfile } from '../lib/api/voiceProfiles'
import type { ServiceDefinition, VoiceDefinition, VoiceProfile, VoiceStyleProfile } from '../lib/api/types'

const VOICE_TABS = [
  { key: 'library', label: '音色库' },
  { key: 'presets', label: '预置音色' },
  { key: 'designs', label: '音色设计' },
  { key: 'styles', label: '发音风格' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '已启用' },
  { value: 'inactive', label: '未启用' },
]

const DEFAULT_PREVIEW_TEXT = '这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。'

function languageLabel(value?: string | null): string {
  if (value === 'zh-CN') return '中文'
  if (value === 'en-US') return '英文'
  return '—'
}

function genderLabel(value?: string | null): string {
  if (value === 'female') return '女'
  if (value === 'male') return '男'
  return '—'
}

/* ── Shared sub-components ─────────────────────────────────────────────── */

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

/* ── Voice Detail ──────────────────────────────────────────────────────── */

function VoiceDetail({
  voice: v,
  submitting,
  onSaved,
  onDelete,
}: {
  voice: VoiceDefinition
  submitting: string | null
  onSaved: () => void | Promise<void>
  onDelete: () => void
}) {
  const audioUrl = getVoiceContentUrl(v.voice_id)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(v)
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  useEffect(() => {
    setDraft(v)
    setEditing(false)
    setEditError(null)
  }, [v.voice_id, v.updated_at])

  const cancelEdit = () => {
    setDraft(v)
    setEditing(false)
    setEditError(null)
  }

  const saveEdit = async () => {
    if (!draft.name.trim()) {
      setEditError('音色名称不能为空')
      return
    }
    setSaving(true)
    setEditError(null)
    try {
      await updateVoice(v.voice_id, {
        name: draft.name.trim(),
        tags: draft.tags,
        language: draft.language ?? '',
        emotion_mode: draft.emotion_mode ?? '',
        example_text: draft.example_text ?? '',
        availability_status: draft.availability_status,
        status_note: draft.status_note ?? '',
        engine: draft.engine ?? '',
        compatibility: draft.compatibility,
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
    <>
      <div className="am-detail-head">
        <div className="am-voice-avatar" aria-hidden="true">🔊</div>
        <div>
          <h2 className="am-detail-name">{editing ? '编辑音色' : v.name}</h2>
          <div className="am-detail-tag"><AssetStatus status={v.status} /> · 修订媒体: {new Date(v.updated_at).toLocaleDateString()}</div>
        </div>
        <div className="am-tools">
          {editing ? <><button type="button" className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving}>{saving ? '保存中...' : '保存'}</button><button type="button" className="btn btn-ghost btn-sm" onClick={cancelEdit} disabled={saving}>取消</button></> : <><button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing(true)} disabled={submitting !== null}>编辑</button><button type="button" className="btn btn-danger btn-sm" onClick={onDelete} disabled={submitting !== null}>删除</button></>}
        </div>
      </div>
      {editError && <div className="error-card" role="alert">{editError}</div>}
      <section className="am-detail-section" aria-label="音色试听">
        <h3 className="am-section-title">可播放音色控件</h3>
        <audio controls src={audioUrl} preload="metadata" className="am-voice-player">
          您的浏览器不支持音频播放
        </audio>
      </section>
      <section className="am-detail-section" aria-label="音色信息">
        <h3 className="am-section-title">音色信息</h3>
        <div className="am-detail-field"><span className="am-detail-label">音色名称:</span> {editing ? <input className="input" aria-label="音色名称" value={draft.name} onChange={event => setDraft(current => ({ ...current, name: event.target.value }))} /> : v.name}</div>
        <div className="am-detail-field"><span className="am-detail-label">语言:</span> {editing ? <input className="input" aria-label="语言" value={draft.language ?? ''} onChange={event => setDraft(current => ({ ...current, language: event.target.value }))} /> : v.language || '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">引擎:</span> {editing ? <input className="input" aria-label="合成引擎" value={draft.engine ?? ''} onChange={event => setDraft(current => ({ ...current, engine: event.target.value }))} /> : v.engine || '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">可用状态:</span> {editing ? <><select className="input" aria-label="可用状态" value={draft.availability_status ?? 'available'} onChange={event => setDraft(current => ({ ...current, availability_status: event.target.value as 'available' | 'verified' | 'limited' }))}><option value="available">available</option><option value="verified">verified</option><option value="limited">limited</option></select><input className="input" aria-label="状态说明" value={draft.status_note ?? ''} onChange={event => setDraft(current => ({ ...current, status_note: event.target.value }))} /></> : <>{v.availability_status || '—'}{v.status_note ? ` · ${v.status_note}` : ''}</>}</div>
        <div className="am-detail-field"><span className="am-detail-label">目录启用:</span> <AssetStatus status={v.status} /></div>
        <div className="am-detail-field"><span className="am-detail-label">情感模式:</span> {editing ? <input className="input" aria-label="情感模式" value={draft.emotion_mode ?? ''} onChange={event => setDraft(current => ({ ...current, emotion_mode: event.target.value }))} /> : v.emotion_mode || '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">示例朗读文本:</span> {editing ? <textarea className="input" aria-label="示例朗读文本" rows={3} value={draft.example_text ?? ''} onChange={event => setDraft(current => ({ ...current, example_text: event.target.value }))} /> : v.example_text || '—'}</div>
      </section>
      {editing ? <div className="am-detail-field am-detail-section"><span className="am-detail-label">标签:</span><input className="input" aria-label="音色标签" value={draft.tags.join(', ')} onChange={event => setDraft(current => ({ ...current, tags: event.target.value.split(',').map(tag => tag.trim()).filter(Boolean) }))} /></div> : v.tags.length > 0 && (
        <div className="am-detail-field am-detail-section">
          <span className="am-detail-label">标签:</span>
          {v.tags.map(t => <span key={t} className="badge" style={{ marginRight: 4 }}>{t}</span>)}
        </div>
      )}
      <section className="am-detail-section" aria-label="媒体与兼容性">
        <h3 className="am-section-title">媒体与兼容性</h3>
        <div className="am-detail-field"><span className="am-detail-label">时长:</span> {v.duration_ms ? `${(v.duration_ms / 1000).toFixed(1)}s` : '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">兼容引擎:</span> {editing ? <input className="input" aria-label="兼容引擎" value={draft.compatibility?.engines.join(', ') ?? ''} onChange={event => setDraft(current => ({ ...current, compatibility: { ...(current.compatibility ?? { engines: [], emotion_modes: [], limitations: [] }), engines: event.target.value.split(',').map(item => item.trim()).filter(Boolean) } }))} /> : v.compatibility?.engines.join('、') || '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">支持情感:</span> {editing ? <input className="input" aria-label="支持情感模式" value={draft.compatibility?.emotion_modes.join(', ') ?? ''} onChange={event => setDraft(current => ({ ...current, compatibility: { ...(current.compatibility ?? { engines: [], emotion_modes: [], limitations: [] }), emotion_modes: event.target.value.split(',').map(item => item.trim()).filter(Boolean) } }))} /> : v.compatibility?.emotion_modes.join('、') || '—'}</div>
        <div className="am-detail-field"><span className="am-detail-label">限制:</span> {editing ? <input className="input" aria-label="兼容性限制" value={draft.compatibility?.limitations.join(', ') ?? ''} onChange={event => setDraft(current => ({ ...current, compatibility: { ...(current.compatibility ?? { engines: [], emotion_modes: [], limitations: [] }), limitations: event.target.value.split(',').map(item => item.trim()).filter(Boolean) } }))} /> : v.compatibility?.limitations.join('；') || '无'}</div>
      </section>
    </>
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
  const [language, setLanguage] = useState(existing?.language ?? '')
  const [emotionMode, setEmotionMode] = useState(existing?.emotion_mode ?? '')
  const [exampleText, setExampleText] = useState(existing?.example_text ?? '')
  const [availabilityStatus, setAvailabilityStatus] = useState(existing?.availability_status ?? 'available')
  const [statusNote, setStatusNote] = useState(existing?.status_note ?? '')
  const [engine, setEngine] = useState(existing?.engine ?? '')
  const [compatibility, setCompatibility] = useState(existing?.compatibility ?? { engines: [], emotion_modes: [], limitations: [] })
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
          language, emotion_mode: emotionMode, example_text: exampleText,
          availability_status: availabilityStatus, status_note: statusNote, engine, compatibility,
        })
      } else {
        if (!audioFile) { setError('请选择音频文件'); setSaving(false); return }
        const form = new FormData()
        form.append('file', audioFile)
        form.append('name', name)
        form.append('language', language)
        form.append('emotion_mode', emotionMode)
        form.append('example_text', exampleText)
        form.append('availability_status', availabilityStatus)
        form.append('status_note', statusNote)
        form.append('engine', engine)
        form.append('compatibility', JSON.stringify(compatibility))
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
          <div className="form-field"><label className="form-label">语言</label><input className="input" value={language} onChange={e => setLanguage(e.target.value)} placeholder="zh-CN" /></div>
          <div className="form-field"><label className="form-label">情感模式</label><input className="input" value={emotionMode} onChange={e => setEmotionMode(e.target.value)} placeholder="speaker" /></div>
          <div className="form-field"><label className="form-label">示例朗读文本</label><textarea className="input" rows={2} value={exampleText} onChange={e => setExampleText(e.target.value)} /></div>
          <div className="form-field"><label className="form-label">可用状态</label><select className="input" value={availabilityStatus} onChange={e => setAvailabilityStatus(e.target.value as 'available' | 'verified' | 'limited')}><option value="available">available</option><option value="verified">verified</option><option value="limited">limited</option></select></div>
          <div className="form-field"><label className="form-label">状态说明</label><input className="input" value={statusNote} onChange={e => setStatusNote(e.target.value)} /></div>
          <div className="form-field"><label className="form-label">合成引擎</label><input className="input" value={engine} onChange={e => setEngine(e.target.value)} /></div>
          <div className="form-field"><label className="form-label">兼容引擎（逗号分隔）</label><input className="input" value={compatibility.engines.join(', ')} onChange={e => setCompatibility({ ...compatibility, engines: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></div>
          <div className="form-field"><label className="form-label">支持情感模式（逗号分隔）</label><input className="input" value={compatibility.emotion_modes.join(', ')} onChange={e => setCompatibility({ ...compatibility, emotion_modes: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></div>
          <div className="form-field"><label className="form-label">兼容性限制（逗号分隔）</label><input className="input" value={compatibility.limitations.join(', ')} onChange={e => setCompatibility({ ...compatibility, limitations: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></div>
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

/* ── Main Page ─────────────────────────────────────────────────────────── */

function LocalVoiceLibrary() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [items, setItems] = useState<VoiceDefinition[]>([])
  const [selected, setSelected] = useState<VoiceDefinition | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<VoiceDefinition | null>(null)

  // Cursor pagination state
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const loadedIdsRef = useRef<Set<string>>(new Set())
  const generationRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  const resetAndLoad = useCallback(() => {
    setItems([])
    setNextCursor(null)
    setHasMore(false)
    loadedIdsRef.current = new Set()
    setSelected(null)
    setFeedback(null)
  }, [])

  // Load voices with cursor pagination and stale-request protection
  const loadItems = useCallback(async (cursor?: string) => {
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
      // The current voice endpoint has no q/status/cursor parameters.
      // Filter its authoritative full response locally.
      const res = await fetchVoices()
      if (gen !== generationRef.current) return
      const filtered = res.items.filter((voice) =>
        (!search || `${voice.name} ${voice.tags.join(' ')}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
        && (!statusFilter || voice.status === statusFilter),
      )
      const newItems = filtered.filter(v => !loadedIdsRef.current.has(v.voice_id))
      for (const v of newItems) loadedIdsRef.current.add(v.voice_id)
      setItems(prev => cursor ? [...prev, ...newItems] : newItems)
      if (!cursor) setSelected(newItems[0] ?? null)
      setNextCursor(res.next_cursor)
      setHasMore(res.next_cursor !== null)
    } catch (err) {
      if (gen !== generationRef.current) return
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      if (gen === generationRef.current) {
        setLoading(false)
        setLoadingMore(false)
      }
    }
  }, [search, statusFilter, resetAndLoad])

  // Load on mount and filter change
  useEffect(() => { loadItems() }, [search, statusFilter])

  // Cleanup: abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  // Reset selected item and filters when search/filter changes
  useEffect(() => {
    setSelected(null)
    setFeedback(null)
  }, [search, statusFilter])

  const getId = (item: VoiceDefinition) => item.voice_id

  const handleDelete = async () => {
    if (!deleteTarget) return
    const id = getId(deleteTarget)
    setSubmitting(id); setFeedback(null)
    try {
      await deleteVoice(id)
      setFeedback('已删除')
      setSelected(null)
      await loadItems()
    } catch (err) { setError(err instanceof Error ? err.message : '删除失败') }
    finally { setSubmitting(null); setDeleteTarget(null) }
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

  return (
    <div className="voice-library-panel">
      {feedback && <div className="am-feedback">{feedback}</div>}
      {error && <div className="am-error" role="alert">{error}</div>}

      <div className="am-body am-layout">
        <div className="am-list">
          <div className="am-list-head">
            <div className="am-search-wrap">
              <span className="am-search-ico" aria-hidden="true">🔍</span>
              <input
                type="search"
                placeholder="搜索音色…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="input am-search-input"
                aria-label="搜索音色"
              />
            </div>
            <div className="am-list-action">
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>+ 上传音色</button>
            </div>
            <div className="am-list-filters">
              <select className="am-filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)} aria-label="状态筛选">
                {STATUS_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
          {loading && <div className="am-loading">加载中...</div>}
          {!loading && items.length === 0 && <div className="am-list-empty">没有匹配的音色</div>}
          {!loading && items.map(item => (
            <button
              key={getId(item)}
              type="button"
              className={`am-item am-list-item ${selected && getId(selected) === getId(item) ? 'on am-list-item--selected' : ''}`}
              onClick={() => setSelected(item)}
            >
              <div className="am-list-thumb am-list-thumb-placeholder am-voice-list-thumb" aria-hidden="true">🔊</div>
              <div className="am-item-main am-list-item-main">
                <div className="am-list-item-name">{item.name}</div>
                <div className="am-list-item-desc">{item.language || '—'} · {item.emotion_mode || '—'} · {item.duration_ms ? `${(item.duration_ms / 1000).toFixed(1)}s` : '—'}</div>
                <div className="am-list-item-status"><AssetStatus status={item.status} /></div>
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
            <VoiceDetail
              voice={selected}
              submitting={submitting}
              onSaved={handleInlineSaved}
              onDelete={() => setDeleteTarget(selected)}
            />
          ) : (
            <div className="am-detail-empty">
              <strong>{items.length === 0 ? '暂无数据' : '从左侧列表选择一项'}</strong>
              <span>可从左侧上传音色。</span>
            </div>
          )}
        </div>
      </div>

      {showForm && (
        <VoiceFormDialog
          voice={null}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除音色"
        message={deleteTarget ? `确定将「${deleteTarget.name}」移出资产目录？服务端会保留历史修订与审计记录。` : ''}
        confirmLabel="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

type ProviderTab = 'designs' | 'styles'

function isSpeechProvider(service: ServiceDefinition): boolean {
  return service.enabled && (
    service.capability === 'speech.synthesize'
    || service.capability === 'speech_synthesis'
    || service.capability === 'audio_generation'
  )
}

function PresetVoiceCatalog() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([])
  const [providers, setProviders] = useState<ServiceDefinition[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    setLoading(true)
    setCatalogError(null)
    fetchVoiceProfiles({ kind: 'provider-preset' })
      .then(response => {
        if (!current) return
        setProfiles(response.items)
        setSelectedId(previous => previous && response.items.some(item => item.profile_id === previous)
          ? previous
          : response.items[0]?.profile_id ?? '')
      })
      .catch(error => {
        if (!current) return
        setProfiles([])
        const detail = error instanceof Error ? error.message : '未知错误'
        setCatalogError(`接口尚未就绪：${detail}`)
      })
      .finally(() => { if (current) setLoading(false) })
    fetchServices({ enabled: true })
      .then(response => { if (current) setProviders(response.items.filter(isSpeechProvider)) })
      .catch(() => { if (current) setProviders([]) })
    return () => { current = false }
  }, [])

  const selected = profiles.find(item => item.profile_id === selectedId) ?? null
  const groups = profiles.reduce<Array<{ id: string; name: string; items: VoiceProfile[] }>>((result, profile) => {
    const id = profile.vendor_id || 'unclassified'
    const existing = result.find(group => group.id === id)
    if (existing) existing.items.push(profile)
    else result.push({ id, name: profile.vendor_name || '厂家未标注', items: [profile] })
    return result
  }, [])
  const providerName = selected
    ? providers.find(provider => provider.service_id === selected.provider_id)?.display_name || selected.provider_id
    : '—'

  const selectProfile = (profileId: string) => {
    setSelectedId(profileId)
    setPreviewUrl(null)
    setPreviewError(null)
  }
  const createPreview = async () => {
    if (!selected) return
    setPreviewing(true)
    setPreviewError(null)
    setPreviewUrl(null)
    try {
      const result = await previewVoiceProfile(selected.profile_id, selected.example_text || DEFAULT_PREVIEW_TEXT)
      setPreviewUrl(result.audio_url)
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : '预览接口尚未就绪')
    } finally {
      setPreviewing(false)
    }
  }

  return (
    <section className="voice-preset-panel" aria-label="预置音色">
      {catalogError && <div className="am-error" role="alert">预置音色加载失败：{catalogError}</div>}
      {loading ? <div className="am-loading">加载中...</div> : profiles.length === 0 && !catalogError ? <div className="am-empty">暂无预置音色</div> : (
        <div className="am-layout">
          <aside className="am-list" aria-label="按厂家分组的预置音色">
            {groups.map(group => (
              <section className="voice-vendor-group" key={group.id} aria-labelledby={`voice-vendor-${group.id}`}>
                <h3 id={`voice-vendor-${group.id}`} className="voice-vendor-name">{group.name}</h3>
                {group.items.map(profile => (
                  <button
                    type="button"
                    className={`am-list-item voice-preset-list-item${selectedId === profile.profile_id ? ' am-list-item--selected' : ''}`}
                    key={profile.profile_id}
                    onClick={() => selectProfile(profile.profile_id)}
                    aria-pressed={selectedId === profile.profile_id}
                  >
                    <span className="am-list-item-name">{profile.name}</span>
                    <AssetStatus status={profile.status} />
                  </button>
                ))}
              </section>
            ))}
          </aside>
          <article className="am-detail" aria-label="预置音色详情">
            {selected ? <>
              <div className="am-detail-head">
                <div className="am-voice-avatar" aria-hidden="true">🔊</div>
                <div><h2 className="am-detail-name">{selected.name}</h2><div className="am-detail-tag">只读预置音色 · <AssetStatus status={selected.status} /></div></div>
              </div>
              <section className="am-detail-section" aria-label="预置音色信息">
                <h3 className="am-section-title">音色信息</h3>
                <div className="am-detail-field"><span className="am-detail-label">语言:</span> {languageLabel(selected.language)}</div>
                <div className="am-detail-field"><span className="am-detail-label">性别:</span> {genderLabel(selected.gender)}</div>
                <div className="am-detail-field"><span className="am-detail-label">厂家:</span> {selected.vendor_name || '厂家未标注'}</div>
                <div className="am-detail-field"><span className="am-detail-label">Provider:</span> {providerName}</div>
                <div className="am-detail-field"><span className="am-detail-label">模型:</span> {selected.model_id || '—'}</div>
                <div className="am-detail-field"><span className="am-detail-label">状态:</span> <AssetStatus status={selected.status} /></div>
              </section>
              <section className="am-detail-section" aria-label="真实音色预览">
                <h3 className="am-section-title">音频预览</h3>
                <div className="am-detail-field"><span className="am-detail-label">示例朗读文本:</span> {selected.example_text || DEFAULT_PREVIEW_TEXT}</div>
                <button type="button" className="btn btn-primary btn-sm" onClick={createPreview} disabled={previewing}>{previewing ? '生成中...' : '生成预览'}</button>
                {previewError && <div className="am-error voice-preview-error" role="alert">预览生成失败：{previewError}</div>}
                <audio controls autoPlay={Boolean(previewUrl)} src={previewUrl || undefined} className="am-voice-player">您的浏览器不支持音频播放</audio>
                {!previewUrl && !previewError && <p className="hint">点击“生成预览”后，将调用后端 Provider 生成真实音频。</p>}
              </section>
            </> : <div className="am-detail-empty"><strong>请选择预置音色</strong></div>}
          </article>
        </div>
      )}
    </section>
  )
}

function ProviderProfileForm({
  tab,
  providers,
  initialProviderId,
  onClose,
  onSaved,
}: {
  tab: 'designs' | 'styles'
  providers: ServiceDefinition[]
  initialProviderId: string
  onClose: () => void
  onSaved: () => void | Promise<void>
}) {
  const [providerId, setProviderId] = useState(initialProviderId)
  const initialProvider = providers.find(item => item.service_id === initialProviderId)
  const [modelId, setModelId] = useState(initialProvider?.model ?? '')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const changeProvider = (nextId: string) => {
    setProviderId(nextId)
    setModelId(providers.find(item => item.service_id === nextId)?.model ?? '')
  }
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    const tagList = tags.split(',').map(tag => tag.trim()).filter(Boolean)
    try {
      if (tab === 'designs') {
        await createVoiceProfile({
          name: name.trim(), kind: 'provider-designed', provider_id: providerId,
          model_id: modelId.trim(), design_prompt: description.trim(), tags: tagList,
        })
      } else {
        await createVoiceStyleProfile({
          name: name.trim(), provider_id: providerId, instruction: description.trim(), tags: tagList,
        })
      }
      await onSaved()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const noun = tab === 'designs' ? '音色设计' : '发音风格'
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={event => event.stopPropagation()}>
        <h2 className="modal-title">新建{noun}</h2>
        {error && <div className="error-card" role="alert">{error}</div>}
        <form className="style-form" onSubmit={submit}>
          <div className="form-field"><label className="form-label" htmlFor="profile-provider">Provider *</label><select id="profile-provider" className="input" required value={providerId} onChange={event => changeProvider(event.target.value)}>{providers.map(provider => <option value={provider.service_id} key={provider.service_id}>{provider.display_name}</option>)}</select></div>
          <div className="form-field"><label className="form-label" htmlFor="profile-name">名称 *</label><input id="profile-name" className="input" required value={name} onChange={event => setName(event.target.value)} /></div>
          {tab === 'designs' && <div className="form-field"><label className="form-label" htmlFor="profile-model">模型 *</label><input id="profile-model" className="input" required value={modelId} onChange={event => setModelId(event.target.value)} /></div>}
          <div className="form-field"><label className="form-label" htmlFor="profile-description">{tab === 'designs' ? '设计描述' : '风格指令'} *</label><textarea id="profile-description" className="input" required rows={4} value={description} onChange={event => setDescription(event.target.value)} /></div>
          <div className="form-field"><label className="form-label" htmlFor="profile-tags">标签（逗号分隔）</label><input id="profile-tags" className="input" value={tags} onChange={event => setTags(event.target.value)} /></div>
          <div className="form-actions"><button type="button" className="btn btn-ghost" onClick={onClose}>取消</button><button type="submit" className="btn btn-primary" disabled={saving}>{saving ? '保存中...' : '保存'}</button></div>
        </form>
      </div>
    </div>
  )
}

function ProviderCatalog({ tab }: { tab: ProviderTab }) {
  const [providers, setProviders] = useState<ServiceDefinition[]>([])
  const [providerId, setProviderId] = useState('')
  const [items, setItems] = useState<Array<VoiceProfile | VoiceStyleProfile>>([])
  const [loading, setLoading] = useState(true)
  const [providerError, setProviderError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let current = true
    setProviderError(null)
    fetchServices({ enabled: true })
      .then(response => {
        if (!current) return
        const next = response.items.filter(isSpeechProvider)
        setProviders(next)
        setProviderId(previous => previous && next.some(item => item.service_id === previous) ? previous : next[0]?.service_id ?? '')
      })
      .catch(error => {
        if (current) setProviderError(error instanceof Error ? error.message : 'Provider 列表加载失败')
      })
    return () => { current = false }
  }, [])

  useEffect(() => {
    let current = true
    setLoading(true)
    setCatalogError(null)
    const request = tab === 'styles'
      ? fetchVoiceStyleProfiles({ provider_id: providerId || undefined })
      : fetchVoiceProfiles({ kind: 'provider-designed', provider_id: providerId || undefined })
    request
      .then(response => { if (current) setItems(response.items) })
      .catch(() => {
        if (!current) return
        setItems([])
        setCatalogError('接口尚未就绪，请先完成 VoiceProfile API 配置。')
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [providerId, reload, tab])

  const title = tab === 'designs' ? '音色设计' : '发音风格'

  return (
    <section className="voice-provider-panel" aria-label={title}>
      <div className="voice-provider-toolbar">
        <label htmlFor={`voice-provider-${tab}`}>Provider</label>
        <select
          id={`voice-provider-${tab}`}
          className="input"
          value={providerId}
          onChange={event => setProviderId(event.target.value)}
          disabled={providers.length === 0}
        >
          {providers.length === 0 && <option value="">Provider 未配置</option>}
          {providers.map(provider => <option key={provider.service_id} value={provider.service_id}>{provider.display_name}</option>)}
        </select>
        <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)} disabled={!providerId}>+ 新建{title}</button>
      </div>
      {providerError && <div className="am-error" role="alert">Provider 列表加载失败：{providerError}</div>}
      {!providerError && providers.length === 0 && <div className="am-empty-state"><strong>Provider 未配置</strong><span>请先在模型服务中启用支持语音合成的 Provider。</span></div>}
      {catalogError && <div className="am-error" role="alert">{catalogError}</div>}
      {loading ? <div className="am-loading">加载中...</div> : items.length > 0 && (
        <div className="voice-profile-list">
          {items.map(item => {
            const style = 'style_profile_id' in item
            const id = style ? item.style_profile_id : item.profile_id
            return (
              <article className="card voice-profile-card" key={id}>
                <div className="voice-profile-heading"><strong>{item.name}</strong><AssetStatus status={item.status} /></div>
                <div className="am-detail-field"><span className="am-detail-label">Provider:</span> {item.provider_id || '通用'}</div>
                <div className="am-detail-field"><span className="am-detail-label">修订:</span> {item.revision}</div>
                {style ? <p>{item.instruction}</p> : <>
                  <div className="am-detail-field"><span className="am-detail-label">模型:</span> {item.model_id}</div>
                  <p>{item.design_prompt || '暂无音色描述'}</p>
                </>}
                {item.tags.length > 0 && <div className="am-tags">{item.tags.map(tag => <span className="am-tag" key={tag}>{tag}</span>)}</div>}
              </article>
            )
          })}
        </div>
      )}
      {showCreate && <ProviderProfileForm tab={tab} providers={providers} initialProviderId={providerId} onClose={() => setShowCreate(false)} onSaved={() => setReload(value => value + 1)} />}
    </section>
  )
}

export function VoiceManagementPage() {
  const [activeTab, setActiveTab] = useState('library')
  return (
    <div className="page">
      <div className="page-head am-header">
        <h1 className="page-title">音色管理</h1>
        <p className="page-desc">管理本地音色资产，以及由模型服务 Provider 提供的预置音色、音色设计和发音风格。</p>
      </div>
      <Tabs items={VOICE_TABS} active={activeTab} onChange={setActiveTab} />
      <div role="tabpanel" id={`tab-panel-${activeTab}`} aria-labelledby={`tab-${activeTab}`}>
        {activeTab === 'library'
          ? <LocalVoiceLibrary />
          : activeTab === 'presets'
            ? <PresetVoiceCatalog />
            : <ProviderCatalog tab={activeTab as ProviderTab} />}
      </div>
    </div>
  )
}
