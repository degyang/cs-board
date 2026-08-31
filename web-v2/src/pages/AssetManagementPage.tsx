/* ==========================================================================
   素材管理 — Asset Management Page

   Tabs: 预置风格 | 自定义风格 | 音色库
   Layout: left list + right detail
   ========================================================================== */

import { useState, useEffect, useCallback } from 'react'
import { Tabs } from '../components/ui/Tabs'
import { CopyButton } from '../components/ui/CopyButton'
import { fetchStyles, fetchVoices, activateStyle, deactivateStyle, copyStyle, activateVoice, deactivateVoice } from '../lib/api/assets'
import type { StyleTemplate, VoiceDefinition } from '../lib/api/types'

const TAB_ITEMS = [
  { key: 'preset', label: '预置风格' },
  { key: 'custom', label: '自定义风格' },
  { key: 'voice', label: '音色库' },
]

export function AssetManagementPage() {
  const [activeTab, setActiveTab] = useState('preset')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState<(StyleTemplate | VoiceDefinition)[]>([])
  const [selected, setSelected] = useState<StyleTemplate | VoiceDefinition | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  const loadItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (activeTab === 'voice') {
        const res = await fetchVoices({ q: search || undefined, limit: 50 })
        setItems(res.items)
      } else {
        const kind = activeTab as 'preset' | 'custom'
        const res = await fetchStyles({ kind, q: search || undefined, limit: 50 })
        setItems(res.items)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [activeTab, search])

  useEffect(() => {
    loadItems()
  }, [loadItems])

  useEffect(() => {
    setSelected(null)
    setFeedback(null)
  }, [activeTab])

  const handleActivate = async (id: string) => {
    setSubmitting(id)
    setFeedback(null)
    try {
      if (activeTab === 'voice') {
        await activateVoice(id)
      } else {
        await activateStyle(id)
      }
      setFeedback('已启用')
      await loadItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setSubmitting(null)
    }
  }

  const handleDeactivate = async (id: string) => {
    setSubmitting(id)
    setFeedback(null)
    try {
      if (activeTab === 'voice') {
        await deactivateVoice(id)
      } else {
        await deactivateStyle(id)
      }
      setFeedback('已停用')
      await loadItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setSubmitting(null)
    }
  }

  const handleCopy = async (id: string) => {
    setSubmitting(id)
    setFeedback(null)
    try {
      await copyStyle(id)
      setFeedback('已复制')
      await loadItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setSubmitting(null)
    }
  }

  const isVoice = (item: StyleTemplate | VoiceDefinition): item is VoiceDefinition =>
    'voice_id' in item

  return (
    <div className="page-container">
      <div className="am-header">
        <h1 className="am-title">素材管理</h1>
        <p className="am-description">管理预置风格、自定义风格和音色库</p>
      </div>

      <Tabs items={TAB_ITEMS} active={activeTab} onChange={setActiveTab} />

      {feedback && <div className="am-feedback">{feedback}</div>}
      {error && <div className="am-error">{error}</div>}

      <div className="am-search">
        <input
          type="text"
          placeholder="搜索..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="am-search-input"
        />
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
                key={isVoice(item) ? item.voice_id : item.style_id}
                className={`am-list-item ${selected && (isVoice(item) ? item.voice_id : item.style_id) === (isVoice(selected) ? selected.voice_id : selected.style_id) ? 'am-list-item--selected' : ''}`}
                onClick={() => setSelected(item)}
              >
                <div className="am-list-item-name">{item.name}</div>
                <div className="am-list-item-status">{item.status}</div>
              </div>
            ))}
          </div>

          <div className="am-detail">
            {selected ? (
              <>
                <h2 className="am-detail-name">{selected.name}</h2>
                {selected.description && <p className="am-detail-desc">{selected.description}</p>}
                <div className="am-detail-meta">
                  <span>状态: {selected.status}</span>
                  <span>创建: {new Date(selected.created_at).toLocaleDateString()}</span>
                </div>

                <div className="am-detail-actions">
                  {selected.status === 'active' ? (
                    <button
                      className="btn btn-secondary"
                      disabled={submitting !== null}
                      onClick={() => {
                        const id = isVoice(selected) ? selected.voice_id : selected.style_id
                        handleDeactivate(id)
                      }}
                    >
                      {submitting === (isVoice(selected) ? selected.voice_id : selected.style_id) ? '处理中...' : '停用'}
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      disabled={submitting !== null}
                      onClick={() => {
                        const id = isVoice(selected) ? selected.voice_id : selected.style_id
                        handleActivate(id)
                      }}
                    >
                      {submitting === (isVoice(selected) ? selected.voice_id : selected.style_id) ? '处理中...' : '启用'}
                    </button>
                  )}

                  {!isVoice(selected) && activeTab === 'preset' && (
                    <button
                      className="btn btn-secondary"
                      disabled={submitting !== null}
                      onClick={() => handleCopy(selected.style_id)}
                    >
                      {submitting === selected.style_id ? '处理中...' : '复制为自定义'}
                    </button>
                  )}

                  {isVoice(selected) && selected.content_url && (
                    <CopyButton text={selected.content_url}>复制链接</CopyButton>
                  )}
                </div>
              </>
            ) : (
              <div className="am-detail-empty">选择一项查看详情</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
