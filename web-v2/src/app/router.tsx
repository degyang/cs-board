import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { TasksPage } from '../pages/TasksPage'
import { CreateTaskPage } from '../pages/CreateTaskPage'
import { TaskWorkbenchPage } from '../pages/TaskWorkbenchPage'
import { RunDiagnosticsPage } from '../pages/RunDiagnosticsPage'
import AssetManagementPage from '../pages/AssetManagementPage'
import SettingsPage from '../pages/SettingsPage'
import ServiceDetailPage from '../pages/ServiceDetailPage'
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
      { path: 'settings', element: <SettingsPage /> },
      { path: 'settings/models/:serviceId', element: <ServiceDetailPage /> },
      { path: 'help', element: <HelpPage /> },
      { path: '*', element: <div className="page"><h2>404 — 页面不存在</h2></div> },
    ],
  },
])
