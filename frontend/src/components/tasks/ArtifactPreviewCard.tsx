import { useMemo, useState } from 'react'

export type PreviewAssetKind = 'image' | 'audio' | 'video'
export type GenerationRecord = Record<string, unknown>

export interface ArtifactPreviewCardProps {
  assetId: string
  label: string
  kind: PreviewAssetKind
  mediaUrl?: string | null
  generationRecord?: GenerationRecord | null
}

const SENSITIVE_KEY = /(?:secret|authorization|credential|password|token|api[_-]?key)/iu
const ABSOLUTE_PATH = /^(?:\/|[a-z]:[\\/])/iu

function isSafeValue(key: string, value: unknown): boolean {
  return !SENSITIVE_KEY.test(key) && !(typeof value === 'string' && ABSOLUTE_PATH.test(value))
}

/** Removes fields that must never enter the configuration UI or DOM. */
export function sanitizeGenerationRecord(value: unknown): unknown {
  if (Array.isArray(value)) return value
    .filter(item => !(typeof item === 'string' && ABSOLUTE_PATH.test(item)))
    .map(sanitizeGenerationRecord)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key, child]) => isSafeValue(key, child))
      .map(([key, child]) => [key, sanitizeGenerationRecord(child)]),
  )
}

function editableFieldNames(record: GenerationRecord): string[] {
  const fields = record.editable_fields
  return Array.isArray(fields) ? fields.filter((field): field is string => typeof field === 'string') : []
}

function previewLabel(kind: PreviewAssetKind): string {
  return kind === 'image' ? '查看图片预览' : kind === 'audio' ? '试听音频' : '播放视频'
}

function AssetMedia({ kind, label, mediaUrl }: Pick<ArtifactPreviewCardProps, 'kind' | 'label' | 'mediaUrl'>) {
  if (!mediaUrl) return <p className="artifact-preview-unavailable">预览地址等待后端契约提供。</p>
  if (kind === 'image') return <img className="artifact-preview-image" src={mediaUrl} alt={`${label} 图片预览`} />
  if (kind === 'audio') return <audio className="artifact-preview-audio" controls autoPlay src={mediaUrl}>您的浏览器不支持音频播放</audio>
  return <video className="artifact-preview-video" controls autoPlay src={mediaUrl}>您的浏览器不支持视频播放</video>
}

/**
 * UI-only provenance card. It deliberately accepts data rather than fetching
 * it: the generation-record and regeneration API contracts are not frozen.
 */
export function ArtifactPreviewCard({ assetId, label, kind, mediaUrl, generationRecord }: ArtifactPreviewCardProps) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const safeRecord = useMemo(() => sanitizeGenerationRecord(generationRecord ?? {}) as GenerationRecord, [generationRecord])
  const editableFields = useMemo(() => editableFieldNames(safeRecord), [safeRecord])
  const [draft, setDraft] = useState<Record<string, string>>({})

  const valueFor = (field: string) => draft[field] ?? (typeof safeRecord[field] === 'string' || typeof safeRecord[field] === 'number' ? String(safeRecord[field]) : '')

  return (
    <article className="artifact-preview-card" data-asset-id={assetId} data-asset-kind={kind}>
      <button type="button" className="artifact-preview-open" onClick={() => setPreviewOpen(true)} aria-label={`${previewLabel(kind)}：${label}`}>
        <span className="artifact-preview-kind">{kind === 'image' ? '图片' : kind === 'audio' ? '音频' : '视频'}</span>
        <strong>{label}</strong>
        <span>{previewLabel(kind)}</span>
      </button>
      <button type="button" className="btn btn-ghost btn-sm artifact-config-trigger" onClick={() => setDrawerOpen(true)} aria-label={`查看 ${label} 生成配置`}>
        生成配置
      </button>

      {previewOpen && (
        <div className="artifact-preview-modal" role="dialog" aria-modal="true" aria-label={`${label} 预览`}>
          <div className="artifact-preview-modal-body">
            <div className="artifact-preview-modal-title"><strong>{label}</strong><button type="button" className="btn btn-ghost btn-sm" onClick={() => setPreviewOpen(false)}>关闭预览</button></div>
            <AssetMedia kind={kind} label={label} mediaUrl={mediaUrl} />
          </div>
        </div>
      )}

      {drawerOpen && (
        <aside className="artifact-config-drawer" role="dialog" aria-modal="true" aria-label={`${label} 生成配置`}>
          <div className="artifact-config-drawer-head"><div><h3>生成配置</h3><p>显示当前 revision 实际传入的非敏感记录；编辑内容尚未提交。</p></div><button type="button" className="btn btn-ghost btn-sm" onClick={() => setDrawerOpen(false)}>关闭</button></div>
          {editableFields.length > 0 ? <div className="artifact-config-fields">{editableFields.map(field => (
            <label key={field}>{field}<input className="input" aria-label={field} value={valueFor(field)} onChange={event => setDraft(current => ({ ...current, [field]: event.target.value }))} /></label>
          ))}</div> : <p className="hint">当前生成记录没有声明可编辑参数。</p>}
          <pre className="artifact-config-json" aria-label="实际生成记录">{JSON.stringify(safeRecord, null, 2)}</pre>
          <button type="button" className="btn btn-primary" disabled aria-describedby="regenerate-unwired-note">再次生成</button>
          <p id="regenerate-unwired-note" className="hint">等待后端再生成契约；本界面不会发送请求或保存本地数据。</p>
        </aside>
      )}
    </article>
  )
}
