import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'

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
      { path: 'bridge', element: page(<Placeholder title="Partial-Gravity Bridge" />) },
      { path: 'gaps', element: page(<Placeholder title="Evidence Gap Radar" />) },
      { path: 'evidence', element: page(<Placeholder title="Evidence Explorer" />) },
      { path: 'copilot', element: page(<Placeholder title="Scientific Copilot" />) },
      { path: 'methods', element: page(<Placeholder title="Methods & Sources" />) },
      { path: 'system', element: page(<Placeholder title="System" />) },
      { path: '*', element: page(<Placeholder title="Not found" />) },
    ],
  },
])
