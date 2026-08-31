import { useLocation } from 'react-router-dom'
import { SettingsSubnav } from './SettingsSubnav'
import { ModelsTab } from './ModelsTab'
import { ToolchainStatusTab, TaskStorageStatusTab, SystemDiagnosticsTab } from './systemStatus/SystemStatusTabs'
import { SYS_DEMO_VIEWS, DIAG_VIEW } from './systemStatus/fixtures'

/* 设置 /settings：模型 / 语音与对齐 / 系统工具链 / 任务存储状态 / 系统诊断 五页签。
   模型为可编辑的服务商列表（ModelsTab）；语音与对齐为独立路由页 /settings/voice-alignment；
   系统工具链 / 任务存储状态 / 系统诊断 均为运行环境探测的只读状态，不提供可保存配置，
   所有状态经内存 fixture 注入，不写入 localStorage / sessionStorage。 */

type SettingsTab = 'models' | 'toolchain' | 'storage' | 'diagnostics'

function readTabFromHash(hash: string): SettingsTab {
  const h = hash.replace('#', '')
  const valid: SettingsTab[] = ['models', 'toolchain', 'storage', 'diagnostics']
  return (valid as string[]).includes(h) ? (h as SettingsTab) : 'models'
}

export function SettingsPage() {
  const location = useLocation()

  /* tab 由 location.hash 响应式派生（模型/工具链/存储/诊断 为页内分页）。
   * 关键：React Router 的 navigate 基于 history.pushState，不会触发原生 hashchange 事件，
   * 因此不能用 hashchange 监听来同步 tab，必须从 useLocation().hash 实时读取（每次导航重渲染即重算）。 */
  const tab = readTabFromHash(location.hash)

  /* 原型演示场景：通过 URL 查询参数 ?demo= 切换（available / toolchain-unavailable / storage-not-stated）。
     真实接入后由后端数据注入，忽略 demo。 */
  const demoKey = new URLSearchParams(location.search).get('demo') ?? 'available'
  const scene = SYS_DEMO_VIEWS.find((d) => d.key === demoKey) ?? SYS_DEMO_VIEWS[0]

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">设置</h1>
        <p className="page-desc">
          模型服务、语音与对齐、系统工具链、任务存储与系统诊断的状态总览。
          其中「系统工具链 / 任务存储状态 / 系统诊断」均为运行环境探测的只读状态，不提供可保存的后端配置；所有状态均不写入本机存储。
        </p>
      </div>

      <SettingsSubnav active={tab} />

      <div style={{ marginTop: 18, paddingBottom: 80 }}>
        {/* 模型页签：模型服务商列表（CRUD），独立维护，不走通用只读渲染 */}
        {tab === 'models' && <ModelsTab />}

        {/* 系统工具链：只读状态卡 */}
        {tab === 'toolchain' && <ToolchainStatusTab view={scene.toolchain} />}

        {/* 任务存储状态：五类逻辑存储只读状态 */}
        {tab === 'storage' && <TaskStorageStatusTab view={scene.storage} />}

        {/* 系统诊断：只读汇总 + 任务级诊断入口 */}
        {tab === 'diagnostics' && <SystemDiagnosticsTab view={DIAG_VIEW} />}
      </div>
    </div>
  )
}
