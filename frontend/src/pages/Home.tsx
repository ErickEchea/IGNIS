import { Link } from 'react-router-dom'

export function Home() {
  return (
    <section className="space-y-6 py-6">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">The partial-gravity blind spot</p>
      <h1 className="max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl">
        Fire depends on gravity. Crews will live at 0.165&nbsp;g and 0.38&nbsp;g — where the
        evidence is thinnest.
      </h1>
      <p className="max-w-2xl text-muted">
        IGNIS turns decades of low-gravity combustion research into comparable, traceable evidence:
        what we know, how dangerous a mission condition looks given that evidence, and what to
        measure next.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          to="/bridge"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-[#1b1d20] hover:opacity-90"
        >
          Open the Partial-Gravity Bridge
        </Link>
        <Link to="/gaps" className="rounded-md border border-line px-4 py-2 text-sm hover:bg-surface">
          See the evidence gaps
        </Link>
      </div>
      <p className="text-xs text-muted">
        Gravity values: Moon 1.62&nbsp;m/s² (0.165&nbsp;g), Mars 3.73&nbsp;m/s² (0.380&nbsp;g) —
        NASA NSSDC planetary fact sheets.
      </p>
    </section>
  )
}
