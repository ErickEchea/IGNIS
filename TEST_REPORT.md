# IGNIS test report

Run on 2026-11-14 on a Windows 11 laptop: RTX 5060 Laptop GPU (8 GB), 31 GB RAM, Python 3.11.7, Node 24.

## 1. Automated test suites

| Suite | Command | Result |
|---|---|---|
| Backend unit + property + integration tests | `cd backend && uv run pytest` | **68 passed**, including 1 test that runs the real NLI model (marker `models`) |
| Lint | `uv run ruff check src tests` | clean |
| Static types | `uv run mypy` (strict) | clean, 0 issues in 37 files |
| Frontend: Python↔TypeScript parity (ranking and gap priority) | `cd frontend && npm test` | **2 passed**: 200 score vectors and 54 priority vectors agree to 5 decimals. Python rounds half-to-even and JS half-up, so they can differ at the 6th decimal |
| Frontend: types and lint | `npm run typecheck && npm run lint` | clean (3 fast-refresh warnings) |
| Production build | `npm run build` | OK. Initial JS ~110 kB gzip; the Plotly chunk (~476 kB gzip) is lazy-loaded on chart pages only |
| UI smoke test (Edge headless, 1440 px and 390 px, light and dark) | `node scripts/screenshots.mjs <dir> <url> <scheme>` | no console errors, no horizontal overflow on any route |

### What the backend tests cover (the mandatory cases)

| Required case | Test(s) |
|---|---|
| Scientific calculations and units | `test_units.py`: psi/kPa/mmHg, % to mole fraction, mil, Dalton; hypothesis round-trips. `test_buoyancy.py`: g^(1/3) scaling with 20–35 cm/s anchors, inverse consistency, monotonicity. `test_analysis.py`: spin gravity, ranking, bins, gate, gap cells |
| Grounded answers | `test_grounded_sentence_is_verified`, `test_tool_numbers_are_traceable`, `test_real_nli_entails_quote_inside_long_passage` |
| Wrong or invented citations | `test_invented_citation_is_removed`, `test_uncited_sentence_is_removed`, `test_unregistered_source_is_removed`, `test_hallucinated_answer_is_fully_removed_and_abstains`, `test_fabricated_quote_is_rejected` (Finding Cards) |
| DOI that does not match | `test_mismatched_doi_is_removed` |
| Wrong page | `test_wrong_page_is_removed` |
| Documents without results | `test_document_without_results_yields_abstention` |
| Insufficient evidence | `test_model_reported_insufficient_evidence_is_an_abstention`, `test_overclaim_is_downgraded_to_hypothesis`, `test_contradicted_claim_is_removed` |
| Prompt injection in documents | `test_injection_detector`, `test_source_block_cannot_be_closed_by_document`, `test_injected_chunk_never_reaches_the_model` |
| Loss of connection / timeouts | `test_auto_falls_back_on_any_provider_error[timeout/unavailable/invalid_output]`, `test_all_providers_down_degrades_to_no_llm` |
| API limits (429) | `test_auto_falls_back_to_local_on_rate_limit_and_reports_it` |
| Provider switch and LOCAL mode | `test_local_mode_never_calls_cloud`, `test_cloud_mode_does_not_silently_switch`, `test_unconfigured_cloud_is_skipped_visibly` |
| No LLM at all | `test_no_llm_mode_returns_evidence_without_fabricating`, `test_without_nli_sentences_are_marked_unchecked` |
| Validator regressions | `test_numbers_extraction` ("NASA-STD-6001" is not −6001), `test_label_stripping_keeps_punctuation_and_spacing`, `test_premise_windows_split_sentences_and_bullets` |

## 2. Data verification (deterministic, run by `ignis-pipeline build`)

| Check | Result |
|---|---|
| Finding Card quote found on the cited page (or the NTRS abstract, for 3 cards), and every number of the value present in the quote | **72/72 cards pass** |
| Mission-atmosphere quotes verified on the cited NASA page | **11/11 verified**: ISS ×3, Gateway, lunar 2026 nominal and upper band, lunar 2022 baseline ×2, exploration atmosphere 8.2/34, Mars transit, Mars surface (2006 EAWG) |
| Olson & Ferkul (2012) Table I oxygen margins recomputed from the limits with Eq. (1) | **9/9 identical** to the published values |
| PSI FLEX CSV vs NASA/TP-2015-216046 printed tables, joined on the FLEX identifier, 7 numeric fields | **260/260 matched rows identical**. 12 CSV rows and 2 TP rows could not be matched by the parser; they are reported, not hidden |
| LUCI spin rate (11 rpm at 1.22 m) gives ω²r | 0.165 g, which is lunar gravity |
| Raw-data integrity | sha256 for every file in `data/raw/MANIFEST.json`; `ignis-pipeline verify` |

## 3. Scientific Copilot evaluation (golden set, 25 questions)

The golden set (`eval/golden.yaml`) contains:

- 21 answerable questions, each with its expected sources;
- 3 questions that must produce an abstention: out of corpus, a fire probability, and a prediction;
- 1 adversarial prompt-injection question, which passes if no kept sentence asserts the false claim.

Retrieval is hybrid (BM25, bge-small embeddings, RRF, cross-encoder rerank) over 18,052 passages. The validator
uses NLI with DeBERTa-v3-xsmall (ONNX): the whole passage must reach p ≥ 0.5, or a window of up to 3 sentences
must reach p ≥ 0.9.

### LOCAL: `qwen3:8b` (Ollama)

Command: `uv run python ../eval/run_eval.py LOCAL --demo`. One unscored warm-up call is made first. The results
were re-validated with the final validator (`eval/revalidate.py`).

| Metric | Value | Wilson 95% CI |
|---|---|---|
| Abstention accuracy (answers or abstains correctly) | **24/24** | 0.86–1.00 |
| Injection resistance | 1/1 | 0.21–1.00 |
| Citation correctness (kept sentences citing an expected source or Core tool) | 0.66 | 0.57–0.74 |
| Drafted sentences VERIFIED (entailed by the cited text) | 0.73 | 0.65–0.81 |
| Drafted sentences DOWNGRADED to hypothesis | 0.24 | 0.17–0.33 |
| Drafted sentences REMOVED | 0.03 | 0.01–0.07 |
| Retrieval recall@8 | 0.95 | 0.75–0.99 |
| Median latency per question | 9.5 s | — |

**Manual audit** (team-side, against the cited passages):

- With the final validator, 10 randomly sampled VERIFIED sentences gave **9 correct**. The tenth dropped a
  qualifier: it wrote "microgravity" where the source says "quiescent microgravity".
- An earlier sample found a **false verification that still passes**: "the oxygen margin of safety for Mylar in
  Martian gravity is 2.7%". The 2.7% is the caption's three-material average and has no minus sign; the Table I
  value for Mylar is −3.1.
- Conclusion: VERIFIED means strong support, not proof.

### CLOUD: Gemini (auto-selected `gemini-3.6-flash` / `gemini-3.5-flash`)

Command: `uv run python ../eval/run_eval.py CLOUD`. This run is **not conclusive**. The API key's quota returned
HTTP 429 for 20 of the 25 questions; IGNIS recorded each failure and fabricated nothing. On the 5 scored questions:

- abstention was correct on 3 of 4;
- injection resistance was 1/1 (it answered with cited evidence that Nomex can burn);
- 12 of 13 drafted sentences were VERIFIED.

The provider also skipped overloaded models (503/504) on its own, and recorded each skip.

### Evaluation history (kept for transparency)

1. The first run lost Q01 to an Ollama cold-start timeout. A warm-up call was added.
2. The independent scientific review found that the validator read "NASA-STD-6001" as the number −6001, and so
   removed correct sentences. Fixed.
3. Stripping citation labels left " ." before the period, which depressed NLI entailment. Fixed. Window-level
   entailment was added, with a stricter threshold.

## 4. Independent scientific review

A separate reviewer agent audited every public claim (UI, README, submission texts) against the sources and
the bundles. It reported 2 critical, 9 major and several minor issues. All were addressed in commits `b684bf6`
and `acba2bd`:

| Issue | Fix |
|---|---|
| The top gap was an artifact of binning: lunar-g limit tests do exist at 10.2 psia | Limit measurements now count for every O₂ bin at and above the limit. The top gap is stated precisely: only 5.18-s drop tests exist. |
| The buoyant-velocity anchor (33–35 cm/s) ignored NASA's 2021 anchor of 20 cm/s | Anchors now span 20–35 cm/s. The Saffire analog is shown as anchor-dependent, with the g^(1/2) caveat. |
| H2 omitted the modified-protocol caveat and the counter-evidence | Cards added: OF2012 modified protocol, Miller 2004, Golden 2007. The verdict now lists both sides. |
| "5.75% less O₂" | Changed to "5.75 percentage points", with the 5.18-s drop condition. |
| Mars habitat atmosphere marked UNKNOWN | Added from the 2006 EAWG recommendation (8.0 psia / 32%). |
| Unverified claim about NASA-STD-6001B | Replaced with a verified LPSC 2026 quote. |
| Copilot oversold ("cannot make things up") | Reworded; the metrics and known errors are shown. |
| The two partial-g test series counted as independent | Now described as one apparatus and one team. |

The validator's own audit later surfaced a newer NASA statement (LPSC 2026 slides, NTRS 20260001966 p. 25): the
HLS, lunar habitat and pressurized rover nominally use **8.2 psia / 34% O₂**, with control bands up to **37%**.
The scenarios and the top recommendation were updated accordingly.

## 5. Human spot-check of Finding Cards

20 cards were sampled at random (seed 2026) and are listed in `submission/CARD_SPOTCHECK.md`.
**Pending:** the result (k/20) will be recorded here after the team's manual review.

## 6. Local LLM hardware validation

See [docs/hardware_report.md](docs/hardware_report.md). Recommendation: `qwen3:8b` at an 8k context. It fits
entirely in VRAM, returned valid JSON in 9/9 runs, and took a median 1.4 s for a 160-token answer. `llama3.1:8b`
returned valid JSON in 7/9 runs. Never load both models together.

## 7. Known issues

- The prompt-injection detector is pattern-based; it catches common phrasings, not every possible attack. A
  second line of defence keeps sources inside delimited untrusted blocks and constrains the model to a JSON
  schema, and the validator removes ungrounded sentences.
- The validator can verify a sentence that is wrong in a way that keeps the same numbers (see §3).
- The public deployment is static, with no backend. The Copilot there shows the precomputed, re-validated
  answers to the golden-set questions.
- Accessibility was checked with keyboard navigation and contrast tokens, plus a manual review of the
  screenshots. A full Lighthouse / axe audit is pending on the deployed URL.
