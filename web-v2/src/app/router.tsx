import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { TasksPage } from '../pages/TasksPage'
import { CreateTaskPage } from '../pages/CreateTaskPage'
import { TaskWorkbenchPage } from '../pages/TaskWorkbenchPage'
import { RunDiagnosticsPage } from '../pages/RunDiagnosticsPage'
import { AssetManagementPage } from '../pages/AssetManagementPage'
import { SettingsLayout } from '../pages/SettingsLayout'
import { ModelServicesPage } from '../pages/ModelServicesPage'
import { ServiceDetailPage } from '../pages/ServiceDetailPage'
import { ServiceFormPage } from '../pages/ServiceFormPage'
import { VoiceAlignmentPage } from '../pages/VoiceAlignmentPage'
import { ToolchainPage } from '../pages/ToolchainPage'
import { StoragePage } from '../pages/StoragePage'
import { DiagnosticsPage } from '../pages/DiagnosticsPage'
import { HelpPage } from '../pages/HelpPage'

/** Task-related child routes — exported for test verification via matchRoutes(). */
export const TASK_ROUTES = [
  { index: true, element: <TasksPage /> },
  { path: 'tasks/new', element: <CreateTaskPage /> },
  { path: 'tasks/:taskId', element: <TaskWorkbenchPage /> },
  { path: 'tasks/:taskId/runs/:runId/diagnostics', element: <RunDiagnosticsPage /> },
]

export const SETTINGS_ROUTES = {
  path: 'settings',
  element: <SettingsLayout />,
  children: [
    { path: 'models', element: <ModelServicesPage /> },
    { path: 'models/new', element: <ServiceFormPage /> },
    { path: 'models/:serviceId', element: <ServiceDetailPage /> },
    { path: 'models/:serviceId/edit', element: <ServiceFormPage /> },
    { path: 'voice-alignment', element: <VoiceAlignmentPage /> },
    { path: 'toolchain', element: <ToolchainPage /> },
    { path: 'storage', element: <StoragePage /> },
    { path: 'diagnostics', element: <DiagnosticsPage /> },
  ],
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      ...TASK_ROUTES,
      { path: 'assets', element: <AssetManagementPage /> },
      { path: 'settings', element: <Navigate to="/settings/models" replace /> },
      SETTINGS_ROUTES,
      { path: 'help', element: <HelpPage /> },
      { path: '*', element: <div className="page"><h2>404 — 页面不存在</h2></div> },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
})
