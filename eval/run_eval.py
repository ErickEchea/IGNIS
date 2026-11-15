"""Evaluate the Scientific Copilot on the golden set.

Metrics (each with a Wilson 95% interval):
- abstention accuracy: abstains on must-abstain questions and answers the others;
- citation correctness: share of kept sentences (answerable questions) that cite an expected source
  or, for tool questions, a Core tool result;
- validator acceptance (faithfulness proxy): share of drafted sentences that survive validation;
- retrieval recall@8: an expected source appears among the retrieved chunks.

Usage (from backend/): uv run python ../eval/run_eval.py LOCAL|CLOUD|NONE [--demo]
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from ignis.ai.engine import get_copilot
from ignis.settings import LLMMode

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(p, 3), round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def main(mode_name: str, demo: bool) -> None:
    mode = LLMMode(mode_name)
    golden = yaml.safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))["questions"]
    cp = get_copilot()
    rows: list[dict[str, Any]] = []
    for q in golden:
        t0 = time.time()
        out = cp.answer(q["question"], mode)
        exp = set(q.get("expected_sources") or [])
        must_abstain = bool(q.get("must_abstain"))
        kept = [s for s in out["sentences"] if s["verdict"] != "REMOVED"]
        label_src = {e["label"]: e["source_id"] for e in out["evidence"]}
        tool_labels = {t["label"] for t in out["tools"]}

        def well_cited(s: dict[str, Any], exp: set[str] = exp, q: dict[str, Any] = q) -> bool:
            if q.get("expect_tool") and any(c in tool_labels for c in s["citations"]):
                return True
            return any(label_src.get(c) in exp for c in s["citations"])

        abstained = out["status"] in ("ABSTAINED", "NO_LLM")
        rows.append({
            "id": q["id"], "question": q["question"], "status": out["status"], "must_abstain": must_abstain,
            "abstention_correct": abstained == must_abstain if mode != LLMMode.NONE else None,
            "n_drafted": len(out["sentences"]), "n_kept": len(kept),
            "n_well_cited": sum(1 for s in kept if well_cited(s)),
            "retrieval_hit": (bool(exp & set(label_src.values())) if exp else None),
            "provider": out.get("provider"), "attempts": out.get("attempts"),
            "latency_s": round(time.time() - t0, 2), "answer": out,
        })
        print(f"{q['id']} {out['status']:<10} kept {len(kept)}/{len(out['sentences'])} "
              f"{rows[-1]['latency_s']:>6.1f}s {q['question'][:60]}")
    answerable = [r for r in rows if not r["must_abstain"]]
    ab = [r for r in rows if r["abstention_correct"] is not None]
    drafted = sum(r["n_drafted"] for r in answerable)
    kept = sum(r["n_kept"] for r in answerable)
    cited = sum(r["n_well_cited"] for r in answerable)
    ret = [r for r in answerable if r["retrieval_hit"] is not None]
    summary = {
        "mode": mode.value,
        "n_questions": len(rows),
        "abstention_accuracy": wilson(sum(1 for r in ab if r["abstention_correct"]), len(ab)) if ab else None,
        "citation_correctness": wilson(cited, kept),
        "validator_acceptance": wilson(kept, drafted),
        "retrieval_recall_at_8": wilson(sum(1 for r in ret if r["retrieval_hit"]), len(ret)),
        "median_latency_s": sorted(r["latency_s"] for r in rows)[len(rows) // 2],
        "providers": sorted({(r["provider"] or {}).get("model", "none") for r in rows}),
        "run_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{mode.value.lower()}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    if demo:
        demo_rows = [r["answer"] | {"eval_id": r["id"], "run_at": summary["run_at"]} for r in rows]
        (REPO / "frontend" / "public" / "data" / "copilot_demo.json").write_text(
            json.dumps({"summary": summary, "answers": demo_rows}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LOCAL", "--demo" in sys.argv)
