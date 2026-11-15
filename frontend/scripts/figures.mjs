// Export the app's charts (light theme) as PNG figures for the paper. Usage: node scripts/figures.mjs <outDir> [baseUrl]
import { chromium } from 'playwright-core'
const out = process.argv[2] ?? '../paper/figures'
const base = process.argv[3] ?? 'http://localhost:4173'
const shots = [
  ['/bridge', 'Upward flammability limits of Mylar, Ultem and Nomex versus gravity level', 'fig_limits.png'],
  ['/bridge', 'Oxygen margin of safety by gravity level and material', 'fig_margins.png'],
  ['/bridge', 'Buoyancy-induced velocity scale versus gravity level with microgravity forced-flow levels', 'fig_buoyancy.png'],
  ['/gaps', 'Heatmap of evidence priority or coverage by gravity level and oxygen concentration', 'fig_gaps.png'],
]
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const ctx = await browser.newContext({ viewport: { width: 640, height: 900 }, colorScheme: 'light', deviceScaleFactor: 3 })
const page = await ctx.newPage()
for (const [route, label, file] of shots) {
  await page.goto(base + route, { waitUntil: 'networkidle' })
  const el = page.locator(`[aria-label="${label}"]`)
  await el.waitFor({ timeout: 20000 })
  await page.waitForTimeout(1500)
  await el.screenshot({ path: `${out}/${file}` })
  console.log('saved', file)
}
await browser.close()
