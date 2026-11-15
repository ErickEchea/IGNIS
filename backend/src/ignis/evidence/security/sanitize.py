"""Treat external documents as untrusted data.

Retrieved text is passed to a language model only inside delimited SOURCE blocks, after scanning for
instruction-like content. Chunks that look like prompt-injection attempts are withheld from the model
(and reported), never "cleaned" in place, so quotes shown to the user stay verbatim.
"""

from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?|rules)",
    r"disregard (all |any )?(the )?(previous|prior|above)",
    r"you are now\b",
    r"new instructions?:",
    r"system prompt",
    r"\bact as (an?|the)\b",
    r"reveal (your|the) (instructions|prompt|api key|secret)",
    r"(print|output|return) (your|the) (api[_ ]?key|secret|password)",
    r"</?\s*(system|assistant|instruction)s?\s*>",
    r"\bjailbreak\b",
    r"do not (cite|mention) (this|the) source",
]
_RX = re.compile("|".join(f"(?:{p})" for p in INJECTION_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    return _RX.search(text) is not None


def source_block(label: str, source_id: str, page: int | None, text: str) -> str:
    """Wrap untrusted text; strip delimiter look-alikes so a document cannot close its own block."""
    safe = text.replace("<<<", "‹‹‹").replace(">>>", "›››")  # noqa: RUF001
    where = f", page {page}" if page else ""
    return f"<<<SOURCE {label} ({source_id}{where})\n{safe}\n>>>"
