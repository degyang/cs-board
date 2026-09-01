import { BackButton } from '../components/ui/BackButton'

export function HelpPage() {
  return (
    <div className="page page-narrow">
      <BackButton to="/" label="返回任务队列" />
      <div className="page-head">
        <h1 className="page-title">帮助中心</h1>
        <p className="page-desc">了解山野小读视频制作流水线</p>
      </div>

      <div className="help-section">
        <h2>六阶段流水线</h2>
        <p>每个任务按以下六个阶段依次执行：</p>
        <ul>
          <li><strong>生成画面锚定重点</strong> — 从已整理的 Voice Units 生成视觉锚定信息</li>
          <li><strong>克隆配音</strong> — 使用 TTS 为每个单元生成配音</li>
          <li><strong>拆分分镜</strong> — 规划每个单元的视觉呈现方式</li>
          <li><strong>生成插画</strong> — 为每个分镜生成配图</li>
          <li><strong>白板渲染</strong> — 将静态图转为动画序列</li>
          <li><strong>合成成片</strong> — 将配音与画面合成最终视频</li>
        </ul>
      </div>

      <div className="help-section">
        <h2>状态说明</h2>
        <ul>
          <li><strong>待执行</strong> — 任务已创建，等待系统调度</li>
          <li><strong>运行中</strong> — 正在执行流水线的某个阶段</li>
          <li><strong>已成功</strong> — 所有阶段执行完成</li>
          <li><strong>失败</strong> — 某个阶段执行出错，可查看诊断详情</li>
          <li><strong>已取消</strong> — 用户手动取消了任务</li>
          <li><strong>已过期</strong> — 任务因长时间未完成被系统清理</li>
        </ul>
      </div>

      <div className="help-section">
        <h2>常见错误码</h2>
        <ul>
          <li><code>E-TTS-503</code> — TTS 服务暂时不可用，请稍后重试</li>
          <li><code>E-IMG-TIMEOUT</code> — 图片生成超时，可能是负载过高</li>
          <li><code>E-ALIGN-LOWCOV</code> — 音画对齐覆盖率过低，建议检查文案</li>
        </ul>
      </div>

      <div className="help-section">
        <h2>Trace 与诊断</h2>
        <p>
          每次运行都有唯一的 <code>trace_id</code>，用于追踪完整的执行链路。
          在工作台点击"诊断"可查看事件流、日志和每阶段的详细信息。
        </p>
      </div>
    </div>
  )
}
