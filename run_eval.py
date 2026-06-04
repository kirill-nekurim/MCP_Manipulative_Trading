#!/usr/bin/env python3
"""
Run evaluation queries through MCP search (chroma_query_documents).

Reads eval_queries.csv, writes eval_results.csv and eval_report.md.

Usage:
    python run_eval.py
    python run_eval.py --k 3 --queries eval_queries.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from mcp_chroma import MCP_TOOL, distance_to_score, query_documents_batch

PROJECT_ROOT = Path(__file__).parent
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
DEFAULT_QUERIES = PROJECT_ROOT / "eval_queries.csv"
DEFAULT_RESULTS = PROJECT_ROOT / "eval_results.csv"
DEFAULT_REPORT = PROJECT_ROOT / "eval_report.md"


def parse_expected(raw: str) -> set[str]:
    raw = (raw or "").strip()
    if not raw or raw.lower() == "none":
        return set()
    return {x.strip() for x in raw.split("|") if x.strip()}


def hits_from_payload(payload: dict) -> list[dict]:
    ids = payload.get("ids", [[]])[0]
    metadatas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]
    hits = []
    for chunk_id, meta, distance in zip(ids, metadatas, distances):
        meta = meta or {}
        hits.append(
            {
                "document_id": meta.get("document_id", ""),
                "chunk_id": chunk_id,
                "source": meta.get("source", ""),
                "section": meta.get("section", ""),
                "score": distance_to_score(distance),
                "distance": distance,
            }
        )
    return hits


def judge_hit(expected: set[str], hits: list[dict]) -> tuple[str, str, bool]:
    """Return (first_hit_str, in_top3 yes/no, auto_comment)."""
    if not hits:
        return "", "no", "no results returned"

    first = hits[0]
    first_str = f"{first['document_id']}/{first['chunk_id']}"

    if not expected:
        # negative query: pass if top doc is not a core manipulation doc with high score
        top_score = first.get("score") or 0
        if top_score < 0.55:
            return first_str, "yes", "low relevance score — good negative"
        return first_str, "no", "irrelevant doc ranked too high for out-of-corpus query"

    top_ids = {h["document_id"] for h in hits}
    if expected & top_ids:
        matched = expected & top_ids
        return first_str, "yes", f"expected doc in top-3: {', '.join(sorted(matched))}"

    return first_str, "no", f"expected {expected}, got {first['document_id']}"


def build_result_row(row: dict, k: int, payload: dict) -> dict:
    query = row["query"]
    expected = parse_expected(row.get("expected_document_id", ""))
    hits = hits_from_payload(payload)

    first_str, in_top3, auto_comment = judge_hit(expected, hits)
    top3_summary = "; ".join(
        f"{h['document_id']}/{h['chunk_id']}({h['score']})" for h in hits
    )

    return {
        "id": row.get("id", ""),
        "query_type": row.get("query_type", ""),
        "query": query,
        "expected_document_id": row.get("expected_document_id", ""),
        "first_hit": first_str,
        "top3_hits": top3_summary,
        "in_top3": in_top3,
        "manual_judgement": in_top3,
        "comment": auto_comment,
        "mcp_tool": MCP_TOOL,
        "notes": row.get("notes", ""),
    }


def write_results(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict], k: int) -> None:
    yes = sum(1 for r in rows if r["in_top3"] == "yes")
    total = len(rows)
    lines = [
        "# Evaluation Report — Market Manipulation KB",
        "",
        f"Search: MCP tool `{MCP_TOOL}`, top-k={k}, queries in English (Chroma embedding: all-MiniLM-L6-v2).",
        "",
        f"**Summary:** {yes}/{total} queries with expected hit in top-{k} (`in_top3=yes`).",
        "",
        "Review `manual_judgement` and `comment` — adjust if you disagree with auto labels.",
        "",
        "| # | Type | Query | Expected | First hit | Top-3 | In top-3 | Comment |",
        "|---|------|-------|----------|-----------|-------|----------|---------|",
    ]
    for r in rows:
        q = r["query"].replace("|", "\\|")
        if len(q) > 60:
            q = q[:57] + "..."
        lines.append(
            f"| {r['id']} | {r['query_type']} | {q} | {r['expected_document_id']} | "
            f"{r['first_hit']} | {r['in_top3']} | {r['manual_judgement']} | {r['comment']} |"
        )
    lines.extend(
        [
            "",
            "## How to reproduce",
            "",
            "```bash",
            "python ingest.py --reset",
            "python run_eval.py",
            "```",
            "",
            "Results: `eval_results.csv`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(
    chroma_path: Path,
    queries_path: Path,
    results_path: Path,
    report_path: Path,
    k: int,
) -> None:
    if not chroma_path.is_dir():
        raise SystemExit("chroma_db missing. Run: python ingest.py --reset")

    with queries_path.open(encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))

    print(f"Running {len(rows_in)} queries via MCP ({MCP_TOOL}), k={k} ...")
    payloads = await query_documents_batch(
        chroma_path, [(row["query"], k) for row in rows_in]
    )
    results = []
    for row, payload in zip(rows_in, payloads):
        print(f"  [{row.get('id')}] {row['query'][:50]}...")
        results.append(build_result_row(row, k, payload))

    write_results(results_path, results)
    write_report(report_path, results, k)
    yes = sum(1 for r in results if r["in_top3"] == "yes")
    print(f"\nDone: {yes}/{len(results)} in top-{k}")
    print(f"  {results_path}")
    print(f"  {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MCP search quality")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--chroma-path", type=Path, default=CHROMA_PATH)
    args = parser.parse_args()

    asyncio.run(
        main_async(
            args.chroma_path,
            args.queries,
            args.output,
            args.report,
            args.k,
        )
    )


if __name__ == "__main__":
    main()
