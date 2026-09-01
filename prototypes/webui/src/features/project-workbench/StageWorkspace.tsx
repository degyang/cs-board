import { formatSeconds } from '../../lib/formatting'
import { submitCommand } from '../../lib/api/client'
import type { RunView, StageKey } from '../../lib/api/types'

// 阶段主工作区：每个阶段展示对应内容与允许的操作（04 §6.4）
// 所有操作调用共享 Application Command，前端不得通过删除文件表达「重做」
export function StageWorkspace({ run, stage, selectedUnitId }: { run: RunView; stage: StageKey; selectedUnitId: string | null }) {
  const unit = run.voice_units.find((u) => u.unit_id === selectedUnitId) ?? run.voice_units[0]
  const cmd = (command: string, payload: Record<string, unknown>) => {
    void submitCommand(command, payload).then((r) => window.alert(r.message))
  }

  return (
    <div className="wb-col">
      <h3>
        阶段工作区
        <span className="spacer">
          {run.strategy === 'auto' ? '执行策略：自动完成' : '执行策略：逐步执行'}
        </span>
      </h3>

      {stage === 'split' && (
        <div>
          <p style={{ fontSize: 13.5, color: 'var(--nt-text-secondary)', marginTop: 0 }}>
            文案已分割为 {run.whisper_aligned + run.fallback_units} 个 Voice Unit、48 个 Visual Item，文字覆盖率 100%。
            分割以「2–3 句话 + 1–2 张图」为常见提示，不承诺固定数量。
          </p>
          <div className="cost-hint">
            <span>规划依据：句意完整性 &gt; 字数均衡 &gt; 画面可切分性</span>
          </div>
          <div style={{ marginTop: 14 }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => cmd('stage.rerun', { stage: 'split', run_id: run.run_id })}>
              重跑分割
            </button>
            <span style={{ fontSize: 12, color: 'var(--nt-text-muted)', marginLeft: 10 }}>首版不开放单元编辑（合并/拆分待下游失效设计完成）</span>
          </div>
        </div>
      )}

      {stage === 'voice' && (
        <div>
          {unit ? (
            <>
              <p style={{ fontSize: 13.5, marginTop: 0 }}>
                单元 <span className="mono">#{String(unit.index).padStart(2, '0')} {unit.unit_id}</span> · {unit.char_count} 字 ·
                实际时长 <b>{formatSeconds(unit.duration_s)}</b> ·{' '}
                <span className={'badge ' + (unit.alignment === 'whisper' ? 'tag-info' : 'tag-warn')}>
                  {unit.alignment === 'whisper' ? 'Whisper 对齐' : '平均切图'}
                </span>
              </p>
              {unit.fallback_reason && (
                <div className="notice notice-warn">fallback 原因：{unit.fallback_reason}（不影响成片可用性）</div>
              )}
              <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.alert('播放单元音频（mock）')}>
                  播放单元
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => window.alert('播放 Voice 母带（mock）')}>
                  播放母带
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => cmd('unit.retry', { run_id: run.run_id, unit_id: unit.unit_id })}>
                  重试该单元
                </button>
              </div>
            </>
          ) : (
            <p style={{ fontSize: 13.5, color: 'var(--nt-text-muted)' }}>该 Run 的配音阶段失败于 u-07，可在上方错误卡中重试。</p>
          )}
        </div>
      )}

      {stage === 'storyboard' && (
        <div>
          <p style={{ fontSize: 13.5, marginTop: 0 }}>
            分镜规划完成：48 个 Visual Item，画面意图与 overlay 已生成；每个 Visual 绑定文字范围与切换点。
          </p>
          {unit?.visuals.map((v) => (
            <div key={v.visual_id} className="visual-item" style={{ alignItems: 'flex-start' }}>
              <span className="visual-thumb">{v.visual_id.replace('v-', '')}</span>
              <div style={{ flex: 1 }}>
                <div>{v.text_excerpt}</div>
                <div className="mono" style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>
                  range [{v.text_range[0]}, {v.text_range[1]}] · switch {v.switch_point_s?.toFixed(1)}s · clip {formatSeconds(v.clip_seconds)}
                </div>
              </div>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => cmd('visual.replan', { run_id: run.run_id, visual_id: v.visual_id })}>
                重跑该 Unit 规划
              </button>
            </div>
          ))}
          <button type="button" className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={() => cmd('stage.rerun', { stage: 'storyboard', run_id: run.run_id })}>
            重跑全部规划
          </button>
        </div>
      )}

      {stage === 'illustration' && (
        <div>
          <p style={{ fontSize: 13.5, marginTop: 0 }}>
            统一插画生成中：35/48 已完成。重新生成单张只失效该 Visual 下游，不改变 Voice 与时间边界。
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(96px, 1fr))', gap: 8, marginTop: 10 }}>
            {run.voice_units.flatMap((u) => u.visuals).map((v) => (
              <div key={v.visual_id} style={{ textAlign: 'center' }}>
                <div
                  style={{
                    aspectRatio: '4/3', borderRadius: 6, marginBottom: 4,
                    background: v.status === 'succeeded'
                      ? 'linear-gradient(135deg, var(--nt-primary-200), var(--nt-info-200))'
                      : 'var(--nt-neutral-100)',
                    border: '1px solid var(--nt-border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, fontFamily: 'var(--nt-font-mono)', color: 'var(--nt-text-muted)',
                  }}
                >
                  {v.status === 'succeeded' ? v.visual_id.replace('v-', '') : '生成中'}
                </div>
                {v.status !== 'succeeded' && (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => cmd('visual.regenerate', { run_id: run.run_id, visual_id: v.visual_id })}>
                    重新生成
                  </button>
                )}
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--nt-text-muted)', marginTop: 10 }}>
            单图重生成明确提示：不改变 Voice 与时间边界（04 §12 验收项）。
          </p>
        </div>
      )}

      {stage === 'render' && (
        <div>
          <p style={{ fontSize: 13.5, marginTop: 0, color: 'var(--nt-text-muted)' }}>
            白板动画渲染待插画阶段完成后开始：重点文字、线条绘制量与笔身文字按成片设置执行。
          </p>
          <div className="notice notice-info">
            渲染阶段将逐 Visual 绘制 annotation 与 clip，目标时长来自 Voice 实际时长；误差超过 200ms 会自动补偿。
          </div>
        </div>
      )}

      {stage === 'compose' && (
        <div>
          <p style={{ fontSize: 13.5, marginTop: 0, color: 'var(--nt-text-muted)' }}>
            合成阶段将输出字幕（可开关）、成片与 A/V 校验报告。
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-ghost btn-sm" disabled onClick={() => cmd('compose.redo', { run_id: run.run_id })}>
              修改成片设置后重合成
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

