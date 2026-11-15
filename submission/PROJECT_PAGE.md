# IGNIS — Space Fire Intelligence

**Challenge:** Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data
**Team:** Artisanal Intelligence (Riobamba, Ecuador)

## Summary (≈150 words)

Fire depends on gravity, yet nearly all spacecraft-fire evidence comes from Earth (1 g) or orbit (~0 g). Artemis
and Mars crews will live at 0.165 g and 0.38 g, in reduced-pressure, oxygen-enriched cabins. IGNIS turns NASA's
combustion archive into traceable evidence, and asks what we know, how well a mission condition is covered,
and what to measure next.

- **Evidence Ledger:** the harvested PSI catalog and NTRS papers become Finding Cards. Each card quotes its source,
  and the quote is verified on the cited page.
- **Partial-Gravity Bridge:** compares limits at 0 g, lunar, Martian and 1 g, and finds where 1-g screening may
  not be conservative.
- **Gap Radar:** ranks untested mission conditions with a transparent formula.
- **Scientific Copilot:** answers only with sentences that pass a deterministic and NLI validator.

The headline gap: no partial-gravity flammability test in our ledger, and no experiment planned in our sources,
covers the nominal lunar-habitat atmosphere (10.2 psia, 26.5% O₂).

## What it does

1. **Evidence Explorer.** Turns the 24 combustion investigations in NASA's Physical Sciences Informatics (PSI)
   archive and NASA Technical Reports into **Finding Cards**. Each card records the claim, material,
   O₂, pressure, flow, gravity, platform and value in SI units, plus its data type
   (MEASURED / DERIVED / MODELED / CONCEPTUAL) and its epistemic status (fact / interpretation / hypothesis /
   unknown). Every card carries a verbatim quote that the pipeline verifies on the cited page.
2. **Partial-Gravity Bridge.** Lines up the limited partial-gravity evidence against the microgravity and 1-g data:
   - 5 campaigns, the longest test 150 s;
   - oxygen limits for three materials at 0, 0.165, 0.38 and 1 g (Olson & Ferkul 2012);
   - long-duration spread rates from LUCI.

   It flags where measurements are not comparable, such as 5-s drop tests, Coriolis effects, or forced versus
   buoyant flow. It also places microgravity forced-flow tests on the gravity axis through a documented
   buoyant-velocity scaling.
3. **Standards Stress-Test.** Shows the published oxygen margins: Mylar kept burning at 5.75% O₂ less in lunar
   gravity than its 1-g limit. IGNIS recomputes all 9 margins (9/9 match). The result is framed as a finding to
   investigate: H2 is *partially supported*, with its caveats on screen.
4. **Evidence Gap Radar + Next-Experiment Designer.** Maps gravity × O₂ × pressure against mission scenarios
   whose atmospheres are verified in NASA documents. It ranks gaps with P = relevance × 1/(1+campaigns) ×
   duration factor × planned-experiment factor. It proposes the platform, the conditions and the hypothesis to
   test, and notes what FM2 already plans.
5. **Scientific Copilot.** Hybrid retrieval (BM25 + embeddings + reranking) over ~18,000 passages from
   public-use NASA documents. Core calculations are run by code, never by the model. A validator removes
   invented citations and untraceable numbers, and downgrades claims that the cited text does not entail. The
   app keeps working with no language model at all.

## Why it matters

The predictor is deliberately **switched off**. Its pre-registered gate fails on the data, with only 2 of the 3
required partial-gravity campaigns for the best candidate. IGNIS will not show fire probabilities or risk maps
that no data can validate. It shows NASA what to measure next.

## Space agency data

See [NASA_DATA.md](NASA_DATA.md).

## Use of AI (SI) tools

The code, data pipeline and documentation were written with an AI coding agent (Claude Code), under the team's
direction. The project idea and research questions are the team's own.

Finding Cards were drafted with AI assistance and accepted only after deterministic checks: the quote was found
on the cited page, and every number appears in the quote.

Inside the app, the language models (Gemini, or Ollama locally) only phrase answers from retrieved evidence. A
validator checks every sentence.

The logo was produced with AI assistance and is marked as such on the project page.
