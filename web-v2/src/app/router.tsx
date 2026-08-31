import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { TasksPage } from '../pages/TasksPage'
import { CreateTaskPage } from '../pages/CreateTaskPage'
import { TaskWorkbenchPage } from '../pages/TaskWorkbenchPage'
import { RunDiagnosticsPage } from '../pages/RunDiagnosticsPage'
import { AssetManagementPage } from '../pages/AssetManagementPage'
import { SettingsPage } from '../pages/SettingsPage'
import { ServiceDetailPage } from '../pages/ServiceDetailPage'
import { HelpPage } from '../pages/HelpPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <TasksPage /> },
      { path: 'tasks/new', element: <CreateTaskPage /> },
      { path: 'tasks/:taskId', element: <TaskWorkbenchPage /> },
      { path: 'tasks/:taskId/runs/:runId/diagnostics', element: <RunDiagnosticsPage /> },
      { path: 'assets', element: <AssetManagementPage /> },
      { path: 'settings', element: <Navigate to="/settings/models" replace /> },
      {
        path: 'settings',
        element: <SettingsPage />,
        children: [
          { path: 'models', element: <div /> },
          { path: 'voice-alignment', element: <div /> },
          { path: 'toolchain', element: <div /> },
          { path: 'storage', element: <div /> },
          { path: 'diagnostics', element: <div /> },
        ],
      },
      { path: 'settings/models/:serviceId', element: <ServiceDetailPage /> },
      { path: 'help', element: <HelpPage /> },
      { path: '*', element: <div className="page"><h2>404 — 页面不存在</h2></div> },
    ],
  },
])
