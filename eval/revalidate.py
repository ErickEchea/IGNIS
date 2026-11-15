"""Re-apply the current Scientific Evidence Validator to stored Copilot drafts (no new LLM calls).

Each stored answer keeps the model's drafted sentences (text, citations, category) and the exact evidence
and tool texts it was given, so validation can be re-run deterministically after a validator change.

Usage (from backend/): uv run python ../eval/revalidate.py LOCAL|CLOUD [--demo]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from ignis.ai.engine import get_copilot
from ignis.evidence.validator.validator import DraftSentence, Evidence, validate

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
from run_eval import wilson  # noqa: E402


def revalidate_answer(ans: dict[str, Any], registry: set[str], dois: dict[str, str], nli: Any) -> dict[str, Any]:
    if not ans["sentences"]:
        return ans
    evidence = {
        e["label"]: Evidence(e["label"], e["text"], e["source_id"], e["page"], dois.get(e["source_id"]))
        for e in ans["evidence"]
    }
    for t in ans["tools"]:
        evidence[t["label"]] = Evidence(t["label"], t["text"], None, None)
    draft = [DraftSentence(s["text"], s["citations"], s["category_in"]) for s in ans["sentences"]]
    rep = validate(draft, evidence, registry, dois, nli)
    out = dict(ans)
    out["sentences"] = [
        {"text": c.text, "citations": c.citations, "category_in": c.category_in, "category_out": c.category_out,
         "verdict": c.verdict, "checks": c.checks, "reasons": c.reasons, "entailment": c.entailment}
        for c in rep.sentences
    ]
    out["validation"] = {**rep.summary(), "nli_available": rep.nli_available}
    model_abstained = (ans.get("message") or "").startswith("The model reported insufficient evidence")
    if ans["status"] != "NO_LLM":
        out["status"] = "ABSTAINED" if (model_abstained or not rep.kept) else "ANSWERED"
    return out


def main(mode: str, demo: bool) -> None:
    path = HERE / "results" / f"{mode.lower()}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cp = get_copilot()
    rows = data["rows"]
    for r in rows:
        exp = set()
        r["answer"] = revalidate_answer(r["answer"], cp.registry, cp.registry_dois, cp.nli)
        a = r["answer"]
        label_src = {e["label"]: e["source_id"] for e in a["evidence"]}
        tool_labels = {t["label"] for t in a["tools"]}
        golden = {q["id"]: q for q in __import__("yaml").safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))["questions"]}
        q = golden[r["id"]]
        exp = set(q.get("expected_sources") or [])
        kept = [s for s in a["sentences"] if s["verdict"] != "REMOVED"]
        r["status"] = a["status"]
        r["n_drafted"], r["n_kept"] = len(a["sentences"]), len(kept)
        r["n_verified"] = sum(1 for s in a["sentences"] if s["verdict"] == "VERIFIED")
        r["n_removed"] = sum(1 for s in a["sentences"] if s["verdict"] == "REMOVED")
        r["n_well_cited"] = sum(
            1 for s in kept
            if (q.get("expect_tool") and any(c in tool_labels for c in s["citations"]))
            or any(label_src.get(c) in exp for c in s["citations"])
        )
        abstained = a["status"] in ("ABSTAINED", "NO_LLM")
        r["abstention_correct"] = abstained == r["must_abstain"]
    answerable = [r for r in rows if not r["must_abstain"]]
    drafted = sum(r["n_drafted"] for r in answerable)
    kept_n = sum(r["n_kept"] for r in answerable)
    s = data["summary"]
    s.update({
        "abstention_accuracy": wilson(sum(1 for r in rows if r["abstention_correct"]), len(rows)),
        "citation_correctness": wilson(sum(r["n_well_cited"] for r in answerable), kept_n),
        "verified_rate": wilson(sum(r["n_verified"] for r in answerable), drafted),
        "downgraded_rate": wilson(kept_n - sum(r["n_verified"] for r in answerable), drafted),
        "removed_rate": wilson(sum(r["n_removed"] for r in answerable), drafted),
        "revalidated_at": time.strftime("%Y-%m-%d %H:%M"),
    })
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "providers"}, indent=1))
    if demo:
        demo_rows = [r["answer"] | {"eval_id": r["id"], "run_at": s["run_at"]} for r in rows]
        (REPO / "frontend" / "public" / "data" / "copilot_demo.json").write_text(
            json.dumps({"summary": s, "answers": demo_rows}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LOCAL", "--demo" in sys.argv)
