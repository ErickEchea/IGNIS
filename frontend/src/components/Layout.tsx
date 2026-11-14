import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/bridge', label: 'Partial-Gravity Bridge' },
  { to: '/gaps', label: 'Gap Radar' },
  { to: '/evidence', label: 'Evidence' },
  { to: '/copilot', label: 'Copilot' },
  { to: '/methods', label: 'Methods' },
] as const

export function Layout() {
  return (
    <div className="min-h-dvh flex flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-line bg-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2.5" aria-label="IGNIS home">
            <img src="/ignis-logo.svg" alt="" width={32} height={32} className="rounded-md" />
            <span className="leading-tight">
              <span className="block text-base font-semibold tracking-[0.18em]">IGNIS</span>
              <span className="block text-[11px] uppercase tracking-wider text-muted">
                Space Fire Intelligence
              </span>
            </span>
          </NavLink>
          <nav aria-label="Primary" className="flex flex-1 flex-wrap gap-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 transition-colors ${
                    isActive ? 'bg-surface-2 text-ink' : 'text-muted hover:text-ink'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <NavLink to="/system" className="text-xs text-muted hover:text-ink">
            System
          </NavLink>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto max-w-7xl px-4 py-4 text-xs text-muted">
          IGNIS · Team Artisanal Intelligence (Riobamba, Ecuador) · NASA Space Apps Challenge 2026 —
          “Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data”. Not
          affiliated with or endorsed by NASA. Data sources and licenses: see Methods.
        </div>
      </footer>
    </div>
  )
}
