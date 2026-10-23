"""Evaluate retrieval (and optionally answers) on eval/questions.jsonl.

  python eval/run_eval.py                 # compare bm25 vs vector vs hybrid retrieval
  python eval/run_eval.py --answers       # also generate answers (costs API calls)

Results print as a table and are saved to eval/results/.
Questions with an empty "relevant" list are skipped for retrieval metrics,
so label them first with scripts/find_chunks.py.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from visarag.assistant import VisaAssistant  # noqa: E402
from visarag.metrics import hit_at_k, recall_at_k, reciprocal_rank, summarize  # noqa: E402

MODES = ["bm25", "vector", "hybrid"]   # only the ones available are evaluated


def load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_retrieval(assistant: VisaAssistant, questions: list[dict], k: int) -> dict:
    labeled = [q for q in questions if q.get("relevant")]
    if not labeled:
        print("No labeled questions yet. Add chunk IDs to 'relevant' (see scripts/find_chunks.py).")
        return {}
    print(f"Retrieval: {len(labeled)} labeled questions, top-{k}\n")
    report = {}
    for mode in [m for m in MODES if m in assistant.retrievers]:
        rows = []
        for q in labeled:
            ranked = [cid for cid, _ in assistant.retrievers[mode].search(q["question"])]
            rel = set(q["relevant"])
            rows.append({"hit": hit_at_k(ranked, rel, k), "recall": recall_at_k(ranked, rel, k),
                         "rr": reciprocal_rank(ranked, rel)})
        report[mode] = summarize(rows, k)

    if not assistant.use_llm:
        print("(search-only mode: add GEMINI_API_KEY to also evaluate vector and hybrid)\n")
    header = f"{'mode':<8}" + "".join(f"{m:>11}" for m in report["bm25"] if m != "n")
    print(header + "\n" + "-" * len(header))
    for mode, s in report.items():
        print(f"{mode:<8}" + "".join(f"{v:>11}" for m, v in s.items() if m != "n"))
    return report


def eval_answers(assistant: VisaAssistant, questions: list[dict]) -> dict:
    print("\nGenerating answers (hybrid)…")
    rows = []
    for q in questions:
        a = assistant.ask(q["question"], mode="hybrid")
        rows.append({
            "id": q["id"], "question": q["question"], "answer": a.text,
            "cited": a.cited, "sources": [s.chunk_id for s in a.sources],
            "has_citation": bool(a.cited), "latency_s": a.latency_s,
            "tokens": a.usage.get("total_tokens", 0),
            "out_of_scope": q.get("out_of_scope", False),
        })
    in_scope = [r for r in rows if not r["out_of_scope"]]
    summary = {
        "citation_rate": round(mean(r["has_citation"] for r in in_scope), 3) if in_scope else None,
        "avg_latency_s": round(mean(r["latency_s"] for r in rows), 2),
        "avg_tokens": round(mean(r["tokens"] for r in rows)),
    }
    print(json.dumps(summary, indent=2))
    print("Read the answers in the results file and mark each correct/incorrect by hand: "
          "that manual accuracy number is the one to put on your résumé.")
    return {"summary": summary, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--answers", action="store_true")
    args = parser.parse_args()

    questions = load_questions(Path(args.questions))
    assistant = VisaAssistant()
    result = {"retrieval": eval_retrieval(assistant, questions, args.k)}
    if args.answers:
        if not assistant.use_llm:
            sys.exit("--answers needs GEMINI_API_KEY in .env")
        result["answers"] = eval_answers(assistant, questions)

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
