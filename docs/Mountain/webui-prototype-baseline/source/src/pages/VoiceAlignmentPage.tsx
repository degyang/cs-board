import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { SettingsSubnav } from '../features/settings/SettingsSubnav'
import { VoiceServiceCard } from '../features/voice-alignment/VoiceServiceCard'
import { VA_DEMO_VIEWS } from '../features/voice-alignment/fixtures'
import type { VoiceAlignmentView } from '../features/voice-alignment/types'

/* 语音与对齐 /settings/voice-alignment
 * 定位：IndexTTS（语音克隆）+ Whisper（时间对齐）的配置/状态基准页。
 * 边界：
 *  - 参考音频与文案属于任务工作台的制作输入，本页不提供任何上传入口；
 *  - 同步策略是产品规则，只读展示，不提供策略下拉 / 重试开关 / 阈值编辑；
 *  - 数据全部经 Props 注入（原型用 fixtures 演示三态），无任何本地存储。 */

/** 同步策略 · 产品规则（严格只读，顺序即执行顺序） */
const SYNC_RULES: { title: string; desc: string }[] = [
  { title: '文案整理', desc: '文案先被拆分为多个 Voice Unit（按整理规则、字数与句边界）。' },
  { title: '逐段合成', desc: '每个 Unit 独立生成语音，单段失败不影响其它段落。' },
  { title: '对齐驱动', desc: 'Whisper 成功时，以文字时间点驱动画面切换，字幕精确到字。' },
  { title: '等比降级', desc: 'Whisper 失败时，按该 Unit 内图片数等比例分配语音总时长。' },
  { title: '可见降级', desc: 'fallback 是可见的降级标记（工作台可识别），不等同于制作失败。' },
]

export function VoiceAlignmentPage({
  /** 可注入 View Model；缺省用原型 fixtures + 页内切换器演示 */
  view,
}: {
  view?: VoiceAlignmentView
}) {
  const location = useLocation()
  /* 演示态通过 URL 查询参数 ?demo= 切换（available / tts-unavailable / whisper-unavailable / loading），
     页面内不再提供可见切换器；真实接入后由 view 属性注入，忽略 demo。 */
  const demoKey = new URLSearchParams(location.search).get('demo') ?? 'available'
  const demo = VA_DEMO_VIEWS.find((d) => d.key === demoKey) ?? VA_DEMO_VIEWS[0]
  const vm = view ?? demo.view

  /* 原型刷新：点击后该卡片短暂 loading，再回到当前演示态（不触达任何真实 API） */
  const [refreshingId, setRefreshingId] = useState<string | null>(null)
  const timer = useRef<number | null>(null)
  useEffect(() => () => {
    if (timer.current) window.clearTimeout(timer.current)
  }, [])
  const fakeRefresh = (id: string) => {
    setRefreshingId(id)
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setRefreshingId(null), 900)
  }

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">语音与对齐</h1>
        <p className="page-desc">
          IndexTTS 负责语音克隆；Whisper 负责语音与画面的时间对齐。
          参考音频和文案属于任务工作台的制作输入，<b>不在此页面上传</b>。
        </p>
      </div>

      <SettingsSubnav active="voice-alignment" />

      {vm.state === 'loading' ? (
        <LoadingSkeleton />
      ) : (
        <>
          <div className="va-grid">
            <VoiceServiceCard
              vm={vm.tts}
              refreshing={refreshingId === vm.tts.id}
              onRefresh={() => fakeRefresh(vm.tts.id)}
            />
            <VoiceServiceCard
              vm={vm.alignment}
              refreshing={refreshingId === vm.alignment.id}
              onRefresh={() => fakeRefresh(vm.alignment.id)}
            />
          </div>

          {/* 同步策略 · 严格只读 */}
          <div className="card va-sync-card">
            <h2 className="card-title">同步策略</h2>
            <p className="card-sub">
              产品规则，只读展示；各阶段行为由 pipeline 固定实现，本页不提供策略配置。
            </p>
            <ol className="va-rules">
              {SYNC_RULES.map((r, i) => (
                <li key={r.title} className="va-rule">
                  <span className="va-rule-step">{i + 1}</span>
                  <span className="va-rule-body">
                    <span className="va-rule-title">{r.title}</span>
                    <span className="va-rule-desc">{r.desc}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>

          {/* 项目入口：制作输入在任务工作台 */}
          <div className="card va-entry-card">
            <div className="va-entry-body">
              <h2 className="card-title">参考音频与文案</h2>
              <p className="card-sub" style={{ marginBottom: 0 }}>
                参考音频与文案请在<b>任务工作台</b>上传——它们是每个任务的制作输入，而不是全局配置。
              </p>
            </div>
            <div className="va-entry-actions">
              <Link className="btn btn-sm" to="/tasks">
                前往任务队列
              </Link>
              <Link className="btn btn-ghost btn-sm" to="/tasks/new">
                新建任务
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/* 加载骨架：与 ready 态同构的两卡片占位 */
function LoadingSkeleton() {
  return (
    <>
      <div className="va-grid">
        {[0, 1].map((i) => (
          <div key={i} className="va-card va-skeleton" aria-hidden>
            <div className="va-sk-line w-40" />
            <div className="va-sk-line w-70" />
            <div className="va-sk-row">
              <div className="va-sk-chip" />
              <div className="va-sk-chip" />
            </div>
            <div className="va-sk-line w-60" />
            <div className="va-sk-line w-50" />
          </div>
        ))}
      </div>
      <div className="card va-skeleton">
        <div className="va-sk-line w-30" />
        <div className="va-sk-line w-80" />
        <div className="va-sk-line w-70" />
        <div className="va-sk-line w-75" />
      </div>
    </>
  )
}

