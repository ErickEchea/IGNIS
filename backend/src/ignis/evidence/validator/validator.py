"""Scientific Evidence Validator: checks every sentence of a drafted answer against its evidence.

A sentence survives only if:
1. it cites at least one label, and every label was really provided to the model in this request
   (retrieved chunk ``S#`` or Core tool result ``T#``)          -> otherwise REMOVED (invented citation)
2. every cited chunk belongs to a registered source             -> otherwise REMOVED
3. any DOI or page number written in the sentence matches the cited source/chunk -> otherwise REMOVED
4. every number in the sentence appears in the cited text or tool output (integers 0-10 exempt,
   since they are usually counts written in words in the source) -> otherwise REMOVED
5. NLI: entailed by at least one cited text (p >= 0.5) keeps its category; contradicted (p >= 0.5)
   is REMOVED; otherwise the claim is downgraded to HYPOTHESIS ("not entailed by the cited text").
   If the NLI model is unavailable, the sentence is kept with "entailment NOT CHECKED".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Protocol

from ignis.evidence.cards import normalize_text, numbers_in

Verdict = Literal["VERIFIED", "DOWNGRADED", "REMOVED", "UNCHECKED"]
CATEGORIES = ("DOCUMENTED_FACT", "SCIENTIFIC_INTERPRETATION", "HYPOTHESIS", "UNKNOWN")
ENTAIL_MIN = 0.5
CONTRADICT_MIN = 0.5
_DOI = re.compile(r"\b10\.\d{4,9}/[^\s\]\),;]+", re.IGNORECASE)
_PAGE = re.compile(r"\b(?:p\.|page)\s*(\d{1,4})\b", re.IGNORECASE)
_LABEL = re.compile(r"\[(?:[ST]\d+)(?:\s*,\s*[ST]\d+)*\]")


class NliLike(Protocol):
    def predict(self, premise: str, hypothesis: str) -> object: ...


@dataclass(frozen=True)
class Evidence:
    label: str  # "S1".. or "T1"..
    text: str
    source_id: str | None  # None for Core tool results
    page: int | None
    doi: str | None = None


@dataclass
class DraftSentence:
    text: str
    citations: list[str]
    category: str


@dataclass
class SentenceCheck:
    text: str
    citations: list[str]
    category_in: str
    category_out: str
    verdict: Verdict
    checks: dict[str, bool | None] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    entailment: float | None = None


@dataclass
class ValidationReport:
    sentences: list[SentenceCheck]
    nli_available: bool

    @property
    def kept(self) -> list[SentenceCheck]:
        return [s for s in self.sentences if s.verdict != "REMOVED"]

    def summary(self) -> dict[str, int]:
        out = {"VERIFIED": 0, "DOWNGRADED": 0, "REMOVED": 0, "UNCHECKED": 0}
        for s in self.sentences:
            out[s.verdict] += 1
        return out


# Sentence boundaries, plus bullet glyphs that PDF slides extract as U+2022, U+00BE or U+F0B7.
_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+|\s*[\u2022\u00be\uf0b7]\s*|\n{2,}")


def premise_windows(text: str, size: int = 3, max_windows: int = 12) -> list[str]:
    """Overlapping windows of up to ``size`` sentences (bullets count as sentence breaks)."""
    sents = [x.strip() for x in _SENT_SPLIT.split(text) if x and len(x.strip()) > 3]
    if len(sents) <= 1:
        return []
    out = [" ".join(sents[i : i + size]) for i in range(0, max(1, len(sents) - size + 1))]
    return out[:max_windows]


def _strip_labels(text: str) -> str:
    return _LABEL.sub("", text).strip()


def _significant_numbers(text: str) -> set[str]:
    nums = numbers_in(_strip_labels(text))
    return {n for n in nums if not (n.isdigit() and 0 <= int(n) <= 10)}


def validate(
    draft: list[DraftSentence],
    evidence: dict[str, Evidence],
    registry: set[str],
    registry_dois: dict[str, str],
    nli: NliLike | None,
) -> ValidationReport:
    results: list[SentenceCheck] = []
    for d in draft:
        cat = d.category if d.category in CATEGORIES else "UNKNOWN"
        chk = SentenceCheck(d.text, list(d.citations), cat, cat, "VERIFIED")
        cited = [evidence[c] for c in d.citations if c in evidence]
        # 1. citations exist and were provided
        chk.checks["has_citation"] = bool(d.citations)
        chk.checks["citations_were_retrieved"] = bool(d.citations) and len(cited) == len(d.citations)
        if not chk.checks["has_citation"]:
            chk.reasons.append("no citation")
        elif not chk.checks["citations_were_retrieved"]:
            missing = [c for c in d.citations if c not in evidence]
            chk.reasons.append(f"cites labels that were never provided: {', '.join(missing)}")
        # 2. registered sources
        chk.checks["sources_registered"] = all(e.source_id is None or e.source_id in registry for e in cited)
        if not chk.checks["sources_registered"]:
            chk.reasons.append("cites a source that is not in the registry")
        # 3. DOI and page claims written in the sentence
        dois = [m.group(0).rstrip(".").lower() for m in _DOI.finditer(d.text)]
        cited_dois = {(e.doi or "").lower() for e in cited} | {
            registry_dois.get(e.source_id or "", "").lower() for e in cited
        }
        chk.checks["doi_consistent"] = all(x in cited_dois for x in dois) if dois else None
        if chk.checks["doi_consistent"] is False:
            chk.reasons.append("DOI in the sentence does not match the cited source record")
        pages = [int(m.group(1)) for m in _PAGE.finditer(d.text)]
        chk.checks["page_consistent"] = all(any(e.page == p for e in cited) for p in pages) if pages else None
        if chk.checks["page_consistent"] is False:
            chk.reasons.append("page number in the sentence does not match the cited chunk")
        # 4. numbers traceable to cited text or tool output
        cited_nums: set[str] = set()
        for e in cited:
            cited_nums |= numbers_in(e.text)
        missing_nums = sorted(_significant_numbers(d.text) - cited_nums)
        chk.checks["numbers_traceable"] = not missing_nums
        if missing_nums:
            chk.reasons.append(f"numbers not found in cited evidence: {', '.join(missing_nums)}")

        hard_fail = any(
            chk.checks.get(k) is False
            for k in (
                "has_citation",
                "citations_were_retrieved",
                "sources_registered",
                "doi_consistent",
                "page_consistent",
                "numbers_traceable",
            )
        )
        if hard_fail:
            chk.verdict, chk.category_out = "REMOVED", "UNKNOWN"
            results.append(chk)
            continue
        # 5. entailment
        if nli is None:
            chk.verdict = "UNCHECKED"
            chk.checks["entailed"] = None
            chk.reasons.append("entailment NOT CHECKED (NLI model unavailable)")
        else:
            hyp = _strip_labels(d.text)
            best_e, best_c = 0.0, 0.0
            for e in cited:
                # Contradiction is judged on the whole passage (conservative); entailment is the max over the
                # whole passage and its windows of up to 3 sentences (NLI models degrade on long premises).
                r = nli.predict(e.text, hyp)
                best_e = max(best_e, float(getattr(r, "entailment", 0.0)))
                best_c = max(best_c, float(getattr(r, "contradiction", 0.0)))
                for window in premise_windows(e.text):
                    if best_e >= ENTAIL_MIN:
                        break
                    rw = nli.predict(window, hyp)
                    best_e = max(best_e, float(getattr(rw, "entailment", 0.0)))
            chk.entailment = round(best_e, 3)
            chk.checks["entailed"] = best_e >= ENTAIL_MIN
            if best_e < ENTAIL_MIN and best_c >= CONTRADICT_MIN:
                chk.verdict, chk.category_out = "REMOVED", "UNKNOWN"
                chk.reasons.append(f"contradicted by the cited text (p={best_c:.2f})")
            elif best_e < ENTAIL_MIN:
                chk.verdict = "DOWNGRADED"
                if cat in ("DOCUMENTED_FACT", "SCIENTIFIC_INTERPRETATION"):
                    chk.category_out = "HYPOTHESIS"
                chk.reasons.append(f"not entailed by the cited text (p={best_e:.2f}): treat as hypothesis")
        results.append(chk)
    return ValidationReport(results, nli is not None)


def quote_supported(quote: str, text: str) -> bool:
    return normalize_text(quote) in normalize_text(text)
