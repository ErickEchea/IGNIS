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
from run_eval import score_row, summarize  # noqa: E402


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
    golden = {q["id"]: q for q in __import__("yaml").safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))["questions"]}
    for r in rows:
        r["answer"] = revalidate_answer(r["answer"], cp.registry, cp.registry_dois, cp.nli)
        score_row(r, golden[r["id"]])
    run_at = data["summary"].get("run_at")
    s = summarize(rows, data["summary"]["mode"])
    s["run_at"] = run_at
    s["revalidated_at"] = time.strftime("%Y-%m-%d %H:%M")
    data["summary"] = s
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "providers"}, indent=1))
    if demo:
        demo_rows = [r["answer"] | {"eval_id": r["id"], "run_at": s["run_at"]} for r in rows]
        (REPO / "frontend" / "public" / "data" / "copilot_demo.json").write_text(
            json.dumps({"summary": s, "answers": demo_rows}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LOCAL", "--demo" in sys.argv)
