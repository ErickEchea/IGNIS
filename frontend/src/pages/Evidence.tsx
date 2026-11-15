import { useMemo, useState } from 'react'
import { FindingCardView } from '../components/FindingCardView'
import { Loading, Note, Section } from '../components/ui'
import { useAnalysis, useCards, useCatalog, useScenarios } from '../lib/data'
import { weightedGeometricScore } from '../lib/ranking'
import type { Epistemic, FindingCard } from '../lib/types'

const GRAVITY_FILTERS: [string, string, (c: FindingCard) => boolean][] = [
  ['all', 'All gravity levels', () => true],
  ['micro', 'Microgravity (<0.01 g)', (c) => c.gravity_lo < 0.01],
  ['partial', 'Partial gravity (0.01–0.9 g)', (c) => c.gravity_hi > 0.01 && c.gravity_lo < 0.9],
  ['earth', 'Earth (≈1 g)', (c) => c.gravity_hi >= 0.9],
]
const FACTOR_HELP: Record<string, string> = {
  M: 'Mission relevance: closeness of the card’s gravity, O₂ and pressure to the selected scenario',
  E: 'Evidence strength: data type × epistemic category × confidence',
  R: 'Reproducibility: 1 − e^(−n/2), n = independent campaigns reporting the same variable family for the same material class',
}

export default function Evidence() {
  const cards = useCards()
  const analysis = useAnalysis()
  const scenarios = useScenarios()
  const [tab, setTab] = useState<'cards' | 'psi'>('cards')
  const [scenario, setScenario] = useState('LUNAR-2026-NOMINAL')
  const [weights, setWeights] = useState<Record<string, number>>({ M: 1, E: 1, R: 1 })
  const [gfilter, setGfilter] = useState('all')
  const [epi, setEpi] = useState<'all' | Epistemic>('all')
  const [q, setQ] = useState('')

  const ranked = useMemo(() => {
    if (!cards.data || !analysis.data) return []
    const gf = GRAVITY_FILTERS.find((g) => g[0] === gfilter)?.[2] ?? (() => true)
    const needle = q.trim().toLowerCase()
    return cards.data.cards
      .filter(gf)
      .filter((c) => epi === 'all' || c.epistemic === epi)
      .filter((c) => !needle || `${c.claim} ${c.material} ${c.measured_variable} ${c.provenance.source_id}`.toLowerCase().includes(needle))
      .map((c) => {
        const f = analysis.data.ranking[c.id]
        const factors = { M: f.M[scenario] ?? 0, E: f.E, R: f.R }
        const score = weightedGeometricScore(factors, weights)
        return { card: c, factors, score, why: explain(factors, weights, f.n_campaigns_same_family) }
      })
      .sort((x, y) => y.score - x.score || x.card.id.localeCompare(y.card.id))
  }, [cards.data, analysis.data, scenario, weights, gfilter, epi, q])

  if (!cards.data || !analysis.data || !scenarios.data) return <Loading what="the Evidence Ledger" />
  const sc = scenarios.data.find((s) => s.id === scenario)

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">A · Evidence Explorer</p>
        <h1 className="text-2xl font-semibold sm:text-3xl">The Evidence Ledger</h1>
        <p className="max-w-3xl text-sm text-muted">
          {cards.data.cards.length} Finding Cards, each with a verbatim quote that the pipeline verified on the cited page of the source, plus the catalog of every
          combustion investigation in NASA's Physical Sciences Informatics archive.
        </p>
        <div role="tablist" aria-label="Ledger views" className="flex gap-1">
          {(['cards', 'psi'] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`rounded-md border px-3 py-1.5 text-sm ${tab === t ? 'border-accent bg-surface-2' : 'border-line text-muted'}`}
            >
              {t === 'cards' ? 'Finding Cards' : 'PSI investigations'}
            </button>
          ))}
        </div>
      </header>

      {tab === 'psi' ? (
        <PsiCatalog />
      ) : (
        <>
          <Section kicker="Transparent ranking" title="Rank the evidence for a mission">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3">
                <label className="block text-sm">
                  <span className="text-muted">Mission scenario</span>
                  <select
                    value={scenario}
                    onChange={(e) => setScenario(e.target.value)}
                    className="mt-1 w-full rounded-md border border-line bg-surface-2 px-2 py-1.5 text-sm"
                  >
                    {scenarios.data.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                {sc && (
                  <p className="num text-xs text-muted">
                    g = {sc.gravity_g0 ?? 'any'} · O₂ = {sc.o2_percent ?? 'UNKNOWN'}% · p = {sc.derived.pressure_kpa ?? 'UNKNOWN'} kPa
                    {sc.derived.o2_partial_pressure_kpa != null && ` · pO₂ = ${sc.derived.o2_partial_pressure_kpa} kPa (DERIVED)`}
                  </p>
                )}
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <Select label="Gravity" value={gfilter} set={setGfilter} options={GRAVITY_FILTERS.map(([v, l]) => [v, l])} />
                  <Select
                    label="Epistemic status"
                    value={epi}
                    set={(v) => setEpi(v as 'all' | Epistemic)}
                    options={[
                      ['all', 'All'],
                      ['DOCUMENTED_FACT', 'Documented fact'],
                      ['SCIENTIFIC_INTERPRETATION', 'Interpretation'],
                      ['HYPOTHESIS', 'Hypothesis'],
                    ]}
                  />
                  <label className="block text-xs">
                    <span className="text-muted">Search</span>
                    <input
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                      placeholder="e.g. Mylar, LUCI"
                      className="mt-1 w-full rounded-md border border-line bg-surface-2 px-2 py-1.5 text-sm"
                    />
                  </label>
                </div>
              </div>
              <div className="space-y-2">
                <div className="rounded-md bg-surface-2 p-3 font-mono text-xs">
                  S = (M<sup>a</sup> · E<sup>b</sup> · R<sup>c</sup>)<sup>1/(a+b+c)</sup> (weighted geometric mean)
                </div>
                {(['M', 'E', 'R'] as const).map((k, i) => (
                  <label key={k} className="block text-xs" title={FACTOR_HELP[k]}>
                    <span className="flex justify-between">
                      <span>
                        {k} weight ({['a', 'b', 'c'][i]}): <span className="text-muted">{FACTOR_HELP[k]}</span>
                      </span>
                      <span className="num">{weights[k].toFixed(1)}</span>
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={3}
                      step={0.5}
                      value={weights[k]}
                      onChange={(e) => setWeights((w) => ({ ...w, [k]: Number(e.target.value) }))}
                      className="w-full accent-[color:var(--accent)]"
                    />
                  </label>
                ))}
              </div>
            </div>
            <Note>
              Factor values are computed by the IGNIS Scientific Core in Python and shipped with the page; the browser only recombines them with your weights.
              Ranking orders evidence for reading — it is not a risk score.
            </Note>
          </Section>

          <p className="text-sm text-muted" aria-live="polite">
            {ranked.length} cards
          </p>
          <ol className="space-y-3">
            {ranked.map((r, i) => (
              <li key={r.card.id} className="flex gap-3">
                <span className="num w-7 shrink-0 pt-3 text-right text-xs text-muted">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <FindingCardView card={r.card} score={r.score} why={r.why} notes={analysis.data.comparability[r.card.id]} />
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  )
}

function explain(f: Record<string, number>, w: Record<string, number>, n: number): string {
  const active = Object.entries(f).filter(([k]) => (w[k] ?? 0) > 0)
  if (active.length === 0) return 'All weights are zero.'
  const [lowK, lowV] = active.reduce((a, b) => (b[1] < a[1] ? b : a))
  const [highK, highV] = active.reduce((a, b) => (b[1] > a[1] ? b : a))
  const name: Record<string, string> = { M: 'mission relevance', E: 'evidence strength', R: `reproducibility (${n} campaign${n === 1 ? '' : 's'})` }
  return `Ranked here mainly by ${name[highK]} (${highV.toFixed(2)}); held back by ${name[lowK]} (${lowV.toFixed(2)}).`
}

function Select({ label: l, value, set, options }: { label: string; value: string; set: (v: string) => void; options: [string, string][] }) {
  return (
    <label className="block text-xs">
      <span className="text-muted">{l}</span>
      <select value={value} onChange={(e) => set(e.target.value)} className="mt-1 w-full rounded-md border border-line bg-surface-2 px-2 py-1.5 text-sm">
        {options.map(([v, t]) => (
          <option key={v} value={v}>
            {t}
          </option>
        ))}
      </select>
    </label>
  )
}

function PsiCatalog() {
  const catalog = useCatalog()
  if (!catalog.data) return <Loading what="the PSI catalog" />
  const inv = catalog.data
  const micro = inv.filter((i) => i.gravity_regime === 'microgravity').length
  return (
    <Section kicker="NASA Physical Sciences Informatics · CC0" title={`${inv.length} combustion investigations — ${micro} in microgravity, 0 at partial gravity`}>
      <Note>
        Harvested by the IGNIS pipeline from PSI (Research Area = Combustion Science). Gravity regime is derived from each record's project type; ground and
        computational investigations are listed separately. People are listed by name and role only.
      </Note>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead className="text-muted">
            <tr>
              <th className="py-1.5 pr-3">ID</th>
              <th className="pr-3">Investigation</th>
              <th className="pr-3">Platform</th>
              <th className="pr-3">Regime</th>
              <th className="pr-3">Dates</th>
              <th className="pr-3">Publications</th>
              <th>Data tables</th>
            </tr>
          </thead>
          <tbody>
            {inv.map((i) => (
              <tr key={i.accession} className="border-t border-line align-top">
                <td className="num py-1.5 pr-3">
                  <a href={i.url} target="_blank" rel="noreferrer" className="text-accent underline decoration-dotted">
                    {i.accession}
                  </a>
                </td>
                <td className="pr-3">
                  <span className="font-medium">{i.acronym || '—'}</span>
                  <span className="block text-muted">{i.title}</span>
                </td>
                <td className="pr-3">{i.platform || '—'}</td>
                <td className="pr-3">{i.gravity_regime === 'microgravity' ? 'µg' : 'ground / model'}</td>
                <td className="num pr-3">
                  {i.start_date || '?'} – {i.end_date || '?'}
                </td>
                <td className="num pr-3">{i.n_publications}</td>
                <td className="num">{i.tables.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>PSI platform metadata are shown as published; known inconsistencies (e.g. SAFFIRE-I dates) are listed under Methods → data quality.</Note>
    </Section>
  )
}

