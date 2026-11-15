import type { FindingCard, Quantity } from './types'

export function fmtNum(x: number, digits = 3): string {
  if (!Number.isFinite(x)) return '∞'
  const abs = Math.abs(x)
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e5)) return x.toExponential(2)
  return Number(x.toPrecision(digits)).toString()
}

/** Display a quantity exactly as written in the source (value + original unit). */
export function fmtQty(q: Quantity | null): string {
  if (!q) return '—'
  const unit = q.unit === '%' ? '% O₂' : q.unit === 'g' ? 'g' : q.unit
  const unc = q.uncertainty != null ? ` ± ${q.uncertainty}` : ''
  return `${q.value}${unc} ${unit}`
}

export function fmtGravity(c: FindingCard): string {
  if (c.gravity) return `${c.gravity.value} g`
  if (c.gravity_range_g0) return `${c.gravity_range_g0[0]}–${c.gravity_range_g0[1]} g`
  return '—'
}

export const PLATFORM_LABEL: Record<string, string> = {
  ISS: 'ISS',
  Cygnus_Saffire: 'Cygnus (Saffire)',
  Space_Shuttle: 'Space Shuttle',
  Skylab: 'Skylab',
  drop_tower: 'Drop tower',
  drop_tower_centrifuge: 'Drop-tower centrifuge',
  parabolic_flight: 'Parabolic flight',
  suborbital_spin: 'Spinning suborbital (New Shepard)',
  sounding_rocket: 'Sounding rocket',
  centrifuge: 'Centrifuge',
  ground_1g: 'Ground (1 g)',
  reduced_pressure_analog: 'Reduced-pressure analog',
  lunar_surface: 'Lunar surface',
  model: 'Model / review',
}

export const VARIABLE_LABEL: Record<string, string> = {
  upward_limiting_oxygen_index: 'Upward limiting O₂ index',
  maximum_oxygen_concentration: 'Maximum O₂ concentration',
  oxygen_margin_of_safety: 'O₂ margin of safety',
  flame_spread_rate: 'Flame spread rate',
  flame_tip_spread_rate: 'Flame-tip spread rate',
  flame_spread_rate_trend: 'Spread-rate trend vs g',
  flame_spread_rate_peak_location: 'Spread-rate peak vs g',
  flammability_boundary_shape: 'Flammability boundary shape',
  flammable_domain_comparison: 'Flammable domain',
  limiting_oxygen_index_model: 'Limiting O₂ index (model)',
  chamber_o2_minimum_during_burn: 'Chamber O₂ during burn',
  burn_duration_difference: 'Burn duration difference',
  interpretation: 'Interpretation',
  methodological_limitation: 'Methodological limitation',
  test_condition: 'Test condition',
  evidence_gap_statement: 'Evidence-gap statement',
  test_duration_record: 'Test duration',
  planned_experiment: 'Planned experiment',
  test_matrix: 'Test matrix',
  hazard_expectation: 'Hazard expectation',
}

export function label(map: Record<string, string>, key: string): string {
  return map[key] ?? key.replace(/_/g, ' ')
}
