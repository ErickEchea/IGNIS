// Screenshot the main routes with the locally installed Edge (no browser download).
// Usage: node scripts/screenshots.mjs <outDir> [baseUrl] [colorScheme]
import { chromium } from 'playwright-core'

const out = process.argv[2] ?? 'screenshots'
const base = process.argv[3] ?? 'http://localhost:5173'
const scheme = process.argv[4] ?? 'dark'
const routes = ['/', '/bridge', '/gaps', '/evidence', '/copilot', '/methods', '/system']
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const errors = []
for (const [w, h, tag] of [[1440, 900, 'desktop'], [390, 844, 'mobile']]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`${tag} ${m.text()}`) })
  page.on('pageerror', (e) => errors.push(`${tag} pageerror ${e.message}`))
  for (const r of routes) {
    await page.goto(base + r, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1500)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
    if (overflow) errors.push(`${tag} ${r} horizontal overflow`)
    const name = `${out}/${tag}-${scheme}${r === '/' ? '-home' : r.replace('/', '-')}.png`
    await page.screenshot({ path: name, fullPage: true })
  }
  await ctx.close()
}
await browser.close()
console.log(errors.length ? errors.join('\n') : 'no console errors, no horizontal overflow')
