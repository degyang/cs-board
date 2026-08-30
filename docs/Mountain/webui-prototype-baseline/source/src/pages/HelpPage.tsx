import { STAGE_KEYS, STAGE_NAMES } from '../lib/api/types'

// 帮助 /help：流程、状态、错误与诊断说明（04 §3 信息架构）
export function HelpPage() {
  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">帮助</h1>
        <p className="page-desc">流程、状态、错误与诊断的简要说明。不需要理解阶段也能一次点击完成视频。</p>
      </div>

      <div className="help-sec">
        <h3>制作流程（六阶段）</h3>
        <ol>
          {STAGE_KEYS.map((k) => (
            <li key={k}>{STAGE_NAMES[k]}</li>
          ))}
        </ol>
        <p>
          默认策略是「自动完成」：提交文案与参考声音后一次启动，系统自动确定「文字—Voice—图片」关系并逐单元生成。
          阶段视图主要用于理解进度、恢复与返工，不会打断默认流程。
        </p>
      </div>

      <div className="help-sec">
        <h3>状态说明</h3>
        <ul>
          <li><b>待执行 / 运行中 / 已成功</b>：常规生命周期。</li>
          <li><b>失败</b>：错误卡会显示稳定的 error_code、是否可重试、失败对象与建议动作。</li>
          <li><b>已取消 / 已过期（stale）/ 已跳过</b>：取消的 Run 可恢复；上游重生成后下游产物标记为 stale。</li>
          <li><b>fallback（平均切图）</b>：Whisper 置信度不足时按等分估计切换点，可见但不是失败。</li>
        </ul>
      </div>

      <div className="help-sec">
        <h3>常见错误码</h3>
        <ul>
          <li><span className="mono">E-TTS-503</span>：语音节点过载，可重试，已完成单元不会重算。</li>
          <li><span className="mono">E-IMG-TIMEOUT</span>：插画生成超时，系统自动重试；也可单独重新生成该图（不改变 Voice 与时间边界）。</li>
          <li><span className="mono">E-ALIGN-LOWCOV</span>：对齐置信度低，已 fallback 平均切图，可重试对齐。</li>
        </ul>
      </div>

      <div className="help-sec">
        <h3>诊断与 trace</h3>
        <p>
          每个 Run 有唯一 trace_id，工作台与诊断页均可复制。Web、Desktop、CLI、Skill 四个入口共享同一链路：
          Web 创建的 Run 可由 Skill 通过同一 trace_id 继续，反向亦然。诊断包导出前自动脱敏，不含任何 Secret。
        </p>
      </div>

      <div className="help-sec">
        <h3>旧版任务</h3>
        <p>
          旧任务仍可查看与下载，卡片会标注「旧版 · 同步精度为等分切图」。需要重渲染时，请显式迁移为新 Run（mountain-av-v1）。
        </p>
      </div>
    </div>
  )
}

