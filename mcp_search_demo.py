#!/usr/bin/env python3
"""
Manual demo: search via official chroma-mcp server (MCP tool chroma_query_documents).

Prerequisites:
  1. python ingest.py --reset
  2. uvx available (or: pip install chroma-mcp)
  3. mcp_config.json points --data-dir to ./chroma_db

Usage:
    python mcp_search_demo.py --query "What is spoofing?" --k 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "market_manipulation_kb"
MCP_TOOL = "chroma_query_documents"
TEXT_PREVIEW_LEN = 280


def distance_to_score(distance: float | None) -> float | None:
    if distance is None:
        return None
    return round(1.0 - distance, 4)


def format_results(query: str, k: int, payload: dict) -> None:
    ids = payload.get("ids", [[]])[0]
    documents = payload.get("documents", [[]])[0]
    metadatas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]

    print(f"MCP tool: {MCP_TOOL}")
    print(f"Query: {query}")
    print(f"Top-k: {k}")
    print()

    if not ids:
        print("No results found.")
        return

    for rank, (chunk_id, doc, meta, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        meta = meta or {}
        score = distance_to_score(distance)
        document_id = meta.get("document_id", "?")
        source = meta.get("source", "?")
        section = meta.get("section", "")

        print(
            f"{rank}. document_id={document_id}, chunk_id={chunk_id}, "
            f"score={score}, distance={distance}"
        )
        print(f"   source={source}")
        if section:
            print(f"   section={section}")
        preview = (doc or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}")
        print()


async def run_search(query: str, k: int, chroma_path: Path, collection: str) -> None:
    if not chroma_path.is_dir():
        raise SystemExit(
            f"Index not found at {chroma_path}. Run: python ingest.py --reset"
        )

    server_params = StdioServerParameters(
        command="uvx",
        args=[
            "chroma-mcp",
            "--client-type",
            "persistent",
            "--data-dir",
            str(chroma_path.resolve()),
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                MCP_TOOL,
                {
                    "collection_name": collection,
                    "query_texts": [query],
                    "n_results": k,
                    "include": ["documents", "metadatas", "distances"],
                },
            )

    raw = result.content[0].text
    payload = json.loads(raw)
    format_results(query, k, payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search knowledge base via chroma-mcp (MCP)"
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--k", type=int, default=3, help="Number of results")
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=CHROMA_PATH,
        help="Chroma persistence directory",
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help=f"Collection name (default: {COLLECTION_NAME})",
    )
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    asyncio.run(
        run_search(
            query=args.query,
            k=args.k,
            chroma_path=args.chroma_path,
            collection=args.collection,
        )
    )


if __name__ == "__main__":
    main()
