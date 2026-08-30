import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { CreateProjectPage } from '../pages/CreateProjectPage'
import { ProjectsPage } from '../pages/ProjectsPage'
import { AssetManagementPage } from '../features/asset-management/AssetManagementPage'
import { ProjectWorkbenchPage } from '../pages/ProjectWorkbenchPage'
import { RunDiagnosticsPage } from '../pages/RunDiagnosticsPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { HelpPage } from '../pages/HelpPage'

// 路由结构对应 docs/Mountain/04-webui-redesign.md §3 信息架构
export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/create" replace />} />
        <Route path="/create" element={<CreateProjectPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/assets" element={<AssetManagementPage />} />
        <Route path="/projects/:projectId" element={<ProjectWorkbenchPage />} />
        <Route path="/projects/:projectId/runs/:runId/diagnostics" element={<RunDiagnosticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/help" element={<HelpPage />} />
      </Route>
    </Routes>
  )
}

