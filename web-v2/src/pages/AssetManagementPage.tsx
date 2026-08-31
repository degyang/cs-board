/* ==========================================================================
   Asset Management Page — Three tabs: preset styles, custom styles, voices.
   ========================================================================== */

import { useState, useEffect } from 'react'
import { Tabs } from '../components/ui/Tabs'
import { MountainApiError } from '../lib/api/http'
import {
  fetchPresetStyles,
  fetchCustomStyles,
  createCustomStyle,
  deleteCustomStyle,
  fetchVoiceAssets,
  createVoiceAsset,
  deleteVoiceAsset,
} from '../lib/api/assets'
import type {
  PresetStyle,
  CustomStyle,
  VoiceAsset,
  StyleCategory,
} from '../lib/api/types'

const STYLE_TABS = [
  { key: 'preset', label: '预设风格' },
  { key: 'custom', label: '自定义风格' },
  { key: 'voices', label: '声音库' },
]

const STYLE_CATEGORIES: { value: StyleCategory; label: string }[] = [
  { value: 'realistic', label: '写实' },
  { value: 'anime', label: '动漫' },
  { value: 'watercolor', label: '水彩' },
  { value: 'sketch', label: '素描' },
  { value: 'oil_painting', label: '油画' },
  { value: 'flat', label: '扁平' },
  { value: 'other', label: '其他' },
]

export default function AssetManagementPage() {
  const [activeTab, setActiveTab] = useState('preset')

  return (
    <div className="am-page">
      <header className="am-page__header">
        <h1 className="am-page__title">素材管理</h1>
        <p className="am-page__subtitle">管理预设风格、自定义风格和声音素材</p>
      </header>

      <Tabs
        items={STYLE_TABS}
        active={activeTab}
        onChange={setActiveTab}
      />

      <div className="am-page__content">
        {activeTab === 'preset' && <PresetStylesTab />}
        {activeTab === 'custom' && <CustomStylesTab />}
        {activeTab === 'voices' && <VoicesTab />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Preset Styles Tab (read-only)
// ---------------------------------------------------------------------------

function PresetStylesTab() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<StyleCategory | ''>('')
  const [styles, setStyles] = useState<PresetStyle[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  useEffect(() => {
    fetchPresetStyles()
      .then(data => setStyles(data.items))
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const filtered = styles.filter(s => {
    if (search && !s.name.toLowerCase().includes(search.toLowerCase())) return false
    if (category && s.category !== category) return false
    return true
  })

  if (isLoading) {
    return <div className="am-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="am-error">
        <p>加载预设风格失败</p>
        <p className="am-error__detail">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="am-preset">
      <div className="am-preset__filters">
        <input
          type="text"
          className="am-preset__search"
          placeholder="搜索风格..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          aria-label="搜索预设风格"
        />
        <select
          className="am-preset__category"
          value={category}
          onChange={e => setCategory(e.target.value as StyleCategory | '')}
          aria-label="按分类筛选"
        >
          <option value="">全部分类</option>
          {STYLE_CATEGORIES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="am-empty">暂无预设风格</div>
      ) : (
        <div className="am-style-grid">
          {filtered.map(style => (
            <StyleCard key={style.style_id} style={style} />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Custom Styles Tab (CRUD)
// ---------------------------------------------------------------------------

function CustomStylesTab() {
  const [styles, setStyles] = useState<CustomStyle[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadStyles = () => {
    setIsLoading(true)
    fetchCustomStyles()
      .then(data => setStyles(data.items))
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadStyles()
  }, [])

  const handleDelete = async (styleId: string) => {
    try {
      await deleteCustomStyle(styleId)
      setStyles(prev => prev.filter(s => s.style_id !== styleId))
      setDeleteError(null)
    } catch (err) {
      setDeleteError(err instanceof MountainApiError ? err.message : '删除失败')
    }
  }

  if (isLoading) {
    return <div className="am-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="am-error">
        <p>加载自定义风格失败</p>
        <p className="am-error__detail">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="am-custom">
      <div className="am-custom__header">
        <h2 className="am-custom__title">自定义风格</h2>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => setShowCreate(true)}
        >
          创建风格
        </button>
      </div>

      {showCreate && (
        <CreateStyleForm
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false)
            loadStyles()
          }}
        />
      )}

      {deleteError && (
        <div className="am-error" role="alert">
          删除失败: {deleteError}
        </div>
      )}

      {styles.length === 0 ? (
        <div className="am-empty">暂无自定义风格</div>
      ) : (
        <div className="am-style-grid">
          {styles.map(style => (
            <StyleCard
              key={style.style_id}
              style={style}
              onDelete={() => handleDelete(style.style_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Voices Tab (CRUD)
// ---------------------------------------------------------------------------

function VoicesTab() {
  const [voices, setVoices] = useState<VoiceAsset[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadVoices = () => {
    setIsLoading(true)
    fetchVoiceAssets()
      .then(data => setVoices(data.items))
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadVoices()
  }, [])

  const handleDelete = async (assetId: string) => {
    try {
      await deleteVoiceAsset(assetId)
      setVoices(prev => prev.filter(v => v.asset_id !== assetId))
      setDeleteError(null)
    } catch (err) {
      setDeleteError(err instanceof MountainApiError ? err.message : '删除失败')
    }
  }

  if (isLoading) {
    return <div className="am-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="am-error">
        <p>加载声音素材失败</p>
        <p className="am-error__detail">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="am-voices">
      <div className="am-voices__header">
        <h2 className="am-voices__title">声音库</h2>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => setShowCreate(true)}
        >
          上传声音
        </button>
      </div>

      {showCreate && (
        <CreateVoiceForm
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false)
            loadVoices()
          }}
        />
      )}

      {deleteError && (
        <div className="am-error" role="alert">
          删除失败: {deleteError}
        </div>
      )}

      {voices.length === 0 ? (
        <div className="am-empty">暂无声音素材</div>
      ) : (
        <div className="am-voice-grid">
          {voices.map(voice => (
            <VoiceCard
              key={voice.asset_id}
              voice={voice}
              onDelete={() => handleDelete(voice.asset_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared Components
// ---------------------------------------------------------------------------

interface StyleCardProps {
  style: PresetStyle | CustomStyle
  onDelete?: () => void
}

function StyleCard({ style, onDelete }: StyleCardProps) {
  const categoryLabel = STYLE_CATEGORIES.find(c => c.value === style.category)?.label ?? style.category

  return (
    <article className="am-style-card">
      {style.preview_url ? (
        <img
          src={style.preview_url}
          alt={style.name}
          className="am-style-card__preview"
        />
      ) : (
        <div className="am-style-card__placeholder" aria-hidden="true" />
      )}
      <div className="am-style-card__body">
        <h3 className="am-style-card__name">{style.name}</h3>
        <span className="am-style-card__category">{categoryLabel}</span>
        {style.description && (
          <p className="am-style-card__desc">{style.description}</p>
        )}
        {onDelete && (
          <button
            type="button"
            className="btn btn--danger btn--sm"
            onClick={onDelete}
            aria-label={`删除风格 ${style.name}`}
          >
            删除
          </button>
        )}
      </div>
    </article>
  )
}

interface VoiceCardProps {
  voice: VoiceAsset
  onDelete: () => void
}

function VoiceCard({ voice, onDelete }: VoiceCardProps) {
  return (
    <article className="am-voice-card">
      <div className="am-voice-card__body">
        <h3 className="am-voice-card__name">{voice.name}</h3>
        {voice.description && (
          <p className="am-voice-card__desc">{voice.description}</p>
        )}
        <span className="am-voice-card__duration">
          {voice.duration_seconds.toFixed(1)}秒
        </span>
        {voice.preview_url && (
          <audio controls src={voice.preview_url} className="am-voice-card__audio">
            您的浏览器不支持音频播放
          </audio>
        )}
        <button
          type="button"
          className="btn btn--danger btn--sm"
          onClick={onDelete}
          aria-label={`删除声音 ${voice.name}`}
        >
          删除
        </button>
      </div>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Create Forms
// ---------------------------------------------------------------------------

interface CreateStyleFormProps {
  onClose: () => void
  onSuccess: () => void
}

function CreateStyleForm({ onClose, onSuccess }: CreateStyleFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState<StyleCategory>('other')
  const [files, setFiles] = useState<File[]>([])
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setIsPending(true)
    setError(null)
    try {
      await createCustomStyle({ name, description, category, reference_images: files })
      onSuccess()
    } catch (err) {
      setError(err instanceof MountainApiError ? err.message : '创建失败')
    } finally {
      setIsPending(false)
    }
  }

  return (
    <form className="am-form" onSubmit={handleSubmit}>
      <h3 className="am-form__title">创建自定义风格</h3>

      <div className="am-form__field">
        <label htmlFor="style-name">风格名称 *</label>
        <input
          id="style-name"
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          required
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="style-desc">描述</label>
        <textarea
          id="style-desc"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="style-category">分类</label>
        <select
          id="style-category"
          value={category}
          onChange={e => setCategory(e.target.value as StyleCategory)}
        >
          {STYLE_CATEGORIES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </div>

      <div className="am-form__field">
        <label htmlFor="style-images">参考图片</label>
        <input
          id="style-images"
          type="file"
          accept="image/*"
          multiple
          onChange={e => setFiles(Array.from(e.target.files ?? []))}
        />
      </div>

      {error && (
        <div className="am-form__error" role="alert">
          {error}
        </div>
      )}

      <div className="am-form__actions">
        <button type="button" className="btn btn--secondary" onClick={onClose}>
          取消
        </button>
        <button
          type="submit"
          className="btn btn--primary"
          disabled={isPending || !name.trim()}
        >
          {isPending ? '创建中...' : '创建'}
        </button>
      </div>
    </form>
  )
}

interface CreateVoiceFormProps {
  onClose: () => void
  onSuccess: () => void
}

function CreateVoiceForm({ onClose, onSuccess }: CreateVoiceFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !file) return
    setIsPending(true)
    setError(null)
    try {
      await createVoiceAsset({ name, description, audio_file: file })
      onSuccess()
    } catch (err) {
      setError(err instanceof MountainApiError ? err.message : '上传失败')
    } finally {
      setIsPending(false)
    }
  }

  return (
    <form className="am-form" onSubmit={handleSubmit}>
      <h3 className="am-form__title">上传声音素材</h3>

      <div className="am-form__field">
        <label htmlFor="voice-name">名称 *</label>
        <input
          id="voice-name"
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          required
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="voice-desc">描述</label>
        <textarea
          id="voice-desc"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="voice-file">音频文件 *</label>
        <input
          id="voice-file"
          type="file"
          accept="audio/*"
          onChange={e => setFile(e.target.files?.[0] ?? null)}
          required
        />
      </div>

      {error && (
        <div className="am-form__error" role="alert">
          {error}
        </div>
      )}

      <div className="am-form__actions">
        <button type="button" className="btn btn--secondary" onClick={onClose}>
          取消
        </button>
        <button
          type="submit"
          className="btn btn--primary"
          disabled={isPending || !name.trim() || !file}
        >
          {isPending ? '上传中...' : '上传'}
        </button>
      </div>
    </form>
  )
}
