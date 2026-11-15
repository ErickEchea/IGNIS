# IGNIS: 7 slides with speaker notes

The Space Apps limit is 7 slides including the title. This is the slide alternative to the 30 s video; submit
**either** the video **or** the slides.

---

## Slide 1: IGNIS, Space Fire Intelligence

- Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data
- Team Artisanal Intelligence · Riobamba, Ecuador
- Visual: logo and the line "Fire depends on gravity."

**Speaker notes:** We built an evidence engine for a question NASA has not closed: how do fires behave at the
gravity levels where crews will actually live?

---

## Slide 2: The partial-gravity blind spot

- Artemis surface operations at 0.165 g; Mars at 0.38 g.
- Planned cabins: 10.2 psia / 26.5% O₂ and 8.2 psia / 34% O₂ (NASA/TM-20220000524).
- 0 of 24 NASA PSI combustion investigations are at partial gravity.
- 5 partial-gravity campaigns in our ledger. The longest test lasted 150 s; most lasted 5–25 s.

**Speaker notes:** Partial-gravity data exist, but they are sparse, short and mostly locked in plots, and we found
no downloadable partial-gravity dataset. We quantify the gap instead of claiming there is no research.

---

## Slide 3: Every number traceable

- Finding Cards record material, O₂, pressure, flow, gravity and platform, plus value, data type and epistemic
  status.
- 66 cards. Each verbatim quote is verified on the cited page by code, not by an LLM.
- Cross-checks:
  - 9/9 published oxygen margins recomputed;
  - 260/260 FLEX rows identical between the PSI CSV and the NASA TP;
  - the LUCI spin rate reproduces 0.165 g.

**Speaker notes:** Scientific validity is non-negotiable. We found and logged errors in the sources
themselves: a wrong unit in the PSI FLEX table, and an inconsistent figure caption.

---

## Slide 4: Is the 1-g screening test conservative?

- Visual: oxygen-margin bars. Mylar at lunar g: −5.75% O₂. All lunar and Martian margins are negative.
- Verdict on H2: **partially supported.** It holds for these materials at partial g, but not for charring fabrics
  in 0 g.
- Caveats:
  - the limits come from 5-s drops;
  - "more flammable" means a lower O₂ limit, not faster spread.

**Speaker notes:** We frame this as a finding to investigate, not an accusation. NASA researchers raise the same
concern, and NASA-STD-6001B itself is silent on partial gravity.

---

## Slide 5: We refuse to fake a predictor

- The predictor gate is evaluated live from the ledger:
  - 2 of the 3 required partial-g campaigns;
  - 8 of the 20 required compatible points;
  - 4 of the 5 required held-out points.
- So there are **no fire probabilities and no risk maps**.
- The physics bridge u_b ∝ g^(1/3) is shown as MODELED, with its assumptions. Saffire's 20 cm/s flow is the
  closest orbital analog to lunar convection.

**Speaker notes:** Predicting habitat fire risk from microgravity data alone is not yet supported by evidence. We
show why, and what data would unlock it.

---

## Slide 6: What NASA should measure next

- Gap Radar: P = relevance × 1/(1 + campaigns) × D × F, with the formula on screen.
- #1: lunar gravity at the nominal lunar-habitat atmosphere (10.2 psia, 26.5% O₂). It has no data, and the
  sources we indexed show no plan to test it. FM2 plans 8.2 psia/34% and 14.7 psia/21%.
- Recommended platform: lunar surface (FM2-class) or a spin vehicle (LUCI-class). Pair every test with a 1-g
  test to compute the oxygen margin.

**Speaker notes:** IGNIS doesn't just summarize the archive; it tells NASA what to measure next.

---

## Slide 7: A copilot that cannot make things up

- Hybrid retrieval over about 18,000 passages of public-use NASA documents.
- Validator checks:
  - invented citations, DOI or page mismatches and untraceable numbers are removed;
  - claims the cited text does not entail are downgraded.
- Works with Gemini, a local Ollama model, or no LLM at all.

**Speaker notes:** Language models explain; they never compute or decide the truth. Thank you. Everything is
open source, with the data provenance documented.
