/* ==========================================================================
   Confirm Dialog — replaces window.confirm with accessible React dialog.
   Falls back to a div-based overlay when <dialog> is not supported (jsdom).
   ========================================================================== */

import { useEffect, useRef } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '确认',
  cancelLabel = '取消',
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const hasShowModal = typeof HTMLDialogElement !== 'undefined' && typeof HTMLDialogElement.prototype.showModal === 'function'

  useEffect(() => {
    if (hasShowModal) {
      const el = dialogRef.current
      if (!el) return
      if (open && !el.open) {
        el.showModal()
      } else if (!open && el.open) {
        el.close()
      }
    }
  }, [open, hasShowModal])

  useEffect(() => {
    if (!hasShowModal) return
    const el = dialogRef.current
    if (!el) return
    const handleClose = () => {
      if (open) onCancel()
    }
    el.addEventListener('close', handleClose)
    return () => el.removeEventListener('close', handleClose)
  }, [open, onCancel, hasShowModal])

  // Fallback: render as div overlay when <dialog> showModal is not available
  if (!hasShowModal) {
    if (!open) return null
    return (
      <div className="confirm-dialog-overlay" role="dialog" aria-modal="true">
        <div className="confirm-dialog confirm-dialog--fallback">
          <div className="confirm-dialog-body">
            <h3 className="confirm-dialog-title">{title}</h3>
            <p className="confirm-dialog-message">{message}</p>
            <div className="confirm-dialog-actions">
              <button type="button" className="btn btn-ghost" onClick={onCancel}>{cancelLabel}</button>
              <button
                type="button"
                className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
                onClick={onConfirm}
              >
                {confirmLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <dialog ref={dialogRef} className="confirm-dialog">
      <div className="confirm-dialog-body">
        <h3 className="confirm-dialog-title">{title}</h3>
        <p className="confirm-dialog-message">{message}</p>
        <div className="confirm-dialog-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>{cancelLabel}</button>
          <button
            type="button"
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  )
}
