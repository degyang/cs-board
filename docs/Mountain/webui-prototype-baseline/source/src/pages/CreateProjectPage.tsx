import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tabs } from '../components/ui/Tabs'
import { useAsync } from '../lib/api/queries'
import { fetchCapability, submitCommand } from '../lib/api/client'
import type { EngineKind, VisualSourceKind } from '../lib/api/types'
import { useAssetStore } from '../features/asset-management/assetStore'
import type { PresetStyle, VoiceAsset } from '../features/asset-management/assetStore'
import { VOICE_LANG_LABEL, VOICE_EMO_LABEL } from '../features/asset-management/assetStore'
import { AssetThumb } from '../features/asset-management/components'
import { splitBySentences } from '../lib/splitText'

// 新建任务 /create：用 Tab 页分割完整任务的内容（任务介绍 / 视频文案 / 声音生成 /
// 输出类型 / 视觉设置 / 成片设置），所有表单状态保持在页面级，切 Tab 不丢数据。
// engine 与 visual_source 是两个独立字段；不支持的组合由 Capability API 返回，不在前端隐藏。
// 视觉设置中的「预设风格 / 自定义风格」直接读取资产管理（assetStore）的数据，保证两处一致。

const TABS = [
  { key: 'intro', label: '任务介绍' },
  { key: 'copy', label: '视频文案' },
  { key: 'voice', label: '声音生成' },
  { key: 'output', label: '输出类型' },
  { key: 'visual', label: '视觉设置' },
  { key: 'final', label: '成片设置' },
] as const

// 时长展示（与资产管理-音色库 fmt 一致的简洁格式）
function fmtDur(sec: number): string {
  if (!Number.isFinite(sec) || sec <= 0) return '—'
  return sec < 60 ? `${sec.toFixed(1)}s` : `${Math.floor(sec / 60)}m${Math.round(sec % 60)}s`
}

/* ===================== 智能分段 · 按完整句子动态切分 =====================
 * 思路（详见 UI 说明）：
 *   · 分割字数是「段落字数上限」，**不是**强制按多少字硬切。
 *   · 优先按完整句子切分：句号、问号、叹号、感叹号(!)、换行 都算一个完整句的结束。
 *   · 贪心装句成段：每段累计的字符数不超过上限；一旦加入下一句会超，就先把当前段收尾。
 *   · 如果单个原子句本身就超过上限（极少见，比如一长串没有标点的内容），
 *     才按上限值硬切作为兜底，保证「任意文案都能切出来」。
 *   · 这样得到的分段天然按语义边界断开（句号/问号/叹号/换行），不会出现"把一句话从中间砍断"的违和感。
 * ===================================================================== */

// 每张图包含几个分镜（仅「白板动画」引擎）
const SHOTS_PER_IMAGE = [
  { value: '1', label: '1 个分镜（画面最大）' },
  { value: '2', label: '2 个分镜（推荐）' },
  { value: '3', label: '3 个分镜' },
  { value: '4', label: '4 个分镜（最省图口）' },
]

// 线条绘制量（仅「白板动画」引擎）
const LINE_DENSITY = [
  { value: 'minimal', label: '精简 · 24 条' },
  { value: 'standard', label: '标准 · 48 条' },
  { value: 'rich', label: '丰富 · 96 条（推荐）' },
  { value: 'complete', label: '完整 · 全部线条' },
]

// 执行策略（成片设置内下拉选择；默认自动完成，可切换为手动完成逐步确认）
const EXECUTION_STRATEGY = [
  { value: 'auto', label: '自动完成（推荐）' },
  { value: 'manual', label: '手动完成（逐阶段确认）' },
]

export function CreateProjectPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<string>('intro')

  // Tab 1 · 任务介绍
  const [name, setName] = useState('')
  const [summary, setSummary] = useState('')

  // Tab 2 · 视频文案
  const [text, setText] = useState('')
  const [segLen, setSegLen] = useState<number>(45)

  // Tab 3 · 声音生成 —— 音色库与「资产管理-音色库」同源（assetStore.voices）
  const { presets, customs, voices } = useAssetStore()
  const [voiceId, setVoiceId] = useState<string>(voices[0]?.id ?? '')
  const [refAudio, setRefAudio] = useState('')
  // 音色试听：同一时刻只播放一条（点卡片上的 ▶ / ⏸ 切换）
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const togglePlayVoice = (v: VoiceAsset) => {
    if (playingId === v.id) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }
    audioRef.current?.pause()
    const a = new Audio(v.filePath)
    a.onended = () => setPlayingId(null)
    a.play().catch(() => setPlayingId(null))
    audioRef.current = a
    setPlayingId(v.id)
  }

  // Tab 4 · 输出类型（独立字段 engine）
  const [engine, setEngine] = useState<EngineKind>('whiteboard')

  // Tab 5 · 视觉设置（独立字段 visual_source）
  // 预设风格 / 自定义风格 直接来自资产管理（assetStore），两处数据保持一致
  const [visualSource, setVisualSource] = useState<VisualSourceKind>('preset')
  const [presetId, setPresetId] = useState<string>(presets[0]?.id ?? '')
  const [customId, setCustomId] = useState<string>(customs[0]?.id ?? '')

  const selPreset: PresetStyle | null = presets.find((p) => p.id === presetId) ?? null
  const selCustom = customs.find((c) => c.id === customId) ?? null
  const selVoice = voices.find((v) => v.id === voiceId) ?? null

  // Tab 6 · 成片设置（原本由 视频文案 Tab 中的 shots_per_image / brand_or_account 及
  // 输出类型 Tab 中的 line_density 集中迁移过来；其余字段按设计稿补齐）
  const [chineseSubtitle, setChineseSubtitle] = useState(true)
  // 执行策略：auto=自动完成（默认）/ manual=手动完成（逐阶段确认）
  const [executionStrategy, setExecutionStrategy] = useState<'auto' | 'manual'>('auto')
  // 白板动画专属
  const [shotsPerImage, setShotsPerImage] = useState<string>('2')
  const [brandOrAccount, setBrandOrAccount] = useState('')
  const [lineDensity, setLineDensity] = useState<string>('rich')
  const [anchorText, setAnchorText] = useState(true)
  // 动态信息图专属：作为引擎内置能力展示（非用户可关；预留字段以便扩展）
  const semanticTimeline = true
  const smartStructure = true
  const textSafety = true

  const [saved, setSaved] = useState<string | null>(null)

  const capability = useAsync(() => fetchCapability(engine, visualSource), [engine, visualSource])

  const split = useMemo(() => splitBySentences(text, segLen), [text, segLen])

  // 顶栏/角标用的字符数（与 split.chars 一致，单独取便于阅读）
  const charCount = split.chars

  const save = async () => {
    const r = await submitCommand('project.save', {
      name,
      summary,
      text,
      seg_len: segLen,
      shots_per_image: shotsPerImage,
      brand_or_account: brandOrAccount,
      anchor_text: anchorText,
      chinese_subtitle: chineseSubtitle,
      line_density: lineDensity,
      execution_strategy: executionStrategy,
      // 动态信息图内置能力（保存为可观测字段，便于后续扩展）
      semantic_timeline: semanticTimeline,
      smart_structure: smartStructure,
      text_safety: textSafety,
      voice_id: voiceId,
      ref_audio: refAudio,
      engine,
      visual_source: visualSource,
      preset: visualSource === 'preset' ? presetId : undefined,
      custom_style: visualSource === 'custom-reference' ? customId : undefined,
    })
    if (r.ok) setSaved(r.project_id ?? 'p-2402')
  }

  const launch = async () => {
    const r = await submitCommand('project.run.start', { project_id: saved, text })
    if (r.ok) navigate('/projects')
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">新建任务</h1>
        <p className="page-desc">
          按 Tab 逐项填写任务信息，提交文案与声音，一次启动即可自动完成视频。系统会先确定「文字—Voice—图片」<span style={{ whiteSpace: 'nowrap' }}>关系</span>，再逐单元生成 Voice 并同步画面。
        </p>
      </div>

      <Tabs
        items={TABS.map((t) => (t.key === 'copy' ? { ...t, count: charCount || undefined } : { ...t }))}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* ============ Tab 1 · 任务介绍 ============ */}
      {activeTab === 'intro' && (
        <div className="tab-pane">
          <div className="field">
            <label>任务名称</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：量子计算十分钟科普" />
          </div>
          <div className="field">
            <label>任务摘要</label>
            <textarea
              className="textarea"
              style={{ minHeight: 160 }}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="用一两句话概括这个任务的目标、受众或亮点……"
            />
            <div className="hint">{summary.trim().length} 字</div>
          </div>
        </div>
      )}

      {/* ============ Tab 2 · 视频文案 ============ */}
      {activeTab === 'copy' && (
        <div className="tab-pane">
          <div className="copy-split">
            <div className="copy-col">
              <label className="copy-label">原始文案</label>
              <textarea
                className="textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="粘贴要制作成视频的文案……"
              />
              <div className="copy-count">
                <span>字数统计</span>
                <span><b>{charCount}</b> 字</span>
              </div>
            </div>
            <div className="copy-col">
              <div className="copy-label-row">
                <label className="copy-label">分割文案</label>
                <span className="copy-tag">按完整句子动态切分</span>
              </div>
              <textarea
                className="textarea preview"
                readOnly
                value={split.text}
                placeholder="根据「分割字数」自动按完整句子动态分段，预览会显示在这里"
              />
              <div className="copy-count">
                <span>字数统计（智能分段）</span>
                <span><b>{split.chars}</b> 字 · <b>{split.segments}</b> 段</span>
              </div>
            </div>
          </div>

          <div className="vs-row">
            <div className="mini-field">
              <label htmlFor="segLen">分割字数</label>
              <input
                id="segLen"
                className="input"
                type="number"
                min={5}
                value={segLen}
                onChange={(e) => setSegLen(Math.max(5, Number(e.target.value) || 0))}
              />
              <span className="mini-hint">当前 {charCount} 字 · 预计 <b>{split.segments}</b> 段</span>
            </div>
          </div>
        </div>
      )}

      {/* ============ Tab 3 · 声音生成 ============ */}
      {activeTab === 'voice' && (
        <div className="tab-pane">
          <div className="field">
            <label>音色选择</label>
            <p className="zone-desc" style={{ marginTop: 0 }}>
              与「资产管理-音色库」同一数据源；选中项作为成片配音，▶ 可用样例音频试听。受限音色（多语种 / QwenEmotion）可试听但当前环境不可合成。
            </p>
            <select
              className="select"
              style={{ maxWidth: 520 }}
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} · {VOICE_LANG_LABEL[v.langCode ?? ''] ?? '—'} ·{' '}
                  {VOICE_EMO_LABEL[v.emotionMode ?? ''] ?? '—'}
                  {v.status === 'limited' ? '（受限）' : ''}
                </option>
              ))}
            </select>
            {voices.length === 0 && (
              <div className="hint">音色库为空——请先到「资产管理-音色库」添加音色。</div>
            )}
            {selVoice && (
              <div className="vc-preview">
                <button
                  type="button"
                  className={'vc-play' + (playingId === selVoice.id ? ' playing' : '')}
                  aria-label={playingId === selVoice.id ? '停止试听' : '试听'}
                  onClick={() => togglePlayVoice(selVoice)}
                >
                  {playingId === selVoice.id ? '⏸' : '▶'}
                </button>
                <div className="vc-preview-main">
                  <div className="vc-head">
                    <span className="vc-name">{selVoice.name}</span>
                    {selVoice.status === 'limited' && <span className="am-badge am-badge-vm">受限</span>}
                    {selVoice.status === 'verified' && <span className="am-badge am-badge-新增">已验证</span>}
                  </div>
                  <div className="vc-sub">
                    {VOICE_LANG_LABEL[selVoice.langCode ?? ''] ?? '—'} ·{' '}
                    {VOICE_EMO_LABEL[selVoice.emotionMode ?? ''] ?? '—'} · {fmtDur(selVoice.durationSec)}
                    {selVoice.engine ? ` · ${selVoice.engine}` : ''}
                  </div>
                  {selVoice.sampleText && <div className="vc-sample">{selVoice.sampleText}</div>}
                  {selVoice.statusNote && <div className="hint">{selVoice.statusNote}</div>}
                </div>
              </div>
            )}
          </div>
          <div className="field" style={{ marginTop: 8 }}>
            <label>参考音色 / 参考音频</label>
            <input className="input" value={refAudio} onChange={(e) => setRefAudio(e.target.value)} placeholder="上传参考音频以克隆自定义音色（可选）" />
            <div className="hint">上传成功与启动执行是两个独立动作；启动失败时项目与已上传素材保留，无需重新上传。</div>
          </div>
        </div>
      )}

      {/* ============ Tab 4 · 输出类型 ============ */}
      {activeTab === 'output' && (
        <div className="tab-pane">
          <p className="zone-desc">输出引擎决定成片形态；与视觉来源是两个独立选择。</p>
          <div className="opt-grid">
            <button type="button" className={'opt-card' + (engine === 'whiteboard' ? ' selected' : '')} onClick={() => setEngine('whiteboard')}>
              <span className="opt-name">白板动画</span>
              <span className="opt-desc">手绘线条逐步呈现，适合讲解型内容与知识科普；生成成本较低。</span>
            </button>
            <button
              type="button"
              className={'opt-card' + (engine === 'infographic-remotion' ? ' selected' : '') + ' unsupported'}
              onClick={() => setEngine('infographic-remotion')}
            >
              <span className="opt-name">
                动态信息图 <span className="badge tag-neutral">M09 开放</span>
              </span>
              <span className="opt-desc">数据驱动的动态图表，适合对比、趋势类内容；当前由 Capability 返回 unsupported，不显示为可提交任务。</span>
            </button>
          </div>
        </div>
      )}

      {/* ============ Tab 5 · 视觉设置 ============ */}
      {activeTab === 'visual' && (
        <div className="tab-pane">
          <p className="zone-desc">选择预设风格，或提供自定义风格参考与人物组；当前组合是否受支持由服务端 Capability 决定。</p>
          <div className="opt-grid">
            <button type="button" className={'opt-card' + (visualSource === 'preset' ? ' selected' : '')} onClick={() => setVisualSource('preset')}>
              <span className="opt-name">预设风格</span>
              <span className="opt-desc">选择内置 style preset，无需上传素材。</span>
            </button>
            <button
              type="button"
              className={'opt-card' + (visualSource === 'custom-reference' ? ' selected' : '') + ' unsupported'}
              onClick={() => setVisualSource('custom-reference')}
            >
              <span className="opt-name">
                自定义参考 <span className="badge tag-neutral">M09 开放</span>
              </span>
              <span className="opt-desc">风格图 + 1–5 个人物组，需等待 adapter 回归与 capability 测试完成。</span>
            </button>
          </div>
          {visualSource === 'preset' && (
            <div className="field" style={{ marginTop: 14, marginBottom: 0 }}>
              <label>预设风格</label>
              <select className="select" style={{ maxWidth: 360 }} value={presetId} onChange={(e) => setPresetId(e.target.value)}>
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.shortDesc ? ` · ${p.shortDesc}` : ''}
                  </option>
                ))}
              </select>
              {selPreset && (
                <div className="vs-preview">
                  <AssetThumb seed={selPreset.id} emoji="🎨" image={selPreset.image} size="sm" />
                  <div className="vs-meta">
                    <div className="vs-name">
                      {selPreset.name}
                      {selPreset.badge && (
                        <span className={`am-badge am-badge-${selPreset.badge.replace(/\s+/g, '-')}`}>
                          {selPreset.badge}
                        </span>
                      )}
                    </div>
                    <div className="vs-sub">{selPreset.shortDesc || (selPreset.tags ?? []).join(' · ')}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {visualSource === 'custom-reference' && (
            <div className="field" style={{ marginTop: 14, marginBottom: 0 }}>
              <label>自定义风格</label>
              <select className="select" style={{ maxWidth: 360 }} value={customId} onChange={(e) => setCustomId(e.target.value)}>
                {customs.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              {selCustom && (
                <div className="vs-preview">
                  <AssetThumb seed={selCustom.id} emoji="🧩" image={selCustom.styleImage} size="sm" />
                  <div className="vs-meta">
                    <div className="vs-name">{selCustom.name}</div>
                    <div className="vs-sub">
                      {selCustom.characters.length} 个人物
                      {selCustom.characters.length > 0 &&
                        `：${selCustom.characters.map((c) => c.name).join('、')}`}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          {capability.data && !capability.data.supported && (
            <div className="notice notice-warn">
              当前组合（{engine === 'whiteboard' ? '白板动画' : '动态信息图'} + {visualSource === 'preset' ? '预设风格' : '自定义参考'}）暂不受支持：
              {capability.data.reason}
            </div>
          )}
        </div>
      )}

      {/* ============ Tab 6 · 成片设置 ============
       * 设计依据：截图 #1（白板动画）- 三列(分镜/账号/图片上限 sunk 提示) + 画面锚定文字 + 生成字幕 + 线条绘制量
       *           截图 #2（动态信息图）- 语义时间轴 + 智能结构 + 文字安全 + 生成字幕
       * 所有「白板动画」分支字段在引擎为「动态信息图」时不显示；反之同理。
       * 任务名已统一在「任务介绍」Tab 维护，此处不再重复。 */}
      {activeTab === 'final' && (
        <div className="tab-pane">
          {/* ========== 白板动画 分支 ========== */}
          {engine === 'whiteboard' && (
            <>
              <div className="vs-row">
                <div className="mini-field vs-grow">
                  <label>每张图包含几个分镜</label>
                  <select className="select" value={shotsPerImage} onChange={(e) => setShotsPerImage(e.target.value)}>
                    {SHOTS_PER_IMAGE.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div className="mini-field vs-grow">
                  <label>线条绘制量</label>
                  <select
                    className="select"
                    value={lineDensity}
                    onChange={(e) => setLineDensity(e.target.value)}
                  >
                    {LINE_DENSITY.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mini-field vs-grow">
                  <label>笔身文字 / 媒体账号号</label>
                  <input
                    className="input"
                    value={brandOrAccount}
                    onChange={(e) => setBrandOrAccount(e.target.value)}
                    placeholder="例如：你的账号名"
                  />
                </div>
              </div>

              <label className="switch fs-card">
                <input type="checkbox" checked={anchorText} onChange={(e) => setAnchorText(e.target.checked)} />
                <span className="track" />
                <span className="fs-card-text">
                  <span className="fs-card-title">画面锚定文字</span>
                  <span className="fs-card-desc">每个分镜显示一条重点锚击</span>
                </span>
              </label>

              <label className="switch fs-card">
                <input type="checkbox" checked={chineseSubtitle} onChange={(e) => setChineseSubtitle(e.target.checked)} />
                <span className="track" />
                <span className="fs-card-text">
                  <span className="fs-card-title">生成字幕</span>
                  <span className="fs-card-desc">成片会预装中文字幕</span>
                </span>
              </label>
            </>
          )}

          {/* ========== 动态信息图 分支 ========== */}
          {engine === 'infographic-remotion' && (
            <>
              <div className="fs-feature">
                <span className="fs-feature-tag">语义时间轴</span>
                <span className="fs-feature-desc">每个元素绑定真实旁白，讲到才出现</span>
              </div>
              <div className="fs-feature">
                <span className="fs-feature-tag">智能结构</span>
                <span className="fs-feature-desc">自动选图对比、时间轴、层级、因果、案例或总结</span>
              </div>
              <div className="fs-feature">
                <span className="fs-feature-tag">文字安全</span>
                <span className="fs-feature-desc">标题与论点作程序预，不让歪从模型生成中文</span>
              </div>

              <label className="switch fs-card">
                <input type="checkbox" checked={chineseSubtitle} onChange={(e) => setChineseSubtitle(e.target.checked)} />
                <span className="track" />
                <span className="fs-card-text">
                  <span className="fs-card-title">生成字幕</span>
                  <span className="fs-card-desc">成片会预装中文字幕</span>
                </span>
              </label>
            </>
          )}

          <div className="field exec-strategy-field">
            <label htmlFor="execStrategy">执行策略</label>
            <select
              id="execStrategy"
              className="select"
              style={{ maxWidth: 360 }}
              value={executionStrategy}
              onChange={(e) => setExecutionStrategy(e.target.value as 'auto' | 'manual')}
            >
              {EXECUTION_STRATEGY.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <div className="hint">
              {executionStrategy === 'auto'
                ? '阶段化自动推进，用于理解与恢复，不打断默认流程'
                : '运行到每个阶段暂停，等待手动确认后再继续'}
            </div>
          </div>

          <div className="cost-hint">
            {capability.data?.supported && <span>pipeline：<b>{capability.data.pipeline}</b></span>}
          </div>
        </div>
      )}

      <div className="action-bar">
        <button type="button" className="btn btn-primary" disabled={!capability.data?.supported || !charCount} onClick={launch}>
          {saved ? '启动运行' : '保存并启动'}
        </button>
        <button type="button" className="btn btn-ghost" disabled={!charCount} onClick={save}>
          仅保存项目
        </button>
        {saved && <span style={{ fontSize: 13, color: 'var(--nt-primary-700)' }}>已保存 <span className="mono">{saved}</span>（未启动 Run）</span>}
        {!capability.data?.supported && (
          <span style={{ fontSize: 13, color: 'var(--nt-accent-700)' }}>当前引擎/视觉来源组合未开放，无法提交</span>
        )}
      </div>

      <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', marginTop: 16 }}>
        提交流程：客户端校验 → POST /api/projects（保存输入，返回 project_id）→ POST /api/projects/:id/runs（返回
        run_id / trace_id / command_id）→ 跳转项目工作台。
      </p>
    </div>
  )
}

