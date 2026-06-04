#!/usr/bin/env python3
"""Run evaluation queries through MCP search."""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from config import (
    CHROMA_PATH,
    EVAL_QUERIES,
    EVAL_REPORT,
    EVAL_RESULTS,
    MCP_TOOL,
)
from mcp_chroma import distance_to_score, query_documents_batch


def parse_expected(raw: str) -> set[str]:
    raw = (raw or "").strip()
    if not raw or raw.lower() == "none":
        return set()
    return {x.strip() for x in raw.split("|") if x.strip()}


def hits_from_payload(payload: dict) -> list[dict]:
    ids = payload.get("ids", [[]])[0]
    metadatas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]
    return [
        {
            "document_id": (meta or {}).get("document_id", ""),
            "chunk_id": chunk_id,
            "source": (meta or {}).get("source", ""),
            "score": distance_to_score(distance),
        }
        for chunk_id, meta, distance in zip(ids, metadatas, distances)
    ]


def judge_hit(expected: set[str], hits: list[dict]) -> tuple[str, str, str]:
    if not hits:
        return "", "no", "no results returned"

    first = hits[0]
    first_str = f"{first['document_id']}/{first['chunk_id']}"

    if not expected:
        if (first.get("score") or 0) < 0.55:
            return first_str, "yes", "low relevance score — good negative"
        return first_str, "no", "irrelevant doc ranked too high for out-of-corpus query"

    if expected & {h["document_id"] for h in hits}:
        matched = expected & {h["document_id"] for h in hits}
        return first_str, "yes", f"expected doc in top-3: {', '.join(sorted(matched))}"

    return first_str, "no", f"expected {expected}, got {first['document_id']}"


def build_result_row(row: dict, k: int, payload: dict) -> dict:
    hits = hits_from_payload(payload)
    first_str, in_top3, comment = judge_hit(
        parse_expected(row.get("expected_document_id", "")), hits
    )
    return {
        "id": row.get("id", ""),
        "query_type": row.get("query_type", ""),
        "query": row["query"],
        "expected_document_id": row.get("expected_document_id", ""),
        "first_hit": first_str,
        "top3_hits": "; ".join(
            f"{h['document_id']}/{h['chunk_id']}({h['score']})" for h in hits
        ),
        "in_top3": in_top3,
        "manual_judgement": in_top3,
        "comment": comment,
        "mcp_tool": MCP_TOOL,
        "notes": row.get("notes", ""),
    }


def write_results(path: Path, rows: list[dict]) -> None:
    EVAL_DIR = path.parent
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict], k: int) -> None:
    yes = sum(1 for r in rows if r["in_top3"] == "yes")
    lines = [
        "# Evaluation Report",
        "",
        f"MCP tool: `{MCP_TOOL}`, top-k={k}, English queries.",
        "",
        f"**Summary:** {yes}/{len(rows)} queries with expected document in top-{k}.",
        "",
        "Regenerate: `python src/run_eval.py`. Raw rows: `eval/results.csv`.",
        "",
        "| # | Type | Query | Expected | First hit | In top-3 | Comment |",
        "|---|------|-------|----------|-----------|----------|---------|",
    ]
    for r in rows:
        q = r["query"][:57] + "..." if len(r["query"]) > 60 else r["query"]
        lines.append(
            f"| {r['id']} | {r['query_type']} | {q} | {r['expected_document_id']} | "
            f"{r['first_hit']} | {r['in_top3']} | {r['comment']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(
    chroma_path: Path,
    queries_path: Path,
    results_path: Path,
    report_path: Path,
    k: int,
) -> None:
    if not chroma_path.is_dir():
        raise SystemExit("chroma_db missing. Run: python src/ingest.py --reset")

    with queries_path.open(encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))

    print(f"Running {len(rows_in)} queries via MCP ({MCP_TOOL}), k={k} ...")
    payloads = await query_documents_batch(
        chroma_path, [(r["query"], k) for r in rows_in]
    )
    results = [build_result_row(r, k, p) for r, p in zip(rows_in, payloads)]

    write_results(results_path, results)
    write_report(report_path, results, k)
    yes = sum(1 for r in results if r["in_top3"] == "yes")
    print(f"\nDone: {yes}/{len(results)} in top-{k}")
    print(f"  {results_path}\n  {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MCP search")
    parser.add_argument("--queries", type=Path, default=EVAL_QUERIES)
    parser.add_argument("--output", type=Path, default=EVAL_RESULTS)
    parser.add_argument("--report", type=Path, default=EVAL_REPORT)
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
