import { useState, type ReactNode } from 'react'
import { useSources } from '../lib/data'
import type { DataType, Epistemic } from '../lib/types'

const DT_STYLE: Record<DataType, string> = {
  MEASURED: 'border-[color:var(--series-1)] text-ink',
  DERIVED: 'border-[color:var(--series-3)] text-ink',
  MODELED: 'border-[color:var(--series-2)] text-ink',
  CONCEPTUAL: 'border-line text-muted',
}
const DT_HELP: Record<DataType, string> = {
  MEASURED: 'Directly measured and reported by the source.',
  DERIVED: 'Computed from measurements (by the source or by the IGNIS Core).',
  MODELED: 'Output of a physical or statistical model.',
  CONCEPTUAL: 'Illustrative or planned; not a quantitative result.',
}
const EP_LABEL: Record<Epistemic, string> = {
  DOCUMENTED_FACT: 'Documented fact',
  SCIENTIFIC_INTERPRETATION: 'Scientific interpretation',
  HYPOTHESIS: 'Hypothesis',
  UNKNOWN: 'Unknown',
}
const EP_ICON: Record<Epistemic, string> = {
  DOCUMENTED_FACT: '■',
  SCIENTIFIC_INTERPRETATION: '◆',
  HYPOTHESIS: '△',
  UNKNOWN: '?',
}

export function DataTypeBadge({ type }: { type: DataType }) {
  return (
    <span
      title={DT_HELP[type]}
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] tracking-wider ${DT_STYLE[type]}`}
    >
      {type}
    </span>
  )
}

export function EpistemicBadge({ value }: { value: Epistemic }) {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink">
      <span aria-hidden="true" className="text-muted">
        {EP_ICON[value]}
      </span>
      {EP_LABEL[value]}
    </span>
  )
}

export function StatusPill({ ok, children }: { ok: boolean | null; children: ReactNode }) {
  const cls = ok === null ? 'text-muted' : ok ? 'text-good' : 'text-critical'
  const icon = ok === null ? '○' : ok ? '✓' : '✕'
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${cls}`}>
      <span aria-hidden="true">{icon}</span>
      {children}
    </span>
  )
}

/** Link to a source in the registry, with page and locator. Shows the title on hover. */
export function SourceRef({ id, page, locator }: { id: string; page?: number | null; locator?: string | null }) {
  const { data: sources } = useSources()
  const s = sources?.get(id)
  const where = [page ? `p. ${page}` : null, locator].filter(Boolean).join(', ')
  const text = s ? `${shortCite(s.authors, s.year, s.title)}${where ? ` · ${where}` : ''}` : id
  return (
    <a
      href={s?.url ?? '#'}
      target="_blank"
      rel="noreferrer"
      title={s ? `${s.title} — ${s.license}` : id}
      className="text-xs text-accent underline decoration-dotted underline-offset-2 hover:decoration-solid"
    >
      {text}
    </a>
  )
}

function shortCite(authors: string[], year: number | null, title: string): string {
  if (authors.length === 0) return title.length > 60 ? `${title.slice(0, 57)}…` : title
  // NTRS lists names as 'Last, First' or 'First M Last'
  const last = (a: string) => (a.includes(',') ? a.split(',')[0].trim() : a.trim().split(/\s+/).pop() ?? a)
  const who = authors.length > 2 ? `${last(authors[0])} et al.` : authors.map(last).join(' & ')
  return `${who}${year ? ` ${year}` : ''}`
}

export function Section({ title, kicker, children, id }: { title: string; kicker?: string; children: ReactNode; id?: string }) {
  return (
    <section id={id} className="space-y-3 rounded-lg border border-line bg-surface p-4 sm:p-5">
      <header className="space-y-1">
        {kicker && <p className="text-[11px] uppercase tracking-[0.16em] text-accent">{kicker}</p>}
        <h2 className="text-lg font-semibold leading-snug">{title}</h2>
      </header>
      {children}
    </section>
  )
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="text-xs leading-relaxed text-muted">{children}</p>
}

export function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded border border-line">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-2"
      >
        {summary}
        <span aria-hidden="true" className="text-muted">
          {open ? '−' : '+'}
        </span>
      </button>
      {open && <div className="border-t border-line px-3 py-2">{children}</div>}
    </div>
  )
}

export function Loading({ what }: { what: string }) {
  return <p className="text-sm text-muted">Loading {what}…</p>
}
