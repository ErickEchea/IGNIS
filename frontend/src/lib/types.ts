// Types of the static bundles produced by `ignis-pipeline build` (backend/src/ignis/pipeline/build.py).

export type DataType = 'MEASURED' | 'DERIVED' | 'MODELED' | 'CONCEPTUAL'
export type Epistemic = 'DOCUMENTED_FACT' | 'SCIENTIFIC_INTERPRETATION' | 'HYPOTHESIS' | 'UNKNOWN'

export interface Quantity {
  value: number
  unit: string
  dimension: string
  uncertainty: number | null
  uncertainty_kind: string
  value_si: number
  uncertainty_si: number | null
}

export interface Provenance {
  source_id: string
  page: number | null
  locator: string | null
  quote: string
  extraction: string
  verified_by: string | null
  verified_at: string | null
}

export interface FindingCard {
  id: string
  claim: string
  material: string
  material_class: string
  geometry: string
  thickness: Quantity | null
  o2: Quantity | null
  pressure: Quantity | null
  flow_velocity: Quantity | null
  flow_direction: string
  gravity: Quantity | null
  gravity_range_g0: [number, number] | null
  gravity_lo: number
  gravity_hi: number
  platform: string
  reduced_gravity_duration_s: number | null
  measured_variable: string
  value: Quantity | null
  comparison_1g: Quantity | null
  data_type: DataType
  epistemic: Epistemic
  confidence: 'high' | 'medium' | 'low'
  confidence_rationale: string
  caveats: string[]
  campaign_id: string
  tags: string[]
  provenance: Provenance
}

export interface Source {
  id: string
  title: string
  authors: string[]
  year: number | null
  url: string
  doi: string | null
  license: string
  full_text_indexed: boolean
  raw_path: string | null
  sha256: string | null
}

export interface Scenario {
  id: string
  name: string
  gravity_g0: number | null
  gravity_note: string
  pressure: { value: number; unit: string } | null
  o2_percent: number | null
  unknown_note: string | null
  provenance: { source_id: string; page: number | null; quote: string } | null
  derived: { pressure_kpa: number | null; o2_mole_fraction: number | null; o2_partial_pressure_kpa: number | null }
  verification: string
}

export interface PsiInvestigation {
  accession: string
  acronym: string
  title: string
  project_type: string
  platform: string
  hardware: string
  sub_area: string
  start_date: string
  end_date: string
  objective: string
  doi: string
  license: string
  total_file_size_bytes: number
  n_publications: number
  people: { name: string; role: string; affiliation: string }[]
  tables: string[]
  url: string
  gravity_regime: string
}

export interface GapCell {
  g: number
  o2: number
  pressure: string
  n_campaigns: number
  n_points: number
  campaigns: string[]
  max_duration_s: number | null
  long_duration_evidence: boolean
  scarcity: number
  duration_factor: number
  relevance: Record<string, number>
  planned: string[]
  planned_factor: number
  refs: string[]
}

export interface NextExperiment {
  gravity_bin: string
  o2_bin: string
  pressure_class: string
  priority: number
  relevance: number
  scarcity: number
  duration_factor: number
  closest_scenario: { id: string; name: string }
  existing_campaigns: string[]
  already_planned: string[]
  planned_factor: number
  platform: string
  platform_rationale: string
  hypothesis: string
  measure: string
}

export interface GateCheck {
  criterion: string
  value: number | null
  passed: boolean | null
}

export interface Analysis {
  built_at: string
  ranking: Record<string, { E: number; R: number; n_campaigns_same_family: number; M: Record<string, number> }>
  ranking_constants: Record<string, unknown>
  comparability: Record<string, string[]>
  gaps: {
    gravity_bins: string[]
    o2_bins: string[]
    pressure_classes: string[]
    long_duration_s: number
    solid: { fuel_class: string; cells: GapCell[]; unplaced_points: number }
    droplet: { fuel_class: string; cells: GapCell[]; unplaced_points: number }
  }
  next_experiments: NextExperiment[]
  partial_gravity: {
    n_cards: number
    campaigns: string[]
    sources: string[]
    platforms: string[]
    material_classes: string[]
    single_gravity_levels: number[]
    gravity_ranges: [number, number][]
    max_reduced_g_duration_s: number | null
    n_numeric_measurements: number
  }
  gate: {
    enabled: boolean | null
    status: string
    best_candidate: {
      variable_family: string
      material_class: string
      n_points: number
      n_partial_g_points: number
      n_partial_g_campaigns: number
      partial_g_campaigns: string[]
    } | null
    checks: GateCheck[]
  }
  bridge: {
    buoyancy_curve: { g: number; low_cm_s: number; high_cm_s: number }[]
    anchor_cm_s: [number, number]
    anchor_sources: string[]
    assumptions: string[]
    moon: { gravity_g0: number; low_cm_s: number; high_cm_s: number; ratio_to_1g: number }
    mars: { gravity_g0: number; low_cm_s: number; high_cm_s: number; ratio_to_1g: number }
    flow_analogs: {
      ref: string
      label: string
      flow_cm_s: number
      equiv_g_low: number
      equiv_g_high: number
      kind: string
    }[]
    margin_checks: {
      material: string
      gravity_g0: number
      computed: number
      reported: number | null
      matches: boolean | null
      card_ids: string[]
    }[]
    luci_centrifugal_check: { rpm: number; radius_m: number; g0: number; source: string }
  }
}

export interface Datasets {
  flex_crosscheck: {
    source_a: string
    source_b: string
    join_key: string
    n_csv: number
    n_tp: number
    n_compared: number
    n_identical: number
    only_in_tp: number[]
    only_in_csv: number[]
  } | null
  quality_log: { dataset: string; issue: string; action: string; evidence: string }[]
  flex: Record<string, unknown>[]
  bass2: Record<string, unknown>[]
  saffire: Record<string, unknown>[]
}

export interface Verification {
  n_cards: number
  n_passed: number
  results: { card_id: string; passed: boolean; quote_on_page: boolean | null; numbers_in_quote: boolean; messages: string[] }[]
}
