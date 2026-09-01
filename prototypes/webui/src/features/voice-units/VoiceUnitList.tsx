import { StatusBadge, statusText } from '../../components/ui/StatusBadge'
import { formatSeconds } from '../../lib/formatting'
import type { RunView } from '../../lib/api/types'

// Voice Unit / Visual Item 列表（首版只读展示边界，06 §6.3）
// Whisper 对齐 / 平均切图标签；fallback 可见但误报为失败
export function VoiceUnitList({
  run,
  selectedUnit,
  onSelectUnit,
}: {
  run: RunView
  selectedUnit: string | null
  onSelectUnit: (unitId: string) => void
}) {
  return (
    <div className="wb-col">
      <h3>
        Voice Unit / Visual Item
        <span className="spacer">
          {run.voice_units.length} 单元 · {run.whisper_aligned} Whisper / {run.fallback_units} fallback
        </span>
      </h3>
      {run.voice_units.length === 0 && (
        <p style={{ fontSize: 13, color: 'var(--nt-text-muted)' }}>当前阶段尚未产生 Voice Unit。</p>
      )}
      {run.voice_units.map((u) => (
        <div
          key={u.unit_id}
          className={'unit-item' + (selectedUnit === u.unit_id ? ' on' : '')}
          onClick={() => onSelectUnit(u.unit_id)}
        >
          <div className="unit-head">
            <span className="unit-idx">#{String(u.index).padStart(2, '0')}</span>
            <span className="mono">{u.unit_id}</span>
            <StatusBadge status={u.voice_status} label={u.voice_status === 'succeeded' ? 'Voice 完成' : statusText(u.voice_status)} />
            <span className={'badge ' + (u.alignment === 'whisper' ? 'tag-info' : 'tag-warn')}>
              {u.alignment === 'whisper' ? 'Whisper 对齐' : '平均切图'}
            </span>
            <span>{formatSeconds(u.duration_s)}</span>
          </div>
          <p className="unit-text">{u.text}</p>
          <div className="unit-stats">
            <span>{u.char_count} 字</span>
            {u.alignment === 'whisper' && u.alignment_coverage != null && <span>覆盖率 {(u.alignment_coverage * 100).toFixed(0)}%</span>}
            {u.fallback_reason && <span title={u.fallback_reason}>fallback：低置信度</span>}
          </div>
          {u.visuals.map((v) => (
            <div key={v.visual_id} className="visual-item">
              <span className="visual-thumb">{v.visual_id.replace('v-', '')}</span>
              <span style={{ flex: 1 }}>{v.text_excerpt}</span>
              <span className="mono">{formatSeconds(v.clip_seconds)}</span>
              <span className="mono" title="切换点">⇄{v.switch_point_s?.toFixed(1)}s</span>
              <StatusBadge status={v.status === 'generating' ? 'running' : v.status} label={v.status === 'generating' ? '生成中' : undefined} />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

