# IGNIS: 7 slides with speaker notes

The Space Apps limit is 7 slides including the title. This is the slide alternative to the 30 s video; submit
**either** the video **or** the slides.

---

## Slide 1: IGNIS, Space Fire Intelligence

- Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data
- Team Artisanal Intelligence · Riobamba, Ecuador · not affiliated with or endorsed by NASA
- Visual: logo and the line "Fire depends on gravity."

**Speaker notes:** We built an evidence engine for a question NASA has not closed: how do fires behave at the
gravity levels where crews will actually live?

---

## Slide 2: The partial-gravity blind spot

- Artemis surface operations at 0.165 g; Mars at 0.38 g.
- Cabins: HLS, lunar habitat and pressurized rover will nominally use 8.2 psia / 34% O₂, with control bands up to 37%
  (NASA, LPSC 2026). The earlier baseline was 10.2 psia / 26.5% (NASA/TM-20220000524). Mars habitats: 8.0 psia / 32%
  (2006 EAWG).
- 0 of 24 NASA PSI combustion investigations are at partial gravity.
- 5 partial-gravity campaigns in our ledger. The longest test lasted 150 s; most lasted 5–25 s.

**Speaker notes:** Partial-gravity data exist, but they are sparse, short and mostly locked in plots, and we found
no downloadable partial-gravity dataset. We quantify the gap instead of claiming there is no research.

---

## Slide 3: Every number traceable

- Finding Cards record material, O₂, pressure, flow, gravity and platform, plus value, data type and epistemic
  status.
- 72 cards. Each verbatim quote is verified on the cited page (3 against NTRS abstracts) by code, not by an LLM.
- Cross-checks:
  - 9/9 published oxygen margins recomputed;
  - 260/260 FLEX rows identical between the PSI CSV and the NASA TP;
  - the LUCI spin rate reproduces 0.165 g.

**Speaker notes:** Scientific validity is non-negotiable. We found and logged errors in the sources
themselves: a wrong unit in the PSI FLEX table, and an inconsistent figure caption.

---

## Slide 4: Is the 1-g screening test conservative?

- Visual: oxygen-margin bars. Mylar at lunar g: −5.75 percentage points (5.18-s drop). All 6 lunar and Martian
  margins are negative.
- Verdict on H2: **partially supported.** It holds for these materials at partial g, but not for the charring Ultem
  film and Nomex fabric in 0 g.
- Caveats:
  - the low-g limits come from 5-s drops, and the 1-g limits from a modified Test 1;
  - earlier NASA assessments judged Test 1 conservative for quiescent microgravity;
  - "more flammable" means a lower O₂ limit, not faster spread.

**Speaker notes:** We frame this as a finding to investigate, not an accusation. NASA researchers raise the same
concern: in their words, Test 1 is run in Earth gravity "with the assumption that if a material passes the 1-g
test, then it is considered safe for spaceflight" (LPSC 2026).

---

## Slide 5: We refuse to fake a predictor

- The predictor gate is evaluated live from the ledger:
  - 2 of the 3 required partial-g test series (both from one apparatus);
  - 8 of the 20 required compatible points;
  - 4 of the 5 required held-out points.
- So there are **no fire probabilities and no risk maps**.
- The physics bridge u_b ∝ g^(1/3) is shown as MODELED and anchor-dependent: with 1-g anchors of 20–35 cm/s
  across sources, lunar buoyant flow is about 11–19 cm/s.

**Speaker notes:** Predicting habitat fire risk from microgravity data alone is not yet supported by evidence. We
show why, and what data would unlock it.

---

## Slide 6: What to measure next (our recommendation)

- Gap Radar: P = relevance × 1/(1 + campaigns) × D × F, with the formula on screen.
- #1: lunar gravity at the upper O₂ control band of the lunar habitat (8.2 psia, up to 37% O₂; NASA, 2026). The only lunar-gravity evidence at reduced pressure in our ledger is a 5.18-s drop-tower limit series on two films (at 10.2 psia). FM2 plans 34% at 8.2 psia, not the 37% upper band, and no long-duration test at 37% is planned in our sources.
- Recommended platform: lunar surface (FM2-class) or a spin vehicle (LUCI-class). Pair every test with a 1-g
  test to compute the oxygen margin.

**Speaker notes:** IGNIS doesn't just summarize the archive; it suggests what to measure next, and shows why.

---

## Slide 7: A copilot that shows its evidence

- Hybrid retrieval over about 18,000 passages of public-use NASA documents.
- Validator checks:
  - invented citations, DOI or page mismatches and untraceable numbers are removed;
  - claims the cited text does not entail are downgraded to hypotheses.
- Golden set (25 questions, local qwen3:8b): abstained correctly 25/25; 73% of sentences verified, 24% kept as
  hypotheses, 3% removed. Manual audit: 9/10 verified sentences correct.
- Works with Gemini, a local Ollama model, or no LLM at all.

**Speaker notes:** Language models explain; they never compute or decide the truth. Thank you. Everything is
open source, with the data provenance documented.
