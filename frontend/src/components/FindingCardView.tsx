import { fmtGravity, fmtQty, label, PLATFORM_LABEL, VARIABLE_LABEL } from '../lib/format'
import type { FindingCard } from '../lib/types'
import { DataTypeBadge, EpistemicBadge, SourceRef } from './ui'

interface Props {
  card: FindingCard
  why?: string
  score?: number
  notes?: string[]
  compact?: boolean
}

export function FindingCardView({ card, why, score, notes, compact }: Props) {
  return (
    <article className="space-y-2 rounded-md border border-line bg-bg/40 p-3" aria-labelledby={`c-${card.id}`}>
      <div className="flex flex-wrap items-center gap-1.5">
        <DataTypeBadge type={card.data_type} />
        <EpistemicBadge value={card.epistemic} />
        <span className="text-[11px] text-muted">confidence: {card.confidence}</span>
        {score !== undefined && (
          <span className="ml-auto font-mono text-xs text-muted" title="Ranking score S">
            S = {score.toFixed(3)}
          </span>
        )}
      </div>
      <p id={`c-${card.id}`} className="text-sm leading-relaxed">
        {card.claim}
      </p>
      {why && <p className="text-xs text-accent">{why}</p>}
      {!compact && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
          <Field k="Gravity" v={fmtGravity(card)} />
          <Field k="Platform" v={label(PLATFORM_LABEL, card.platform)} />
          <Field k="Variable" v={label(VARIABLE_LABEL, card.measured_variable)} />
          <Field k="Value" v={fmtQty(card.value)} />
          {card.comparison_1g && <Field k="Same source, 1 g" v={fmtQty(card.comparison_1g)} />}
          {card.pressure && <Field k="Pressure" v={fmtQty(card.pressure)} />}
          {card.o2 && <Field k="O₂" v={fmtQty(card.o2)} />}
          {card.flow_velocity && <Field k="Forced flow" v={`${fmtQty(card.flow_velocity)} (${card.flow_direction})`} />}
          {card.reduced_gravity_duration_s != null && <Field k="Low-g time" v={`${card.reduced_gravity_duration_s} s`} />}
          <Field k="Material" v={card.material} />
        </dl>
      )}
      <blockquote className="border-l-2 border-line pl-3 text-xs italic text-muted">
        “{card.provenance.quote}”
      </blockquote>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <SourceRef id={card.provenance.source_id} page={card.provenance.page} locator={card.provenance.locator} />
        <span className="text-[11px] text-muted" title="Deterministic check: quote found on the cited page and every number of the value present in the quote">
          ✓ quote verified on page
        </span>
      </div>
      {!compact && (card.caveats.length > 0 || (notes && notes.length > 0)) && (
        <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted">
          {card.caveats.map((c) => (
            <li key={c}>{c}</li>
          ))}
          {notes?.map((n) => (
            <li key={n}>
              <span className="text-warning">Comparability:</span> {n}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted">{k}</dt>
      <dd className="num truncate text-ink" title={v}>
        {v}
      </dd>
    </div>
  )
}
