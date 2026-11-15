import { useEffect, useRef, useState } from 'react'
import type { Config, Data, Layout } from 'plotly.js'

type PlotlyModule = {
  react: (el: HTMLElement, data: Data[], layout: Partial<Layout>, config: Partial<Config>) => Promise<unknown>
  purge: (el: HTMLElement) => void
}

let plotlyPromise: Promise<PlotlyModule> | null = null
function loadPlotly(): Promise<PlotlyModule> {
  plotlyPromise ??= import('plotly.js-cartesian-dist-min').then((m) => (m.default ?? m) as PlotlyModule)
  return plotlyPromise
}

export interface ChartTheme {
  text: string
  muted: string
  grid: string
  axis: string
  surface: string
  series: [string, string, string]
  good: string
  warning: string
  critical: string
  accent: string
}

export function readTheme(): ChartTheme {
  const cs = getComputedStyle(document.documentElement)
  const v = (name: string) => cs.getPropertyValue(name).trim()
  return {
    text: v('--text'),
    muted: v('--chart-muted'),
    grid: v('--chart-grid'),
    axis: v('--chart-axis'),
    surface: v('--surface'),
    series: [v('--series-1'), v('--series-2'), v('--series-3')],
    good: v('--status-good'),
    warning: v('--status-warning'),
    critical: v('--status-critical'),
    accent: v('--accent'),
  }
}

/** Re-read theme tokens when the OS color scheme changes. */
export function useChartTheme(): ChartTheme | null {
  const [theme, setTheme] = useState<ChartTheme | null>(null)
  useEffect(() => {
    const update = () => setTheme(readTheme())
    update()
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return theme
}

export function baseLayout(t: ChartTheme, extra: Partial<Layout> = {}): Partial<Layout> {
  const axis = {
    gridcolor: t.grid,
    linecolor: t.axis,
    zerolinecolor: t.axis,
    tickcolor: t.axis,
    tickfont: { color: t.muted, size: 11 },
    title: { font: { color: t.muted, size: 12 } },
    automargin: true,
  }
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'IBM Plex Sans, system-ui, sans-serif', color: t.text, size: 12 },
    margin: { l: 56, r: 16, t: 12, b: 48 },
    hoverlabel: { bgcolor: t.surface, bordercolor: t.axis, font: { color: t.text, size: 12 } },
    legend: { orientation: 'h', y: -0.22, font: { color: t.text, size: 12 } },
    ...extra,
    xaxis: { ...axis, ...(extra.xaxis ?? {}) },
    yaxis: { ...axis, ...(extra.yaxis ?? {}) },
  }
}

interface PlotProps {
  data: Data[]
  layout: Partial<Layout>
  height?: number
  ariaLabel: string
}

export function Plot({ data, layout, height = 360, ariaLabel }: PlotProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    let cancelled = false
    loadPlotly()
      .then((Plotly) => {
        if (cancelled) return
        return Plotly.react(el, data, { ...layout, height, autosize: true }, {
          displaylogo: false,
          responsive: true,
          modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
          toImageButtonOptions: { format: 'png', filename: 'ignis-chart', scale: 2 },
        })
      })
      .catch(() => setFailed(true))
    return () => {
      cancelled = true
    }
  }, [data, layout, height])
  useEffect(() => {
    const el = ref.current
    return () => {
      if (el) loadPlotly().then((P) => P.purge(el)).catch(() => undefined)
    }
  }, [])
  if (failed) return <p className="text-sm text-critical">Chart library failed to load. See the table view.</p>
  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ minHeight: height }} className="w-full" />
}
