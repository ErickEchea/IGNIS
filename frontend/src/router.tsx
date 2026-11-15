import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'

const Bridge = lazy(() => import('./pages/Bridge'))
const Gaps = lazy(() => import('./pages/Gaps'))
const Evidence = lazy(() => import('./pages/Evidence'))
const Methods = lazy(() => import('./pages/Methods'))
const Copilot = lazy(() => import('./pages/Copilot'))
const System = lazy(() => import('./pages/System'))
const Placeholder = lazy(() => import('./pages/Placeholder'))

function page(node: ReactNode) {
  return <Suspense fallback={<p className="p-6 text-muted">Loading…</p>}>{node}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'bridge', element: page(<Bridge />) },
      { path: 'gaps', element: page(<Gaps />) },
      { path: 'evidence', element: page(<Evidence />) },
      { path: 'copilot', element: page(<Copilot />) },
      { path: 'methods', element: page(<Methods />) },
      { path: 'system', element: page(<System />) },
      { path: '*', element: page(<Placeholder title="Not found" />) },
    ],
  },
])
