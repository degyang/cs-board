/* ==========================================================================
   Settings Page — Legacy redirect.
   /settings redirects to /settings/models.
   All functionality moved to SettingsLayout + child pages.
   ========================================================================== */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export function SettingsPage() {
  const navigate = useNavigate()

  useEffect(() => {
    navigate('/settings/models', { replace: true })
  }, [navigate])

  return (
    <div className="page">
      <div className="loading"><span className="spinner" />重定向中...</div>
    </div>
  )
}
