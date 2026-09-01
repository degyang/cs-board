import { useEffect, useRef, useState } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { useAsync } from '../../lib/api/queries'
import { fetchCapability, fetchServiceHealth, submitCommand } from '../../lib/api/client'
import { ENGINE_NAMES, VISUAL_SOURCE_NAMES } from '../../lib/api/types'
import { useSettingsStore, validateSections, type SettingItem, type SettingSection } from './settingsStore'
import { ModelsTab } from './ModelsTab'

/* 设置 /settings：模型 / 语音与对齐 / 工具链 / 存储 / 诊断 五页签。
   前四类为可编辑配置（字段按类型渲染控件，脏检测 + 保存/重置 + 本地持久化）；
   诊断为只读探测（服务健康、能力矩阵、日志级别、脱敏诊断包导出）。
   Secret 仅显示掩码与 secret_ref，原始密钥不落盘、不回显。 */

type SettingsTab = 'models' | 'speech' | 'toolchain' | 'storage' | 'diagnostics'

const TAB_ITEMS = [
  { key: 'models', label: '模型' },
  { key: 'speech', label: '语音与对齐' },
  { key: 'toolchain', label: '工具链' },
  { key: 'storage', label: '存储' },
  { key: 'diagnostics', label: '诊断' },
]

function SecretField({ item, error, onChange }: { item: SettingItem; error?: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false)
  const [val, setVal] = useState('')
  const commit = () => {
    onChange(val)
    setOpen(false)
    setVal('')
  }
  return (
    <div className="set-secret">
      <span className={`badge ${item.configured ? 'st-succeeded' : 'tag-neutral'}`}>
        {item.configured ? '已配置' : '未配置'}
      </span>
      {item.configured && <span className="mono set-secret-mask">{item.value || '••••••••'}</span>}
      {!open ? (
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(true)}>
          {item.configured ? '更新' : '设置'}
        </button>
      ) : (
        <span className="set-secret-edit">
          <input
            className={`input set-secret-input${error ? ' is-error' : ''}`}
            type="password"
            autoFocus
            placeholder="输入新的密钥"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
            }}
          />
          <button className="btn btn-sm" onClick={commit}>
            确认
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}>
            取消
          </button>
        </span>
      )}
      {item.configured && (
        <button className="btn btn-ghost btn-sm set-danger" onClick={() => onChange('')}>
          清除
        </button>
      )}
      {item.secret_ref && <span className="set-secret-ref mono">{item.secret_ref}</span>}
      {error && <div className="set-error">{error}</div>}
    </div>
  )
}

function renderControl(
  sec: SettingSection,
  item: SettingItem,
  error: string,
  updateValue: (s: string, k: string, v: string) => void,
) {
  switch (item.type) {
    case 'text':
      return (
        <div className="set-control-col">
          <input
            className={`input set-input${error ? ' is-error' : ''}`}
            value={item.value}
            onChange={(e) => updateValue(sec.key, item.key, e.target.value)}
          />
          {error && <div className="set-error">{error}</div>}
        </div>
      )
    case 'select':
      return (
        <select
          className="select set-select"
          value={item.value}
          onChange={(e) => updateValue(sec.key, item.key, e.target.value)}
        >
          {(item.options ?? []).map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      )
    case 'toggle':
      return (
        <label className="switch">
          <input
            type="checkbox"
            checked={item.value === 'true'}
            onChange={(e) => updateValue(sec.key, item.key, e.target.checked ? 'true' : 'false')}
          />
          <span className="track" />
          <span className="switch-text">{item.value === 'true' ? '开启' : '关闭'}</span>
        </label>
      )
    case 'secret':
      return <SecretField item={item} error={error} onChange={(v) => updateValue(sec.key, item.key, v)} />
    case 'info':
    default:
      return (
        <span className="set-info">
          <span className="set-info-lock" title="只读（由运行环境探测）">
            🔒
          </span>
          {item.value}
        </span>
      )
  }
}

export function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>('models')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ kind: 'success' | 'error' | 'info'; msg: string } | null>(null)
  const toastTimer = useRef<number | null>(null)

  const { sections, dirty, updateValue, reset, save, logLevel, setLogLevel } = useSettingsStore()
  const errMap = validateSections(sections)
  const hasErrors = Object.keys(errMap).length > 0

  const health = useAsync(() => fetchServiceHealth(), [])
  const caps = useAsync(
    () =>
      Promise.all([
        fetchCapability('whiteboard', 'preset'),
        fetchCapability('whiteboard', 'custom-reference'),
        fetchCapability('infographic-remotion', 'preset'),
        fetchCapability('infographic-remotion', 'custom-reference'),
      ]),
    [],
  )

  const showToast = (kind: 'success' | 'error' | 'info', msg: string) => {
    setToast({ kind, msg })
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(null), 2800)
  }
  useEffect(() => () => {
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
  }, [])

  const onSave = async () => {
    if (hasErrors) {
      showToast('error', '请先修正高亮的字段后再保存')
      return
    }
    setSaving(true)
    const r = await save()
    setSaving(false)
    if (r.ok) showToast('success', '设置已保存')
    else showToast('error', '保存失败：' + (r.message || '未知错误'))
  }

  const section = sections.find((s) => s.key === tab)

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">设置</h1>
        <p className="page-desc">
          服务、模型、存储与诊断配置。可修改项会暂存为「未保存更改」，点击底部保存后生效；Secret 仅保存在本机后端或系统密钥存储，本页只显示掩码与 secret_ref，日志与诊断包均不含 Secret。
        </p>
      </div>

      <Tabs items={TAB_ITEMS} active={tab} onChange={(k) => setTab(k as SettingsTab)} />

      <div style={{ marginTop: 18, paddingBottom: 80 }}>
        {/* 模型页签：模型服务商列表（CRUD），不走通用键值配置渲染 */}
        {tab === 'models' && <ModelsTab />}

        {section && tab !== 'models' && (
          <div className="card">
            <h2 className="card-title">{section.title}</h2>
            <p className="card-sub">修改后请点击页面底部的「保存」生效；「重置」可放弃本次更改。</p>
            {section.items.map((item) => (
              <div key={item.key} className={`settings-row${errMap[`${section.key}.${item.key}`] ? ' row-error' : ''}`}>
                <span className="k">{item.label}</span>
                <span className="v">
                  {renderControl(section, item, errMap[`${section.key}.${item.key}`] ?? '', updateValue)}
                  {item.note && item.type !== 'info' && <div className="note">{item.note}</div>}
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === 'diagnostics' && (
          <>
            <div className="card">
              <h2 className="card-title">服务健康</h2>
              <p className="card-sub">各组件状态来自 ServiceHealthView。</p>
              {(health.data ?? []).map((h) => (
                <div key={h.component} className="settings-row">
                  <span className="k">{h.title}</span>
                  <span className="v">
                    <StatusBadge
                      status={h.status === 'ok' ? 'succeeded' : h.status === 'degraded' ? 'running' : 'failed'}
                      label={h.status === 'ok' ? '正常' : h.status === 'degraded' ? '降级' : '不可用'}
                    />
                    <span className="mono" style={{ fontSize: 12, marginLeft: 8 }}>
                      {h.version}
                    </span>
                    {h.detail && <div className="note">{h.detail}</div>}
                  </span>
                </div>
              ))}
            </div>

            <div className="card">
              <h2 className="card-title">日志与诊断包</h2>
              <div className="settings-row">
                <span className="k">日志级别</span>
                <span className="v">
                  <select
                    className="select set-select"
                    value={logLevel}
                    onChange={(e) => setLogLevel(e.target.value)}
                  >
                    <option value="debug">debug</option>
                    <option value="info">info</option>
                    <option value="warn">warn</option>
                    <option value="error">error</option>
                  </select>
                  <div className="note">日志均经服务端脱敏；修改后随底部「保存」生效。</div>
                </span>
              </div>
              <div className="settings-row">
                <span className="k">诊断包</span>
                <span className="v">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={async () => {
                      const r = await submitCommand('export_diagnostics', {})
                      showToast(r.ok ? 'success' : 'error', r.message)
                    }}
                  >
                    导出脱敏诊断包
                  </button>
                </span>
              </div>
            </div>

            <div className="card">
              <h2 className="card-title">高级能力探测</h2>
              <p className="card-sub">引擎 × 视觉来源组合由后端 Capability API 返回，前端不做业务规则隐藏。</p>
              {(caps.data ?? []).map((c) => (
                <div key={`${c.engine}-${c.visual_source}`} className="settings-row">
                  <span className="k">
                    {ENGINE_NAMES[c.engine]} + {VISUAL_SOURCE_NAMES[c.visual_source]}
                  </span>
                  <span className="v">
                    {c.supported ? (
                      <span className="badge st-succeeded">受支持 · {c.pipeline}</span>
                    ) : (
                      <span className="badge tag-neutral">unsupported · {c.reason}</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {dirty && (
        <div className={`set-savebar${hasErrors ? ' savebar-error' : ''}`}>
          <span className="set-savebar-dot" />
          {hasErrors ? (
            <span className="set-savebar-err">有 {Object.keys(errMap).length} 处校验未通过</span>
          ) : (
            <span>有未保存的更改</span>
          )}
          <span className="set-savebar-spacer" />
          <button className="btn btn-ghost btn-sm" onClick={reset} disabled={saving}>
            重置
          </button>
          <button className="btn btn-primary btn-sm" onClick={onSave} disabled={saving || hasErrors}>
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      )}

      {toast && <div className={`toast toast-${toast.kind}`} onClick={() => setToast(null)}>{toast.msg}</div>}
    </div>
  )
}

