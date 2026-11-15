import { useQuery } from '@tanstack/react-query'
import type {
  Analysis,
  Datasets,
  FindingCard,
  PsiInvestigation,
  Scenario,
  Source,
  Verification,
} from './types'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`/data/${path}`)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return (await res.json()) as T
}

export function useCards() {
  return useQuery({
    queryKey: ['cards'],
    queryFn: () => getJson<{ built_at: string; cards: FindingCard[] }>('cards.json'),
  })
}

export function useSources() {
  return useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      const d = await getJson<{ sources: Source[] }>('sources.json')
      return new Map(d.sources.map((s) => [s.id, s]))
    },
  })
}

export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: async () => (await getJson<{ scenarios: Scenario[] }>('scenarios.json')).scenarios,
  })
}

export function useAnalysis() {
  return useQuery({ queryKey: ['analysis'], queryFn: () => getJson<Analysis>('analysis.json') })
}

export function useCatalog() {
  return useQuery({
    queryKey: ['catalog'],
    queryFn: async () =>
      (await getJson<{ investigations: PsiInvestigation[] }>('psi_catalog.json')).investigations,
  })
}

export function useDatasets() {
  return useQuery({ queryKey: ['datasets'], queryFn: () => getJson<Datasets>('datasets.json') })
}

export function useVerification() {
  return useQuery({ queryKey: ['verification'], queryFn: () => getJson<Verification>('verification.json') })
}
