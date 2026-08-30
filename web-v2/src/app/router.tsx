import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { ProjectsPage } from '../pages/ProjectsPage'
import { CreateProjectPage } from '../pages/CreateProjectPage'
import { ProjectWorkbenchPage } from '../pages/ProjectWorkbenchPage'
import { RunDiagnosticsPage } from '../pages/RunDiagnosticsPage'
import { ProvidersPage } from '../pages/ProvidersPage'
import { ProviderDetailPage } from '../pages/ProviderDetailPage'
import { HelpPage } from '../pages/HelpPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <ProjectsPage /> },
      { path: 'projects/new', element: <CreateProjectPage /> },
      { path: 'projects/:projectId', element: <ProjectWorkbenchPage /> },
      { path: 'projects/:projectId/runs/:runId/diagnostics', element: <RunDiagnosticsPage /> },
      { path: 'settings/providers', element: <ProvidersPage /> },
      { path: 'settings/providers/:name', element: <ProviderDetailPage /> },
      { path: 'help', element: <HelpPage /> },
      { path: '*', element: <div className="page"><h2>404 — 页面不存在</h2></div> },
    ],
  },
])
