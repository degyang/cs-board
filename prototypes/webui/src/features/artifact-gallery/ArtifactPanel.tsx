import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatBytes, formatTime } from '../../lib/formatting'
import type { ArtifactView } from '../../lib/api/types'

const ARTIFACT_STATUS_TEXT: Record<ArtifactView['status'], string> = {
  ready: '就绪',
  generating: '生成中',
  stale: '已过期',
  invalid: '已失效',
}

// 产物侧栏：只显示逻辑 key / schema version / revision / hash，不显示物理绝对路径（04 §6.5）
export function ArtifactPanel({ artifacts }: { artifacts: ArtifactView[] }) {
  const download = (a: ArtifactView) => {
    // 下载走后端 Artifact API，此处为 mock 提示
    window.alert(`下载 ${a.logical_key}（rev ${a.revision}）\n真实实现：GET /api/artifacts/${a.artifact_id}/download`)
  }
  return (
    <div className="wb-col">
      <h3>
        Artifact 产物
        <span className="spacer">{artifacts.length} 项</span>
      </h3>
      {artifacts.map((a) => (
        <div key={a.artifact_id} className="art-item">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="art-key">{a.logical_key}</div>
            <div className="art-meta">
              <span className="mono">{a.schema_version}</span>
              <span>rev {a.revision}</span>
              <span>{formatBytes(a.size_bytes)}</span>
              <span>{formatTime(a.created_at)}</span>
              <span className="mono" title={a.hash}>{a.hash}</span>
            </div>
            <div style={{ marginTop: 4 }}>
              <StatusBadge
                status={a.status === 'ready' ? 'succeeded' : a.status === 'generating' ? 'running' : 'stale'}
                label={ARTIFACT_STATUS_TEXT[a.status]}
              />
            </div>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm art-dl"
            disabled={a.status !== 'ready'}
            onClick={() => download(a)}
          >
            下载
          </button>
        </div>
      ))}
      <p style={{ fontSize: 11.5, color: 'var(--nt-text-muted)', marginTop: 10 }}>
        仅显示逻辑 key 与版本信息，物理路径不对普通用户展示。
      </p>
    </div>
  )
}

