import { useRef, useState } from 'react'

/* ==========================================================================
   资产管理 · 通用 UI 组件
   - AssetThumb：缩略图，传入 image 时显示真实图片，否则渐变 + emoji 占位
   - AssetImage：可点击编辑的图片源。支持「选择本地文件」(转 dataURL 离线保存)
     与「输入路径 / URL」(相对/绝对路径、http URL 直接加载) 两种方式，可清除。
   - ConfirmModal：删除等危险操作的二次确认弹窗。
   ========================================================================== */

/* 山野小读调色板：按 seed 取稳定渐变（占位图专用） */
const PALETTE = [
  'linear-gradient(135deg,#8FA46B,#5E7350)',
  'linear-gradient(135deg,#E0A766,#C57B3E)',
  'linear-gradient(135deg,#6F9BC4,#3E6E9E)',
  'linear-gradient(135deg,#C98AA0,#9E5E73)',
  'linear-gradient(135deg,#9BB0A0,#5E7E6E)',
  'linear-gradient(135deg,#D6B86A,#B08A2E)',
]
export function gradFor(seed: string): string {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

type Size = 'sm' | 'lg' | 'xl'
export function AssetThumb({
  seed,
  emoji,
  image,
  size = 'sm',
}: {
  seed: string
  emoji?: string
  image?: string | null
  size?: Size
}) {
  if (image) {
    return (
      <div className={`am-thumb am-thumb-${size} am-thumb-img`}>
        <img src={image} alt="" />
      </div>
    )
  }
  return (
    <div className={`am-thumb am-thumb-${size}`} style={{ background: gradFor(seed) }}>
      {emoji ?? ''}
    </div>
  )
}

/* 可编辑图片源：点击唤出「上传 / 路径 / 清除」面板 */
export function AssetImage({
  value,
  label,
  placeholder = '🖼️',
  onChange,
  size = 'xl',
  allowEdit = true,
}: {
  value: string | null
  label: string
  placeholder?: string
  onChange: (next: string | null) => void
  size?: Size
  allowEdit?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [path, setPath] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    const r = new FileReader()
    r.onload = () => {
      onChange(String(r.result))
      setOpen(false)
      setPath('')
    }
    r.readAsDataURL(f)
    e.target.value = ''
  }
  const applyPath = () => {
    const p = path.trim()
    if (!p) return
    onChange(p)
    setOpen(false)
    setPath('')
  }
  const clear = () => {
    onChange(null)
    setOpen(false)
    setPath('')
  }

  return (
    <div className="am-img-editor">
      <button
        type="button"
        className={`am-img-btn am-thumb am-thumb-${size}${value ? ' am-thumb-img' : ''}`}
        style={value ? undefined : { background: gradFor(label) }}
        onClick={() => allowEdit && setOpen((o) => !o)}
        title={allowEdit ? '点击设置图片' : '图片'}
      >
        {value ? <img src={value} alt="" /> : <span className="am-img-ph">{placeholder}</span>}
        {allowEdit && <span className="am-img-edit-badge">编辑</span>}
      </button>

      {allowEdit && open && (
        <div className="am-img-pop" onClick={(e) => e.stopPropagation()}>
          <div className="am-img-pop-title">{label}</div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => fileRef.current?.click()}>
            📁 选择图片文件…
          </button>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onFile} />
          <div className="am-img-path">
            <input
              className="input"
              placeholder="或输入图片路径 / URL"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') applyPath()
              }}
            />
            <button type="button" className="btn btn-sm" onClick={applyPath}>
              确定
            </button>
          </div>
          <div className="am-img-pop-foot">
            <span>支持本地文件、相对/绝对路径或 http(s) URL</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={clear}>
              清除
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* 危险操作二次确认弹窗 */
export function ConfirmModal({
  open,
  title,
  message,
  confirmText = '删除',
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  message: string
  confirmText?: string
  onConfirm: () => void
  onCancel: () => void
}) {
  if (!open) return null
  return (
    <div className="modal-mask" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">{title}</h3>
        <p className="modal-msg">{message}</p>
        <div className="modal-foot">
          <button className="btn btn-ghost btn-sm" onClick={onCancel}>
            取消
          </button>
          <button className="btn btn-danger btn-sm" onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
