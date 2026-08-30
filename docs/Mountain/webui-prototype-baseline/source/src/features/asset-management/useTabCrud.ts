import { useState } from 'react'

/* ==========================================================================
   通用主从 CRUD 逻辑（借鉴专业 CMS / 资源库编辑器）
   - 列表选中 -> 右侧只读展示
   - 新建：生成空白草稿（不进列表），进入编辑态；保存时落库，取消则丢弃
   - 编辑：拷贝选中项为草稿，保存写回，取消还原
   - 删除：二次确认后移除；列表空时进入空状态
   ========================================================================== */
export function useTabCrud<T extends { id: string }>(
  items: T[],
  add: (item: T) => void,
  update: (item: T) => void,
  remove: (id: string) => void,
  makeBlank: () => T,
) {
  const [sel, setSel] = useState<string>(items[0]?.id ?? '')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<T | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)

  const item = items.find((i) => i.id === sel) ?? null
  const isNew = !!draft && !items.some((i) => i.id === draft.id)

  const startNew = () => {
    setDraft(makeBlank())
    setSel('')
    setEditing(true)
    setConfirmId(null)
  }
  const startEdit = () => {
    if (item) {
      setDraft({ ...item })
      setEditing(true)
    }
  }
  const save = () => {
    if (!draft) return
    if (isNew) add(draft)
    else update(draft)
    setEditing(false)
    setSel(draft.id)
    setDraft(null)
  }
  const cancel = () => {
    setEditing(false)
    setDraft(null)
    if (isNew) setSel(items[0]?.id ?? '')
  }
  const askDelete = () => {
    if (item) setConfirmId(item.id)
  }
  const doDelete = () => {
    if (!confirmId) return
    remove(confirmId)
    setConfirmId(null)
    setEditing(false)
    setDraft(null)
    setSel('')
  }

  // 编辑态显示草稿，否则显示选中项
  const view = (editing ? draft : item) as T | null

  return {
    sel,
    setSel,
    setConfirmId,
    editing,
    draft,
    setDraft,
    confirmId,
    item,
    isNew,
    view,
    startNew,
    startEdit,
    save,
    cancel,
    askDelete,
    doDelete,
  }
}

