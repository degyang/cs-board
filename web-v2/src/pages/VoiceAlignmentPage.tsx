/* ==========================================================================
   声音对齐 — Voice Alignment Page
   ========================================================================== */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchVoiceAlignmentSettings } from '../lib/api/settings'
import { probeService } from '../lib/api/services'
import type { VoiceAlignmentSettings, VoiceAlignmentServiceSummary } from '../lib/api/types'

export function VoiceAlignmentPage() {
  const [settings, setSettings] = useState<VoiceAlignmentSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [probing, setProbing] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchVoiceAlignmentSettings()
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

  const handleProbe = async (serviceId: string) => {
    setProbing(serviceId)
    setFeedback(null)
    try {
      await probeService(serviceId)
      setFeedback('探测完成')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '探测失败')
    } finally {
      setProbing(null)
    }
  }

  if (loading) return <div className="page-container"><div className="va-loading">加载中...</div></div>
  if (error) return <div className="page-container"><div className="va-error">{error}</div></div>
  if (!settings) return <div className="page-container"><div className="va-empty">未找到配置</div></div>

  return (
    <div className="page-container">
      <div className="va-header">
        <h1 className="va-title">声音对齐</h1>
      </div>

      {feedback && <div className="va-feedback">{feedback}</div>}

      <div className="va-service-grid">
        {settings.speech_synthesis && (
          <ServiceCard
            title="语音合成 (TTS)"
            service={settings.speech_synthesis}
            probing={probing === settings.speech_synthesis.service_id}
            onProbe={() => handleProbe(settings.speech_synthesis!.service_id)}
          />
        )}
        {settings.speech_alignment && (
          <ServiceCard
            title="语音对齐"
            service={settings.speech_alignment}
            probing={probing === settings.speech_alignment.service_id}
            onProbe={() => handleProbe(settings.speech_alignment!.service_id)}
          />
        )}
      </div>

      {!settings.speech_synthesis && !settings.speech_alignment && (
        <div className="va-empty">未配置语音服务</div>
      )}
    </div>
  )
}

function ServiceCard({
  title,
  service,
  probing,
  onProbe,
}: {
  title: string
  service: VoiceAlignmentServiceSummary
  probing: boolean
  onProbe: () => void
}) {
  return (
    <div className="va-service-card">
      <div className="va-service-header">
        <h2 className="va-service-title">{title}</h2>
        <Link to="/settings/models" className="va-service-link">
          {service.display_name}
        </Link>
      </div>
      <div className="va-service-meta">
        <span>端点: {service.endpoint ?? '未配置'}</span>
        <span>模型: {service.model ?? '未配置'}</span>
        {service.availability.available !== undefined && (
          <span>状态: {service.availability.available ? '可用' : '不可用'}</span>
        )}
        {service.availability.checked_at && (
          <span>检查时间: {new Date(service.availability.checked_at).toLocaleString()}</span>
        )}
        {service.availability.latency_ms != null && (
          <span>延迟: {service.availability.latency_ms}ms</span>
        )}
      </div>
      <div className="va-service-actions">
        <button className="btn btn-secondary" disabled={probing} onClick={onProbe}>
          {probing ? '探测中...' : '探测'}
        </button>
      </div>
    </div>
  )
}
