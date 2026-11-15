// Optional live backend. The static site works without it; VITE_API_BASE points at the deployed API.
export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''
// Live Copilot only in development (Vite proxies /api) or when a backend URL is configured.
export const LIVE_BACKEND: boolean = import.meta.env.DEV || API_BASE !== ''

export type Mode = 'AUTO' | 'CLOUD' | 'LOCAL' | 'NONE'

export interface CopilotSentence {
  text: string
  citations: string[]
  category_in: string
  category_out: string
  verdict: 'VERIFIED' | 'DOWNGRADED' | 'REMOVED' | 'UNCHECKED'
  checks: Record<string, boolean | null>
  reasons: string[]
  entailment: number | null
}

export interface CopilotAnswer {
  question: string
  mode: Mode
  status: 'ANSWERED' | 'ABSTAINED' | 'NO_LLM'
  message: string | null
  provider: { name: string; model: string; latency_s: number; fallback_used: boolean } | null
  attempts: { provider: string; model: string; ok: boolean; error_kind: string | null; message: string | null }[]
  sentences: CopilotSentence[]
  validation?: { VERIFIED: number; DOWNGRADED: number; REMOVED: number; UNCHECKED: number; nli_available: boolean }
  evidence: { label: string; chunk_id: string; source_id: string; page: number | null; kind: string; text: string; url: string | null }[]
  tools: { label: string; name: string; text: string; data_type: string }[]
  retrieval: { dense_available: boolean; n_hits: number; injection_flagged: string[] }
  latency_s: number
  eval_id?: string
  run_at?: string
}

export async function askCopilot(question: string, mode: Mode, signal?: AbortSignal): Promise<CopilotAnswer> {
  const res = await fetch(`${API_BASE}/api/copilot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, mode }),
    signal,
  })
  if (!res.ok) throw new Error(`Copilot API error ${res.status}`)
  return (await res.json()) as CopilotAnswer
}

export async function getStatus(signal?: AbortSignal): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/status`, { signal })
  if (!res.ok) throw new Error(`Status API error ${res.status}`)
  return (await res.json()) as Record<string, unknown>
}
