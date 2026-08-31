import { Link } from 'react-router-dom'
import type {
  ToolchainStatusView,
  TaskStorageStatusView,
  SystemDiagnosticsView,
  ToolStatusCardVM,
  StorageClassVM,
  DiagHealthRow,
} from './types'

/* 状态徽标（复用既有 .badge .st-* 体系，不引入新配色） */
function StateBadge({ kind, label }: { kind: 'succeeded' | 'failed' | 'running' | 'pending'; label: string }) {
  return <span className={`badge st-${kind}`}>{label}</span>
}

/* 候选契约注解（只读原型，未实现 fetch / mock fallback / 假保存） */
function ContractNote({ api }: { api: string }) {
  return <div className="ss-hint">数据来源（候选契约，待后端确认，未实现 fetch）：{api}</div>
}

/* ============================ 系统工具链 ============================ */
export function ToolchainStatusTab({ view }: { view: ToolchainStatusView }) {
  return (
    <div className="ss-section">
      <div className="card">
        <h2 className="card-title">系统工具链</h2>
        <p className="card-sub">
          以下为本地运行环境探测到的系统工具链状态，仅作只读展示；可执行文件路径、命令行参数、引擎选择与密钥均不在此呈现，也不提供刷新探测按钮（避免伪装真实服务探测）。
        </p>
        <ContractNote api="/api/v1/toolchain/status" />
        <div className="ss-grid">
          {view.tools.map((t) => (
            <ToolCard key={t.id} vm={t} />
          ))}
        </div>
      </div>
    </div>
  )
}

function ToolCard({ vm }: { vm: ToolStatusCardVM }) {
  const available = vm.state === 'available'
  return (
    <div className="ss-card">
      <div className="ss-card-head">
        <h3 className="ss-card-name">{vm.name}</h3>
        <StateBadge kind={available ? 'succeeded' : 'failed'} label={available ? '可用' : '不可用'} />
      </div>
      <p className="ss-card-purpose">{vm.purpose}</p>
      {vm.modeOrVersion && <div className="ss-card-meta mono">{vm.modeOrVersion}</div>}

      {!available && (
        <div className="ss-error">
          <div className="ss-error-head">
            <span className="ss-error-code mono">{vm.error_code ?? 'E-UNKNOWN'}</span>
          </div>
          <p className="ss-error-suggestion">{vm.suggestion ?? '请检查运行环境后重试。'}</p>
        </div>
      )}
    </div>
  )
}

/* ============================ 运行时存储状态 ============================ */
export function TaskStorageStatusTab({ view }: { view: TaskStorageStatusView }) {
  return (
    <div className="ss-section">
      <div className="card">
        <h2 className="card-title">运行时存储状态</h2>
        <p className="card-sub">
          以下为五类逻辑存储的运行状态，仅展示状态与逻辑摘要，不暴露本机绝对路径、目录树或文件名，也不暗示任何具体任务上下文。
        </p>
        <div className="ss-hint">
          存储策略由本地运行时统一管理；配额、保留和清理配置将在具备真实后端 API 与安全确认后开放。
        </div>
        <ContractNote api="/api/v1/storage/status" />
        <ul className="ss-storage-list">
          {view.classes.map((c) => (
            <StorageRow key={c.id} vm={c} />
          ))}
        </ul>
      </div>
    </div>
  )
}

function StorageRow({ vm }: { vm: StorageClassVM }) {
  const map = {
    normal: { kind: 'succeeded' as const, label: '正常' },
    unavailable: { kind: 'failed' as const, label: '不可用' },
    'not-stated': { kind: 'pending' as const, label: '未统计' },
  }[vm.state]
  return (
    <li className="ss-storage-row">
      <span className="ss-storage-name">{vm.name}</span>
      <StateBadge kind={map.kind} label={map.label} />
      {vm.summary && <span className="ss-storage-summary">{vm.summary}</span>}
    </li>
  )
}

/* ============================ 系统诊断 ============================ */
export function SystemDiagnosticsTab({ view }: { view: SystemDiagnosticsView }) {
  return (
    <div className="ss-section">
      <div className="card">
        <h2 className="card-title">服务健康汇总</h2>
        <p className="card-sub">各组件状态来自运行环境探测，仅作只读展示。</p>
        <ContractNote api="/api/v1/diagnostics/summary" />
        <div className="ss-health-list">
          {view.health.map((h) => (
            <HealthRow key={h.component} row={h} />
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="card-title">系统能力矩阵</h2>
        <p className="card-sub">引擎 × 视觉来源组合的可用状态，由运行环境探测返回。</p>
        <div className="ss-cap-list">
          {view.capabilityMatrix.map((c, i) => (
            <div key={i} className="ss-cap-row">
              <span className="ss-cap-name">
                {c.engine} + {c.visualSource}
              </span>
              <StateBadge kind={c.supported ? 'succeeded' : 'pending'} label={c.supported ? '受支持' : '未开放'} />
              {c.detail && <span className="ss-cap-detail">{c.detail}</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="card-title">脱敏与隐私说明</h2>
        <p className="card-sub" style={{ marginBottom: 0 }}>
          {view.redactionNote}
        </p>
      </div>

      <div className="card ss-task-card">
        <div className="ss-task-body">
          <h2 className="card-title">{view.taskLevel.title}</h2>
          <p className="card-sub" style={{ marginBottom: 0 }}>
            {view.taskLevel.desc}
          </p>
        </div>
        <div className="ss-task-actions">
          <Link className="btn btn-sm" to={view.taskLevel.queueRoute}>
            前往任务队列
          </Link>
          <span className="ss-task-hint">{view.taskLevel.workbenchHint}</span>
        </div>
      </div>
    </div>
  )
}

function HealthRow({ row }: { row: DiagHealthRow }) {
  const map = {
    ok: { kind: 'succeeded' as const, label: '正常' },
    degraded: { kind: 'running' as const, label: '降级' },
    down: { kind: 'failed' as const, label: '不可用' },
  }[row.status]
  return (
    <div className="ss-health-row">
      <span className="ss-health-name">{row.title}</span>
      <StateBadge kind={map.kind} label={map.label} />
      {row.version && <span className="ss-health-ver mono">{row.version}</span>}
      {row.detail && <span className="ss-health-detail">{row.detail}</span>}
    </div>
  )
}
