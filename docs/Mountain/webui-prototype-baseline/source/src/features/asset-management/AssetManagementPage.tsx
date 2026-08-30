import { useEffect, useRef, useState } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import { AssetThumb, AssetImage, ConfirmModal } from './components'
import { useAssetStore, type PresetStyle, type CustomStyle, type VoiceAsset, type Character } from './assetStore'
import { VOICE_LANG_LABEL as LANG_LABEL, VOICE_EMO_LABEL as EMO_LABEL, VOICE_STATUS_LABEL as STATUS_LABEL } from './assetStore'
import { useTabCrud } from './useTabCrud'

/* ==========================================================================
   资产管理 /assets
   子资产通过 Tab 分隔：预设风格 / 自定义风格 / 音色库。
   每个 Tab = 左侧列表（搜索 + 新建 + 选中）+ 右侧详情（查看 / 编辑 / 删除）。
   文字可编辑、图片可指定路径或上传加载、数据 localStorage 持久化。
   ========================================================================== */

/* ---------------- 可播放音色控件（真实音频优先，缺源时模拟） ---------------- */
function fmt(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
function VoicePlayer({ src, durationSec }: { src?: string; durationSec: number }) {
  const [playing, setPlaying] = useState(false)
  const [t, setT] = useState(0)
  const simRef = useRef<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const playingRef = useRef(false)
  useEffect(() => {
    playingRef.current = playing
  }, [playing])

  const stopSim = () => {
    if (simRef.current) {
      window.clearInterval(simRef.current)
      simRef.current = null
    }
  }
  const startSim = (from: number) => {
    stopSim()
    const start = Date.now() - from * 1000
    simRef.current = window.setInterval(() => {
      const el = (Date.now() - start) / 1000
      if (el >= durationSec) {
        setT(durationSec)
        setPlaying(false)
        stopSim()
      } else setT(el)
    }, 100)
  }
  const ensureAudio = () => {
    if (audioRef.current) return audioRef.current
    const a = new Audio()
    a.addEventListener('timeupdate', () => setT(a.currentTime))
    a.addEventListener('ended', () => {
      setPlaying(false)
      stopSim()
    })
    audioRef.current = a
    return a
  }
  const toggle = () => {
    if (playing) {
      setPlaying(false)
      stopSim()
      audioRef.current?.pause()
      return
    }
    const playable = !!src && (src.startsWith('data:') || src.startsWith('http') || src.startsWith('/'))
    const from = t >= durationSec ? 0 : t
    setT(from)
    setPlaying(true)
    if (playable) {
      const a = ensureAudio()
      a.src = src!
      a.currentTime = from
      a.play().catch(() => startSim(from))
      window.setTimeout(() => {
        if (playingRef.current && a.currentTime <= from + 0.05 && !a.ended) startSim(from)
      }, 400)
    } else {
      startSim(from)
    }
  }
  useEffect(() => () => {
    stopSim()
    audioRef.current?.pause()
  }, [])

  const pct = durationSec ? (t / durationSec) * 100 : 0
  return (
    <div className="voice-player">
      <button className="voice-play" onClick={toggle} aria-label={playing ? '暂停' : '播放'}>
        {playing ? '❚❚' : '▶'}
      </button>
      <div className={`voice-eq${playing ? ' playing' : ''}`}>
        <i /><i /><i /><i /><i />
      </div>
      <div className="voice-bar">
        <i style={{ width: pct + '%' }} />
      </div>
      <span className="voice-time">
        {fmt(t)} / {fmt(durationSec)}
      </span>
    </div>
  )
}

/* ---------------- 详情工具条（编辑/保存/取消/删除 + 已保存提示） ---------------- */
function DetailTools({
  editing,
  canSave,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  saved,
}: {
  editing: boolean
  canSave: boolean
  onEdit: () => void
  onSave: () => void
  onCancel: () => void
  onDelete: () => void
  saved: boolean
}) {
  return (
    <div className="am-tools">
      {!editing ? (
        <>
          <button className="btn btn-primary btn-sm" onClick={onEdit}>
            编辑
          </button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}>
            删除
          </button>
        </>
      ) : (
        <>
          {saved && <span className="am-saved">✓ 已保存</span>}
          <button className="btn btn-primary btn-sm" onClick={onSave} disabled={!canSave}>
            保存
          </button>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}>
            取消
          </button>
        </>
      )}
    </div>
  )
}

/* ---------------- 空状态 ---------------- */
function EmptyState({ label, onNew }: { label: string; onNew: () => void }) {
  return (
    <div className="am-empty-state">
      <div className="am-empty-illu">🗂️</div>
      <div className="am-empty-title">暂无{label}</div>
      <div className="am-empty-sub">点击右侧「新建」创建第一个{label}</div>
      <button className="btn btn-primary btn-sm" onClick={onNew}>
        + 新建{label}
      </button>
    </div>
  )
}

/* ---------------- 列表头部：搜索 + 新建 ---------------- */
function ListHead({ q, setQ, onNew }: { q: string; setQ: (v: string) => void; onNew: () => void }) {
  return (
    <div className="am-list-head">
      <div className="am-search">
        <span className="am-search-ico">🔍</span>
        <input className="input" placeholder="搜索资产…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <button className="btn btn-primary btn-sm am-new-btn" onClick={onNew}>
        + 新建
      </button>
    </div>
  )
}

/* ====================================================================== */
/* Tab：预设风格                                                            */
/* ====================================================================== */
const BADGE_OPTIONS: { value: string | null; label: string }[] = [
  { value: null, label: '无' },
  { value: '热门', label: '热门' },
  { value: '新增', label: '新增' },
  { value: '推荐', label: '推荐' },
]

function PresetTab({ store }: { store: ReturnType<typeof useAssetStore> }) {
  const { presets, addPreset, updatePreset, removePreset, uid } = store
  const crud = useTabCrud<PresetStyle>(
    presets,
    addPreset,
    updatePreset,
    removePreset,
    () => ({
      id: uid('ps'),
      name: '新风格',
      image: null,
      intro: '',
      shortDesc: '',
      tags: [],
      badge: null,
      refImages: [],
      source: '',
      prompt: '',
    }),
  )
  const [q, setQ] = useState('')
  const [saved, setSaved] = useState(false)
  // 关键字编辑缓冲：用本地 state 承接输入，避免受控派生值（tags.join）
  // 在末尾输入 / 中文输入法组字时被反复 split→join 打断导致文字吞掉
  const [tagText, setTagText] = useState('')
  useEffect(() => {
    setTagText((crud.view?.tags ?? []).join('、'))
  }, [crud.editing, crud.sel])
  // 搜索：name / shortDesc / tags 任一关键字命中
  const needle = q.trim().toLowerCase()
  const list = presets.filter((p) => {
    if (!needle) return true
    if (p.name.toLowerCase().includes(needle)) return true
    if (p.shortDesc?.toLowerCase().includes(needle)) return true
    if (p.tags?.some((t) => t.toLowerCase().includes(needle))) return true
    return false
  })

  const onSave = () => {
    crud.save()
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="am-body">
      <div className="am-list">
        <ListHead q={q} setQ={setQ} onNew={crud.startNew} />
        {list.map((s) => (
          <button
            key={s.id}
            type="button"
            className={'am-item' + (s.id === crud.sel ? ' on' : '')}
            onClick={() => crud.setSel(s.id)}
          >
            <AssetThumb seed={s.id} emoji="🎨" image={s.image} size="sm" />
            <div className="am-item-main">
              <div className="am-item-name">
                {s.name}
                {s.badge && <span className={`am-badge am-badge-${s.badge.replace(/\s+/g, '-')}`}>{s.badge}</span>}
              </div>
              <div className="am-item-sub">{s.shortDesc || (s.tags?.[0] ?? (s.prompt ? '含提示词' : '无提示词'))}</div>
              {s.tags && s.tags.length > 0 && (
                <div className="am-tags">
                  {s.tags.slice(0, 4).map((t) => (
                    <span key={t} className="am-tag">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </button>
        ))}
        {list.length === 0 && <div className="am-list-empty">无匹配结果</div>}
      </div>

      <div className="am-detail card">
        {!crud.view ? (
          <EmptyState label="预设风格" onNew={crud.startNew} />
        ) : (
          <>
            <div className="am-detail-head">
              <AssetThumb seed={crud.view.id} emoji="🎨" image={crud.view.image} size="lg" />
              <div style={{ flex: 1 }}>
                <h2 className="am-detail-title">
                  {crud.editing ? '编辑预设风格' : crud.view.name}
                  {!crud.editing && crud.view.badge && (
                    <span className={`am-badge am-badge-${crud.view.badge!.replace(/\s+/g, '-')} am-badge-lg`}>
                      {crud.view.badge}
                    </span>
                  )}
                </h2>
                <div className="am-detail-tag">
                  预设风格 · {crud.isNew ? '新建' : '查看 / 编辑'}
                  {crud.view.source && <> · 出处 {crud.view.source}</>}
                </div>
              </div>
              <DetailTools
                editing={crud.editing}
                canSave={!!crud.view.name.trim()}
                onEdit={crud.startEdit}
                onSave={onSave}
                onCancel={crud.cancel}
                onDelete={crud.askDelete}
                saved={saved}
              />
            </div>

            <div className="field">
              <label>风格名称 *</label>
              {crud.editing ? (
                <input
                  className="input"
                  value={crud.view.name}
                  onChange={(e) => crud.setDraft({ ...crud.view!, name: e.target.value })}
                  placeholder="例如：手绘白板 · 苔绿"
                />
              ) : (
                <p className="am-prose">{crud.view.name}</p>
              )}
            </div>

            <div className="field">
              <label>4 字口诀（搜索关键词 / 卡片副标题）</label>
              {crud.editing ? (
                <input
                  className="input"
                  value={crud.view.shortDesc ?? ''}
                  onChange={(e) => crud.setDraft({ ...crud.view!, shortDesc: e.target.value })}
                  placeholder="例如：粗黑线 · 少量配色 · 清爽留白"
                />
              ) : (
                <p className="am-prose am-short">{crud.view.shortDesc || '（未填写）'}</p>
              )}
            </div>

            <div className="field">
              <label>角标（卡片 / 详情页左上角小标签 · 单选，缺省无）</label>
              {crud.editing ? (
                <div className="am-radio-row">
                  {BADGE_OPTIONS.map((opt) => {
                    const active = (crud.view!.badge ?? null) === opt.value
                    return (
                      <label
                        key={String(opt.value)}
                        className={'am-radio' + (active ? ' on' : '')}
                      >
                        <input
                          type="radio"
                          name="preset-badge"
                          checked={active}
                          onChange={() =>
                            crud.setDraft({ ...crud.view!, badge: opt.value })
                          }
                        />
                        {opt.label}
                      </label>
                    )
                  })}
                </div>
              ) : (
                <p className="am-prose">{crud.view.badge || '（无）'}</p>
              )}
            </div>

            <div className="field">
              <label>关键字（用于搜索 · 用空格 / 顿号分隔，可自由输入）</label>
              {crud.editing ? (
                <input
                  className="input"
                  value={tagText}
                  onChange={(e) => {
                    const v = e.target.value
                    setTagText(v)
                    crud.setDraft({
                      ...crud.view!,
                      tags: v.split(/[、,，\s]+/).map((x) => x.trim()).filter(Boolean),
                    })
                  }}
                  placeholder="例如：白板 粗线 马克笔 知识科普"
                />
              ) : (
                <div className="am-tags">
                  {(crud.view.tags ?? []).length === 0 ? (
                    <span className="am-empty">未设置关键字</span>
                  ) : (
                    crud.view.tags!.map((t) => (
                      <span key={t} className="am-tag">
                        {t}
                      </span>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="field">
              <label>风格图片（可指定路径或上传）</label>
              <AssetImage
                value={crud.view.image}
                label="风格图片"
                placeholder="🎨"
                allowEdit={crud.editing}
                onChange={(v) => crud.editing && crud.setDraft({ ...crud.view!, image: v })}
              />
            </div>

            <div className="field">
              <label>视觉配方（用作文案生成的提示词）</label>
              {crud.editing ? (
                <textarea
                  className="textarea"
                  style={{ minHeight: 110 }}
                  value={crud.view.intro}
                  onChange={(e) => crud.setDraft({ ...crud.view!, intro: e.target.value })}
                  placeholder="底色 / 主色 / 主结构 / 禁忌 ……"
                />
              ) : (
                <pre className="am-prompt">{crud.view.intro || '（未填写）'}</pre>
              )}
            </div>

            {(crud.view.refImages?.length ?? 0) > 0 && (
              <div className="field">
                <label>本地参考图（用于路由 · 共 {crud.view.refImages!.length} 张）</label>
                <div className="am-ref-grid">
                  {crud.view.refImages!.map((p) => (
                    <a
                      key={p}
                      href={p}
                      target="_blank"
                      rel="noreferrer"
                      className="am-ref-tile"
                      title={p.split('/').pop()}
                    >
                      <img src={p} alt="" loading="lazy" />
                      <span className="am-ref-cap">{p.split('/').pop()}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            <div className="field">
              <label>出处</label>
              {crud.editing ? (
                <input
                  className="input mono"
                  value={crud.view.source ?? ''}
                  onChange={(e) => crud.setDraft({ ...crud.view!, source: e.target.value })}
                  placeholder="例如：cs-board STYLE_PRESETS"
                />
              ) : (
                <p className="am-prose mono">{crud.view.source || '（未填写）'}</p>
              )}
            </div>
          </>
        )}
      </div>

      <ConfirmModal
        open={!!crud.confirmId}
        title="删除预设风格"
        message="确定要删除该预设风格吗？此操作不可撤销。"
        onConfirm={crud.doDelete}
        onCancel={() => crud.setConfirmId(null)}
      />
    </div>
  )
}

/* ====================================================================== */
/* Tab：自定义风格                                                          */
/* ====================================================================== */
function CustomTab({ store }: { store: ReturnType<typeof useAssetStore> }) {
  const { customs, addCustom, updateCustom, removeCustom, uid } = store
  const crud = useTabCrud<CustomStyle>(
    customs,
    addCustom,
    updateCustom,
    removeCustom,
    () => ({ id: uid('cs'), name: '新自定义风格', styleImage: null, characters: [] }),
  )
  const [q, setQ] = useState('')
  const [saved, setSaved] = useState(false)
  const list = customs.filter((c) => c.name.toLowerCase().includes(q.toLowerCase()))

  const v = crud.view
  const setV = (patch: Partial<CustomStyle>) => crud.setDraft({ ...v!, ...patch })
  const setChar = (cid: string, patch: Partial<Character>) =>
    crud.setDraft({ ...v!, characters: v!.characters.map((c) => (c.id === cid ? { ...c, ...patch } : c)) })
  const addChar = () =>
    crud.setDraft({
      ...v!,
      characters: [...v!.characters, { id: uid('ch'), name: '新人物', intro: '', refImage: null }],
    })
  const delChar = (cid: string) =>
    crud.setDraft({ ...v!, characters: v!.characters.filter((c) => c.id !== cid) })

  const onSave = () => {
    crud.save()
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="am-body">
      <div className="am-list">
        <ListHead q={q} setQ={setQ} onNew={crud.startNew} />
        {list.map((s) => (
          <button
            key={s.id}
            type="button"
            className={'am-item' + (s.id === crud.sel ? ' on' : '')}
            onClick={() => crud.setSel(s.id)}
          >
            <AssetThumb seed={s.id} emoji="🧩" image={s.styleImage} size="sm" />
            <div className="am-item-main">
              <div className="am-item-name">{s.name}</div>
              <div className="am-item-sub">{s.characters.length} 个人物</div>
            </div>
          </button>
        ))}
        {list.length === 0 && <div className="am-list-empty">无匹配结果</div>}
      </div>

      <div className="am-detail card">
        {!v ? (
          <EmptyState label="自定义风格" onNew={crud.startNew} />
        ) : (
          <>
            <div className="am-detail-head">
              <AssetThumb seed={v.id} emoji="🧩" image={v.styleImage} size="lg" />
              <div style={{ flex: 1 }}>
                <h2 className="am-detail-title">{crud.editing ? '编辑自定义风格' : v.name}</h2>
                <div className="am-detail-tag">风格名 + 风格图 + 人物组</div>
              </div>
              <DetailTools
                editing={crud.editing}
                canSave={!!v.name.trim()}
                onEdit={crud.startEdit}
                onSave={onSave}
                onCancel={crud.cancel}
                onDelete={crud.askDelete}
                saved={saved}
              />
            </div>

            <div className="field">
              <label>风格名 *</label>
              {crud.editing ? (
                <input className="input" value={v.name} onChange={(e) => setV({ name: e.target.value })} />
              ) : (
                <p className="am-prose">{v.name}</p>
              )}
            </div>

            <div className="field">
              <label>风格图（可指定路径或上传）</label>
              <div className="am-img-row">
                <div>
                  <AssetImage
                    value={v.styleImage}
                    label="风格图"
                    placeholder="🧩"
                    allowEdit={crud.editing}
                    onChange={(img) => crud.editing && setV({ styleImage: img })}
                  />
                  <div className="am-img-cap">风格图</div>
                </div>
              </div>
            </div>

            <div className="field">
              <label>人物组（可添加多人）</label>
              {(crud.editing ? v.characters : v.characters).map((c) => (
                <div className="char-card" key={c.id}>
                  <div className="char-head">
                    <AssetThumb seed={c.id} emoji="🙂" image={c.refImage} size="sm" />
                    {crud.editing ? (
                      <input
                        className="input"
                        style={{ flex: 1 }}
                        value={c.name}
                        onChange={(e) => setChar(c.id, { name: e.target.value })}
                      />
                    ) : (
                      <div className="am-item-name" style={{ flex: 1 }}>
                        {c.name}
                      </div>
                    )}
                    {crud.editing && (
                      <button type="button" className="btn btn-danger btn-sm" onClick={() => delChar(c.id)}>
                        删除
                      </button>
                    )}
                  </div>
                  <div className="field" style={{ marginBottom: 0, marginTop: 10 }}>
                    <label>人物参考图</label>
                    <AssetImage
                      value={c.refImage}
                      label="人物参考图"
                      placeholder="🙂"
                      size="xl"
                      allowEdit={crud.editing}
                      onChange={(img) => crud.editing && setChar(c.id, { refImage: img })}
                    />
                  </div>
                  <div className="field" style={{ marginTop: 12, marginBottom: 0 }}>
                    <label>风格介绍</label>
                    {crud.editing ? (
                      <textarea
                        className="textarea"
                        style={{ minHeight: 64 }}
                        value={c.intro}
                        onChange={(e) => setChar(c.id, { intro: e.target.value })}
                        placeholder="描述该人物的音色 / 画面位置 / 性格特征……"
                      />
                    ) : (
                      <p className="am-prose">{c.intro || '（未填写）'}</p>
                    )}
                  </div>
                </div>
              ))}
              {crud.editing && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={addChar}>
                  + 添加人物
                </button>
              )}
              {!crud.editing && v.characters.length === 0 && <div className="am-empty">该风格暂无人物</div>}
            </div>
          </>
        )}
      </div>

      <ConfirmModal
        open={!!crud.confirmId}
        title="删除自定义风格"
        message="确定要删除该自定义风格吗？其下所有人物将一并移除，此操作不可撤销。"
        onConfirm={crud.doDelete}
        onCancel={() => crud.setConfirmId(null)}
      />
    </div>
  )
}

/* ====================================================================== */
/* ---------------- 音色库 · 字典 ----------------
 * 标签字典已抽到 assetStore.ts（VOICE_LANG_LABEL / VOICE_EMO_LABEL / VOICE_STATUS_LABEL），
 * 供「资产管理-音色库」与「新建任务-声音生成」共用，保证两处展示一致。 */

/* Tab：音色库                                                              */
/* ====================================================================== */
function VoiceTab({ store }: { store: ReturnType<typeof useAssetStore> }) {
  const { voices, addVoice, updateVoice, removeVoice, uid } = store
  const crud = useTabCrud<VoiceAsset>(
    voices,
    addVoice,
    updateVoice,
    removeVoice,
    () => ({
      id: uid('va'),
      name: '新音色',
      filePath: '',
      durationSec: 6,
      langCode: 'ZH',
      engine: 'indextts-2',
      emotionMode: 'speaker',
      tags: [],
      status: 'available',
    }),
  )
  const [q, setQ] = useState('')
  const [saved, setSaved] = useState(false)
  const kw = q.toLowerCase()
  const list = voices.filter(
    (v) =>
      v.name.toLowerCase().includes(kw) ||
      (v.tags ?? []).some((t) => t.toLowerCase().includes(kw)) ||
      LANG_LABEL[v.langCode ?? '']?.toLowerCase().includes(kw),
  )

  const v = crud.view
  const onSave = () => {
    crud.save()
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div className="am-body">
      <div className="am-list">
        <ListHead q={q} setQ={setQ} onNew={crud.startNew} />
        {list.map((vo) => (
          <button
            key={vo.id}
            type="button"
            className={'am-item' + (vo.id === crud.sel ? ' on' : '')}
            onClick={() => crud.setSel(vo.id)}
          >
            <AssetThumb seed={vo.id} emoji="🔊" size="sm" />
            <div className="am-item-main">
              <div className="am-item-name">{vo.name}</div>
              <div className="am-item-sub">
                {LANG_LABEL[vo.langCode ?? ''] ?? '—'} · {EMO_LABEL[vo.emotionMode ?? ''] ?? '—'} ·{' '}
                {fmt(vo.durationSec)}
              </div>
            </div>
            {vo.status === 'limited' && <span className="am-badge am-badge-vm">受限</span>}
            {vo.status === 'verified' && <span className="am-badge">已验证</span>}
          </button>
        ))}
        {list.length === 0 && <div className="am-list-empty">无匹配结果</div>}
      </div>

      <div className="am-detail card">
        {!v ? (
          <EmptyState label="音色" onNew={crud.startNew} />
        ) : (
          <>
            <div className="am-detail-head">
              <AssetThumb seed={v.id} emoji="🔊" size="lg" />
              <div style={{ flex: 1 }}>
                <h2 className="am-detail-title">{crud.editing ? '编辑音色' : v.name}</h2>
                <div className="am-detail-tag">
                  {LANG_LABEL[v.langCode ?? ''] ?? '未设置语言'} ·{' '}
                  {EMO_LABEL[v.emotionMode ?? ''] ?? '未设置情感模式'} · {v.engine || '—'}
                  {v.status ? ` · ${STATUS_LABEL[v.status] ?? v.status}` : ''}
                </div>
              </div>
              <DetailTools
                editing={crud.editing}
                canSave={!!v.name.trim()}
                onEdit={crud.startEdit}
                onSave={onSave}
                onCancel={crud.cancel}
                onDelete={crud.askDelete}
                saved={saved}
              />
            </div>

            <div className="field">
              <label>音色名称 *</label>
              {crud.editing ? (
                <input className="input" value={v.name} onChange={(e) => crud.setDraft({ ...v, name: e.target.value })} />
              ) : (
                <p className="am-prose">{v.name}</p>
              )}
            </div>

            <div className="field">
              <label>音色文件路径</label>
              {crud.editing ? (
                <>
                  <input
                    className="input mono"
                    value={v.filePath}
                    onChange={(e) => crud.setDraft({ ...v, filePath: e.target.value })}
                    placeholder="/voices/xxx.wav 或 http(s)://…"
                  />
                  <div className="hint">相对 public 目录（如 /voices/voice_03.wav），或填写可访问的 http(s) URL / data URL。</div>
                </>
              ) : (
                <p className="am-prose mono">{v.filePath || '（未设置路径）'}</p>
              )}
            </div>

            <div className="field">
              <label>可播放音色控件</label>
              <VoicePlayer src={v.filePath} durationSec={v.durationSec} />
            </div>

            <div className="field">
              <label>语言 / 引擎 / 状态</label>
              {crud.editing ? (
                <div className="vs-row" style={{ marginTop: 0 }}>
                  <div className="mini-field">
                    <label>语言</label>
                    <select
                      className="select"
                      value={v.langCode ?? 'ZH'}
                      onChange={(e) => crud.setDraft({ ...v, langCode: e.target.value })}
                    >
                      {Object.entries(LANG_LABEL).map(([k, label]) => (
                        <option key={k} value={k}>{label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="mini-field">
                    <label>引擎</label>
                    <select
                      className="select"
                      value={v.engine ?? 'indextts-2'}
                      onChange={(e) => crud.setDraft({ ...v, engine: e.target.value })}
                    >
                      <option value="indextts-2">IndexTTS-2</option>
                      <option value="indextts-2.5">IndexTTS-2.5</option>
                    </select>
                  </div>
                  <div className="mini-field">
                    <label>状态</label>
                    <select
                      className="select"
                      value={v.status ?? 'available'}
                      onChange={(e) => crud.setDraft({ ...v, status: e.target.value })}
                    >
                      {Object.entries(STATUS_LABEL).map(([k, label]) => (
                        <option key={k} value={k}>{label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              ) : (
                <p className="am-prose">
                  {LANG_LABEL[v.langCode ?? ''] ?? '—'} · {v.engine || '—'} ·{' '}
                  {v.status ? (STATUS_LABEL[v.status] ?? v.status) : '—'}
                </p>
              )}
            </div>

            <div className="field">
              <label>情感模式</label>
              {crud.editing ? (
                <>
                  <select
                    className="select"
                    value={v.emotionMode ?? 'speaker'}
                    onChange={(e) => crud.setDraft({ ...v, emotionMode: e.target.value })}
                  >
                    {Object.entries(EMO_LABEL).map(([k, label]) => (
                      <option key={k} value={k}>{label}</option>
                    ))}
                  </select>
                  {(v.emotionMode === 'reference_audio') && (
                    <>
                      <input
                        className="input mono"
                        style={{ marginTop: 8 }}
                        value={v.emotionRefPath ?? ''}
                        onChange={(e) => crud.setDraft({ ...v, emotionRefPath: e.target.value })}
                        placeholder="/voices/emo_sad.wav（情感参考音频）"
                      />
                      <div className="hint">情感权重 {v.emotionWeight ?? '—'}（0~1）；参考音频越贴目标情绪，迁移越准。</div>
                    </>
                  )}
                  {(v.emotionMode === 'vector' || v.emotionMode === 'text') && (
                    <div className="hint" style={{ marginTop: 6 }}>
                      情感权重 {v.emotionWeight ?? '—'}（0~1）。
                      {v.emotionMode === 'text' && ' 情绪文本依赖 QwenEmotion；低显存环境建议改用显式情绪向量。'}
                    </div>
                  )}
                </>
              ) : (
                <p className="am-prose">
                  {EMO_LABEL[v.emotionMode ?? ''] ?? '—'}
                  {v.emotionWeight != null && `（权重 ${v.emotionWeight}）`}
                  {v.emotionRefPath && (
                    <>
                      {' '}
                      · 参考音频 <span className="mono">{v.emotionRefPath}</span>
                    </>
                  )}
                </p>
              )}
            </div>

            <div className="field">
              <label>示例朗读文本</label>
              {crud.editing ? (
                <textarea
                  className="input"
                  rows={3}
                  value={v.sampleText ?? ''}
                  onChange={(e) => crud.setDraft({ ...v, sampleText: e.target.value })}
                  placeholder="该音色在 WebUI examples 中的展示语，可试听对照。"
                />
              ) : (
                <p className="am-prose">{v.sampleText || '（未填写）'}</p>
              )}
            </div>

            <div className="field">
              <label>关键字</label>
              {crud.editing ? (
                <input
                  className="input"
                  value={(v.tags ?? []).join('、')}
                  onChange={(e) =>
                    crud.setDraft({
                      ...v,
                      tags: e.target.value.split(/[、,，\s]+/).map((x) => x.trim()).filter(Boolean),
                    })
                  }
                  placeholder="用「、」分隔，例如：中文、悲伤、叙述"
                />
              ) : (
                <div className="am-tagrow">
                  {(v.tags ?? []).map((t) => (
                    <span key={t} className="badge">{t}</span>
                  ))}
                  {(v.tags ?? []).length === 0 && <p className="am-prose">（无）</p>}
                </div>
              )}
            </div>

            {v.statusNote && (
              <div className="field">
                <label>兼容性 / 状态说明</label>
                <p className="am-prose">{v.statusNote}</p>
              </div>
            )}
          </>
        )}
      </div>

      <ConfirmModal
        open={!!crud.confirmId}
        title="删除音色"
        message="确定要删除该音色吗？此操作不可撤销。"
        onConfirm={crud.doDelete}
        onCancel={() => crud.setConfirmId(null)}
      />
    </div>
  )
}

/* ---------------- 页面：Tab 容器 ---------------- */
const AM_TABS = [
  { key: 'preset', label: '预设风格' },
  { key: 'custom', label: '自定义风格' },
  { key: 'voice', label: '音色库' },
] as const

export function AssetManagementPage() {
  const [tab, setTab] = useState<string>('preset')
  const store = useAssetStore()

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">资产管理</h1>
        <p className="page-desc">
          集中维护视频生产所需的风格与音色资产。预设风格、自定义风格、音色库分别用 Tab 分隔；每个 Tab 内左侧为资产列表、右侧为选中资产的具体内容。
          支持「新建 / 编辑 / 删除」，文字可直接编辑，图片可指定路径或上传加载，所有改动自动保存到本地。
        </p>
      </div>

      <Tabs items={AM_TABS.map((t) => ({ ...t }))} active={tab} onChange={setTab} />

      {tab === 'preset' && <PresetTab store={store} />}
      {tab === 'custom' && <CustomTab store={store} />}
      {tab === 'voice' && <VoiceTab store={store} />}
    </div>
  )
}

