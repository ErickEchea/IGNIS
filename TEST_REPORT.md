# IGNIS test report

Run on 2026-11-14 on a Windows 11 laptop: RTX 5060 Laptop GPU (8 GB), 31 GB RAM, Python 3.11.7, Node 24.

## 1. Automated test suites

| Suite | Command | Result |
|---|---|---|
| Backend unit + property + integration tests | `cd backend && uv run pytest` | **65 passed** |
| Lint | `uv run ruff check src tests` | clean |
| Static types | `uv run mypy` (strict) | clean, 0 issues in 37 files |
| Frontend: Python↔TypeScript parity (ranking and gap priority) | `cd frontend && npm test` | **2 passed** (200 score vectors and 54 priority vectors identical to 6 decimals) |
| Frontend: types and lint | `npm run typecheck && npm run lint` | clean (3 fast-refresh warnings) |
| Production build | `npm run build` | OK. Initial JS 110 kB gzip; the Plotly chunk (476 kB gzip) is lazy-loaded on chart pages only |
| UI smoke test (Edge headless, desktop 1440 px and mobile 390 px, light and dark) | `node scripts/screenshots.mjs` | no console errors, no horizontal overflow on any route |

### What the backend tests cover (the mandatory cases)

| Required case | Test(s) |
|---|---|
| Scientific calculations and units | `test_units.py`: psi/kPa/mmHg, % to mole fraction, mil, Dalton; hypothesis round-trips. `test_buoyancy.py`: g^(1/3) scaling, inverse consistency, monotonicity. `test_analysis.py`: spin gravity, ranking, bins, gate |
| Grounded answers | `test_grounded_sentence_is_verified`, `test_tool_numbers_are_traceable` |
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

## 2. Data verification (deterministic, run by `ignis-pipeline build`)

| Check | Result |
|---|---|
| Finding Card quote found on the cited page (or NTRS abstract), and every number of the value present in the quote | **66/66 cards pass** |
| Mission-atmosphere quotes verified on the cited NASA page | 8/8 verified; the Mars surface habitat is left UNKNOWN (no source found) |
| Olson & Ferkul (2012) Table I oxygen margins recomputed from the limits with Eq. (1) | **9/9 identical** to the published values |
| PSI FLEX CSV vs NASA/TP-2015-216046 printed tables, joined on the FLEX identifier, 7 numeric fields | **260/260 matched rows identical**. 12 CSV rows and 2 TP rows could not be matched by the parser; they are reported, not hidden |
| LUCI spin rate (11 rpm at 1.22 m) gives ω²r | 0.165 g, which is lunar gravity |
| Raw-data integrity | sha256 for every file in `data/raw/MANIFEST.json`; `ignis-pipeline verify` |

Data-quality problems found in the sources are listed in the app (Methods → Data quality) and in
DATA_SOURCES.md.

## 3. Scientific Copilot evaluation (golden set, 25 questions)

The golden set (`eval/golden.yaml`) has 21 answerable questions, each with its expected sources, and
4 questions that must produce an abstention: out of corpus, a fire probability, a prediction, and a prompt
injection.

Run: `cd backend && uv run python ../eval/run_eval.py LOCAL --demo`. Model: `qwen3:8b` (Ollama, local), with one
unscored warm-up call. Retrieval is hybrid (BM25, bge-small embeddings, RRF, cross-encoder rerank) over 18,046
passages. The validator uses NLI with DeBERTa-v3-xsmall (ONNX).

| Metric | Value | Wilson 95% CI |
|---|---|---|
| Abstention accuracy (abstains exactly when it should) | **1.00** (25/25) | 0.87–1.00 |
| Citation correctness (kept sentences citing an expected source or Core tool) | 0.72 | 0.63–0.80 |
| Drafted sentences VERIFIED (entailed by cited text) | 0.41 | 0.33–0.51 |
| Drafted sentences DOWNGRADED to hypothesis (not entailed) | 0.52 | 0.43–0.61 |
| Drafted sentences REMOVED (invented citation, untraceable number, contradiction) | 0.07 | 0.04–0.13 |
| Retrieval recall@8 (an expected source among the retrieved passages) | 0.95 | 0.75–0.99 |
| Median latency per question | 9.0 s | — |

How to read these results:

- The validator is strict. More than half of the drafted sentences are kept only as hypotheses, because the
  NLI model did not find them entailed by the specific cited passage. The UI marks every such sentence.
- **The validator also makes conservative errors.** It removed a correct sentence ("0.92 mm/s", LUCI slide 19)
  because the passage it cited (slide 33) writes the value as ".9".
- The one retrieval miss, Q16 (lunar-habitat atmosphere), happens because the source document abbreviates
  "surface habitat" as "SH".
- In the first run, without a warm-up call, Q01 failed because the cold start of Ollama exceeded the 60 s
  timeout. The UI showed it as a visible provider failure, not a fabricated answer.
- With 21 answerable questions the intervals are wide, and the metrics should be read as indicative.
- The Gemini (CLOUD) evaluation is pending until an API key is configured.

## 4. Human spot-check of Finding Cards

20 cards were sampled at random (seed 2026) and are listed in `submission/CARD_SPOTCHECK.md`.
**Pending:** the result (k/20) will be recorded here after the team's manual review.

## 5. Local LLM hardware validation

See [docs/hardware_report.md](docs/hardware_report.md). Each model was loaded alone (never both at once) and
measured for load time, VRAM fit, latency, tokens/s at 4k, 8k and 16k context, JSON validity, and stability over
3 runs.

## 6. Known issues

- The prompt-injection detector is pattern-based. It catches common phrasings, not every possible attack. A
  second line of defence keeps sources inside delimited untrusted blocks and constrains the model to a JSON
  schema, and the validator removes any sentence that is not grounded.
- The retrieval index is built from public-use NTRS PDFs only, so paywalled papers are not searchable as full
  text.
- Accessibility was checked with keyboard navigation and contrast tokens, plus a manual review of the
  screenshots. A full automated audit (Lighthouse / axe) has not been run yet.
