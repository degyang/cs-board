/* ==========================================================================
   工具链 — Toolchain Page
   ========================================================================== */

import { useState, useEffect } from 'react'
import { fetchToolchainSettings } from '../lib/api/settings'
import type { ToolchainSettings } from '../lib/api/types'

export function ToolchainPage() {
  const [settings, setSettings] = useState<ToolchainSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchToolchainSettings()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) return <div className="page-container"><div className="tc-loading">加载中...</div></div>
  if (error) return <div className="page-container"><div className="tc-error">{error}</div></div>
  if (!settings) return <div className="page-container"><div className="tc-empty">未找到配置</div></div>

  return (
    <div className="page-container">
      <div className="tc-header">
        <h1 className="tc-title">工具链</h1>
        <p className="tc-description">系统依赖组件状态</p>
      </div>

      <div className="tc-list">
        {settings.tools.map(tool => (
          <div key={tool.component} className="tc-item">
            <div className="tc-item-header">
              <span className="tc-item-name">{tool.component}</span>
              <span className={`tc-item-status ${tool.available ? 'tc-item-status--ok' : 'tc-item-status--fail'}`}>
                {tool.available ? '可用' : '不可用'}
              </span>
            </div>
            {tool.version && <div className="tc-item-version">版本: {tool.version}</div>}
            {tool.error_code && <div className="tc-item-error">错误: {tool.error_code}</div>}
            {tool.suggestion && <div className="tc-item-suggestion">建议: {tool.suggestion}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
