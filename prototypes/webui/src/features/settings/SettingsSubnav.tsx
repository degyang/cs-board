import { Tabs } from '../../components/ui/Tabs'
import { useLocation, useNavigate } from 'react-router-dom'

/* 设置二级导航（统一）：模型服务 / 语音与对齐 / 工具链 / 存储 / 诊断。
 * - 模型服务 / 工具链 / 存储 / 诊断 为设置页内分页（复用 Tabs 视觉与交互）；
 * - 语音与对齐 是设置下的独立路由页（/settings/voice-alignment），点击跳转而非页内切换。
 * 该组件同时被 SettingsPage 与 VoiceAlignmentPage 复用，保证导航一致性。 */

const SETTINGS_NAV = [
  { key: 'models', label: '模型服务' },
  { key: 'voice-alignment', label: '语音与对齐' },
  { key: 'toolchain', label: '工具链' },
  { key: 'storage', label: '存储' },
  { key: 'diagnostics', label: '诊断' },
]

export function SettingsSubnav({ active }: { active: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const onSelect = (key: string) => {
    if (key === 'voice-alignment') navigate('/settings/voice-alignment')
    /* 保留当前查询参数（如 ?demo=），避免切换分页时丢失演示态；
       hash 用于页内分页，由 React Router 的 useLocation().hash 响应式驱动。 */
    else navigate(`/settings${location.search}#${key}`)
  }
  return <Tabs items={SETTINGS_NAV} active={active} onChange={onSelect} />
}
