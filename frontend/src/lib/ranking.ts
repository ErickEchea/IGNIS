// Mirror of ignis.core.analysis.weighted_geometric_score and ignis.core.analysis.priority.
// The factors themselves are computed in Python; the browser only combines them so the user can
// move weights interactively. Parity with Python is enforced by ranking.test.ts.

export type Weights = Record<string, number>

function round6(x: number): number {
  return Math.round(x * 1e6) / 1e6
}

export function weightedGeometricScore(factors: Record<string, number>, weights: Weights): number {
  const total = Object.values(weights).reduce((a, b) => a + b, 0)
  if (total <= 0) return 0
  let logSum = 0
  for (const [k, w] of Object.entries(weights)) {
    const f = factors[k]
    if (f === undefined || f <= 0) return 0
    logSum += w * Math.log(f)
  }
  return round6(Math.exp(logSum / total))
}

export interface PriorityCell {
  relevance: Record<string, number>
  scarcity: number
  duration_factor: number
}

/** P = max_s R_s(cell) x 1/(1 + n_campaigns) x D */
export function priority(cell: PriorityCell, scenarioIds: string[]): number {
  if (scenarioIds.length === 0) return 0
  const r = Math.max(...scenarioIds.map((s) => cell.relevance[s] ?? 0))
  return round6(r * cell.scarcity * cell.duration_factor)
}
