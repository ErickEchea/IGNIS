import { Link } from 'react-router-dom'
import { useAnalysis, useCards, useCatalog } from '../lib/data'
import { priority } from '../lib/ranking'

const LUNAR = ['LUNAR-SURFACE-HABITAT', 'LUNAR-SURFACE-HABITAT-EVA']

export function Home() {
  const catalog = useCatalog()
  const analysis = useAnalysis()
  const cards = useCards()

  const nPsi = catalog.data?.length
  const nPartialPsi = catalog.data?.filter((i) => i.gravity_regime === 'partial_gravity').length
  const minMargin = analysis.data ? Math.min(...analysis.data.bridge.margin_checks.map((m) => m.computed)) : undefined
  const lunarCells = analysis.data?.gaps.solid.cells.filter((c) => c.g === 2 && c.pressure.startsWith('reduced') && c.o2 === 2)
  const lunarCampaigns = lunarCells?.reduce((n, c) => n + c.n_campaigns, 0)
  const lunarTop = lunarCells?.every((c) => priority(c, LUNAR) === 1)

  return (
    <div className="space-y-10 py-4">
      <section className="space-y-5">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">The partial-gravity blind spot</p>
        <h1 className="max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl">
          Fire depends on gravity. Crews will live at 0.165&nbsp;g and 0.38&nbsp;g — where the evidence is thinnest.
        </h1>
        <p className="max-w-2xl text-muted">
          IGNIS turns NASA's low-gravity combustion archive into traceable evidence: what we know, how well a mission condition is covered, and which experiment
          should fly next. Every number shows its source; every claim shows how certain it is.
        </p>
      </section>

      <section aria-label="Key findings" className="grid gap-3 md:grid-cols-3">
        <Fact
          value={nPsi === undefined ? '…' : `${nPartialPsi} of ${nPsi}`}
          text="combustion investigations in NASA's PSI archive were run at partial gravity."
          src="PSI catalog harvested by IGNIS · DERIVED"
        />
        <Fact
          value={minMargin === undefined ? '…' : `${minMargin.toFixed(2)}% O₂`}
          text="lowest oxygen margin vs the 1-g screening limit: Mylar G kept burning at lower O₂ in lunar gravity."
          src="Olson & Ferkul 2012, Table I · recomputed by IGNIS (9/9 match)"
        />
        <Fact
          value={lunarCampaigns === undefined ? '…' : `${lunarCampaigns} campaigns`}
          text="in the IGNIS ledger test flammability at lunar gravity in the nominal lunar-habitat atmosphere (10.2 psia, 26.5% O₂), and none of the planned experiments in our sources targets it."
          src={lunarTop ? 'Gap Radar · top priority (P = 1); FM2 plans 8.2 psia/34% and 14.7 psia/21% instead' : 'Gap Radar'}
        />
      </section>

      <section aria-label="Guided tour" className="space-y-3">
        <h2 className="text-sm uppercase tracking-[0.18em] text-muted">30-second tour</h2>
        <ol className="grid gap-3 md:grid-cols-3">
          <Step n={1} to="/bridge" title="Partial-Gravity Bridge" text="See how flammability limits change from 0 g to 1 g, and why the 1-g screening test may not be conservative." />
          <Step n={2} to="/gaps" title="Evidence Gap Radar" text="Map gravity × oxygen × pressure against the missions you care about and see where no data exist." />
          <Step n={3} to="/gaps" title="Next-Experiment Designer" text="Get a ranked, explained list of what to measure next, and on which platform." />
        </ol>
      </section>

      <section className="grid gap-3 text-sm md:grid-cols-2">
        <div className="rounded-lg border border-line bg-surface p-4">
          <h2 className="mb-2 font-semibold">How to read IGNIS</h2>
          <ul className="space-y-1 text-muted">
            <li>
              <span className="font-mono text-xs text-ink">MEASURED · DERIVED · MODELED · CONCEPTUAL</span> — what kind of number it is.
            </li>
            <li>
              <span className="text-ink">■ Documented fact · ◆ Interpretation · △ Hypothesis · ? Unknown</span> — how certain the claim is.
            </li>
            <li>Each Finding Card quotes its source verbatim; the quote was found on the cited page by a deterministic check.</li>
          </ul>
        </div>
        <div className="rounded-lg border border-line bg-surface p-4">
          <h2 className="mb-2 font-semibold">What IGNIS does not do</h2>
          <ul className="space-y-1 text-muted">
            <li>No fire probabilities or risk maps: no model has been validated at partial gravity (see the predictor gate).</li>
            <li>Language models only explain results computed by deterministic code; the app works without them.</li>
            <li>{cards.data ? `${cards.data.cards.length} curated cards` : 'The ledger'} is a focused evidence base, not an exhaustive literature review.</li>
          </ul>
        </div>
      </section>
    </div>
  )
}

function Fact({ value, text, src }: { value: string; text: string; src: string }) {
  return (
    <div className="flex flex-col rounded-lg border border-line bg-surface p-4">
      <p className="text-3xl font-semibold text-accent">{value}</p>
      <p className="mt-1 text-sm">{text}</p>
      <p className="mt-auto pt-3 text-[11px] text-muted">{src}</p>
    </div>
  )
}

function Step({ n, to, title, text }: { n: number; to: string; title: string; text: string }) {
  return (
    <li>
      <Link to={to} className="block h-full rounded-lg border border-line bg-surface p-4 transition-colors hover:border-accent">
        <span className="num text-xs text-accent">0{n}</span>
        <span className="mt-1 block font-semibold">{title} →</span>
        <span className="mt-1 block text-sm text-muted">{text}</span>
      </Link>
    </li>
  )
}
