import { useMemo, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { FindingCardView } from '../components/FindingCardView'
import { baseLayout, Plot, useChartTheme, type ChartTheme } from '../components/Plot'
import { Loading, Note, Section } from '../components/ui'
import { useAnalysis, useCards, useScenarios } from '../lib/data'
import { priority } from '../lib/ranking'
import type { Analysis, GapCell, Scenario } from '../lib/types'

const DEFAULT_SCENARIOS = ['LUNAR-SURFACE-HABITAT', 'LUNAR-SURFACE-HABITAT-EVA', 'GATEWAY-NOMINAL', 'MARS-SURFACE-HABITAT']
type View = 'priority' | 'coverage'

const RAMP_LIGHT = ['#f4f8fd', '#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#0d366b']
const RAMP_DARK = ['#20262e', '#184f95', '#256abf', '#3987e5', '#6da7ec', '#b7d3f6']

function isLight(): boolean {
  return getComputedStyle(document.documentElement).colorScheme.includes('light')
}

function heatmap(
  a: Analysis,
  cells: GapCell[],
  view: View,
  selected: string[],
  t: ChartTheme,
): { data: Data[]; layout: Partial<Layout> } {
  const gb = a.gaps.gravity_bins
  const ob = a.gaps.o2_bins
  const z: number[][] = gb.map(() => ob.map(() => 0))
  const hover: string[][] = gb.map(() => ob.map(() => ''))
  for (const c of cells) {
    const p = priority(c, selected)
    z[c.g][c.o2] = view === 'priority' ? p : c.n_campaigns
    hover[c.g][c.o2] =
      `<b>${gb[c.g]} · ${ob[c.o2]} O₂</b><br>` +
      `Independent campaigns: ${c.n_campaigns}${c.campaigns.length ? ` (${c.campaigns.slice(0, 4).join(', ')}${c.campaigns.length > 4 ? '…' : ''})` : ''}<br>` +
      `Long-duration (≥${a.gaps.long_duration_s} s) evidence: ${c.long_duration_evidence ? 'yes' : 'no'}<br>` +
      (c.planned?.length ? `Already planned: ${c.planned.join(', ')}<br>` : '') +
      `Priority P = ${p.toFixed(3)}`
  }
  const ramp = isLight() ? RAMP_LIGHT : RAMP_DARK
  const maxZ = Math.max(1e-9, ...z.flat())
  const colorscale = ramp.map((c, i) => [i / (ramp.length - 1), c]) as [number, string][]
  const textX: string[] = []
  const textY: string[] = []
  const textV: string[] = []
  const textC: string[] = []
  gb.forEach((g, gi) =>
    ob.forEach((o, oi) => {
      textX.push(o)
      textY.push(g)
      const v = z[gi][oi]
      textV.push(view === 'priority' ? (v > 0 ? v.toFixed(2) : '·') : String(v))
      const frac = v / maxZ
      textC.push(isLight() ? (frac > 0.5 ? '#ffffff' : t.text) : frac > 0.65 ? '#0b0b0b' : t.text)
    }),
  )
  return {
    data: [
      {
        type: 'heatmap',
        x: ob,
        y: gb,
        z,
        zmin: 0,
        zmax: view === 'priority' ? 1 : maxZ,
        colorscale,
        xgap: 2,
        ygap: 2,
        text: hover as unknown as string[],
        hovertemplate: '%{text}<extra></extra>',
        colorbar: {
          title: { text: view === 'priority' ? 'Priority P' : 'Campaigns', font: { color: t.muted, size: 11 } },
          tickfont: { color: t.muted, size: 11 },
          outlinewidth: 0,
          thickness: 10,
        },
      } as Data,
      {
        type: 'scatter',
        mode: 'text',
        x: textX,
        y: textY,
        text: textV,
        textfont: { color: textC, size: 11, family: 'IBM Plex Mono, monospace' },
        hoverinfo: 'skip',
        showlegend: false,
      } as Data,
    ],
    layout: baseLayout(t, {
      margin: { l: 150, r: 16, t: 8, b: 48 },
      xaxis: { title: { text: 'O₂ concentration bin (% by volume)' }, type: 'category', showgrid: false },
      yaxis: { title: { text: '' }, type: 'category', showgrid: false, autorange: true },
    }),
  }
}

export default function Gaps() {
  const analysis = useAnalysis()
  const scenarios = useScenarios()
  const cards = useCards()
  const theme = useChartTheme()
  const [selected, setSelected] = useState<string[]>(DEFAULT_SCENARIOS)
  const [pclass, setPclass] = useState<string>('reduced (<85 kPa)')
  const [fuel, setFuel] = useState<'solid' | 'droplet'>('solid')
  const [view, setView] = useState<View>('priority')

  const cells = useMemo(() => {
    if (!analysis.data) return []
    return analysis.data.gaps[fuel].cells.filter((c) => c.pressure === pclass)
  }, [analysis.data, fuel, pclass])
  const chart = useMemo(
    () => (analysis.data && theme ? heatmap(analysis.data, cells, view, selected, theme) : null),
    [analysis.data, cells, view, selected, theme],
  )

  if (!analysis.data || !scenarios.data || !cards.data) return <Loading what="the Gap Radar" />
  const a = analysis.data
  const fm2 = cards.data.cards.find((c) => c.id === 'LPSC2026-FM2-PLANNED')
  const fm2atm = cards.data.cards.find((c) => c.id === 'FM2-2024-ATM-34-8.2')
  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  const usable = scenarios.data.filter((s) => s.gravity_g0 !== null)

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">F · Evidence Gap Radar + Next-Experiment Designer</p>
        <h1 className="text-2xl font-semibold sm:text-3xl">Where the evidence ends, and what to measure next</h1>
        <p className="max-w-3xl text-sm text-muted">
          Each cell is a combination of gravity, oxygen concentration and pressure. Cell values count independent experimental campaigns in the IGNIS ledger
          (Finding Cards plus PSI test tables); priority combines mission relevance, scarcity and the lack of long-duration tests.
        </p>
      </header>

      <Section kicker="Controls" title="Mission scenarios and conditions">
        <fieldset className="space-y-2">
          <legend className="text-xs uppercase tracking-wider text-muted">Missions (relevance = best match over the selected scenarios)</legend>
          <div className="flex flex-wrap gap-2">
            {usable.map((s: Scenario) => (
              <label key={s.id} className={`cursor-pointer rounded-md border px-2.5 py-1.5 text-xs ${selected.includes(s.id) ? 'border-accent bg-surface-2' : 'border-line'}`}>
                <input type="checkbox" className="sr-only" checked={selected.includes(s.id)} onChange={() => toggle(s.id)} />
                <span aria-hidden="true" className="mr-1">{selected.includes(s.id) ? '■' : '□'}</span>
                {s.name}
                <span className="num ml-1 text-muted">
                  {s.gravity_g0} g · {s.o2_percent ?? '?'}% · {s.pressure ? `${s.pressure.value} psia` : '?'}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="flex flex-wrap gap-4 text-sm">
          <Radio name="view" value={view} set={(v) => setView(v as View)} options={[['priority', 'Priority'], ['coverage', 'Coverage (campaigns)']]} />
          <Radio
            name="pressure"
            value={pclass}
            set={setPclass}
            options={a.gaps.pressure_classes.map((p) => [p, p.replace(' (', ' · ').replace(')', '')])}
          />
          <Radio name="fuel" value={fuel} set={(v) => setFuel(v as 'solid' | 'droplet')} options={[['solid', 'Solid materials'], ['droplet', 'Liquid droplets']]} />
        </div>
      </Section>

      <Section kicker={view === 'priority' ? 'Priority map' : 'Coverage map'} title={`Gravity × O₂ at ${pclass} pressure — ${fuel === 'solid' ? 'solid materials' : 'droplets'}`}>
        {chart && <Plot {...chart} height={420} ariaLabel="Heatmap of evidence priority or coverage by gravity level and oxygen concentration" />}
        <div className="rounded-md bg-surface-2 p-3 font-mono text-xs leading-relaxed">
          P(cell) = max<sub>s∈missions</sub> R<sub>s</sub>(cell) × 1/(1 + n<sub>campaigns</sub>) × D × F
          <br />R<sub>s</sub> = 1 inside the scenario's bin, Gaussian decay outside (σ<sub>g</sub> = 0.05 g, σ<sub>O₂</sub> = 4 pts); orbital free fall only matches µg; unknown
          scenario atmospheres count 0.8.
          <br />D = 1 if no evidence in the cell lasted ≥ {a.gaps.long_duration_s} s of reduced gravity, else 0.5. F = 0.5 if a documented planned experiment
          (e.g. FM2) already targets the cell, else 1.
        </div>
        <Note>
          {a.gaps[fuel].unplaced_points} evidence points with no reported O₂ are not placed on the map. Partial-gravity limits from Olson & Ferkul (2012) sit in the
          &lt;19% and 19–23% bins because they are the O₂ values at which flames went out. The IGNIS ledger contains no partial-gravity flammability test at the habitat oxygen levels (26.5% or 34%); absence from this ledger is not proof that no such test exists.
        </Note>
      </Section>

      <Section kicker="F.1 · Next-Experiment Designer (transparent priority, not Bayesian)" title="What should fly next">
        <div className="grid gap-3 md:grid-cols-2">
          {a.next_experiments.map((n, i) => (
            <article key={`${n.gravity_bin}-${n.o2_bin}-${n.closest_scenario.id}`} className="space-y-2 rounded-md border border-line bg-bg/40 p-3">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold">
                  #{i + 1} · {n.gravity_bin} · {n.o2_bin} · {n.pressure_class}
                </h3>
                <span className="num text-xs text-muted">P = {n.priority.toFixed(2)}</span>
              </div>
              <p className="text-xs text-muted">
                Closest mission: <span className="text-ink">{n.closest_scenario.name}</span> · existing campaigns:{' '}
                <span className="text-ink">{n.existing_campaigns.length ? n.existing_campaigns.join(', ') : 'none in the ledger'}</span>
              </p>
              <p className="num text-[11px] text-muted">
                R = {n.relevance.toFixed(2)} · 1/(1+n) = {n.scarcity.toFixed(2)} · D = {n.duration_factor} · F = {n.planned_factor}
              </p>
              {n.already_planned.length > 0 && (
                <p className="text-xs text-good">✓ Already targeted by a planned experiment: {n.already_planned.join(', ')} (documented plan, no results yet)</p>
              )}
              <p className="text-sm">
                <span className="text-muted">Platform: </span>
                {n.platform}
              </p>
              <p className="text-xs text-muted">{n.platform_rationale}</p>
              <p className="text-xs">
                <span className="text-muted">Hypothesis: </span>
                {n.hypothesis}
              </p>
              <p className="text-xs">
                <span className="text-muted">Measure: </span>
                {n.measure}
              </p>
            </article>
          ))}
        </div>
        <Note>
          This list is computed from the priority formula for the four exploration scenarios. It is a transparent prioritization, not a Bayesian
          experimental design: expected information gain needs a validated predictor, and the C.2 gate is closed.
        </Note>
        {fm2 && (
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wider text-muted">Already planned</p>
            <FindingCardView card={fm2} compact />
            {fm2atm && <FindingCardView card={fm2atm} compact />}
          </div>
        )}
      </Section>
    </div>
  )
}

function Radio({ name, value, set, options }: { name: string; value: string; set: (v: string) => void; options: [string, string][] }) {
  return (
    <div role="radiogroup" aria-label={name} className="flex flex-wrap gap-1">
      {options.map(([v, l]) => (
        <label key={v} className={`cursor-pointer rounded-md border px-2.5 py-1 text-xs ${value === v ? 'border-accent bg-surface-2' : 'border-line text-muted'}`}>
          <input type="radio" name={name} value={v} className="sr-only" checked={value === v} onChange={() => set(v)} />
          {l}
        </label>
      ))}
    </div>
  )
}
