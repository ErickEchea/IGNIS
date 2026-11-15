"""Load curated Finding Cards and verify every quote against its source.

Two YAML forms live in ``pipeline/cards``:

* ``cards:`` a list of explicit Finding Cards.
* ``table:`` a transcribed source table. Each row carries the verbatim row text as its quote and is
  expanded deterministically into one card per column (material). Expansion is pure code, so the
  transcription can be audited row by row.

Verification (no LLM involved):
1. the source exists in the registry;
2. the quote appears on the cited page of the downloaded document (whitespace, ligatures, hyphens
   and replacement characters normalized);
3. every number in the card value (as written in the source) appears in the quote.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ignis.evidence.schema import FindingCard

_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")  # noqa: RUF001
_QUOTES = dict.fromkeys(map(ord, "‘’‚‛“”„‟´`"), "'")  # noqa: RUF001
# PDF text layers encode line-break hyphens as U+FFFE / soft hyphen: keep them as "-".
_DROP = {ord("￾"): "-", ord("­"): "-", ord("�"): None, ord("​"): None}


def normalize_text(text: str) -> str:
    """Canonical form for quote matching: NFKC, unified dashes/quotes, collapsed whitespace."""
    for k, v in _LIGATURES.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES).translate(_QUOTES).translate(_DROP)
    text = text.replace("®", "").replace("™", "").replace("™", "")
    # Rejoin words hyphenated across line breaks ("fire-\nretarded" -> "fire-retarded").
    text = re.sub(r"-\s*\n\s*", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


_NUM = re.compile(r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)")


def numbers_in(text: str) -> set[str]:
    return {_strip_num(m) for m in _NUM.findall(text.replace(",", ""))}


def _strip_num(n: str) -> str:
    n = n.lstrip("+")
    if n.startswith("-."):
        n = "-0" + n[1:]
    elif n.startswith("."):
        n = "0" + n
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def format_number(value: float) -> str:
    return _strip_num(f"{value:.10g}")


@dataclass
class VerificationResult:
    card_id: str
    source_found: bool
    quote_on_page: bool | None  # None = source text not available locally (metadata-only source)
    numbers_in_quote: bool
    messages: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.source_found and self.quote_on_page is not False and self.numbers_in_quote


# ----------------------------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------------------------


def _expand_table(spec: dict[str, Any]) -> list[dict[str, Any]]:
    cols: list[dict[str, Any]] = spec["columns"]
    out: list[dict[str, Any]] = []
    for row in spec["rows"]:
        values = row["values"]
        if len(values) != len(cols):
            raise ValueError(f"{spec['id_prefix']}/{row['key']}: {len(values)} values for {len(cols)} columns")
        for col, val in zip(cols, values, strict=True):
            if val is None:
                continue
            base = {k: v for k, v in col.items() if k not in {"key", "label"}}
            card: dict[str, Any] = {**spec.get("defaults", {}), **base}
            row_fields = {
                k: v
                for k, v in row.items()
                if k not in {"key", "values", "quote", "claim", "unit", "dimension", "label"}
            }
            card.update(row_fields)
            card["id"] = f"{spec['id_prefix']}-{row['key']}-{col['key']}".upper()
            card["value"] = {
                "value": val,
                "unit": row["unit"],
                "dimension": row["dimension"],
                **({"uncertainty_kind": row["uncertainty_kind"]} if "uncertainty_kind" in row else {}),
            }
            card["claim"] = row["claim"].format(material=col.get("label", col["material"]), value=val)
            card["provenance"] = {
                "source_id": spec["source_id"],
                "page": spec["page"],
                "locator": (f"{spec['locator']}, row '{row['label']}', column '{col.get('label', col['material'])}'"),
                "quote": row["quote"],
                "extraction": spec.get("extraction", "llm_assisted_quote_verified"),
            }
            out.append(card)
    return out


def load_card_dicts(cards_dir: Path) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for path in sorted(cards_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for spec in doc.get("tables", []):
            raw.extend(_expand_table(spec))
        raw.extend(doc.get("cards", []))
    return raw


def load_cards(cards_dir: Path) -> list[FindingCard]:
    cards = [FindingCard.model_validate(d) for d in load_card_dicts(cards_dir)]
    seen: set[str] = set()
    for c in cards:
        if c.id in seen:
            raise ValueError(f"Duplicate card id {c.id}")
        seen.add(c.id)
    return cards


# ----------------------------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------------------------

PageTextFn = Callable[[str, int | None], str | None]


def verify_card(card: FindingCard, known_sources: set[str], page_text: PageTextFn) -> VerificationResult:
    prov = card.provenance
    res = VerificationResult(card.id, prov.source_id in known_sources, None, True)
    if not res.source_found:
        res.messages.append(f"unknown source_id {prov.source_id}")
        return res
    text = page_text(prov.source_id, prov.page)
    quote_norm = normalize_text(prov.quote)
    if text is not None:
        res.quote_on_page = quote_norm in normalize_text(text)
        if not res.quote_on_page:
            res.messages.append(f"quote not found on page {prov.page}")
    # Every number of the card's reported value must appear in the quote as written in the source.
    for name in ("value", "comparison_1g"):
        q = getattr(card, name)
        if q is None:
            continue
        num = format_number(q.value)
        if num not in numbers_in(prov.quote):
            res.numbers_in_quote = False
            res.messages.append(f"{name}={num} not present in quote")
    return res


def verify_all(
    cards: Iterable[FindingCard], known_sources: set[str], page_text: PageTextFn
) -> list[VerificationResult]:
    return [verify_card(c, known_sources, page_text) for c in cards]
