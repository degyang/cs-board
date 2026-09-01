import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { AppProviders } from './app/providers'
import { router } from './app/router'
import './styles/tokens.css'
import './styles/app.css'
import './styles/assets.css'
import './styles/settings.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProviders>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </AppProviders>
  </React.StrictMode>,
)
