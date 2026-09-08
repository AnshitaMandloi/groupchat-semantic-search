"""
Runs all queries in data/queries.json against the search engine and reports:
- top-1 accuracy (correct message ranked #1)
- top-5 accuracy (correct message anywhere in top 5)
- context-hit rate (correct message appears somewhere in the returned context,
  e.g. because it's in the same decision thread as the top hit)
Broken down by query_type, and separately for the no_word_overlap subset
(the queries that are the actual point of this project).
"""
import json
import sys
from engine import SearchEngine

CORPUS_PATH = "../data/corpus.json"
QUERIES_PATH = "../data/queries.json"


def run_eval(top_k=5, verbose=True):
    eng = SearchEngine(CORPUS_PATH)
    with open(QUERIES_PATH, encoding="utf-8") as f:
        queries = json.load(f)

    rows = []
    for q in queries:
        out = eng.search(q["query"], top_k=top_k)
        result_ids = [r["message"]["id"] for r in out["results"]]
        top1_hit = len(result_ids) > 0 and result_ids[0] == q["answer_message_id"]
        top5_hit = q["answer_message_id"] in result_ids

        context_hit = top5_hit
        if not context_hit:
            for r in out["results"]:
                ctx_ids = [m["id"] for m in r["context"]["messages"]]
                if q["answer_message_id"] in ctx_ids:
                    context_hit = True
                    break

        rows.append({
            "query": q["query"],
            "query_type": q["query_type"],
            "no_word_overlap": q["no_word_overlap"],
            "answer_message_id": q["answer_message_id"],
            "detected_type": out["detected_type"],
            "top1_hit": top1_hit,
            "top5_hit": top5_hit,
            "context_hit": context_hit,
            "top1_result_text": out["results"][0]["message"]["text"] if out["results"] else None,
        })

    return rows, eng.embed_mode


def summarize(rows, embed_mode):
    def pct(vals):
        return 100.0 * sum(vals) / len(vals) if vals else 0.0

    print(f"\n=== EVAL SUMMARY (embed_mode={embed_mode}) ===")
    print(f"Total queries: {len(rows)}")
    print(f"Overall  top-1: {pct([r['top1_hit'] for r in rows]):.1f}%  "
          f"top-5: {pct([r['top5_hit'] for r in rows]):.1f}%  "
          f"context-hit: {pct([r['context_hit'] for r in rows]):.1f}%")

    for qtype in ["semantic", "attributed", "temporal"]:
        sub = [r for r in rows if r["query_type"] == qtype]
        if not sub:
            continue
        print(f"\n[{qtype}] n={len(sub)}  "
              f"top-1: {pct([r['top1_hit'] for r in sub]):.1f}%  "
              f"top-5: {pct([r['top5_hit'] for r in sub]):.1f}%  "
              f"context-hit: {pct([r['context_hit'] for r in sub]):.1f}%")

    no_overlap = [r for r in rows if r["no_word_overlap"]]
    print(f"\n[NO WORD OVERLAP subset] n={len(no_overlap)}  "
          f"top-1: {pct([r['top1_hit'] for r in no_overlap]):.1f}%  "
          f"top-5: {pct([r['top5_hit'] for r in no_overlap]):.1f}%  "
          f"context-hit: {pct([r['context_hit'] for r in no_overlap]):.1f}%")

    print("\n--- Failures (top-5 miss) ---")
    for r in rows:
        if not r["top5_hit"]:
            print(f"  [{r['query_type']}{'*' if r['no_word_overlap'] else ''}] "
                  f"{r['query']!r} -> got {r['top1_result_text']!r}")


if __name__ == "__main__":
    rows, embed_mode = run_eval()
    summarize(rows, embed_mode)
    with open("../data/eval_results.json", "w", encoding="utf-8") as f:
        json.dump({"embed_mode": embed_mode, "rows": rows}, f, ensure_ascii=False, indent=1)
