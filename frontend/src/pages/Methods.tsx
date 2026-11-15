import { useQuery } from '@tanstack/react-query'
import { Loading, Note, Section, SourceRef } from '../components/ui'
import { useAnalysis, useDatasets, useScenarios, useSources, useVerification } from '../lib/data'

export default function Methods() {
  const sources = useSources()
  const datasets = useDatasets()
  const verification = useVerification()
  const scenarios = useScenarios()
  const analysis = useAnalysis()
  const evalq = useQuery({
    queryKey: ['copilot-demo'],
    queryFn: async () => {
      const r = await fetch('/data/copilot_demo.json')
      return r.ok ? ((await r.json()) as { summary: Record<string, unknown> }) : null
    },
  })
  if (!sources.data || !datasets.data || !verification.data || !scenarios.data || !analysis.data) return <Loading what="methods and sources" />
  const xc = datasets.data.flex_crosscheck
  const srcs = [...sources.data.values()].sort((a, b) => a.id.localeCompare(b.id))

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">Methods & sources</p>
        <h1 className="text-2xl font-semibold sm:text-3xl">How every number in IGNIS was produced</h1>
        <p className="max-w-3xl text-sm text-muted">
          One command (<code className="font-mono">ignis-pipeline all</code>) downloads the raw sources, checks their sha256 checksums, verifies every Finding Card
          against its source, computes all derived quantities in tested Python, and writes the static bundles this page reads.
        </p>
      </header>

      <Section kicker="Verification" title="Deterministic checks (no language model involved)">
        <ul className="space-y-1 text-sm">
          <li>
            <span className="text-good">✓</span> {verification.data.n_passed}/{verification.data.n_cards} Finding Cards: verbatim quote found on the cited page (or NTRS
            abstract for 3 metadata-only sources), and every number of the card's value present in the quote.
          </li>
          <li>
            <span className="text-good">✓</span> {analysis.data.bridge.margin_checks.filter((m) => m.matches).length}/{analysis.data.bridge.margin_checks.length} oxygen
            margins in Olson & Ferkul (2012) Table I reproduced from the tabulated limits with their Eq. (1).
          </li>
          {xc && (
            <li>
              <span className="text-good">✓</span> FLEX droplet tests: {xc.n_compared} PSI CSV rows matched to the printed tables of NASA/TP-2015-216046 by {xc.join_key};{' '}
              {xc.n_identical}/{xc.n_compared} identical on 7 numeric fields. {xc.only_in_csv.length} CSV rows and {xc.only_in_tp.length} TP rows could not be matched by
              the parser and are reported, not hidden.
            </li>
          )}
          <li>
            <span className="text-good">✓</span> {scenarios.data.filter((s) => s.verification === 'quote verified').length} mission-atmosphere values verified against
            NASA documents; {scenarios.data.filter((s) => s.provenance === null).length} scenario left UNKNOWN (no source found).
          </li>
          <li>
            <span className="text-good">✓</span> LUCI spin check: 11 rpm at 1.22 m gives {analysis.data.bridge.luci_centrifugal_check.g0.toFixed(3)} g ≈ lunar gravity.
          </li>
        </ul>
      </Section>

      {evalq.data && <EvalSection summary={evalq.data.summary} />}

      <Section kicker="Formulas" title="Scientific Core">
        <dl className="space-y-3 text-sm">
          <Formula name="Oxygen margin (Olson & Ferkul 2012, Eq. 1)" f="ΔO₂ = (ULOI* + MOC*)/2 − (ULOI₁g + MOC₁g)/2" />
          <Formula name="Buoyant velocity scale (NASA 2021, NTRS 20210020516; Konno et al. 2024; Nakaya, KAKEN 21K18775)" f="u_b(g) = u_b(1 g) · (g/g₀)^(1/3), u_b(1 g) ∈ [20, 35] cm/s across sources (thermal-length scaling; fixed-length systems scale as g^(1/2))" />
          <Formula name="Spin gravity" f="g/g₀ = (2π·rpm/60)² · r / 9.80665" />
          <Formula name="O₂ partial pressure (Dalton)" f="pO₂ = X_O₂ · p" />
          <Formula name="Evidence ranking" f="S = (M^a · E^b · R^c)^(1/(a+b+c)); E = w_type·w_epistemic·w_confidence; R = 1 − e^(−n/2)" />
          <Formula name="Gap priority" f="P = max_s R_s(cell) × 1/(1 + n_campaigns) × D × F (D = 0.5 if ≥60 s evidence exists; F = 0.5 if a documented planned experiment targets the cell)" />
        </dl>
        <Note>
          Weights: MEASURED 1.0, DERIVED 0.9, MODELED 0.6, CONCEPTUAL 0.3; documented fact 1.0, interpretation 0.8, hypothesis 0.5, unknown 0.3; confidence high 1.0,
          medium 0.8, low 0.6. Kernel widths σ_g = 0.05 g, σ_O₂ = 4 points, σ_ln p = 0.35. These are documented design choices, not fitted parameters. Units are
          converted with pint and covered by property-based tests.
        </Note>
      </Section>

      <Section kicker="Data quality" title="Problems found in the sources, and what IGNIS did">
        <ul className="space-y-2 text-sm">
          {datasets.data.quality_log.map((q) => (
            <li key={q.dataset + q.issue} className="rounded-md border border-line p-2">
              <p className="font-medium">{q.dataset}</p>
              <p className="text-muted">{q.issue}</p>
              <p>
                <span className="text-muted">Action: </span>
                {q.action}
              </p>
              <p className="text-xs text-muted">Evidence: {q.evidence}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section kicker="Limitations" title="What this evidence base cannot tell you">
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
          <li>The ledger is curated for partial-gravity fire safety; it is not an exhaustive review of all combustion literature.</li>
          <li>Most partial-gravity limits come from 5 s drop tests or ~25 s aircraft parabolas; only LUCI (spin-simulated, one flight) lasted longer, about 150 s.</li>
          <li>Paywalled papers are used as metadata and short quotes only; their full text is not indexed or redistributed.</li>
          <li>The buoyant-velocity bridge is an order-of-magnitude scaling, not a flow model and not a predictor.</li>
          <li>Ranking and gap-priority weights are judgment calls, shown openly so they can be challenged.</li>
          <li>No numeric fire probability is computed anywhere in IGNIS.</li>
        </ul>
      </Section>

      <Section kicker="Sources" title={`${srcs.length} sources cited by this build`}>
        <ul className="space-y-1 text-xs">
          {srcs.map((s) => (
            <li key={s.id} className="flex flex-wrap gap-x-2">
              <span className="num text-muted">{s.id}</span>
              <SourceRef id={s.id} />
              <span className="text-muted">— {s.title}</span>
              <span className="text-muted">[{s.license}{s.full_text_indexed ? ', full text indexed' : ''}]</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section kicker="Use of AI (SI) tools" title="Disclosure">
        <p className="text-sm text-muted">
          The IGNIS code base, pipeline and documentation were written with the assistance of an AI coding agent (Claude Code) under human direction; the project
          idea and research questions are the team's. Finding Cards were drafted with AI assistance and accepted only after the deterministic quote and number
          checks above. Language models never compute scientific values in IGNIS.
        </p>
      </Section>
    </div>
  )
}

function Formula({ name, f }: { name: string; f: string }) {
  return (
    <div>
      <dt className="text-muted">{name}</dt>
      <dd className="mt-0.5 rounded bg-surface-2 px-2 py-1 font-mono text-xs">{f}</dd>
    </div>
  )
}

type Ci = [number, number, number] | null

function EvalSection({ summary }: { summary: Record<string, unknown> }) {
  const row = (label: string, key: string, help: string) => {
    const v = summary[key] as Ci
    return (
      <tr className="border-t border-line">
        <td className="py-1.5 pr-3">{label}</td>
        <td className="num pr-3">{v ? v[0].toFixed(2) : '—'}</td>
        <td className="num pr-3 text-muted">{v ? `[${v[1].toFixed(2)}, ${v[2].toFixed(2)}]` : ''}</td>
        <td className="text-muted">{help}</td>
      </tr>
    )
  }
  return (
    <Section kicker="Copilot evaluation" title={`Golden set: ${String(summary.n_questions)} questions, ${String(summary.mode)} mode`}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th className="py-1 pr-3">Metric</th>
              <th className="pr-3">Value</th>
              <th className="pr-3">Wilson 95% CI</th>
              <th>Meaning</th>
            </tr>
          </thead>
          <tbody>
            {row('Abstention accuracy', 'abstention_accuracy', 'abstains exactly when the corpus cannot answer')}
            {row('Injection resistance', 'injection_resistance', 'never asserts the false claim requested by an adversarial question')}
            {row('Citation correctness', 'citation_correctness', 'kept sentences citing an expected source or Core tool')}
            {row('Verified (entailed)', 'verified_rate', 'drafted sentences entailed by the cited text')}
            {row('Downgraded to hypothesis', 'downgraded_rate', 'kept but not entailed by the cited text')}
            {row('Removed', 'removed_rate', 'invented citation, untraceable number or contradiction')}
            {row('Retrieval recall@8', 'retrieval_recall_at_8', 'an expected source is among the retrieved passages')}
          </tbody>
        </table>
      </div>
      <Note>
        Model(s): {String((summary.providers as string[] | undefined)?.join(', ') ?? '')} · median latency {String(summary.median_latency_s)} s · run{' '}
        {String(summary.run_at)}. Small sample: intervals are wide. Errors go both ways: the validator sometimes removes a correct sentence when the cited passage words
        a number differently, and in a manual audit 9 of 10 VERIFIED sentences were correct (one dropped a qualifier). A known false verification
        attributed a three-material average to one material. Treat VERIFIED as strong support, not proof.
      </Note>
    </Section>
  )
}
