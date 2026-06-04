#!/usr/bin/env python3
"""Search via MCP tool chroma_query_documents."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from config import CHROMA_PATH, COLLECTION_NAME, MCP_TOOL, TEXT_PREVIEW_LEN
from mcp_chroma import distance_to_score, query_documents


def format_results(query: str, k: int, payload: dict) -> None:
    ids = payload.get("ids", [[]])[0]
    documents = payload.get("documents", [[]])[0]
    metadatas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]

    print(f"MCP tool: {MCP_TOOL}")
    print(f"Query: {query}")
    print(f"Top-k: {k}\n")

    if not ids:
        print("No results found.")
        return

    for rank, (chunk_id, doc, meta, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        meta = meta or {}
        print(
            f"{rank}. document_id={meta.get('document_id', '?')}, "
            f"chunk_id={chunk_id}, score={distance_to_score(distance)}, distance={distance}"
        )
        print(f"   source={meta.get('source', '?')}")
        if meta.get("section"):
            print(f"   section={meta['section']}")
        preview = (doc or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}\n")


async def run_search(query: str, k: int, chroma_path: Path) -> None:
    if not chroma_path.is_dir():
        raise SystemExit(f"Index not found. Run: python src/ingest.py --reset")

    payload = await query_documents(chroma_path, query, k)
    format_results(query, k, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP search demo")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--chroma-path", type=Path, default=CHROMA_PATH)
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    asyncio.run(run_search(args.query, args.k, args.chroma_path))


if __name__ == "__main__":
    main()
