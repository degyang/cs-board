import { STAGE_NAMES, type StageKey, type StageSummary } from '../../lib/api/types'
import { statusText } from '../../components/ui/StatusBadge'

// 六阶段时间线：总编排不作为第七个节点，体现在 Run 状态与执行策略中（04 §6.2）
export function StageTimeline({
  stages,
  selected,
  onSelect,
}: {
  stages: StageSummary[]
  selected: StageKey
  onSelect: (key: StageKey) => void
}) {
  const done = new Set(stages.filter((s) => s.status === 'succeeded').map((s) => s.stage))
  return (
    <div className="stage-timeline" role="tablist" aria-label="生产阶段">
      {stages.map((s) => {
        const cls = [
          'stage-node',
          'st-' + s.status,
          selected === s.stage ? 'on' : '',
          done.has(s.stage) ? 'done' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <button
            key={s.stage}
            type="button"
            role="tab"
            aria-selected={selected === s.stage}
            className={cls}
            onClick={() => onSelect(s.stage)}
          >
            <span className="stage-dot">{s.status === 'succeeded' ? '✓' : ''}</span>
            <span className="stage-label">{STAGE_NAMES[s.stage]}</span>
            <span className="stage-state">
              {statusText(s.status)}
              {s.progress ? ` · ${s.progress}` : ''}
            </span>
          </button>
        )
      })}
    </div>
  )
}

