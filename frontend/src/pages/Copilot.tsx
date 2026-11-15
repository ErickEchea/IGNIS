import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Note, Section, SourceRef } from '../components/ui'
import { askCopilot, LIVE_BACKEND, type CopilotAnswer, type Mode } from '../lib/api'

const EXAMPLES = [
  'What were the Martian-gravity MOC* values for Mylar, Ultem and Nomex?',
  'Are NASA-STD-6001 Test 1 flammability limits conservative at lunar gravity?',
  'How did the SIBAL fabric flame spread rate in lunar gravity compare with 1 g in LUCI?',
  'What is the characteristic buoyant flow velocity on Mars?',
  'Why is the downward flame spread flammability boundary U-shaped versus gravity?',
  'What is the probability of a fire in a Mars surface habitat during a 500-day mission?',
]
const CAT_LABEL: Record<string, string> = {
  DOCUMENTED_FACT: '■ Documented fact',
  SCIENTIFIC_INTERPRETATION: '◆ Interpretation',
  HYPOTHESIS: '△ Hypothesis',
  UNKNOWN: '? Unknown',
}

function useDemo() {
  return useQuery({
    queryKey: ['copilot-demo'],
    queryFn: async () => {
      const r = await fetch('/data/copilot_demo.json')
      if (!r.ok) return null
      return (await r.json()) as { summary: Record<string, unknown>; answers: CopilotAnswer[] }
    },
  })
}

export default function Copilot() {
  const demo = useDemo()
  const [q, setQ] = useState(EXAMPLES[0])
  const [mode, setMode] = useState<Mode>('AUTO')
  const [answer, setAnswer] = useState<CopilotAnswer | null>(null)
  const [busy, setBusy] = useState(false)
  const [offline, setOffline] = useState(false)
  const [noDemo, setNoDemo] = useState(false)

  const fromDemo = (question: string) => demo.data?.answers.find((a) => a.question === question) ?? null

  async function ask(question: string) {
    if (!LIVE_BACKEND) {
      const a = fromDemo(question)
      setAnswer(a)
      setNoDemo(a === null)
      return
    }
    setBusy(true)
    setAnswer(null)
    try {
      const a = await askCopilot(question, mode, AbortSignal.timeout(120_000))
      setOffline(false)
      setAnswer(a)
    } catch {
      setOffline(true)
      setAnswer(fromDemo(question))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (demo.data && !answer) setAnswer(fromDemo(EXAMPLES[0]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo.data])

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">G · Scientific Copilot</p>
        <h1 className="text-2xl font-semibold sm:text-3xl">Ask the evidence, not the model</h1>
        <p className="max-w-3xl text-sm text-muted">
          Answers are drafted by a language model from retrieved NASA documents and Core calculations, then checked sentence by sentence by the Scientific
          Evidence Validator. Unsupported sentences are removed or downgraded, and you see why.
        </p>
      </header>

      <Section kicker="Question" title="What do you want to know?">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (q.trim().length >= 3) void ask(q.trim())
          }}
          className="space-y-3"
        >
          <label className="block">
            <span className="sr-only">Question</span>
            <textarea
              value={q}
              onChange={(e) => setQ(e.target.value)}
              rows={2}
              maxLength={600}
              className="w-full rounded-md border border-line bg-surface-2 px-3 py-2 text-sm"
            />
          </label>
          <div className="flex flex-wrap items-center gap-2">
            <button type="submit" disabled={busy} className="rounded-md bg-accent px-4 py-1.5 text-sm font-medium text-[#1b1d20] disabled:opacity-50">
              {busy ? 'Checking evidence…' : 'Ask'}
            </button>
            <label className={`text-xs text-muted ${LIVE_BACKEND ? '' : 'hidden'}`}>
              Model routing{' '}
              <select value={mode} onChange={(e) => setMode(e.target.value as Mode)} className="ml-1 rounded border border-line bg-surface-2 px-1.5 py-1 text-xs text-ink">
                <option value="AUTO">AUTO (Gemini → Ollama → none)</option>
                <option value="CLOUD">CLOUD (Gemini only)</option>
                <option value="LOCAL">LOCAL (Ollama only)</option>
                <option value="NONE">NONE (evidence only)</option>
              </select>
            </label>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(LIVE_BACKEND ? EXAMPLES : (demo.data?.answers.map((a) => a.question) ?? EXAMPLES)).map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQ(ex)
                  void ask(ex)
                }}
                className="rounded-full border border-line px-2.5 py-1 text-left text-xs text-muted hover:text-ink"
              >
                {ex}
              </button>
            ))}
          </div>
        </form>
      </Section>

      {!LIVE_BACKEND && (
        <p role="note" className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
          <span className="text-ink">Static deployment.</span> This public site runs without a backend, so it shows the precomputed answers that the
          validated pipeline produced for the {demo.data?.answers.length ?? 25} golden-set questions above (model and date on each answer). Run IGNIS locally
          with Gemini or Ollama for live answers to new questions.
        </p>
      )}

      {noDemo && !LIVE_BACKEND && (
        <p role="status" className="rounded-md border border-warning px-3 py-2 text-sm">
          <span className="text-warning">No precomputed answer for this question.</span> The static deployment only holds answers to the golden-set questions
          listed above; IGNIS shows nothing rather than inventing one.
        </p>
      )}

      {offline && LIVE_BACKEND && (
        <p role="status" className="rounded-md border border-warning px-3 py-2 text-sm">
          <span className="text-warning">Live backend unreachable.</span>{' '}
          {answer
            ? `Showing a precomputed answer produced by the same pipeline (${answer.provider?.model ?? 'no model'}, ${answer.run_at ?? ''}). It is not regenerated.`
            : 'No precomputed answer exists for this question, so IGNIS shows nothing rather than inventing one.'}
        </p>
      )}

      {answer && <AnswerView a={answer} />}

      {demo.data && (
        <Note>
          Golden-set evaluation ({String(demo.data.summary.n_questions)} questions, {String(demo.data.summary.mode)} mode,{' '}
          {String((demo.data.summary.providers as string[]).join(', '))}): see Methods for metrics with 95% intervals.
        </Note>
      )}
    </div>
  )
}

function AnswerView({ a }: { a: CopilotAnswer }) {
  const kept = a.sentences.filter((s) => s.verdict !== 'REMOVED')
  const removed = a.sentences.filter((s) => s.verdict === 'REMOVED')
  const statusText = { ANSWERED: 'Answered with validated citations', ABSTAINED: 'Abstained', NO_LLM: 'No language model: evidence only' }[a.status]
  return (
    <Section kicker="Answer" title={statusText}>
      <div className="flex flex-wrap gap-2 text-xs">
        {a.provider ? (
          <span className="rounded bg-surface-2 px-2 py-1">
            Model: <span className="font-mono">{a.provider.name} · {a.provider.model}</span> · {a.provider.latency_s}s
            {a.provider.fallback_used && <span className="text-warning"> · fallback used</span>}
          </span>
        ) : (
          <span className="rounded bg-surface-2 px-2 py-1">Model: none</span>
        )}
        {a.attempts
          .filter((t) => !t.ok)
          .map((t) => (
            <span key={t.provider} className="rounded border border-warning px-2 py-1 text-warning">
              {t.provider} failed: {t.error_kind}
            </span>
          ))}
        {a.validation && (
          <span className="rounded bg-surface-2 px-2 py-1">
            Validator: {a.validation.VERIFIED} verified · {a.validation.DOWNGRADED} downgraded · {a.validation.REMOVED} removed
            {a.validation.UNCHECKED ? ` · ${a.validation.UNCHECKED} unchecked` : ''}
            {!a.validation.nli_available && ' · NLI unavailable'}
          </span>
        )}
        <span className="rounded bg-surface-2 px-2 py-1">Retrieval: {a.retrieval.dense_available ? 'BM25 + embeddings + rerank' : 'BM25 only'}</span>
        {a.retrieval.injection_flagged.length > 0 && (
          <span className="rounded border border-critical px-2 py-1 text-critical">
            {a.retrieval.injection_flagged.length} retrieved passage(s) withheld: instruction-like content
          </span>
        )}
      </div>
      {a.message && <p className="text-sm text-muted">{a.message}</p>}
      {kept.length > 0 && (
        <ol className="space-y-2">
          {kept.map((s, i) => (
            <li key={i} className="rounded-md border border-line bg-bg/40 p-3 text-sm">
              <p>{s.text.replace(/\s*\[[ST]\d+(?:\s*,\s*[ST]\d+)*\]/g, '')}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                <span className="rounded bg-surface-2 px-1.5 py-0.5">{CAT_LABEL[s.category_out] ?? s.category_out}</span>
                {s.citations.map((c) => (
                  <a key={c} href={`#ev-${c}`} className="font-mono text-accent underline decoration-dotted">
                    [{c}]
                  </a>
                ))}
                <span className={s.verdict === 'VERIFIED' ? 'text-good' : s.verdict === 'DOWNGRADED' ? 'text-warning' : 'text-muted'}>
                  {s.verdict === 'VERIFIED' ? '✓ verified' : s.verdict === 'DOWNGRADED' ? '△ downgraded' : '○ unchecked'}
                  {s.entailment != null && ` (entailment ${s.entailment.toFixed(2)})`}
                </span>
                {s.reasons.length > 0 && <span className="text-muted">{s.reasons.join('; ')}</span>}
              </div>
            </li>
          ))}
        </ol>
      )}
      {removed.length > 0 && (
        <details className="rounded-md border border-line p-3 text-sm">
          <summary className="cursor-pointer text-muted">{removed.length} sentence(s) removed by the Validator</summary>
          <ul className="mt-2 space-y-1">
            {removed.map((s, i) => (
              <li key={i}>
                <span className="line-through opacity-70">{s.text}</span> <span className="text-xs text-critical">— {s.reasons.join('; ')}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {a.tools.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wider text-muted">Scientific Core calculations</p>
          {a.tools.map((t) => (
            <p id={`ev-${t.label}`} key={t.label} className="rounded bg-surface-2 px-2 py-1 font-mono text-xs">
              [{t.label}] {t.text}
            </p>
          ))}
        </div>
      )}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wider text-muted">Retrieved evidence (verbatim)</p>
        <ul className="space-y-2">
          {a.evidence.map((e) => (
            <li id={`ev-${e.label}`} key={e.label} className="rounded-md border border-line p-2 text-xs">
              <div className="mb-1 flex flex-wrap gap-2">
                <span className="font-mono text-accent">[{e.label}]</span>
                <SourceRef id={e.source_id} page={e.page} locator={e.kind === 'card' ? 'Finding Card' : undefined} />
              </div>
              <p className="text-muted">{e.text.length > 600 ? `${e.text.slice(0, 600)}…` : e.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </Section>
  )
}
