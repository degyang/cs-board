import { useState, type ReactNode } from 'react'

export function CopyButton({ text, children }: { text: string; children?: ReactNode }) {
  const [ok, setOk] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // clipboard unavailable — still show feedback
    }
    setOk(true)
    setTimeout(() => setOk(false), 1400)
  }
  return (
    <button type="button" onClick={copy} title={`复制 ${text}`}>
      {ok ? '已复制' : (children ?? '复制')}
    </button>
  )
}
