<p align="center"><img src="frontend/public/ignis-logo.svg" width="96" alt="IGNIS logo"></p>

# IGNIS — Space Fire Intelligence

**NASA Space Apps Challenge 2026 · “Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data”**
Team **Artisanal Intelligence** (Riobamba, Ecuador)

> **Status:** under active construction during the hackathon (Nov 14–15, 2026). This README is a draft.

## The question
Fire depends on gravity. Nearly all spacecraft-fire evidence comes from Earth (1 g) or from orbit
(~0 g), yet Artemis and Mars crews will live at **0.165 g** and **0.38 g**, often in reduced-pressure,
oxygen-enriched cabins. IGNIS asks three questions of NASA's combustion archive:

1. What do we know with confidence about fire away from Earth, and on what evidence?
2. How well is a specific mission condition covered by that evidence, and with what uncertainty?
3. What don't we know yet, and which experiment should fly next to find out?

## Principles
- Every number shows its source and type (`MEASURED / DERIVED / MODELED / CONCEPTUAL`).
- Every claim shows its epistemic status (`DOCUMENTED FACT / SCIENTIFIC INTERPRETATION / HYPOTHESIS / UNKNOWN`).
- Science is computed by deterministic, tested Python. Language models only explain validated results,
  and the app works with no language model at all.
- No fire probabilities or risk maps without a validated model.

## Repository layout
See [CLAUDE.md](CLAUDE.md) for commands and layout. Data provenance: [DATA_SOURCES.md](DATA_SOURCES.md).

## Not affiliated with NASA
IGNIS is an independent hackathon project. It does not use NASA logos or insignia and is not endorsed by NASA.
