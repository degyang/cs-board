import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '../components/ui/BackButton'
import { Tabs } from '../components/ui/Tabs'
import { useAsync } from '../lib/api/queries'
import { createTask, fetchCreateOptions, uploadInputs } from '../lib/api/client'
import { fetchStyles, fetchVoices } from '../lib/api/assets'
import { getAssetBlobUrl, getVoiceContentUrl } from '../lib/api/http'
import type { StyleTemplate, VoiceDefinition } from '../lib/api/types'

const PIPELINE_ID = 'mountain-av-v1'
const TABS = [
  { key: 'intro', label: '任务介绍' }, { key: 'script', label: '视频文案' },
  { key: 'voice', label: '声音生成' }, { key: 'output', label: '输出类型' },
  { key: 'visual', label: '视觉设置' }, { key: 'final', label: '成片设置' },
] as const
type TabKey = (typeof TABS)[number]['key']
const LINE_DENSITIES = [{ id: 'minimal', label: '精简' }, { id: 'standard', label: '标准' }, { id: 'rich', label: '丰富' }, { id: 'complete', label: '完整' }]
const SHOTS = [1, 2, 3, 4]

interface FormState {
  title: string; summary: string; script: string; targetChars: number
  voiceSource: string; voiceAssetId: string; referenceFile: File | null
  engine: string; visualSource: string; styleAssetId: string
  shotsPerImage: number; lineDensity: string; brandText: string
  visualAnchorEnabled: boolean; includeSubtitles: boolean
}
interface CreatedTask { task_id: string; run_id: string; trace_id?: string }

function sentencePreview(value: string, targetChars: number): { text: string; segments: string[] } {
  const atoms = value.split(/(?<=[。！？!?；;])|\n+/u).map((part) => part.trim()).filter(Boolean)
  const segments: string[] = []; let current = ''
  for (const atom of atoms) {
    if (!current) current = atom
    else if (current.length + atom.length <= targetChars) current += atom
    else { segments.push(current); current = atom }
  }
  if (current) segments.push(current)
  return { text: segments.join('\n\n'), segments }
}
function safeError(error: unknown): string { return error instanceof Error ? error.message : '请求失败' }
function optionLabel(option: { id: string; label: string }) { return option.label || option.id }

export function CreateTaskPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabKey>('intro')
  const [form, setForm] = useState<FormState>({ title: '', summary: '', script: '', targetChars: 80, voiceSource: 'uploaded-reference', voiceAssetId: '', referenceFile: null, engine: '', visualSource: '', styleAssetId: '', shotsPerImage: 1, lineDensity: 'standard', brandText: '', visualAnchorEnabled: true, includeSubtitles: true })
  const [created, setCreated] = useState<CreatedTask | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const mountedRef = useRef(true); const submissionIdRef = useRef<string | null>(null); const defaultsAppliedRef = useRef(false); const submittingRef = useRef(false)
  useEffect(() => () => { mountedRef.current = false }, [])

  const options = useAsync(() => fetchCreateOptions(), [])
  const voices = useAsync(() => fetchVoices(), [])
  const styles = useAsync(() => fetchStyles({ kind: 'preset' }), [])
  useEffect(() => {
    const value = options.data
    if (!value || defaultsAppliedRef.current) return
    defaultsAppliedRef.current = true
    setForm((previous) => ({ ...previous, engine: value.defaults.engine, visualSource: value.defaults.visual_source, targetChars: value.defaults.target_chars, shotsPerImage: value.defaults.shots_per_image, lineDensity: value.defaults.line_density, visualAnchorEnabled: value.defaults.visual_anchor_enabled, includeSubtitles: value.defaults.include_subtitles, voiceSource: value.voice_sources.find((item) => item.available)?.id ?? previous.voiceSource }))
  }, [options.data])
  useEffect(() => {
    const first = voices.data?.items.find((item) => item.status === 'active' && item.enabled)
    if (first) setForm((previous) => previous.voiceAssetId ? previous : { ...previous, voiceAssetId: first.voice_id })
  }, [voices.data])
  useEffect(() => {
    const first = styles.data?.items.find((item) => item.status === 'active')
    if (first) setForm((previous) => previous.styleAssetId ? previous : { ...previous, styleAssetId: first.style_id })
  }, [styles.data])

  const preview = useMemo(() => sentencePreview(form.script, Math.max(1, form.targetChars)), [form.script, form.targetChars])
  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((previous) => ({ ...previous, [key]: value }))
  const selectedVoice = voices.data?.items?.find((item) => item.voice_id === form.voiceAssetId)
  const selectedStyle = styles.data?.items?.find((item) => item.style_id === form.styleAssetId)
  const option = (group: 'engines' | 'visual_sources' | 'voice_sources', id: string) => options.data?.[group].find((item) => item.id === id)

  function validate() {
    const errors: Record<string, string> = {}; const limits = options.data?.limits
    if (!form.title.trim()) errors.title = '请输入任务名称'
    if (!form.summary.trim()) errors.summary = '请输入任务摘要'
    if (form.script.trim().length < (limits?.script_min_chars ?? 10)) errors.script = `文案至少需要 ${limits?.script_min_chars ?? 10} 个字`
    if (limits && (form.targetChars < limits.target_chars_min || form.targetChars > limits.target_chars_max)) errors.targetChars = `目标分段长度需在 ${limits.target_chars_min}–${limits.target_chars_max} 之间`
    if (!options.data) errors.options = 'create-options 尚未联调，当前仅可预览，暂不可提交'
    const engine = option('engines', form.engine); const visual = option('visual_sources', form.visualSource)
    if (!engine || !engine.available) errors.engine = engine?.reason || '该输出引擎当前不可用'
    if (!visual || !visual.available) errors.visualSource = visual?.reason || '该视觉来源当前不可用'
    if (form.voiceSource === 'voice-asset' && !form.voiceAssetId) errors.voiceAssetId = '请选择真实音色资产'
    if (form.voiceSource === 'uploaded-reference' && !form.referenceFile && !created) errors.referenceFile = '首次保存请选择参考音频'
    if (form.visualSource === 'preset' && !form.styleAssetId) errors.styleAssetId = '请选择真实风格资产'
    if (options.data && form.brandText.length > options.data.limits.brand_text_max_chars) errors.brandText = `账号文字不能超过 ${options.data.limits.brand_text_max_chars} 字`
    setFieldErrors(errors); return Object.keys(errors).length === 0
  }
  function buildInputs() {
    const data = new FormData(); data.set('script', form.script); data.set('target_chars', String(form.targetChars)); data.set('voice_source', form.voiceSource)
    if (form.voiceSource === 'voice-asset') data.set('voice_asset_id', form.voiceAssetId)
    if (form.referenceFile) data.set('reference', form.referenceFile)
    data.set('visual_source', form.visualSource); if (form.visualSource === 'preset') data.set('style_asset_id', form.styleAssetId)
    data.set('shots_per_image', String(form.shotsPerImage)); data.set('line_density', form.lineDensity); data.set('brand_text', form.brandText)
    data.set('visual_anchor_enabled', String(form.visualAnchorEnabled)); data.set('include_subtitles', String(form.includeSubtitles)); return data
  }
  async function saveInputs(taskId: string) {
    submittingRef.current = true
    setSubmitting(true); setSaveError(null)
    try { await uploadInputs(taskId, buildInputs()); if (mountedRef.current) navigate(`/tasks/${encodeURIComponent(taskId)}`) }
    catch (error) { if (mountedRef.current) setSaveError(safeError(error)) }
    finally { submittingRef.current = false; if (mountedRef.current) setSubmitting(false) }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (submitting || submittingRef.current || !validate()) return
    if (created) { await saveInputs(created.task_id); return }
    submittingRef.current = true
    setSubmitting(true); setSubmitError(null)
    try {
      if (!submissionIdRef.current) submissionIdRef.current = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `submission-${Date.now()}`
      const response = await createTask({ title: form.title.trim(), summary: form.summary.trim(), engine: form.engine, pipeline_id: PIPELINE_ID, submission_id: submissionIdRef.current })
      if (!mountedRef.current) return
      setCreated({ task_id: response.task_id, run_id: response.run_id, trace_id: response.trace_id }); await saveInputs(response.task_id)
    } catch (error) { submittingRef.current = false; if (mountedRef.current) { setSubmitError(safeError(error)); setSubmitting(false) } }
  }
  function next() { const index = TABS.findIndex((tab) => tab.key === activeTab); if (index < TABS.length - 1) setActiveTab(TABS[index + 1].key) }
  function previous() { const index = TABS.findIndex((tab) => tab.key === activeTab); if (index > 0) setActiveTab(TABS[index - 1].key) }
  const renderError = (key: string) => fieldErrors[key] && <div className="hint error" role="alert">{fieldErrors[key]}</div>
  const renderAssetState = (loading: boolean, error: string | null, empty: string) => loading ? <div className="hint">正在读取真实资产…</div> : error ? <div className="error-card" role="alert">真实资产读取失败：{error}</div> : empty ? <div className="hint">{empty}</div> : null

  return <div className="page page-narrow">
    <BackButton to="/" label="返回任务队列" />
    <header className="page-head"><h1 className="page-title">新建任务</h1><p className="page-desc">按六个 Tab 完成任务输入预览；提交后创建并保存 Task，随后进入任务工作台。</p></header>
    <Tabs items={TABS.map((tab) => tab.key === 'script' ? { ...tab, count: form.script.length } : tab)} active={activeTab} onChange={(key) => setActiveTab(key as TabKey)} />
    {options.error && <div className="notice notice-warn" role="status">create-options 读取失败：{options.error}。当前仅可预览，暂不可提交。</div>}
    <form onSubmit={submit} noValidate>
      {activeTab === 'intro' && <div className="tab-pane card"><div className="field"><label htmlFor="title">任务名称</label><input id="title" className="input" value={form.title} onChange={(event) => update('title', event.target.value)} disabled={submitting} />{renderError('title')}</div><div className="field"><label htmlFor="summary">任务摘要</label><textarea id="summary" className="textarea" rows={5} value={form.summary} onChange={(event) => update('summary', event.target.value)} disabled={submitting} />{renderError('summary')}</div></div>}
      {activeTab === 'script' && <div className="tab-pane card"><div className="copy-split"><div className="copy-col"><label className="copy-label" htmlFor="script">原始文案</label><textarea id="script" className="textarea" rows={9} value={form.script} onChange={(event) => update('script', event.target.value)} disabled={submitting} />{renderError('script')}<div className="copy-count">实时字数：<b>{form.script.length}</b></div></div><div className="copy-col"><div className="copy-label-row"><span className="copy-label">切分预览</span><span className="copy-tag">完整句子边界</span></div><textarea className="textarea preview" rows={9} readOnly value={preview.text} placeholder="输入文案后显示只读预览" /><div className="copy-count">预览：<b>{preview.segments.length}</b> 段 · {preview.text.length} 字</div><p className="hint">此处是提交前预览，不是后端权威 script_preparation。</p></div></div><div className="field"><label htmlFor="targetChars">目标分段长度</label><input id="targetChars" className="input input-sm" type="number" value={form.targetChars} onChange={(event) => update('targetChars', Number(event.target.value))} disabled={submitting} />{options.data && <span className="hint">服务端范围：{options.data.limits.target_chars_min}–{options.data.limits.target_chars_max}</span>}{renderError('targetChars')}</div></div>}
      {activeTab === 'voice' && <div className="tab-pane card"><h3 className="card-title">真实音色资产</h3>{renderAssetState(voices.loading, voices.error, (voices.data?.items ?? []).length === 0 ? '真实音色列表为空。' : '')}{(voices.data?.items ?? []).length > 0 && <div className="opt-grid">{(voices.data?.items ?? []).map((voice: VoiceDefinition) => <label key={voice.voice_id} className={'opt-card' + (form.voiceAssetId === voice.voice_id ? ' selected' : '') + (voice.status !== 'active' || !voice.enabled ? ' unsupported' : '')}><input type="radio" name="voiceAssetId" checked={form.voiceAssetId === voice.voice_id} onChange={() => update('voiceAssetId', voice.voice_id)} disabled={voice.status !== 'active' || !voice.enabled || submitting} /><span className="opt-name">{voice.name}{voice.status !== 'active' || !voice.enabled ? '（不可用）' : ''}</span><span className="opt-desc">{voice.description || voice.tags.join(' · ') || '真实音色资产'}</span>{voice.status === 'active' && voice.enabled && <audio controls preload="none" src={getVoiceContentUrl(voice.voice_id)} />}</label>)}</div>}{renderError('voiceAssetId')}<div className="field"><span>音色来源</span>{options.data?.voice_sources.map((source) => <label key={source.id} className="checkbox-row"><input type="radio" name="voiceSource" checked={form.voiceSource === source.id} onChange={() => update('voiceSource', source.id)} disabled={!source.available || submitting} />{optionLabel(source)}{!source.available && `（不可用：${source.reason || '服务端能力未就绪'}）`}</label>)}</div><div className="field"><label htmlFor="referenceFile">参考音频</label><input id="referenceFile" type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac" onChange={(event) => update('referenceFile', event.target.files?.[0] ?? null)} disabled={submitting} />{form.referenceFile && <div className="hint">已选择：{form.referenceFile.name}</div>}{renderError('referenceFile')}</div></div>}
      {activeTab === 'output' && <div className="tab-pane card"><p className="zone-desc">输出引擎与视觉来源独立选择；可用性完全来自服务端 create-options。</p><div className="opt-grid">{options.data?.engines.map((item) => <button type="button" key={item.id} className={'opt-card' + (form.engine === item.id ? ' selected' : '') + (!item.available ? ' unsupported' : '')} onClick={() => item.available && update('engine', item.id)} disabled={!item.available || submitting}><span className="opt-name">{optionLabel(item)}</span><span className="opt-desc">{item.available ? '服务端报告可用' : `不可用：${item.reason || '服务端未提供能力'}`}</span></button>)}</div>{!options.data && <div className="hint">等待 create-options 返回可用引擎。</div>}{renderError('engine')}</div>}
      {activeTab === 'visual' && <div className="tab-pane card"><p className="zone-desc">选择真实风格资产并查看服务端预览。</p><div className="opt-grid">{options.data?.visual_sources.map((item) => <button type="button" key={item.id} className={'opt-card' + (form.visualSource === item.id ? ' selected' : '') + (!item.available ? ' unsupported' : '')} onClick={() => item.available && update('visualSource', item.id)} disabled={!item.available || submitting}><span className="opt-name">{optionLabel(item)}</span><span className="opt-desc">{item.available ? '服务端报告可用' : `不可用：${item.reason || '服务端未提供能力'}`}</span></button>)}</div>{form.visualSource === 'preset' && <div className="field"><label htmlFor="styleAssetId">预设风格资产</label>{renderAssetState(styles.loading, styles.error, styles.data?.items.length === 0 ? '真实风格列表为空。' : '')}<select id="styleAssetId" className="select" value={form.styleAssetId} onChange={(event) => update('styleAssetId', event.target.value)} disabled={submitting || styles.loading}>{styles.data?.items.map((style: StyleTemplate) => <option key={style.style_id} value={style.style_id} disabled={style.status !== 'active'}>{style.name}{style.status !== 'active' ? '（不可用）' : ''}</option>)}</select>{selectedStyle?.preview_asset_id && <img src={getAssetBlobUrl(selectedStyle.preview_asset_id)} alt={`${selectedStyle.name} 预览`} style={{ maxWidth: 240, marginTop: 12, borderRadius: 8 }} />}{renderError('styleAssetId')}</div>}{renderError('visualSource')}</div>}
      {activeTab === 'final' && <div className="tab-pane card"><div className="vs-row"><div className="mini-field"><label htmlFor="shotsPerImage">每张图分镜数</label><select id="shotsPerImage" className="select" value={form.shotsPerImage} onChange={(event) => update('shotsPerImage', Number(event.target.value))} disabled={submitting}>{SHOTS.map((value) => <option key={value} value={value}>{value}</option>)}</select></div><div className="mini-field"><label htmlFor="lineDensity">线条绘制量</label><select id="lineDensity" className="select" value={form.lineDensity} onChange={(event) => update('lineDensity', event.target.value)} disabled={submitting}>{LINE_DENSITIES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></div><div className="mini-field"><label htmlFor="brandText">账号/笔身文字</label><input id="brandText" className="input" value={form.brandText} onChange={(event) => update('brandText', event.target.value)} disabled={submitting} />{renderError('brandText')}</div></div><label className="checkbox-row"><input type="checkbox" checked={form.visualAnchorEnabled} onChange={(event) => update('visualAnchorEnabled', event.target.checked)} disabled={submitting} />画面锚定</label><label className="checkbox-row"><input type="checkbox" checked={form.includeSubtitles} onChange={(event) => update('includeSubtitles', event.target.checked)} disabled={submitting} />生成字幕</label><div className="summary-card"><h3>最终汇总</h3><p>任务：{form.title || '未填写'}</p><p>文案：{form.script.length} 字，预览 {preview.segments.length} 段</p><p>引擎：{option('engines', form.engine)?.label || '待服务端选项'}</p><p>视觉：{selectedStyle?.name || form.visualSource || '待选择'}</p><p>音色：{selectedVoice?.name || (form.voiceSource === 'uploaded-reference' ? '参考音频' : '待选择')}</p><p>分镜：每图 {form.shotsPerImage} 个 · 线条 {form.lineDensity} · 字幕 {form.includeSubtitles ? '是' : '否'}</p></div></div>}
      {submitError && <div className="error-card" role="alert">创建 Task 失败：{submitError}</div>}{saveError && <div className="error-card" role="alert"><strong>Task 已创建，输入保存失败</strong><span className="sug">{saveError}</span><span className="sug">task_id：{created?.task_id} · run_id：{created?.run_id}</span></div>}
      <div className="actions"><button type="button" className="btn btn-ghost" onClick={previous} disabled={activeTab === 'intro' || submitting}>上一步</button>{activeTab !== 'final' ? <button type="button" className="btn btn-primary" onClick={next} disabled={submitting}>下一步</button> : <button type="submit" className="btn btn-primary" disabled={submitting || !options.data}>{created ? '重试保存输入' : '创建并保存 Task'}</button>}<Link to="/" className="btn btn-ghost">取消</Link></div>
    </form>
  </div>
}
