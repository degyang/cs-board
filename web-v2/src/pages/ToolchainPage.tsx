/* ===========================================================================
   System toolchain — runtime detection results, presented read-only.
   Card hierarchy 对齐原型 ToolchainStatusTab: card → ss-grid → ss-card
   =========================================================================== */

import { useEffect, useRef, useState } from 'react'
import { fetchToolchainSettings } from '../lib/api/settings'
import type { ToolchainComponent, ToolchainSettings } from '../lib/api/types'

type ToolPresentation = { name: string; purpose: string }

const TOOL_PRESENTATIONS: Record<string, ToolPresentation> = {
  'codex-skills': { name: 'Codex Skills', purpose: '为工作流提供可用的 Codex 技能能力。' },
  indextts: { name: 'IndexTTS', purpose: '提供本地语音合成与音色克隆能力。' },
  whisper: { name: 'Whisper', purpose: '提供本地语音转文字与时间对齐能力。' },
  ffmpeg: { name: 'FFmpeg 音画合成', purpose: '将配音、对齐字幕与画面合成为最终成片。' },
  ffprobe: { name: 'FFprobe', purpose: '读取媒体文件的时长、编码和流信息。' },
  renderer: { name: '白板渲染器', purpose: '将分镜与插画合成为白板动画视频帧。' },
  'whiteboard-renderer': { name: '白板渲染器', purpose: '将分镜与插画合成为白板动画视频帧。' },
}

function presentationFor(component: string): ToolPresentation {
  return TOOL_PRESENTATIONS[component] ?? { name: component, purpose: '运行环境探测到的工具链组件。' }
}

function ToolchainSkeleton() {
  return (
    <div className="ss-grid" aria-label="正在加载系统工具链">
      {[0, 1, 2, 3].map(index => (
        <div className="tc-card tc-card--skeleton" key={index} aria-hidden="true">
          <span className="tc-skeleton tc-skeleton--title" />
          <span className="tc-skeleton tc-skeleton--line" />
          <span className="tc-skeleton tc-skeleton--meta" />
        </div>
      ))}
    </div>
  )
}

function ToolCard({ tool }: { tool: ToolchainComponent }) {
  const presentation = presentationFor(tool.component)

  return (
    <div className="ss-card">
      <div className="ss-card-head">
        <h3 className="ss-card-name">{presentation.name}</h3>
        <span className={`badge st-${tool.available ? 'succeeded' : 'failed'}`}>
          {tool.available ? '可用' : '不可用'}
        </span>
      </div>
      <p className="ss-card-purpose">{presentation.purpose}</p>
      {tool.version && <div className="ss-card-meta mono">{tool.version}</div>}

      {!tool.available && (tool.error_code || tool.suggestion) && (
        <div className="ss-error">
          <div className="ss-error-head">
            {tool.error_code && <span className="ss-error-code mono">{tool.error_code}</span>}
          </div>
          {tool.suggestion && <p className="ss-error-suggestion">{tool.suggestion}</p>}
        </div>
      )}
    </div>
  )
}

export function ToolchainPage() {
  const [settings, setSettings] = useState<ToolchainSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(false)
  const requestId = useRef(0)

  const load = async () => {
    const currentRequest = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const data = await fetchToolchainSettings()
      if (mounted.current && currentRequest === requestId.current) setSettings(data)
    } catch (cause) {
      if (mounted.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause.message : '加载系统工具链失败')
      }
    } finally {
      if (mounted.current && currentRequest === requestId.current) setLoading(false)
    }
  }

  useEffect(() => {
    mounted.current = true
    void load()
    return () => {
      mounted.current = false
      requestId.current += 1
    }
  }, [])

  const tools = settings?.tools ?? []

  return (
    <div className="card">
      <h2 className="card-title">系统工具链</h2>
      <p className="card-sub">
        以下为本地运行环境探测到的系统工具链状态，仅作只读展示；不提供可保存配置或手动探测操作。
      </p>

      {loading && <ToolchainSkeleton />}
      {!loading && error && (
        <div className="tc-error" role="alert">
          <p>加载系统工具链失败：{error}</p>
          <button className="btn btn-secondary" type="button" onClick={() => void load()}>重新加载</button>
        </div>
      )}
      {!loading && !error && tools.length === 0 && <p className="tc-empty">未探测到工具链组件</p>}
      {!loading && !error && tools.length > 0 && (
        <div className="ss-grid">
          {tools.map(tool => <ToolCard key={tool.component} tool={tool} />)}
        </div>
      )}
    </div>
  )
}
