import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchVoiceAlignmentSettings } from '../lib/api/settings'
import { probeService } from '../lib/api/services'
import type { VoiceAlignmentServiceSummary, VoiceAlignmentSettings } from '../lib/api/types'

const SYNC_RULES = [
  ['文案整理', '新建任务时，按用户规则、目标字数与句子边界整理为多个 Voice Unit；每个 Unit 保留连续原文与顺序。这不是运行时的再次切分文案。'],
  ['逐段合成', '每个 Unit 独立生成 Voice，单段失败不影响其它段落。'],
  ['对齐驱动', 'Whisper 成功时，以已确定锚定文字的时间点驱动画面切换，字幕精确到字。'],
  ['等比降级', 'Whisper 失败时，仅在该 Unit 内按图片数量等比例分配 Voice 总时长。'],
  ['可见降级', 'fallback 是可见的降级标记（工作台可识别），不等同于制作失败。'],
] as const

export function VoiceAlignmentPage() {
  const [settings, setSettings] = useState<VoiceAlignmentSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [probing, setProbing] = useState<string | null>(null)

  const load = async () => {
    setLoading(true); setError(null)
    try { setSettings(await fetchVoiceAlignmentSettings()) }
    catch (err) { setError(err instanceof Error ? err.message : '加载语音与对齐配置失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  const handleProbe = async (id: string) => {
    setProbing(id); setError(null)
    try { await probeService(id); await load() }
    catch (err) { setError(err instanceof Error ? err.message : '探测失败') }
    finally { setProbing(null) }
  }

  return (
    <div className="page page-narrow va-page">
      <div className="page-head">
        <h1 className="page-title">语音与对齐</h1>
        <p className="page-desc">IndexTTS 负责语音克隆；Whisper 负责语音与画面的时间对齐。参考音频和文案属于任务工作台的制作输入，<b>不在此页面上传</b>。</p>
      </div>
      {error && <div className="error-card" role="alert">{error}<button className="btn btn-ghost btn-sm" onClick={() => void load()}>重试</button></div>}
      {loading ? <LoadingSkeleton /> : settings ? <>
        <div className="va-grid">
          <VoiceCard title="IndexTTS" category="语音" description="负责逐段语音合成与语音克隆。" service={settings.speech_synthesis} probing={probing} onProbe={handleProbe} />
          <VoiceCard title="Whisper" category="工具链 · 对齐" description="负责语音与画面的时间对齐，提供字级时间锚点。" service={settings.speech_alignment} probing={probing} onProbe={handleProbe} />
        </div>
        <div className="card va-sync-card"><h2 className="card-title">同步策略</h2><p className="card-sub">产品规则，只读展示；各阶段行为由 pipeline 固定实现，本页不提供策略配置。</p><ol className="va-rules">{SYNC_RULES.map(([title, desc], i) => <li className="va-rule" key={title}><span className="va-rule-step">{i + 1}</span><span className="va-rule-body"><span className="va-rule-title">{title}</span><span className="va-rule-desc">{desc}</span></span></li>)}</ol></div>
        <div className="card va-entry-card"><div className="va-entry-body"><h2 className="card-title">参考音频与文案</h2><p className="card-sub">参考音频与文案请在<b>任务工作台</b>上传——它们是每个任务的制作输入，而不是全局配置。</p></div><div className="va-entry-actions"><Link className="btn btn-sm" to="/tasks">前往任务队列</Link></div></div>
      </> : <div className="empty-state"><div className="empty-title">未找到配置</div></div>}
    </div>
  )
}

function VoiceCard({ title, category, description, service, probing, onProbe }: { title: string; category: string; description: string; service: VoiceAlignmentServiceSummary | null; probing: string | null; onProbe: (id: string) => Promise<void> }) {
  const available = Boolean(service?.availability.available)
  const configured = Boolean(service?.endpoint || service?.model)
  const errorCode = service?.availability.error_code
  return <div className="va-card"><div className="va-card-head"><div className="va-card-title-row"><h2 className="va-card-name">{service?.display_name ?? title}</h2><span className="badge tag-neutral">{category}</span></div><p className="va-card-desc">{description}</p></div><div className="va-status-row"><span className="va-status-item"><span className="va-status-label">配置状态</span><span className={`badge ${configured ? 'st-succeeded' : 'st-failed'}`}>{configured ? '已配置' : '未配置'}</span></span><span className="va-status-item"><span className="va-status-label">可用性</span><span className={`badge ${available ? 'st-succeeded' : 'st-failed'}`}>{available ? '可用' : '不可用'}</span></span></div>{service && <div className="va-config"><div className="va-config-row"><span className="va-config-key">端点</span><span className="va-config-val mono">{service.endpoint ?? '未配置'}</span></div><div className="va-config-row"><span className="va-config-key">模型</span><span className="va-config-val mono">{service.model ?? '未配置'}</span></div></div>}{!available && <div className="va-error"><div className="va-error-head"><span className="va-error-code mono">{errorCode ?? 'E-UNAVAILABLE'}</span><span className="badge st-failed">不可用</span></div><p className="va-error-suggestion">{service?.availability.suggestion ?? '请检查模型服务配置后重试。'}</p></div>}<div className="va-card-actions">{service ? <><Link className="btn btn-sm" to={`/settings/models/${service.service_id}`}>查看模型服务</Link><button className="btn btn-ghost btn-sm" disabled={probing === service.service_id} onClick={() => void onProbe(service.service_id)}>{probing === service.service_id ? '探测中...' : '探测'}</button></> : <Link className="btn btn-sm" to="/settings/models">查看模型服务</Link>}</div><div className="va-card-hint">服务配置统一在“模型服务”中维护；此页不展示 Secret。</div></div>
}

function LoadingSkeleton() { return <><div className="va-grid">{[0, 1].map(i => <div key={i} className="va-card va-skeleton" aria-label="加载中"><div className="va-sk-line w-40" /><div className="va-sk-line w-70" /><div className="va-sk-row"><div className="va-sk-chip" /><div className="va-sk-chip" /></div><div className="va-sk-line w-60" /></div>)}</div><div className="card va-skeleton"><div className="va-sk-line w-30" /><div className="va-sk-line w-80" /></div></> }
