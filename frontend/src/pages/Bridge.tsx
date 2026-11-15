import { useMemo, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { FindingCardView } from '../components/FindingCardView'
import { baseLayout, Plot, useChartTheme, type ChartTheme } from '../components/Plot'
import { Loading, Note, Section, SourceRef, StatusPill } from '../components/ui'
import { useAnalysis, useCards, useCatalog, useScenarios } from '../lib/data'
import type { Analysis, FindingCard, Scenario } from '../lib/types'

const MATERIALS = ['MYLAR', 'ULTEM', 'NOMEX'] as const
const SYMBOLS = ['circle', 'square', 'diamond']
const GRAVITY_ROWS: [string, number][] = [
  ['0G', 0],
  ['LUNAR', 0.165],
  ['MARS', 0.38],
  ['1G', 1],
]

interface LimitRow {
  material: string
  label: string
  pressure: string
  gravity: number
  gravityLabel: string
  uloi: number
  moc: number
  uloiId: string
  mocId: string
}

function tableIRows(cards: FindingCard[]): LimitRow[] {
  const byId = new Map(cards.map((c) => [c.id, c]))
  const rows: LimitRow[] = []
  for (const m of MATERIALS) {
    for (const [g, gv] of GRAVITY_ROWS) {
      const u = byId.get(`OF2012-${g}-ULOI-${m}`)
      const mo = byId.get(`OF2012-${g}-MOC-${m}`)
      if (!u?.value || !mo?.value) continue
      rows.push({
        material: m,
        label: u.material,
        pressure: u.pressure ? `${u.pressure.value} psia` : '—',
        gravity: gv,
        gravityLabel: g === '0G' ? '0 g (30 cm/s forced flow)' : g === 'LUNAR' ? 'Lunar' : g === 'MARS' ? 'Martian' : '1 g',
        uloi: u.value.value,
        moc: mo.value.value,
        uloiId: u.id,
        mocId: mo.id,
      })
    }
  }
  return rows
}

function limitsChart(rows: LimitRow[], t: ChartTheme, scenarios: Scenario[]): { data: Data[]; layout: Partial<Layout> } {
  const data: Data[] = MATERIALS.map((m, i) => {
    const r = rows.filter((x) => x.material === m).sort((a, b) => a.gravity - b.gravity)
    const off = (i - 1) * 0.014
    const mid = r.map((x) => (x.uloi + x.moc) / 2)
    return {
      type: 'scatter',
      mode: 'lines+markers',
      name: `${shortName(m)} (${r[0]?.pressure ?? ''})`,
      x: r.map((x) => x.gravity + off),
      y: mid,
      line: { color: t.series[i], width: 2, dash: 'dot' },
      marker: { color: t.series[i], size: 9, symbol: SYMBOLS[i], line: { color: t.surface, width: 2 } },
      error_y: {
        type: 'data',
        symmetric: false,
        array: r.map((x) => x.uloi - (x.uloi + x.moc) / 2),
        arrayminus: r.map((x) => (x.uloi + x.moc) / 2 - x.moc),
        color: t.series[i],
        thickness: 2,
        width: 5,
      },
      customdata: r.map((x) => [x.gravityLabel, x.uloi, x.moc]),
      hovertemplate: `<b>${shortName(m)}</b> · %{customdata[0]}<br>ULOI(*) %{customdata[1]}% O₂ · MOC(*) %{customdata[2]}% O₂<br>midpoint %{y:.2f}%<extra></extra>`,
    } as Data
  })
  const lunarHab = scenarios.find((s) => s.id === 'LUNAR-SURFACE-HABITAT')
  const shapes: Partial<Layout>['shapes'] = []
  const annotations: Partial<Layout>['annotations'] = []
  if (lunarHab?.o2_percent) {
    shapes.push({ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: lunarHab.o2_percent, y1: lunarHab.o2_percent, line: { color: t.muted, width: 1, dash: 'dash' } })
    annotations.push({ xref: 'paper', x: 0.01, y: lunarHab.o2_percent, yanchor: 'bottom', xanchor: 'left', showarrow: false, text: `Lunar habitat nominal: ${lunarHab.o2_percent}% O₂ at 10.2 psia`, font: { size: 11, color: t.muted } })
  }
  for (const [x, txt] of [[0.165, 'Moon'], [0.38, 'Mars']] as [number, string][]) {
    shapes.push({ type: 'line', yref: 'paper', x0: x, x1: x, y0: 0, y1: 1, line: { color: t.grid, width: 1 } })
    annotations.push({ x, yref: 'paper', y: 1, yanchor: 'bottom', showarrow: false, text: txt, font: { size: 11, color: t.muted } })
  }
  return {
    data,
    layout: baseLayout(t, {
      shapes,
      annotations,
      xaxis: { title: { text: 'Gravity level (g/g₀)' }, range: [-0.05, 1.05], zeroline: false },
      yaxis: { title: { text: 'Upward flammability limit (% O₂, molar)' }, range: [12, 28] },
    }),
  }
}

function marginChart(a: Analysis, t: ChartTheme): { data: Data[]; layout: Partial<Layout> } {
  const levels: [number, string][] = [
    [0.38, 'Martian g'],
    [0.165, 'Lunar g'],
    [0, '0 g + 30 cm/s flow'],
  ]
  const groups = new Map<string, { g: number; v: number; rep: number | null }[]>()
  for (const m of a.bridge.margin_checks) {
    const arr = groups.get(m.material) ?? []
    arr.push({ g: m.gravity_g0, v: m.computed, rep: m.reported })
    groups.set(m.material, arr)
  }
  const mats = [...groups.keys()].sort((x, y) => order(x) - order(y))
  const data: Data[] = mats.map((m) => {
    const vals = groups.get(m) ?? []
    return {
      type: 'bar',
      name: shortName(m),
      x: levels.map((l) => l[1]),
      y: levels.map((l) => vals.find((v) => Math.abs(v.g - l[0]) < 1e-6)?.v ?? null),
      marker: { color: t.series[order(m)], line: { color: t.surface, width: 2 } },
      text: levels.map((l) => {
        const v = vals.find((x) => Math.abs(x.g - l[0]) < 1e-6)?.v
        return v === undefined ? '' : `${v > 0 ? '+' : ''}${v}`
      }),
      textposition: 'outside',
      textfont: { color: t.text, size: 11 },
      hovertemplate: `<b>${shortName(m)}</b> · %{x}<br>ΔO₂ = %{y:+.2f}% (IGNIS recomputation = source value)<extra></extra>`,
    } as Data
  })
  return {
    data,
    layout: baseLayout(t, {
      barmode: 'group',
      bargap: 0.3,
      bargroupgap: 0.08,
      yaxis: { title: { text: 'Oxygen margin ΔO₂ vs 1 g (% O₂)' }, range: [-7, 1.5], zeroline: true, zerolinewidth: 2 },
      xaxis: { title: { text: '' } },
      shapes: [],
    }),
  }
}

function order(material: string): number {
  if (material.startsWith('Mylar')) return 0
  if (material.startsWith('Ultem')) return 1
  return 2
}
function shortName(m: string): string {
  if (m.startsWith('MYLAR') || m.startsWith('Mylar')) return 'Mylar G'
  if (m.startsWith('ULTEM') || m.startsWith('Ultem')) return 'Ultem 1000'
  return 'Nomex HT90-40'
}

function buoyancyChart(a: Analysis, t: ChartTheme): { data: Data[]; layout: Partial<Layout> } {
  const c = a.bridge.buoyancy_curve
  const uniqueFlows = [...new Set(a.bridge.flow_analogs.filter((f) => f.kind !== 'model').map((f) => f.flow_cm_s))].sort((x, y) => x - y)
  const data: Data[] = [
    { type: 'scatter', mode: 'lines', x: c.map((p) => p.g), y: c.map((p) => p.high_cm_s), line: { color: t.series[0], width: 0 }, hoverinfo: 'skip', showlegend: false },
    {
      type: 'scatter',
      mode: 'lines',
      name: 'u_b(g) band (MODELED, 1-g anchors 20–35 cm/s across sources)',
      x: c.map((p) => p.g),
      y: c.map((p) => p.low_cm_s),
      fill: 'tonexty',
      fillcolor: hexA(t.series[0], 0.25),
      line: { color: t.series[0], width: 2 },
      customdata: c.map((p) => [p.low_cm_s, p.high_cm_s]),
      hovertemplate: 'g = %{x:.3f}<br>u_b ≈ %{customdata[0]:.1f}–%{customdata[1]:.1f} cm/s<extra>MODELED</extra>',
    } as Data,
    {
      type: 'scatter',
      mode: 'text+markers',
      name: 'Moon / Mars',
      x: [a.bridge.moon.gravity_g0, a.bridge.mars.gravity_g0],
      y: [(a.bridge.moon.low_cm_s + a.bridge.moon.high_cm_s) / 2, (a.bridge.mars.low_cm_s + a.bridge.mars.high_cm_s) / 2],
      text: [
        `Moon ${a.bridge.moon.low_cm_s.toFixed(1)}–${a.bridge.moon.high_cm_s.toFixed(1)} cm/s`,
        `Mars ${a.bridge.mars.low_cm_s.toFixed(1)}–${a.bridge.mars.high_cm_s.toFixed(1)} cm/s`,
      ],
      textposition: ['middle right', 'bottom right'] as unknown as 'middle right', // per-point positions (supported by Plotly at runtime)
      textfont: { color: t.text, size: 11 },
      marker: { color: t.text, size: 9, line: { color: t.surface, width: 2 } },
      hoverinfo: 'skip',
      showlegend: false,
    },
  ]
  const shapes: Partial<Layout>['shapes'] = uniqueFlows.map((v) => ({
    type: 'line',
    xref: 'paper',
    x0: 0,
    x1: 1,
    y0: v,
    y1: v,
    line: { color: t.series[1], width: 1.5, dash: 'dash' },
  }))
  // Labels sit on the side of the plot the u_b curve does not cross at that height.
  const annotations: Partial<Layout>['annotations'] = uniqueFlows.map((v) => ({
    xref: 'paper',
    x: v >= 25 ? 0.01 : 0.99,
    y: v,
    xanchor: v >= 25 ? 'left' : 'right',
    yanchor: 'bottom',
    showarrow: false,
    text: `µg forced flow ${v} cm/s (${v === 20 ? 'Saffire I–II' : 'Saffire III; Olson & Ferkul 0 g'})`,
    font: { size: 11, color: t.muted },
  }))
  return {
    data,
    layout: baseLayout(t, {
      shapes,
      annotations,
      xaxis: { title: { text: 'Gravity level (g/g₀)' }, range: [0, 1] },
      yaxis: { title: { text: 'Characteristic buoyant velocity (cm/s)' }, range: [0, 40] },
      showlegend: true,
    }),
  }
}

function hexA(hex: string, a: number): string {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const n = parseInt(h, 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

export default function Bridge() {
  const cards = useCards()
  const analysis = useAnalysis()
  const scenarios = useScenarios()
  const catalog = useCatalog()
  const theme = useChartTheme()
  const [showTable, setShowTable] = useState(false)

  const rows = useMemo(() => (cards.data ? tableIRows(cards.data.cards) : []), [cards.data])
  const limits = useMemo(() => (theme && scenarios.data ? limitsChart(rows, theme, scenarios.data) : null), [rows, theme, scenarios.data])
  const margins = useMemo(() => (theme && analysis.data ? marginChart(analysis.data, theme) : null), [theme, analysis.data])
  const buoy = useMemo(() => (theme && analysis.data ? buoyancyChart(analysis.data, theme) : null), [theme, analysis.data])

  if (!cards.data || !analysis.data || !scenarios.data || !catalog.data) return <Loading what="the Partial-Gravity Bridge" />
  const a = analysis.data
  const byId = new Map(cards.data.cards.map((c) => [c.id, c]))
  const nMatch = a.bridge.margin_checks.filter((m) => m.matches).length
  const pg = a.partial_gravity
  const psiPartial = catalog.data.filter((i) => i.gravity_regime === 'partial_gravity').length

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">C · Partial-Gravity Bridge · comparator mode</p>
        <h1 className="text-2xl font-semibold sm:text-3xl">What do we actually know between 0 g and 1 g?</h1>
        <p className="max-w-3xl text-sm text-muted">
          The comparator lines up the evidence that exists at microgravity, lunar, Martian and Earth gravity, flags where measurements are not comparable,
          and keeps the predictor switched off until the data can validate it.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat value={`${psiPartial} of ${catalog.data.length}`} label="NASA PSI combustion investigations at partial gravity" src="PSI catalog (CC0), harvested by IGNIS" />
          <Stat
            value={`${pg.campaigns.length} campaigns`}
            label={`with partial-gravity measurements in the IGNIS ledger, from ${pg.sources.length} sources; longest test ${pg.max_reduced_g_duration_s ?? '?'} s`}
            src={`${pg.n_cards} verified evidence cards · ${pg.n_numeric_measurements} numeric measurements · DERIVED by the IGNIS Core`}
          />
          <Stat value="−5.75 pts O₂" label="most negative oxygen margin: Mylar G, lunar g, 10.2 psia (flame survived a 5.18-s drop)" src="Olson & Ferkul 2012, Table I · recomputed 9/9" />
        </div>
      </header>

      <Section kicker="Measured evidence · drop-tower centrifuge and 1-g tests" title="Upward flammability limits at four gravity levels">
        <p className="text-sm text-muted">
          Points are the midpoint of the limit bracket; whiskers span MOC(*) to ULOI(*). Lower is <em>more</em> flammable. Low-g values (*) come from 5.18 s drop
          tests whose criteria differ from 1-g Test 1.
        </p>
        {limits && <Plot {...limits} ariaLabel="Upward flammability limits of Mylar, Ultem and Nomex versus gravity level" height={380} />}
        <div className="flex flex-wrap items-center gap-3">
          <SourceRef id="NTRS-20130010991" page={6} locator="Table I" />
          <button type="button" className="text-xs underline" onClick={() => setShowTable(!showTable)} aria-expanded={showTable}>
            {showTable ? 'Hide' : 'Show'} table view
          </button>
        </div>
        {showTable && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-muted">
                <tr>
                  <th className="py-1 pr-3">Material</th>
                  <th className="pr-3">Pressure</th>
                  <th className="pr-3">Gravity</th>
                  <th className="pr-3">ULOI(*) % O₂</th>
                  <th className="pr-3">MOC(*) % O₂</th>
                  <th>Data type</th>
                </tr>
              </thead>
              <tbody className="num">
                {rows.map((r) => (
                  <tr key={r.uloiId} className="border-t border-line">
                    <td className="py-1 pr-3 font-sans">{shortName(r.material)}</td>
                    <td className="pr-3">{r.pressure}</td>
                    <td className="pr-3 font-sans">{r.gravityLabel}</td>
                    <td className="pr-3">{r.uloi}</td>
                    <td className="pr-3">{r.moc}</td>
                    <td className="font-sans">MEASURED</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section kicker="E · Standards Stress-Test" title="Is the 1-g screening limit conservative at lower gravity? A finding to investigate">
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <div>
            {margins && <Plot {...margins} ariaLabel="Oxygen margin of safety by gravity level and material" height={320} />}
            <Note>
              ΔO₂ = (ULOI* + MOC*)/2 − (ULOI₁g + MOC₁g)/2 (Eq. 1 of the source). Negative means the material kept burning at lower O₂ than in 1 g. IGNIS recomputed
              every margin from the tabulated limits: <strong className="text-good">✓ {nMatch}/{a.bridge.margin_checks.length} match the published values</strong>. The Fig. 6
              caption's 0-g average (−2.6%) does not match Table I (−1.38%); IGNIS uses the table (see Methods → data quality).
            </Note>
          </div>
          <div className="space-y-2 rounded-md border border-line bg-bg/40 p-3 text-sm">
            <p className="text-xs uppercase tracking-wider text-muted">Hypothesis H2 · verdict</p>
            <p className="font-semibold text-warning">Partially supported</p>
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
              <li>Supported for 3 materials at lunar and Martian g (all 6 margins negative, down to −5.75 percentage points) and for the non-charring Mylar film in 0 g with a 30 cm/s forced flow.</li>
              <li>Not supported for charring Ultem film and Nomex fabric in 0 g (margins +0.25 and −0.3, within the 1% O₂ test step).</li>
              <li>Evidence comes from 5.18 s drop-tower tests only; weak flames might have gone out given more time, so the true low-g limits could be higher.</li>
              <li>The 1-g limits come from a modified Test 1 (hot-wire igniter, limit search), not the standard pass/fail screening.</li>
              <li>Counter-evidence: earlier NASA assessments judged Test 1 conservative for quiescent microgravity (Miller 2004; Golden 2007).</li>
              <li>“More flammable” means a lower O₂ limit, not faster fire growth: LUCI spread rates were lower at lunar g than at 1 g.</li>
            </ul>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {[
            'OF2012-INTERP-NOT-CONSERVATIVE',
            'LPSC2026-TEST1-ASSUMPTION',
            'MILLER2004-TEST1-QUIESCENT',
            'GOLDEN2007-TESTS-CONSERVATIVE',
            'OF2012-MODIFIED-PROTOCOL',
            'OF2012-CAVEAT-CRITERIA',
          ].map((id) => {
            const c = byId.get(id)
            return c ? <FindingCardView key={id} card={c} compact /> : null
          })}
        </div>
      </Section>

      <Section kicker="Physics bridge · MODELED scaling, not a predictor" title="How do microgravity forced-flow tests compare with lunar and Martian convection?">
        {buoy && <Plot {...buoy} ariaLabel="Buoyancy-induced velocity scale versus gravity level with microgravity forced-flow levels" height={340} />}
        <p className="text-sm text-muted">
          In the flame stabilization zone the buoyant velocity scales as u_b ∝ (α·g·β·ΔT)<sup>1/3</sup>. Published 1-g anchors range from 20 cm/s (NASA, 2021) to
          35 cm/s (Konno et al., 2024), which gives{' '}
          <span className="num text-ink">
            {a.bridge.moon.low_cm_s.toFixed(1)}–{a.bridge.moon.high_cm_s.toFixed(1)} cm/s
          </span>{' '}
          on the Moon and{' '}
          <span className="num text-ink">
            {a.bridge.mars.low_cm_s.toFixed(1)}–{a.bridge.mars.high_cm_s.toFixed(1)} cm/s
          </span>{' '}
          on Mars (MODELED). The equivalence is anchor-dependent: Saffire's 20 cm/s forced flow corresponds to anywhere from 0.19 g (35 cm/s anchor) to 1 g
          (20 cm/s anchor). Microgravity tests with forced flows of roughly 10–20 cm/s are the relevant analogs for lunar opposed-flow spread, and only as
          analogs: forced flow is uniform, while buoyant flow accelerates along the flame, and fixed-length systems scale as g<sup>1/2</sup> instead.
        </p>
        <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted">
          {a.bridge.assumptions.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-3">
          <SourceRef id="NTRS-20210020516" page={20} locator="U2 ~ g^(1/3), ≈20 cm/s on Earth" />
          <SourceRef id="DOI-10.1016/j.proci.2024.105199" locator="u ∝ a^(1/3), 35 cm/s at 1 G" />
          <SourceRef id="KAKEN-21K18775" locator="V_b = 33.0 cm/s at 1 G, 21% O₂" />
        </div>
        <Note>
          Cross-check of a spin-simulated platform: LUCI's 11 rpm at 1.22 m radius gives ω²r ={' '}
          <span className="num">{a.bridge.luci_centrifugal_check.g0.toFixed(3)} g</span>, consistent with lunar gravity (0.165 g). <SourceRef id="NTRS-20250010653" page={12} />
        </Note>
      </Section>

      <Section kicker="C.2 · Predictor gate" title="Why the partial-gravity predictor is switched off">
        <p className="text-sm text-muted">
          A model that predicts flammability limits at an arbitrary gravity level is enabled only if all pre-specified criteria (fixed before looking at the results) pass. They are evaluated live from
          the ledger. Status: <strong className="text-critical">{a.gate.status}</strong>.
        </p>
        <ul className="space-y-1">
          {a.gate.checks.map((ch) => (
            <li key={ch.criterion} className="flex flex-wrap items-baseline gap-2 text-sm">
              <StatusPill ok={ch.passed}>{ch.passed === null ? 'not evaluated' : ch.passed ? 'pass' : 'fail'}</StatusPill>
              <span>{ch.criterion}</span>
              {ch.value !== null && <span className="num text-xs text-muted">(best candidate: {ch.value})</span>}
            </li>
          ))}
        </ul>
        {a.gate.best_candidate && (
          <Note>
            Best candidate: {a.gate.best_candidate.variable_family.replace('_', ' ')} for “{a.gate.best_candidate.material_class}”, with partial-g data from{' '}
            {a.gate.best_candidate.partial_g_campaigns.join(' and ')}: two test series from one apparatus and team (NASA GRC drop-tower centrifuge), so they are not
            fully independent. Bayesian experimental design (F.2) depends on this predictor and is therefore also disabled;
            the Gap Radar uses a transparent priority formula instead.
          </Note>
        )}
      </Section>

      <Section kicker="B · Consensus & contradiction (curated)" title="Apparent contradictions, explained by conditions">
        <div className="space-y-4">
          <Contradiction
            title="Is microgravity safer or more dangerous than Earth?"
            a={byId.get('SACK2003-DOWNWARD-U-BOUNDARY')}
            b={byId.get('OF2012-0G-DO2-MYLAR')}
            explanation="Both hold. With little or no flow, low-gravity flames can extinguish through radiative loss (low-g branch of the U-shaped boundary). With a forced flow (here 30 cm/s, which the authors call a reasonable maximum local spacecraft ventilation velocity), the same environment sustained a Mylar flame at lower O₂ than in 1 g. Ventilation, not gravity alone, decides which branch applies."
            verdict="Consistent once flow is accounted for"
          />
          <Contradiction
            title="Does downward flame spread peak at lunar or at Martian gravity?"
            a={byId.get('LPSC2026-MIN-O2-NEAR-LUNAR')}
            b={byId.get('SACK2003-DOWNWARD-PEAK-NEAR-MARS')}
            explanation="The lunar-peak statement cites Sacksteder & T'ien (1994). The closest record in our corpus, the same authors' 1993 NTRS abstract (19930040901), reports aircraft tests at normal pressure with 21% O₂ or less; IGNIS infers, but has not verified, that both describe the same campaign. The Martian-peak observation used 27.6 kPa air and 2-cm Kimwipes. The peak location depends on test conditions, so these results are not directly comparable, and IGNIS does not attempt a quantitative reconciliation."
            verdict="Not comparable · reconciliation UNKNOWN"
          />
        </div>
      </Section>
    </div>
  )
}

function Stat({ value, label, src }: { value: string; label: string; src: string }) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-sm">{label}</p>
      <p className="mt-1 text-[11px] text-muted">{src}</p>
    </div>
  )
}

function Contradiction({ title, a, b, explanation, verdict }: { title: string; a?: FindingCard; b?: FindingCard; explanation: string; verdict: string }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="grid gap-3 md:grid-cols-2">
        {a && <FindingCardView card={a} compact />}
        {b && <FindingCardView card={b} compact />}
      </div>
      <p className="text-sm">
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] uppercase tracking-wider text-muted">IGNIS interpretation · {verdict}</span>{' '}
        <span className="text-muted">{explanation}</span>
      </p>
    </div>
  )
}
