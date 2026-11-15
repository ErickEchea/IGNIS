import { useQuery } from '@tanstack/react-query'
import { Loading, Note, Section } from '../components/ui'
import { API_BASE, getStatus, LIVE_BACKEND } from '../lib/api'
import { useCards, useCatalog } from '../lib/data'

export default function System() {
  const status = useQuery({
    queryKey: ['status'],
    queryFn: ({ signal }) => getStatus(signal),
    retry: 0,
    refetchInterval: 30_000,
    enabled: LIVE_BACKEND,
  })
  const cards = useCards()
  const catalog = useCatalog()
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">System</p>
        <h1 className="text-2xl font-semibold">AI system status</h1>
      </header>
      <Section kicker="Static layer" title="Always available">
        <p className="text-sm">
          Evidence Explorer, Partial-Gravity Bridge, Gap Radar and Methods run from precomputed, verified bundles: {cards.data?.cards.length ?? '…'} Finding
          Cards, {catalog.data?.length ?? '…'} PSI investigations (built {cards.data?.built_at ?? '…'}).
        </p>
      </Section>
      <Section kicker="Live layer" title={`Backend ${API_BASE || '(same origin)'}`}>
        {!LIVE_BACKEND ? (
          <p className="text-sm">
            Static deployment: no backend is configured. The Copilot shows precomputed answers from the validated pipeline; run the backend locally for
            live answers (see docs/DEPLOY.md).
          </p>
        ) : status.isLoading ? (
          <Loading what="backend status" />
        ) : status.isError ? (
          <p className="text-sm">
            <span className="text-warning">Unreachable.</span> The Copilot falls back to precomputed answers; everything else keeps working.
          </p>
        ) : (
          <pre className="overflow-x-auto rounded bg-surface-2 p-3 font-mono text-xs">{JSON.stringify(status.data, null, 2)}</pre>
        )}
        <Note>No API keys or secrets are ever sent to the browser; providers are configured only in the backend environment.</Note>
      </Section>
    </div>
  )
}
