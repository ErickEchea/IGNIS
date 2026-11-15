# Data sources

Every input is downloaded by `ignis-pipeline fetch` into `data/raw/` and recorded with its URL, sha256,
size, license and fetch time in [`data/raw/MANIFEST.json`](data/raw/MANIFEST.json). The registry of curated
sources is [`pipeline/manifests/sources.yaml`](pipeline/manifests/sources.yaml). Data were accessed on
2026-11-14.

## NASA datasets

| Source | What IGNIS uses | Access | License / terms | Citation |
|---|---|---|---|---|
| NASA Physical Sciences Informatics (PSI), all 24 investigations with Research Area "Combustion Science" (FLEX, FLEX-2, BASS, BASS-II, CFI, ACME BRE / CLD Flame / E-FIELD / s-Flame / Flame Design / CFI-G, SAFFIRE-I/II/III, SAME, SAME-R, SPICE, SLICE, DAFT, and ground/model studies) | Investigation metadata (objectives, hardware, dates, publications), and the small "Experimental table" CSV files | Public JSON web service `psi.nasa.gov/geode-py/ws` (undocumented; raw responses are snapshotted) | CC0-1.0 (per investigation record) | Cite each investigation's DataCite DOI, e.g. FLEX `10.60555/mbq8-0451`, BASS-II `10.60555/4qc4-de67` |
| NASA Technical Reports Server (NTRS) | 141 records (21 curated + 11 documented search queries, top 25 each); 107 PDFs downloaded | Public API `ntrs.nasa.gov/api/citations` | Full text indexed only when NTRS marks `PUBLIC_USE_PERMITTED`, `GOV_PUBLIC_USE_PERMITTED` or `GOV_PERMITTED`. `MAY_INCLUDE_COPYRIGHT_MATERIAL` PDFs are kept locally only to verify quotes. Everything else is metadata only. | NASA STI; each record's NTRS citation |

Key NTRS documents behind the Finding Cards:

- Olson & Ferkul (2012), *Evaluating Material Flammability in Microgravity and Martian Gravity Compared to the NASA Standard Normal Gravity Test*, 42nd ICES, NTRS 20130010991.
- Ferkul, Kralik & Liao (2026), *Material Flammability at Lunar and Martian Gravity*, LPSC 2026, NTRS 20260000646.
- Ferkul, Johnston, Kralik & Liao (2025), *Lunar Combustion Investigation: Flammability Results from a Rotating Sounding Rocket*, ASGSR 2025, NTRS 20250010653.
- Sacksteder, Ferkul, Feier, Kumar & T'ien (2003), *Upward and Downward Flame Spreading and Extinction in Partial Gravity Environments*, NASA/CP-2003-212376, NTRS 20040053567.
- Sacksteder & T'ien (1993), *Downward Diffusion Flame Spread and Extinction in Variable Gravitational Fields: Lunar and Martian Simulations*, NTRS 19930040901 (abstract only).
- Sacksteder, Ferkul & T'ien (1999), *Flame Spread and Extinction in Partial-Gravity Environments*, NTRS 19990054085 (abstract only).
- Zayac, Johnston, Ruff & Ferkul (2024), *Flammability of Materials on the Moon* (FM2 poster), NTRS 20240015307.
- NASA/TP-2015-216046 (FLEX results), NTRS 20150023456: used to verify the PSI FLEX table.
- Mission atmospheres: NASA/TM-20220000524 (NTRS 20220000524), NTRS 20150021491, NTRS 20070018274.

## Other sources (metadata and short quotes only)

| Source | Use | Terms |
|---|---|---|
| Konno, Ishikawa, Hashimoto & Fujita (2024), Proc. Combust. Inst. 40:105199, doi:10.1016/j.proci.2024.105199 | Buoyant velocity scaling u ∝ a^(1/3), 1-g anchor 35 cm/s | Publisher copyright |
| Nakaya, KAKEN 21K18775 final report | 1-g anchor V_b = 33.0 cm/s | Report; cited only |
| NASA NSSDC Moon and Mars fact sheets | Gravity: 1.62 m/s² (0.165 g), 3.73 m/s² (0.380 g) | US Government work |
| NASA-STD-6001B w/ Change 2 | Test 1 pass/fail criteria and MOC definition | US Government work |
| Space Apps 2026 challenge page "Flame in Freefall" | Challenge framing and quotes | Quoted for reference |

Paywalled journal articles are never redistributed or full-text indexed.

## Known data-quality issues

These issues are listed in the app (Methods → Data quality) together with the action IGNIS took:

- FLEX CSV burning-rate unit (mm → mm²/s).
- FLEX CSV composition headers (O, N, CO → O₂, N₂, CO₂).
- SAFFIRE-II encoding (µ-g).
- SAFFIRE-I sample geometry and dates.
- NTRS author typo.
- Inconsistent figure caption in Olson & Ferkul (2012).

## Partner-agency data

- **JAXA DARTS:** Group Combustion droplet telemetry is browsable. It is not used, because it concerns droplet clouds in microgravity and falls outside the partial-gravity focus.
- **ESA HREDA:** requires a login, so it was not used.
- **CSA:** no combustion dataset was found.
